"""Experiment lab: run queued experiments on this machine and publish the results through git.

Claude (or anyone) queues an experiment as `lab/queue/<name>.json` and pushes it. A machine
running `lab.py watch` pulls, runs every queued experiment that has no result yet, writes
`lab/results/<name>.md` (readable report) and `<name>.json` (data), commits only those two files
and pushes them. The Discord ops bot (deploy/ops_bot.py) posts new results to the channel, so
nobody copies commands or pastes reports.

Experiment kinds (`"kind"` in the queue file):
  ab        teacher_ab match. Keys: teacher_a, teacher_b, pairs (default 12; fresh seeds come
            from lab/seeds.txt, scanned for more when it runs short, the experiment waits if the
            scan finds none) or seeds (explicit list), comparisons (default 2), note,
            stop_round (default 3: games end when round 4 starts; 0 or null plays to the end),
            vp_rate (charges per VP held in the verdict table; default 1.5, 0 leaves VP out).
  command   any command run from gaia-rl/ (e.g. a future PPO-checkpoint evaluation). Keys: run
            (argv list), metrics (optional JSON file the command writes), timeout_hours, note.
  external  run elsewhere (e.g. Seraph PPO). Never run here; its result is added with
            `lab.py record`, which also accepts results without a queue file.
  review    a second model (OpenAI Codex CLI, GAIA_LAB_REVIEW_MODEL, default gpt-6-astra) reviews
            code, read-only. Keys: commits ("old..new": the diff), paths (files to read in full),
            result (an ab result name: attack its verdict), prompt (extra instructions),
            timeout_minutes (default 30), note. Its text is published verbatim under a '🔍'
            notice; the Discord bot answers it (fix or rebut). `watch` queues one automatically
            for every pull that changes code files, and every ab result carries a review of its
            verdict (key review: false skips it).

  .venv/bin/python tools/lab.py watch --jobs 4        # laptop: keep running (tmux/nohup)
  .venv/bin/python tools/lab.py once --jobs 4         # run what is pending, then exit
  .venv/bin/python tools/lab.py status
  .venv/bin/python tools/lab.py record NAME --metrics m.json [--summary s.md] [--push]
  .venv/bin/python tools/lab.py notify "text"         # Discord webhook, if configured

Environment: GAIA_LAB_BRANCH (default claude/epic-goodall-0ot55w), GAIA_LAB_WEBHOOK (optional
Discord webhook URL for start/failure notices; results reach Discord through the ops bot),
GAIA_LAB_CODEX (codex binary; default: codex on PATH), GAIA_LAB_REVIEW_MODEL (default gpt-6-astra),
GAIA_LAB_DIR (tests only).
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request

GAIA_RL = Path(__file__).resolve().parents[1]
LAB = Path(os.environ.get('GAIA_LAB_DIR') or GAIA_RL/'lab')
BRANCH = os.environ.get('GAIA_LAB_BRANCH', 'claude/epic-goodall-0ot55w')
KINDS = ('ab', 'command', 'external', 'review')


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


# ── queue and results ───────────────────────────────────────────────────────

_broken = {}  # path -> error, for files that are not valid JSON (e.g. cut short by a full disk)


def read_json(path):
    """A JSON file's value, or None (recorded in _broken) when it is empty or cut short."""
    try:
        value = json.loads(path.read_text())
    except ValueError as error:
        _broken[str(path)] = str(error)
        return None
    _broken.pop(str(path), None)
    return value


def queue():
    """[(name, spec)] in name order; a file whose name starts with '_' is ignored."""
    items = []
    for path in sorted((LAB/'queue').glob('*.json')):
        if path.name.startswith('_'):
            continue
        spec = read_json(path)
        if spec is None:
            continue
        if spec.get('kind', 'ab') not in KINDS:
            raise ValueError(f'{path.name}: unknown kind {spec.get("kind")!r}')
        items.append((path.stem, spec))
    return items


def result(name):
    path = LAB/'results'/f'{name}.json'
    # An unreadable result counts as missing, so the experiment runs again and rewrites it.
    return read_json(path) if path.exists() else None


def pending():
    return [(name, spec) for name, spec in queue() if result(name) is None]


def used_seeds():
    used = set()
    for path in (LAB/'results').glob('*.json'):
        used.update((read_json(path) or {}).get('seeds', ()))
    for _, spec in queue():
        used.update(spec.get('seeds', ()))
    return used


def fresh_seeds():
    """Seeds of lab/seeds.txt that no result or queued experiment has used, in file order."""
    used = used_seeds()
    lines = (LAB/'seeds.txt').read_text().splitlines()
    return [s.strip() for s in lines if s.strip() and not s.startswith('#') and s.strip() not in used]


def allocate(count):
    fresh = fresh_seeds()
    if len(fresh) < count:
        raise RuntimeError(f'lab/seeds.txt has {len(fresh)} unused seeds, {count} needed; add more '
                           '(tools/scan_seeds.py --files lab/seeds.txt ...)')
    return fresh[:count]


SCAN_WINDOW, SCAN_WINDOWS = 40000, 5  # about 20 hits a window, 50 s at 4 jobs
_scanned_to = {}  # experiment -> first seed number not yet scanned for it


def scan_seeds(start, count, jobs):
    """Append fresh seeds for the lab/seeds.txt lineup (tools/scan_seeds.py); returns the hits added."""
    done = subprocess.run([sys.executable, 'tools/scan_seeds.py', '--files', str(LAB/'seeds.txt'),
                           '--start', str(start), '--count', str(count), '--jobs', str(jobs)],
                          cwd=GAIA_RL, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f'scan_seeds failed: {(done.stderr or done.stdout).strip()[-500:]}')
    hits = done.stdout.rsplit('+', 1)[-1].split()[0] if '+' in done.stdout else '0'  # "...: prefix [...] +N (a-b)"
    return int(hits) if hits.isdigit() else 0


def ensure_seeds(name, count, jobs, push):
    """Fresh seeds for an experiment, scanning more when the file runs short (user 2026-10-21
    "실험을 왜 건너뛰게 하지?": refill, never drop the experiment). None when still short after the
    scan windows: the caller holds the experiment and retries next loop."""
    fresh = fresh_seeds()
    if len(fresh) >= count:
        return fresh[:count]
    lines = [s.strip() for s in (LAB/'seeds.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
    numbers = [int(s.rsplit('-', 1)[-1]) for s in lines if s.rsplit('-', 1)[-1].isdigit()]
    start, added = max(max(numbers)+1 if numbers else 0, _scanned_to.get(name, 0)), 0
    for _ in range(SCAN_WINDOWS):
        print(f'[{now()}] {name}: {len(fresh)} unused seeds, {count} needed; scanning {start}-{start+SCAN_WINDOW}', flush=True)
        added += scan_seeds(start, SCAN_WINDOW, jobs)
        start = _scanned_to[name] = start+SCAN_WINDOW  # a held experiment scans new ground next loop
        fresh = fresh_seeds()
        if len(fresh) >= count:
            break
    if added:
        notify(f'🌱 lab: seeds.txt +{added} (자동 스캔, {name}에 {count}개 필요)')
        if push:
            publish([LAB/'seeds.txt'], f'lab: seeds +{added} for {name}')
    return fresh[:count] if len(fresh) >= count else None


# ── git and notices ─────────────────────────────────────────────────────────

def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=GAIA_RL, capture_output=True, text=True, check=check)


def commit_id():
    return git('rev-parse', '--short', 'HEAD', check=False).stdout.strip()


def ensure_identity():
    """Commits and rebases need a git identity; a host without one gets a repo-local gaia-lab."""
    if not git('config', 'user.email', check=False).stdout.strip():
        git('config', 'user.name', 'gaia-lab')
        git('config', 'user.email', f'gaia-lab@{platform.node() or "host"}')


def commit(message):
    ensure_identity()
    git('commit', '-m', message)


def pull():
    """Update from the branch, keeping any local result commits on top (a push may have failed).

    Results a crashed run left uncommitted (e.g. a failed commit) are committed first."""
    ensure_identity()
    specs = tracked_specs()
    if specs and git('status', '--porcelain', '--', *specs, check=False).stdout.strip():
        git('add', '--', *specs)
        commit('lab: results (recovered)')
    out = git('pull', '--rebase', 'origin', BRANCH, check=False)
    if out.returncode:
        git('rebase', '--abort', check=False)
        raise RuntimeError(f'git pull failed: {out.stderr.strip()[-500:]}')
    ahead = git('rev-list', '--count', f'origin/{BRANCH}..HEAD', check=False).stdout.strip()
    if ahead not in ('', '0') and git('push', 'origin', f'HEAD:{BRANCH}', check=False).returncode:
        raise RuntimeError(f'{ahead} result commit(s) not pushed: check push credentials')


# Everything the native extension is built from (paths from the repository root).
BUILD_INPUTS = ('gaia-engine', 'gaia-rl/src', 'gaia-rl/Cargo.toml', 'gaia-rl/Cargo.lock', 'gaia-rl/build.rs')


def ensure_built():
    """Rebuild the engine extension when a pull changed its sources (stamp in runs/)."""
    tree = git('rev-parse', *[f'HEAD:{p}' for p in BUILD_INPUTS], check=False).stdout.split()
    stamp = GAIA_RL/'runs'/'.lab-build'
    if stamp.exists() and stamp.read_text().split() == tree:
        return
    print(f'[{now()}] engine sources changed: rebuilding', flush=True)
    venv = GAIA_RL/'.venv'
    out = subprocess.run([str(venv/'bin'/'maturin'), 'develop', '--release'], cwd=GAIA_RL,
                         env={**os.environ, 'VIRTUAL_ENV': str(venv)}, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f'engine rebuild failed: {out.stderr.strip()[-800:]}')
    stamp.parent.mkdir(exist_ok=True)
    stamp.write_text(' '.join(tree)+'\n')


def tracked_specs():
    """Git pathspecs of everything the lab writes: results and the seed files (a scan, queued as a
    command or run by ensure_seeds, appends to tracked seed files; left unstaged they block pull)."""
    if not LAB.is_relative_to(GAIA_RL):
        return []
    lab = LAB.relative_to(GAIA_RL)
    return [str(lab/'results'), str(lab/'seeds*.txt')]


def publish(paths, message):
    git('add', '--', *map(str, paths), *tracked_specs())
    if not git('diff', '--cached', '--quiet', check=False).returncode:
        return
    commit(message)
    for attempt in range(5):
        git('pull', '--rebase', 'origin', BRANCH, check=False)
        if not git('push', 'origin', f'HEAD:{BRANCH}', check=False).returncode:
            return
        time.sleep(2**(attempt+1))
    raise RuntimeError('git push failed 5 times; results are committed locally')


def _width(text):
    """Display columns in a monospace font: Hangul and other wide characters take two."""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def discord_text(markdown):
    """A result page as Discord text: Discord has no tables, so tables become aligned code blocks
    (first four columns: what, pairs, difference, interval) and the footer tag is dropped."""
    out, table = [], []

    def flush():
        if table:
            rows = [[c.strip().replace('**', '') for c in row.strip('|').split('|')][:4] for row in table]
            widths = [max(_width(r[i]) if i < len(r) else 0 for r in rows) for i in range(4)]
            out.append('```')
            out.extend('  '.join(c+' '*(widths[i]-_width(c)) for i, c in enumerate(r)).rstrip() for r in rows)
            out.append('```')
            table.clear()
    for line in markdown.splitlines():
        if line.startswith('|'):
            if not set(line) <= set('|-: '):
                table.append(line)
            continue
        flush()
        out.append(line.replace('<sub>', '').replace('</sub>', ''))
    flush()
    return '\n'.join(out).strip()


def chunks(text, size=1900):
    """Split on line boundaries under Discord's 2000-character limit, keeping code blocks closed."""
    parts, current, fenced = [], [], False
    for line in text.splitlines():
        if current and sum(len(l)+1 for l in current)+len(line) > size:
            parts.append('\n'.join(current+(['```'] if fenced else [])))
            current = ['```'] if fenced else []
        current.append(line[:size])
        if line.startswith('```'):
            fenced = not fenced
    if current:
        parts.append('\n'.join(current))
    return parts


def notify(text):
    """Post to the Discord webhook if one is configured; never fails the caller."""
    url = os.environ.get('GAIA_LAB_WEBHOOK')
    if not url:
        return
    for part in chunks(text):
        _post(url, part)


def _post(url, text):
    request = urllib.request.Request(url, data=json.dumps({'content': text}).encode(), method='POST',
                                     headers={'Content-Type': 'application/json',
                                              'User-Agent': 'gaia-lab (https://github.com, 1.0)'})
    try:
        urllib.request.urlopen(request, timeout=15).read()
    except Exception as error:  # a notice must never stop an experiment
        print(f'notify failed: {error}', file=sys.stderr)


# ── running ─────────────────────────────────────────────────────────────────

def timing(run_dir):
    seconds = {'A': [], 'B': []}
    for path in run_dir.glob('pair-*/game-*/decisions.jsonl.gz'):
        with gzip.open(path, 'rt') as rows:
            for line in rows:
                row = json.loads(line)
                if row.get('arm') in seconds and row.get('seconds') is not None:
                    seconds[row['arm']].append(row['seconds'])
    stats = {}
    for arm, values in seconds.items():
        if values:
            values.sort()
            n = len(values)
            stats[arm] = {'n': n, 'mean': sum(values)/n, 'median': statistics.median(values),
                          'p90': values[int(n*.9)], 'max': values[-1]}
    return stats


def final_scores(run_dir):
    """Mean final VP per faction and arm over completed games (absolute level, not just B−A)."""
    table = {}
    for path in run_dir.glob('pair-*/game-*/result.json'):
        result = json.loads(path.read_text())
        if not result.get('complete'):
            continue
        for seat, faction in enumerate(result['factions']):
            arm = 'A' if seat in result['a_seats'] else 'B'
            table.setdefault(faction, {'A': [], 'B': []})[arm].append(result['scores'][str(seat)])
    return table


def scores_table(table):
    rows = ['| 종족 | A 평균 총점 | B 평균 총점 | 최고 |', '|---|---:|---:|---:|']
    every = {'A': [], 'B': []}
    for faction in sorted(table):
        arms = table[faction]
        every['A'] += arms['A']
        every['B'] += arms['B']
        mean = {arm: f'{sum(v)/len(v):.1f}' if v else '—' for arm, v in arms.items()}
        rows.append(f"| {faction} | {mean['A']} | {mean['B']} | {max(arms['A']+arms['B'], default=0)} |")
    if every['A'] or every['B']:
        mean = {arm: f'{sum(v)/len(v):.1f}' if v else '—' for arm, v in every.items()}
        rows.append(f"| **전체** | {mean['A']} | {mean['B']} | {max(every['A']+every['B'], default=0)} |")
    return '\n'.join(rows)


def timing_table(stats):
    rows = ['| 팔 | 결정 수 | 평균 | 중앙값 | p90 | 최대 |', '|---|---:|---:|---:|---:|---:|']
    for arm, s in stats.items():
        rows.append(f"| {arm} | {s['n']} | {s['mean']:.2f}초 | {s['median']:.2f}초 | "
                    f"{s['p90']:.2f}초 | {s['max']:.1f}초 |")
    return '\n'.join(rows)


def charges(run_dir, env, vp_rate=None):
    """charge_rounds.py over the run: {'factions': {...}, 'games': [...]}, or {'error': ...}.

    User (2026-10-07): A/B results are judged only by charges gained in rounds 1-3.
    vp_rate: charges per VP held (None = the guide rate 1.5, 0 = VP left out)."""
    out = run_dir/('charges.json' if vp_rate is None else f'charges-vp{vp_rate:g}.json')
    extra = [] if vp_rate is None else ['--vp-rate', str(vp_rate)]
    done = subprocess.run([sys.executable, 'tools/charge_rounds.py', str(run_dir), '--json', str(out), *extra],
                          cwd=GAIA_RL, env=env, capture_output=True, text=True)
    if done.returncode or not out.exists():
        return {'error': (done.stderr or done.stdout).strip()[-800:]}
    return json.loads(out.read_text())


def charges_table(data):
    if 'error' in data:
        return f"충전량 계산 실패\n\n```\n{data['error']}\n```"
    rows = ['| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |', '|---|---:|---:|---|---:|---:|']
    for faction, r in data['factions'].items():
        low, high = r['ci95']
        a, b = (f"{r[arm]:.1f}" if arm in r else '' for arm in 'AB')
        name = '**전체 (좌석 평균)**' if faction == 'ALL' else faction
        rows.append(f"| {name} | {r['pairs']} | {r['mean_B_minus_A']:+.1f} | [{low:+.1f}, {high:+.1f}] | {a} | {b} |")
    return '\n'.join(rows)


def basics(run_dir, env):
    """basics_rounds.py over the run: {'factions': {...}} or {'error': ...} (E86 (ㄷ), secondary indicator)."""
    out = run_dir/'basics.json'
    done = subprocess.run([sys.executable, 'tools/basics_rounds.py', str(run_dir), '--json', str(out)],
                          cwd=GAIA_RL, env=env, capture_output=True, text=True)
    if done.returncode or not out.exists():
        return {'error': (done.stderr or done.stdout).strip()[-800:]}
    return json.loads(out.read_text())


def basics_table(data):
    if 'error' in data:
        return f"기본기 지표 계산 실패\n\n```\n{data['error']}\n```"
    quad = lambda d: '/'.join(f'{d[k]:.1f}' for k in ('ore', 'credits', 'knowledge', 'qic'))
    rows = ['| 종족 | 쌍 | 4R 보유 A → B (광/크/지/큐) | 1–3R 수입 A → B (광/크/지/큐) | 패스 전 건설 A → B | 패스 시 보유 A → B |',
            '|---|---:|---|---|---|---|']
    for faction, r in data['factions'].items():
        if not r['pairs']:
            rows.append(f"| {faction} | 0 | | | | |")
            continue
        a, b = r['A'], r['B']
        rows.append(f"| {faction} | {r['pairs']} | {quad(a['stock4'])} → {quad(b['stock4'])} | "
                    f"{quad(a['income'])} → {quad(b['income'])} | {a['pass_builds']:.1f} → {b['pass_builds']:.1f} | "
                    f"{a['pass_stock']:.1f} → {b['pass_stock']:.1f} |")
    return '\n'.join(rows)


REPLAY_DIR = Path(os.environ.get('GAIA_LAB_REPLAY_DIR') or '~/gaia-media/ai-replays').expanduser()


def watch_pick(seats):
    """The game to watch: the (pair, faction) with the largest charge gap between the arms, in the
    game where that faction gained less. -> (game, seat, label) or None.

    User (2026-10-09): every experiment publishes one replay worth looking at."""
    by_key = {}
    for game, rows in seats.items():
        for seat, row in enumerate(rows):
            by_key.setdefault((game.split('/')[0], row['faction']), {})[row['arm']] = (row['charges'], game, seat)
    gaps = [(abs(arms['B'][0]-arms['A'][0]), faction, arms)
            for (_, faction), arms in by_key.items() if len(arms) == 2]
    if not gaps:
        return None
    _, faction, arms = max(gaps, key=lambda g: g[0])
    low, high = sorted(arms.values(), key=lambda v: v[0])
    low_arm = 'A' if arms['A'] is low else 'B'
    label = f'{faction} {low_arm}팔 충전 {low[0]:.0f} (상대 팔 {high[0]:.0f})'
    return low[1], low[2], label


def publish_watch_replay(name, run_dir, env, data):
    """Export and publish the watch_pick game; a failure is reported, never fatal."""
    pick = watch_pick(data.get('seats') or {})
    if pick is None:
        return '다시보기: 고를 판 없음'
    game, seat, label = pick
    source = run_dir/'watch-replay'
    steps = [['tools/ab_replays.py', 'export', str(run_dir/game), '--output', str(source),
              '--focus', str(seat)],
             ['tools/publish_replays.py', '--source', str(source), '--destination', str(REPLAY_DIR)]]
    for argv in steps:
        done = subprocess.run([sys.executable, *argv], cwd=GAIA_RL, env=env, capture_output=True, text=True)
        if done.returncode:
            return f"다시보기 게시 실패 ({game})\n\n```\n{(done.stderr or done.stdout).strip()[-600:]}\n```"
    return f'다시보기 게시: {game} 좌석 {seat} — {label}'


def fresh_dir(path):
    """A crashed earlier attempt leaves a partial directory; keep it aside, never reuse it."""
    if path.exists():
        path.rename(path.with_name(f'{path.name}.partial-{int(time.time())}'))
    return path


def tail(path, lines=40):
    try:
        return '\n'.join(Path(path).read_text(errors='replace').splitlines()[-lines:])
    except OSError:
        return ''


def run_ab(name, spec, jobs):
    try:  # teacher_ab needs scipy only for its final table; fail before hours of games
        import scipy.stats  # noqa: F401
    except ImportError:
        raise RuntimeError('scipy is missing: .venv/bin/pip install scipy') from None
    seeds = spec.get('seeds') or allocate(int(spec.get('pairs', 12)))
    out = fresh_dir(GAIA_RL/'runs'/f'lab-{name}')
    log = GAIA_RL/'runs'/f'lab-{name}.log'
    command = [sys.executable, 'tools/teacher_ab.py', 'run',
               '--teacher-a', spec['teacher_a'], '--teacher-b', spec['teacher_b'],
               '--games', str(2*len(seeds)), '--seeds', *seeds,
               '--comparisons', str(spec.get('comparisons', 2)),
               '--jobs', str(spec.get('jobs', jobs)), '--fast-copy', '--output', str(out)]
    stop_round = spec.get('stop_round', 3)  # user 2026-10-07: judged by rounds 1-3, so stop there
    if stop_round:
        command[-2:-2] = ['--stop-round', str(stop_round)]
    env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1',
           'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
    with open(log, 'w') as handle:
        code = subprocess.run(command, cwd=GAIA_RL, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode
    data = {'seeds': seeds, 'command': command[1:], 'exit_code': code}
    if code or not (out/'report.md').exists():
        return 'failed', data, f'teacher_ab 종료 코드 {code}\n\n```\n{tail(log)}\n```'
    summary = json.loads((out/'results.json').read_text())
    data['summary'] = {k: v for k, v in summary.items() if k != 'pairs'}
    data['timing'] = timing(out)
    data['final_scores'] = final_scores(out)
    vp_rate = spec.get('vp_rate')  # user 2026-10-08: judge by charges with VP held left out (0)
    data['charges'] = charges(out, env, vp_rate)
    data['basics'] = basics(out, env)
    reference = ''
    if vp_rate is not None:
        data['charges_vp1.5'] = charges(out, env)
        reference = f"참고: 1점 = 1.5충전으로 잰 충전량\n\n{charges_table(data['charges_vp1.5'])}\n\n"
    data['watch_replay'] = publish_watch_replay(name, out, env, data['charges'])
    reference += f"{data['watch_replay']}\n\n"
    rate = 1.5 if vp_rate is None else vp_rate
    scores_note = (f"{stop_round}라운드 종료 시점 VP 차이" if stop_round else "최종 점수 차이")
    body = (f"A: `{spec['teacher_a']}`\nB: `{spec['teacher_b']}`\n"
            f"시드 {len(seeds)}개 × 좌석 교대 2판 (비교 기본값 {spec.get('comparisons', 2)}, 스펙 파일에 있으면 그 값)"
            f"{f', {stop_round}라운드에서 종료' if stop_round else ''}\n\n"
            f"**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = {rate:g}충전\n\n"
            f"{charges_table(data['charges'])}\n\n{reference}"
            f"참고: 기본기 지표 (보조, 판정에 쓰지 않음) — 4R 시작 보유, 1–3R 수입, 라운드 1–3 패스 전 건설 수와 패스 시 보유\n\n"
            f"{basics_table(data['basics'])}\n\n결정 시간\n\n{timing_table(data['timing'])}\n\n"
            f"참고: 오류·미탐색 수와 {scores_note} (판정에 쓰지 않음)\n\n{(out/'report.md').read_text().strip()}")
    # User 2026-10-20 "결과에서 + -는 보이는데 최종 점수가 몇점인지 안보이던데": the absolute level per arm.
    level = f"{stop_round}라운드 종료 시점 VP" if stop_round else "최종 점수"
    body += f"\n\n참고: {level} 평균 (판정에 쓰지 않음)\n\n{scores_table(data['final_scores'])}"
    body += verdict_review(name, spec, body, data)  # the second model's attack on the verdict, verbatim
    return 'done', data, body


def run_command(name, spec, jobs):
    log = GAIA_RL/'runs'/f'lab-{name}.log'
    log.parent.mkdir(exist_ok=True)
    argv = [sys.executable if a == '{python}' else str(jobs) if a == '{jobs}' else a for a in spec['run']]
    timeout = float(spec.get('timeout_hours', 24))*3600
    with open(log, 'w') as handle:
        try:
            code = subprocess.run(argv, cwd=GAIA_RL, stdout=handle, stderr=subprocess.STDOUT,
                                  timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    data = {'command': argv, 'exit_code': code}
    metrics = spec.get('metrics') and GAIA_RL/spec['metrics']
    if metrics and metrics.exists():
        data['metrics'] = json.loads(metrics.read_text())
    status = 'done' if code == 0 else 'failed'
    body = f'종료 코드 {code}\n\n```\n{tail(log)}\n```'
    if 'metrics' in data:
        body += f"\n\n지표\n\n```json\n{json.dumps(data['metrics'], indent=1, ensure_ascii=False)[:3000]}\n```"
    return status, data, body


# ── Codex review ────────────────────────────────────────────────────────────
# User 2026-10-21 "최소한 다른 agent의 검수가 필요하지 않을까?" → "gpt는 astra로 하자": a second model reviews
# every A/B verdict and every code commit. Its text is published verbatim (the user reads the reviewer, not
# Claude's summary of it); the bot's Claude turn then fixes or rebuts each point, and a rebuttal is flagged
# "불일치" for the user to decide.

REVIEW_MODEL = os.environ.get('GAIA_LAB_REVIEW_MODEL', 'gpt-6-astra')
REVIEW_RULES = ('너는 이 저장소의 독립 검수자다. 한국어로, 휴대폰에서 읽을 수 있게 짧게 답한다. '
                '첫 줄은 반드시 `결론: 이상 없음` 또는 `결론: 지적 N건` 중 하나다. 지적마다 파일:줄, 무엇이 왜 틀렸는지, '
                '확인 방법을 적고, 확신이 없으면 "확인 필요"라고 표시한다. 스타일 지적은 쓰지 않는다. '
                '저장소는 읽기 전용이다: 파일을 고치지 말고 실험을 돌리지 마라.')
VERDICT = re.compile(r'^결론:\s*(이상 없음|지적\s*(\d+)\s*건)', re.M)
DIFF_LIMIT = 60000  # characters of diff put in the prompt; above it the reviewer runs git diff itself


def codex_bin():
    return os.environ.get('GAIA_LAB_CODEX') or shutil.which('codex')


def findings(text):
    """Findings the reviewer's first line claims: 0 for '결론: 이상 없음', None when the line is missing."""
    match = VERDICT.search(text or '')
    if not match:
        return None
    return int(match.group(2)) if match.group(2) else 0


def codex_review(prompt, timeout):
    """(reviewer text or None, failure note): one read-only `codex exec` over the repository, prompt on stdin."""
    codex = codex_bin()
    if not codex:
        return None, 'codex 미설치: lab 기계에서 `npm install -g @openai/codex` 뒤 `codex login`'
    root = git('rev-parse', '--show-toplevel').stdout.strip()
    out = GAIA_RL/'runs'/f'codex-{int(time.time())}.md'
    out.parent.mkdir(exist_ok=True)
    command = [codex, 'exec', '--model', REVIEW_MODEL, '--sandbox', 'read-only', '-c', 'approval_policy="never"',
               '--cd', root, '--color', 'never', '--output-last-message', str(out), '-']
    try:
        done = subprocess.run(command, cwd=root, input=prompt, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f'codex {timeout/60:.0f}분 제한 초과'
    text = out.read_text(errors='replace').strip() if out.exists() else ''
    if done.returncode or not text:
        return None, f'codex 종료 코드 {done.returncode}\n\n```\n{(done.stderr or done.stdout).strip()[-800:]}\n```'
    return text, ''


def verdict_prompt(name, spec, body):
    design = {k: v for k, v in spec.items() if k != 'seeds'}
    return (f'{REVIEW_RULES}\n\n과제: lab 실험 {name}의 A/B 결과를 반박하라. 이 저장소의 판정은 1–3라운드 충전량(B−A, '
            '95% 신뢰구간, 쌍 수)으로만 한다(최종 VP는 판정이 아니다; 읽을 수 있는 선은 종족당 25충전, 같은 코드의 흔들림은 '
            '종족당 ±30·쌍당 ±50). 아래 큐 파일의 사전 등록 판정(note)이 이 숫자로 정당화되는지, 신뢰구간·쌍 수·판 상태'
            '(오류·타임아웃·결정 시간)·측정 창·조건 불일치 가운데 판정을 뒤집거나 약하게 만드는 이유가 있는지 찾아라. '
            '숫자를 만드는 코드는 gaia-rl/tools/charge_rounds.py와 gaia-rl/tools/teacher_ab.py다.\n\n'
            f'큐 파일(설계와 사전 등록 판정):\n```json\n{json.dumps(design, ensure_ascii=False, indent=1)}\n```\n\n'
            f'결과:\n\n{body}')


def verdict_review(name, spec, body, data):
    """The reviewer's attack on an ab result, as a section of the result page (data['review'] keeps it).

    Off unless the queue file says `"review": true` (user 2026-10-22 "실험 자체가 문제가 있다고 검수하지 말고.
    실험에서 문제가 있다는건 실험을 시작하기 전에 이야기할 수 있어야지"): the design is reviewed before the
    start (design_review); the result page keeps only the numbers."""
    if not spec.get('review'):
        return ''
    text, note = codex_review(verdict_prompt(name, spec, body), float(spec.get('review_minutes', 20))*60)
    data['review'] = {'model': REVIEW_MODEL, 'text': text, 'note': note, 'findings': findings(text)}
    if text is None:
        return f'\n\n## 검수 실패 ({REVIEW_MODEL})\n\n{note}'
    return f'\n\n## 검수 ({REVIEW_MODEL}, 원문 그대로)\n\n{text}'


def code_prompt(spec):
    parts = [REVIEW_RULES, '',
             '과제: 아래 코드 변경(또는 파일)을 검수하라. 조용히 틀린 결과를 내는 경로를 먼저 찾아라: 집계·지표·규칙 해석의 오류, '
             '경계 조건, 상태 갱신 누락, 성능 저하, 빠진 테스트. 규칙 코드는 룰북(docs/EN_Gaia_rulebook_lo.pdf, '
             'docs/GP_Exp_Rule_EN_V1_Web.pdf)과 대조한다. 이 저장소의 A/B 판정은 gaia-rl/tools/charge_rounds.py가 세는 '
             '1–3라운드 충전량에 의존하므로, 그 숫자에 닿는 코드는 특히 엄격히 본다.']
    if spec.get('commits'):
        paths = spec.get('paths') or []
        parts.append(f"변경 범위: `git diff {spec['commits']}` (저장소 루트에서 직접 실행해 전체를 읽어라). "
                     f"바뀐 파일: {', '.join(paths) or '(목록 없음)'}")
        diff = git('diff', spec['commits'], '--', *[f':/{p}' for p in paths], check=False).stdout
        if diff and len(diff) <= DIFF_LIMIT:
            parts.append(f'```diff\n{diff}\n```')
    elif spec.get('paths'):
        parts.append('검수할 파일(전체를 읽어라): ' + ', '.join(spec['paths']))
    if spec.get('result'):
        page = LAB/'results'/f"{spec['result']}.md"
        parts.append(f"반박할 A/B 결과: gaia-rl/lab/results/{spec['result']}.md\n\n{page.read_text() if page.exists() else '(결과 파일 없음)'}")
    if spec.get('prompt'):
        parts.append(spec['prompt'])
    return '\n'.join(parts)


def run_review(name, spec, jobs):
    prompt = code_prompt(spec)
    text, note = codex_review(prompt, float(spec.get('timeout_minutes', 30))*60)
    data = {'model': REVIEW_MODEL, 'prompt_chars': len(prompt),
            **{k: spec[k] for k in ('commits', 'paths', 'result') if k in spec}}
    if text is None:
        return 'failed', data, note
    data['findings'] = findings(text)
    return 'done', data, f'검수자 {REVIEW_MODEL} (원문 그대로)\n\n{text}'


def design_prompt(name, spec):
    design = {k: v for k, v in spec.items() if k not in ('seeds', 'design_review')}
    return (f'{REVIEW_RULES}\n\n과제: lab 실험 {name}이 시작되기 전에 그 설계를 검수하라. 아래 큐 파일이 실험이다: '
            'note의 질문과 사전 등록 판정, A·B 교사 spec(tools/*.json; 어느 부품이 다른지는 spec의 factory와 '
            'gaia-rl/tools/teacher_patches.py), 쌍 수·비교 수·stop_round·예산. 이 실험이 note의 질문에 답할 수 없는 이유'
            '(두 팔이 한 가지 이상 다름, 표본이 너무 작음, 판정 기준이 질문과 안 맞음, 측정 예산이 결정을 바꿈, 같은 결론을 '
            '이미 낸 실험이 있음 — lab/results/와 research/strategy/cycles/ 확인)가 있으면 지적하라. 설계에 문제가 없으면 '
            '`결론: 이상 없음`. 결과가 나온 뒤에는 설계를 다시 묻지 않으므로 지금 말해야 한다.\n\n'
            f'큐 파일:\n```json\n{json.dumps(design, ensure_ascii=False, indent=1)}\n```')


def design_review(name, spec, push):
    """Codex reviews an ab design before it starts; True when the experiment is held with findings.

    User 2026-10-22 "실험에서 문제가 있다는건 실험을 시작하기 전에 이야기할 수 있어야지". The queue file's
    `design_review` records the outcome: absent → reviewed now; `"accepted"` or `false` → runs without a review
    (the owner decided, or Claude after the owner did); `{"findings": …}` → held until that changes. Findings are
    announced under '🔍 # <name> — 검수' (the bot opens a response turn) and kept in lab/queue/<name>.design.md."""
    review = spec.get('design_review')
    if spec.get('kind', 'ab') != 'ab' or review is False or review == 'accepted':
        return False
    if isinstance(review, dict):
        return bool(review.get('findings'))
    text, note = codex_review(design_prompt(name, spec), float(spec.get('review_minutes', 20))*60)
    if text is None:
        notify(f'⚠️ 설계 검수 실패: **{name}** — {note}\n실험은 그대로 시작합니다.')
        return False
    count = findings(text)
    if not count:
        notify(f'🔍 설계 검수 **{name}** ({REVIEW_MODEL}): 이상 없음 — 시작합니다')
        return False
    path = LAB/'queue'/f'{name}.json'
    page = LAB/'queue'/f'{name}.design.md'
    page.write_text(f'# {name} — 설계 검수 (실험 보류)\n\n검수자 {REVIEW_MODEL} (원문 그대로)\n\n{text}\n\n'
                    f'<sub>{platform.node()} · 커밋 {commit_id()} · {now()}</sub>\n')
    current = read_json(path) or spec
    path.write_text(json.dumps({**current, 'design_review': {'findings': count, 'model': REVIEW_MODEL, 'at': now()}},
                               ensure_ascii=False, indent=1)+'\n')
    if push:
        publish([path, page], f'lab: {name} held by design review')
    notify(f'🔍 # {name} — 검수 (설계, 실험 보류)\n\n{discord_text(text)}\n\n'
           f'실험은 큐 파일 `design_review`가 `"accepted"`로 바뀌거나 설계가 고쳐질 때까지 시작하지 않습니다.')
    return True


def write_result(name, spec, status, data, body, started):
    (LAB/'results').mkdir(parents=True, exist_ok=True)
    record = {'name': name, 'kind': spec.get('kind', 'ab'), 'status': status, 'note': spec.get('note'),
              'host': platform.node(), 'commit': commit_id(), 'started_at': started,
              'finished_at': now(), **data}
    paths = [LAB/'results'/f'{name}.json', LAB/'results'/f'{name}.md']
    paths[0].write_text(json.dumps(record, indent=1, ensure_ascii=False)+'\n')
    word = '실패' if status != 'done' else '검수' if record['kind'] == 'review' else '완료'
    head = f"# {name} — {word}\n\n"
    if spec.get('note'):
        head += f"{spec['note']}\n\n"
    meta = f"\n\n<sub>{record['host']} · 커밋 {record['commit']} · {started} → {record['finished_at']}</sub>\n"
    paths[1].write_text(head+body+meta)
    return paths


_held = set()  # experiments waiting for seeds, each announced once


def run_one(name, spec, jobs, push):
    """Runs the experiment and writes its result; False when it is held (no seeds yet)."""
    kind = spec.get('kind', 'ab')
    if kind == 'ab' and design_review(name, spec, push):  # before seeds: a held design keeps no seeds
        print(f'[{now()}] {name}: held (design review)', flush=True)
        return False
    if kind == 'ab' and not spec.get('seeds'):  # seeds before the start notice: a short file
        count = int(spec.get('pairs', 12))       # used to kill the service once a minute (E62, E66)
        seeds = ensure_seeds(name, count, jobs, push)
        if seeds is None:
            if name not in _held:
                _held.add(name)
                notify(f'⏸️ 실험 보류: **{name}** — lab/seeds.txt 미사용 {len(fresh_seeds())}개 < 필요 {count}개, '
                       f'자동 스캔으로도 못 채움. 다른 실험을 먼저 돌리고 매 루프 다시 시도합니다 '
                       f'(`tools/scan_seeds.py --files lab/seeds.txt --start N --count 200000`)')
            print(f'[{now()}] {name}: held (seeds)', flush=True)
            return False
        _held.discard(name)
        spec = {**spec, 'seeds': seeds}
    started = now()
    notify(f'🧪 실험 시작: **{name}** ({kind}) — {platform.node()}' + describe(spec))
    print(f'[{started}] {name}: start', flush=True)
    try:
        runner = {'ab': run_ab, 'command': run_command, 'review': run_review}[kind]
        status, data, body = runner(name, spec, jobs)
    except Exception as error:  # record the failure instead of retrying forever
        status, data, body = 'failed', {'error': repr(error)}, f'```\n{error!r}\n```'
    paths = write_result(name, spec, status, data, body, started)
    print(f'[{now()}] {name}: {status}', flush=True)
    if status == 'done':  # '🔍 … — 검수' (not '✅ … — 완료'): the bot answers a review instead of recording a result
        notify(('🔍 ' if kind == 'review' else '✅ ')+discord_text(paths[1].read_text()))
    else:
        notify(f'⚠️ 실험 실패: **{name}** — lab/results/{name}.md 참고')
    if push:
        publish(paths, f'lab: {name} {status}')
    return True


def run_pending(jobs, push):
    ran = 0
    for name, spec in pending():
        if spec.get('kind') == 'external':
            continue
        if run_one(name, spec, jobs, push):
            ran += 1
    return ran


# ── commands ────────────────────────────────────────────────────────────────

def describe(spec):
    lines = [spec['note']] if spec.get('note') else []
    if spec.get('kind', 'ab') == 'ab':
        lines.append(f"A `{Path(spec['teacher_a']).name}` vs B `{Path(spec['teacher_b']).name}`")
    elif spec.get('kind') == 'review':
        lines.append(f"검수자 {REVIEW_MODEL}: " + ', '.join(spec[k] if isinstance(spec[k], str) else ', '.join(spec[k])
                                                        for k in ('commits', 'paths', 'result') if spec.get(k))[:300])
    return ''.join(f'\n> {line}' for line in lines)


def announce_new(seen):
    """Post each queued experiment once, when it first appears (not those queued before start)."""
    waiting = [(n, s) for n, s in pending() if s.get('kind') != 'external']
    for position, (name, spec) in enumerate(waiting, 1):
        if seen is not None and name not in seen:
            notify(f'📋 실험 대기열에 추가: **{name}** ({position}/{len(waiting)}번째)' + describe(spec))
    return {name for name, _ in pending()} | (seen or set())


LOW_DISK_BYTES = 15 * 1024**3


def disk_warning(path, warned):
    """A notice when free space drops below 15 GB (once until it recovers); returns the new flag."""
    free = shutil.disk_usage(path).free
    if free < LOW_DISK_BYTES and not warned:
        notify(f'⚠️ {platform.node()} 디스크 여유 {free/1024**3:.1f}GB: `docker builder prune -f --keep-storage 10GB`, '
               '`df -h /`로 확인하세요 (꽉 차면 실험과 사이트 DB가 멈춥니다)')
        return True
    return free < LOW_DISK_BYTES


def source_digest():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def cmd_watch(args):
    print(f'lab watching {BRANCH} every {args.interval}s (Ctrl+C to stop)', flush=True)
    digest, seen, reported, low_disk = source_digest(), None, set(), False
    # No automatic `review-code-<commit>` queue any more (user 2026-10-22 "모니터링에서 codex가 리뷰하는곳도 빼"):
    # the Codex Discord bot reviews each conversation turn with its commits; a `review` item is queued by hand.
    while True:
        try:
            pull()
            if source_digest() != digest:  # a pull changed lab.py: continue as the new version
                print(f'[{now()}] lab.py changed: restarting', flush=True)
                os.execv(sys.executable, [sys.executable, *sys.argv])
            low_disk = disk_warning(GAIA_RL, low_disk)
            seen = announce_new(seen)
            for path, error in list(_broken.items()):
                if path not in reported:
                    notify(f'⚠️ lab: 읽을 수 없는 파일을 건너뜀 `{Path(path).relative_to(GAIA_RL)}` ({error})')
                    reported.add(path)
            if pending():
                ensure_built()
            run_pending(args.jobs, push=True)
        except Exception as error:
            print(f'[{now()}] {error}', file=sys.stderr, flush=True)
            notify(f'⚠️ lab 오류 ({platform.node()}): {error}')
        time.sleep(args.interval)


def cmd_once(args):
    if not args.no_pull:
        pull()
        ensure_built()
    print(f'{run_pending(args.jobs, push=not args.no_push)} experiment(s) run')


def cmd_status(_args):
    for name, spec in queue():
        r = result(name)
        state = r['status'] if r else ('외부 실행 대기' if spec.get('kind') == 'external' else '대기')
        print(f'{name:32} {spec.get("kind", "ab"):8} {state}')
    queued = {name for name, _ in queue()}
    for path in sorted((LAB/'results').glob('*.json')):
        if path.stem not in queued:
            print(f'{path.stem:32} {"record":8} {json.loads(path.read_text())["status"]}')


def cmd_record(args):
    """Add a result produced elsewhere (e.g. a Seraph PPO run)."""
    spec = dict(queue()).get(args.name, {'kind': 'external'})
    data = {}
    if args.metrics:
        data['metrics'] = json.loads(Path(args.metrics).read_text())
    body = Path(args.summary).read_text() if args.summary else ''
    if 'metrics' in data:
        body += f"\n\n```json\n{json.dumps(data['metrics'], indent=1, ensure_ascii=False)[:3000]}\n```"
    if args.note:
        spec = {**spec, 'note': args.note}
    paths = write_result(args.name, spec, args.status, data, body.strip(), args.started or now())
    print('\n'.join(map(str, paths)))
    notify(('✅ ' if args.status == 'done' else '⚠️ ')+discord_text(paths[1].read_text()))
    if args.push:
        publish(paths, f'lab: record {args.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    watch = sub.add_parser('watch')
    watch.add_argument('--jobs', type=int, default=4)
    watch.add_argument('--interval', type=int, default=300)
    once = sub.add_parser('once')
    once.add_argument('--jobs', type=int, default=4)
    once.add_argument('--no-pull', action='store_true')
    once.add_argument('--no-push', action='store_true')
    sub.add_parser('status')
    record = sub.add_parser('record')
    record.add_argument('name')
    record.add_argument('--metrics')
    record.add_argument('--summary')
    record.add_argument('--note')
    record.add_argument('--status', default='done', choices=('done', 'failed'))
    record.add_argument('--started')
    record.add_argument('--push', action='store_true')
    note = sub.add_parser('notify')
    note.add_argument('text')
    args = parser.parse_args()
    if args.command == 'notify':
        notify(args.text)
    else:
        {'watch': cmd_watch, 'once': cmd_once, 'status': cmd_status, 'record': cmd_record}[args.command](args)


if __name__ == '__main__':
    main()
