"""Experiment lab: run queued experiments on this machine and publish the results through git.

Claude (or anyone) queues an experiment as `lab/queue/<name>.json` and pushes it. A machine
running `lab.py watch` pulls, runs every queued experiment that has no result yet, writes
`lab/results/<name>.md` (readable report) and `<name>.json` (data), commits only those two files
and pushes them. The Discord ops bot (deploy/ops_bot.py) posts new results to the channel, so
nobody copies commands or pastes reports.

Experiment kinds (`"kind"` in the queue file):
  ab        teacher_ab match. Keys: teacher_a, teacher_b, pairs (default 12; fresh seeds come
            from lab/seeds.txt) or seeds (explicit list), comparisons (default 2), note.
  command   any command run from gaia-rl/ (e.g. a future PPO-checkpoint evaluation). Keys: run
            (argv list), metrics (optional JSON file the command writes), timeout_hours, note.
  external  run elsewhere (e.g. Seraph PPO). Never run here; its result is added with
            `lab.py record`, which also accepts results without a queue file.

  .venv/bin/python tools/lab.py watch --jobs 4        # laptop: keep running (tmux/nohup)
  .venv/bin/python tools/lab.py once --jobs 4         # run what is pending, then exit
  .venv/bin/python tools/lab.py status
  .venv/bin/python tools/lab.py record NAME --metrics m.json [--summary s.md] [--push]
  .venv/bin/python tools/lab.py notify "text"         # Discord webhook, if configured

Environment: GAIA_LAB_BRANCH (default claude/epic-goodall-0ot55w), GAIA_LAB_WEBHOOK (optional
Discord webhook URL for start/failure notices; results reach Discord through the ops bot),
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
import shutil
import subprocess
import sys
import time
import urllib.request

GAIA_RL = Path(__file__).resolve().parents[1]
LAB = Path(os.environ.get('GAIA_LAB_DIR') or GAIA_RL/'lab')
BRANCH = os.environ.get('GAIA_LAB_BRANCH', 'claude/epic-goodall-0ot55w')
KINDS = ('ab', 'command', 'external')


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


def allocate(count):
    used = used_seeds()
    lines = (LAB/'seeds.txt').read_text().splitlines()
    fresh = [s.strip() for s in lines if s.strip() and not s.startswith('#') and s.strip() not in used]
    if len(fresh) < count:
        raise SystemExit(f'lab/seeds.txt has {len(fresh)} unused seeds, {count} needed; add more '
                         '(examples/faction_lineups geo-quartet ...)')
    return fresh[:count]


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
    results = str(LAB.relative_to(GAIA_RL)/'results') if LAB.is_relative_to(GAIA_RL) else None
    if results and git('status', '--porcelain', '--', results, check=False).stdout.strip():
        git('add', '--', results)
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


def publish(paths, message):
    git('add', '--', *map(str, paths))
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
            stats[arm] = {'n': n, 'mean': sum(values)/n, 'median': values[n//2],
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
    body = (f"A: `{spec['teacher_a']}`\nB: `{spec['teacher_b']}`\n"
            f"시드 {len(seeds)}개 × 좌석 교대 2판 (비교 기본값 {spec.get('comparisons', 2)}, 스펙 파일에 있으면 그 값)\n\n"
            f"{(out/'report.md').read_text().strip()}\n\n평균 총점 (같은 판의 상대와 겨룬 절대 점수)\n\n"
            f"{scores_table(data['final_scores'])}\n\n결정 시간\n\n{timing_table(data['timing'])}")
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


def write_result(name, spec, status, data, body, started):
    (LAB/'results').mkdir(parents=True, exist_ok=True)
    record = {'name': name, 'kind': spec.get('kind', 'ab'), 'status': status, 'note': spec.get('note'),
              'host': platform.node(), 'commit': commit_id(), 'started_at': started,
              'finished_at': now(), **data}
    paths = [LAB/'results'/f'{name}.json', LAB/'results'/f'{name}.md']
    paths[0].write_text(json.dumps(record, indent=1, ensure_ascii=False)+'\n')
    head = f"# {name} — {'완료' if status == 'done' else '실패'}\n\n"
    if spec.get('note'):
        head += f"{spec['note']}\n\n"
    meta = f"\n\n<sub>{record['host']} · 커밋 {record['commit']} · {started} → {record['finished_at']}</sub>\n"
    paths[1].write_text(head+body+meta)
    return paths


def run_one(name, spec, jobs, push):
    kind = spec.get('kind', 'ab')
    started = now()
    notify(f'🧪 실험 시작: **{name}** ({kind}) — {platform.node()}' + describe(spec))
    print(f'[{started}] {name}: start', flush=True)
    try:
        status, data, body = (run_ab if kind == 'ab' else run_command)(name, spec, jobs)
    except Exception as error:  # record the failure instead of retrying forever
        status, data, body = 'failed', {'error': repr(error)}, f'```\n{error!r}\n```'
    paths = write_result(name, spec, status, data, body, started)
    print(f'[{now()}] {name}: {status}', flush=True)
    if status == 'done':
        notify('✅ '+discord_text(paths[1].read_text()))
    else:
        notify(f'⚠️ 실험 실패: **{name}** — lab/results/{name}.md 참고')
    if push:
        publish(paths, f'lab: {name} {status}')


def run_pending(jobs, push):
    ran = 0
    for name, spec in pending():
        if spec.get('kind') == 'external':
            continue
        run_one(name, spec, jobs, push)
        ran += 1
    return ran


# ── commands ────────────────────────────────────────────────────────────────

def describe(spec):
    lines = [spec['note']] if spec.get('note') else []
    if spec.get('kind', 'ab') == 'ab':
        lines.append(f"A `{Path(spec['teacher_a']).name}` vs B `{Path(spec['teacher_b']).name}`")
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
