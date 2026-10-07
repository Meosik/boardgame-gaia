"""Teacher A vs teacher B on identical setups with swapped seats.

Each pair plays one seed twice: A controls a half of the seats and B the other half,
then the halves swap, so every seat is played once by each teacher. Every teacher runs
in its own worker process with its own source tree on PYTHONPATH, so a frozen baseline
copy and a working-tree teacher never share imported modules. The runner changes no
teacher, evaluation function or weight; it only schedules games and counts outcomes.

  gaia-rl/.venv/bin/python gaia-rl/tools/teacher_ab.py run --teacher-a baseline \
      --teacher-b my-teacher --games 6 --seeds s1 s2 s3 --output gaia-rl/runs/ab-<name>
"""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = Path(__file__).with_name('teachers.json')
# Short "data" thinking: 3 s target, 6 s hard cap, no long thinks.
CLOCKS = {'data': {'target_seconds': 3, 'long_seconds': 6, 'uses': 0},
          'standard': {'target_seconds': 10, 'long_seconds': 120, 'uses': 6}}
# Two-versus-two seat halves, cycled so no two seats are always on the same side.
HALVES = ((0, 2), (0, 1), (0, 3))
WORKER_GRACE_SECONDS = 60
MAX_DECISIONS = 2000
# A count budget never cuts a search short; this is only a hung-worker guard.
BUDGET_DECISION_SECONDS = 900


def budget_clock(comparisons):
    if comparisons < 0:
        raise ValueError('--comparisons must be nonnegative')
    return {'target_seconds': BUDGET_DECISION_SECONDS, 'long_seconds': BUDGET_DECISION_SECONDS,
            'uses': 0, 'comparisons': comparisons}


def now():
    return datetime.now().astimezone().isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


# ── Teacher specifications ──────────────────────────────────────────────────

def resolve_teacher(name):
    """A registry name from teachers.json or a path to a JSON spec file."""
    path = Path(name)
    if path.suffix == '.json' and path.exists():
        spec = json.loads(path.read_text())
        label = path.stem
    else:
        registry = json.loads(REGISTRY.read_text())
        if name not in registry:
            raise ValueError(f'Unknown teacher {name!r}; registry has {sorted(registry)}')
        spec, label = registry[name], name
    missing = {'source', 'factory'} - set(spec)
    if missing:
        raise ValueError(f'Teacher {label}: missing {sorted(missing)}')
    source = (ROOT/spec['source']).resolve()
    if not source.is_dir():
        raise ValueError(f'Teacher {label}: source directory {source} not found')
    module, _, attribute = spec['factory'].partition(':')
    if not module or not attribute:
        raise ValueError(f'Teacher {label}: factory must be "module:callable"')
    env = spec.get('env', {})
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        raise ValueError(f'Teacher {label}: env must map strings to strings')
    comparisons = spec.get('comparisons')
    if comparisons is not None and (type(comparisons) is not int or comparisons < 0):
        raise ValueError(f'Teacher {label}: comparisons must be a nonnegative integer')
    horizon = spec.get('horizon_incomes')
    if horizon is not None and horizon not in (1, 2):
        raise ValueError(f'Teacher {label}: horizon_incomes must be 1 or 2')
    cap = spec.get('max_seconds')
    if cap is not None and not (isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap > 0):
        raise ValueError(f'Teacher {label}: max_seconds must be positive')
    return {'name': label, 'source': str(source), 'factory': spec['factory'],
            'kwargs': spec.get('kwargs', {}), 'env': env, 'comparisons': comparisons,
            'horizon_incomes': horizon, 'max_seconds': cap,
            'frozen': bool(spec.get('frozen', False))}


def frozen_problems(teacher):
    """A frozen teacher must still match its FROZEN.json exactly."""
    if not teacher['frozen']:
        return []
    source = Path(teacher['source'])
    record = json.loads((source/'FROZEN.json').read_text())
    # `.omc/` is agent runtime state that was swept into the freeze but is untracked in Git,
    # so a fresh checkout never has it. It is not teacher code or data.
    runtime = lambda name: '.omc' in Path(name).parts
    actual = {p.relative_to(source).as_posix(): sha256(p) for p in sorted(source.rglob('*'))
              if p.is_file() and p.name != 'FROZEN.json' and '__pycache__' not in p.parts
              and not runtime(p.relative_to(source))}
    problems = [f'changed or missing: {n}' for n, h in record['files'].items()
                if not runtime(n) and actual.get(n) != h]
    problems += [f'added: {n}' for n in actual if n not in record['files']]
    problems += [f'external data changed: {n}' for n, h in record.get('external_data', {}).items()
                 if sha256(ROOT/n) != h]
    return problems


def fingerprint(teacher):
    source = Path(teacher['source'])
    files = sorted(p for p in source.rglob('*.py') if '__pycache__' not in p.parts)
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(source).as_posix().encode())
        digest.update(sha256(path).encode())
    return digest.hexdigest()


# ── Schedule and statistics (pure) ──────────────────────────────────────────

def schedule(seeds, games):
    if games < 2 or games % 2:
        raise ValueError('N must be an even number of games (two per seat-swapped pair)')
    if not seeds or len(set(seeds)) != len(seeds) or not all(isinstance(s, str) and s for s in seeds):
        raise ValueError('Nonempty distinct seed strings required')
    pairs = []
    for pair in range(games//2):
        seed = seeds[pair % len(seeds)]
        # Each repeat of a seed moves to the next seat split, offset per seed.
        half = HALVES[(pair % len(seeds) + pair//len(seeds)) % len(HALVES)]
        other = tuple(s for s in range(4) if s not in half)
        order = (half, other) if pair % 2 == 0 else (other, half)
        pairs.append({'pair': pair, 'seed': seed,
                      'games': [{'a_seats': list(a), 'b_seats': [s for s in range(4) if s not in a]}
                                for a in order]})
    return pairs


def pair_differences(first, second):
    """Per seat B-A for one completed pair; each seat is A in one game and B in the other."""
    if first['seed'] != second['seed'] or first['factions'] != second['factions']:
        raise ValueError('A pair must share the exact seed and faction seats')
    if sorted(first['a_seats']+second['a_seats']) != [0, 1, 2, 3]:
        raise ValueError('Each seat must be played once by A and once by B')
    rows = []
    for seat, faction in enumerate(first['factions']):
        a_game, b_game = (first, second) if seat in first['a_seats'] else (second, first)
        a, b = a_game['scores'][str(seat)], b_game['scores'][str(seat)]
        rows.append({'seat': seat, 'faction': faction, 'A': a, 'B': b, 'B_minus_A': b-a})
    return rows


def confidence_interval(values, level=.95):
    if len(values) < 2:
        return None
    from scipy.stats import t
    mean = statistics.mean(values)
    half = t.ppf((1+level)/2, len(values)-1)*statistics.stdev(values)/math.sqrt(len(values))
    return [mean-half, mean+half]


def summarize(pairs_rows, games):
    by_faction = {}
    for rows in pairs_rows:
        for row in rows:
            by_faction.setdefault(row['faction'], []).append(row)
    overall = [statistics.mean(r['B_minus_A'] for r in rows) for rows in pairs_rows]
    counters = {arm: Counter() for arm in 'AB'}
    per_faction = {}
    for game in games:
        for faction, arms in game.get('counters', {}).items():
            for arm, counts in arms.items():
                counters[arm].update(counts)
                per_faction.setdefault(faction, {'A': Counter(), 'B': Counter()})[arm].update(counts)
    errors = Counter(g['failure_kind'] for g in games if not g['complete'])
    faction_errors = Counter((f, g['failure_kind']) for g in games if not g['complete']
                             for f in (g.get('factions') or ()))

    def line(values, counts, errors_, timeouts):
        return {'pairs': len(values), 'mean_B_minus_A': statistics.mean(values) if values else None,
                'ci95': confidence_interval(values), 'error_games': errors_, 'timeout_games': timeouts,
                **{f'{arm}_{key}': counts[arm][key] for arm in 'AB'
                   for key in ('decisions', 'fallback_timeouts', 'federation_limit_hits',
                               'unsearched_decisions', 'unsearched_comparisons')}}

    empty = {'A': Counter(), 'B': Counter()}
    factions = sorted(set(by_faction) | set(per_faction) | {f for f, _ in faction_errors})
    table = {f: line([r['B_minus_A'] for r in by_faction.get(f, [])], per_faction.get(f, empty),
                     faction_errors[(f, 'error')], faction_errors[(f, 'timeout')]) for f in factions}
    table['ALL'] = line(overall, counters, errors['error'], errors['timeout'])
    return {'factions': table, 'failures': dict(errors),
            'games_planned': len(games), 'games_complete': sum(g['complete'] for g in games),
            'pairs_complete': len(pairs_rows)}


def format_ci(ci):
    return '—' if ci is None else f'[{ci[0]:+.1f}, {ci[1]:+.1f}]'


def report_table(summary):
    header = ('| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | '
              '폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |')
    lines = [header, '|---|---:|---:|---|---:|---:|---:|---:|---:|']
    for faction, row in summary['factions'].items():
        mean = '—' if row['mean_B_minus_A'] is None else f"{row['mean_B_minus_A']:+.1f}"
        name = '**전체 (좌석 평균)**' if faction == 'ALL' else faction
        lines.append(f"| {name} | {row['pairs']} | {mean} | {format_ci(row['ci95'])} | {row['error_games']} | {row['timeout_games']} | "
                     f"{row['A_fallback_timeouts']} / {row['B_fallback_timeouts']} | "
                     f"{row['A_federation_limit_hits']} / {row['B_federation_limit_hits']} | "
                     f"{row['A_unsearched_decisions']} / {row['B_unsearched_decisions']} |")
    return '\n'.join(lines)+'\n'


# ── Worker (one teacher, own process and sources) ───────────────────────────

def worker(args):
    spec = json.loads(args.spec)
    sys.path.insert(0, spec['source'])
    clock_spec = json.loads(args.clock)
    if clock_spec.pop('fast_copy', False):
        # Before any other teacher import: `from copy import deepcopy` and
        # `from strategy_teacher import distance` bind the patched versions.
        import fast_teacher
        fast_teacher.install()
    from importlib import import_module
    from gaia_rl import Environment
    from faction_teachers.clock import AdaptiveClock
    module, _, attribute = spec['factory'].partition(':')
    comparisons = clock_spec.pop('comparisons', None)
    if spec.get('comparisons') is not None:
        # A per-teacher budget (e.g. deeper search for one arm) overrides the match budget.
        comparisons = spec['comparisons']
    if comparisons is not None:
        # Deterministic count budget instead of wall-clock deadlines (tools/budget_teacher.py).
        import budget_teacher
        budget_teacher.install(comparisons, max_seconds=spec.get('max_seconds'))
        if spec.get('horizon_incomes') is not None:
            budget_teacher.set_horizon(spec['horizon_incomes'])
    clock = AdaptiveClock(**clock_spec)
    teacher = getattr(import_module(module), attribute)(
        args.seed, target_seconds=clock.target_seconds, maximum_seconds=clock.long_seconds,
        adaptive_clock=clock, **spec['kwargs'])
    env = Environment(args.seed, MAX_DECISIONS)
    teacher.bind(env)
    snapshot = json.loads(env.snapshot_json())
    out = sys.stdout
    sys.stdout = sys.stderr   # teacher prints must not corrupt the protocol stream

    def reply(value):
        out.write(json.dumps(value, allow_nan=False)+'\n')
        out.flush()

    reply({'ready': True, 'digest': digest(snapshot)})
    for line in sys.stdin:
        command = json.loads(line)
        if command['op'] == 'choose':
            if command['digest'] != digest(snapshot):
                reply({'error': 'worker native state diverged from runner'})
                return
            try:
                decision, index = teacher.choose(snapshot)
            except TimeoutError as error:
                reply({'timeout': repr(error)})
                return
            audit = teacher.last_audit or {}
            reply({'decision_id': decision, 'index': index,
                   'fallback_timeout': audit.get('ranking_mode') == 'shared-quick-fallback',
                   'unsearched_comparisons': audit.get('unsearched_comparisons') or 0,
                   'completed_comparisons': len(audit.get('plans') or ()),
                   'selected': audit.get('selected')})
        elif command['op'] == 'step':
            before = snapshot
            env.step(command['decision_id'], command['index'])
            snapshot = json.loads(env.snapshot_json())
            teacher.observe(before, command['index'], snapshot)
            reply({'digest': digest(snapshot)})
        elif command['op'] == 'stop':
            return


def digest(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


class Worker:
    def __init__(self, teacher, seed, clock, log):
        env = {**os.environ, **teacher.get('env', {}),
               'PYTHONPATH': teacher['source'], 'PYTHONDONTWRITEBYTECODE': '1'}
        self.process = subprocess.Popen(
            [sys.executable, '-u', str(Path(__file__).resolve()), 'worker', '--seed', seed,
             '--spec', json.dumps(teacher), '--clock', json.dumps(clock)],
            cwd=teacher['source'], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=log, text=True)
        self.lines = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.process.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def request(self, command, timeout):
        if command is not None:
            self.process.stdin.write(json.dumps(command)+'\n')
            self.process.stdin.flush()
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            raise WorkerTimeout(f'no reply within {timeout:.0f}s') from None
        if line is None:
            raise RuntimeError(f'worker exited with code {self.process.wait()}')
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write(json.dumps({'op': 'stop'})+'\n')
                self.process.stdin.flush()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
                self.process.wait()


class WorkerTimeout(RuntimeError):
    pass


# ── One game ────────────────────────────────────────────────────────────────

def play(output, seed, teachers, a_seats, clock, stop_round=None):
    """One game. With stop_round, the game ends when round stop_round+1 starts and 'scores' are the
    VP held then (user 2026-10-07: A/B is judged by charges in rounds 1-3, later rounds are unused)."""
    from gaia_rl import Environment
    output.mkdir(parents=True)
    env = Environment(seed, MAX_DECISIONS)
    snapshot = json.loads(env.snapshot_json())
    factions = [p['faction'] for p in snapshot['state']['players']]
    arm_of = {seat: 'A' if seat in a_seats else 'B' for seat in range(4)}
    counters = {f: {'A': Counter(), 'B': Counter()} for f in factions}
    result = {'seed': seed, 'factions': factions, 'a_seats': sorted(a_seats), 'complete': False,
              'started_at': now(), 'counters': counters}
    workers = {}
    decision_budget = clock['long_seconds']+WORKER_GRACE_SECONDS
    try:
        with (output/'workers.log').open('w') as log:
            for arm in 'AB':
                workers[arm] = Worker(teachers[arm], seed, clock, log)
            for arm, w in workers.items():
                hello = w.request(None, timeout=300)
                if hello.get('digest') != digest(snapshot):
                    raise RuntimeError(f'teacher {arm} started from a different native state')
            with gzip.open(output/'decisions.jsonl.gz', 'wt') as trace:
                while not env.is_terminal() and not (stop_round and snapshot['state']['round'] > stop_round):
                    seat, arm = snapshot['player'], arm_of[snapshot['player']]
                    faction = factions[seat]
                    limits = snapshot.get('candidate_generation') or {}
                    tick = time.monotonic()
                    reply = workers[arm].request({'op': 'choose', 'digest': digest(snapshot)}, decision_budget)
                    if 'timeout' in reply:
                        raise WorkerTimeout(reply['timeout'])
                    if 'error' in reply:
                        raise RuntimeError(reply['error'])
                    index = reply['index']
                    if reply['decision_id'] != snapshot['decision_id'] or not 0 <= index < len(snapshot['candidates']):
                        raise RuntimeError('teacher returned a decision for another state')
                    counts = counters[faction][arm]
                    counts['decisions'] += 1
                    counts['fallback_timeouts'] += bool(reply['fallback_timeout'])
                    counts['federation_limit_hits'] += int(limits.get('federation_limit_hits', 0))
                    counts['unsearched_comparisons'] += int(reply['unsearched_comparisons'])
                    counts['unsearched_decisions'] += bool(reply['unsearched_comparisons'])
                    counts['completed_comparisons'] += int(reply.get('completed_comparisons', 0))
                    counts['search_milliseconds'] += round((time.monotonic()-tick)*1000)
                    trace.write(json.dumps({'step': snapshot['steps'], 'seat': seat, 'arm': arm,
                                            'decision_id': snapshot['decision_id'], 'index': index,
                                            'seconds': round(time.monotonic()-tick, 3),
                                            'federation_limit_hits': limits.get('federation_limit_hits', 0),
                                            **{k: reply[k] for k in ('fallback_timeout', 'unsearched_comparisons',
                                                                     'completed_comparisons', 'selected')}})+'\n')
                    env.step(snapshot['decision_id'], index)
                    snapshot = json.loads(env.snapshot_json())
                    expected = digest(snapshot)
                    for other, w in workers.items():
                        if w.request({'op': 'step', 'decision_id': reply['decision_id'], 'index': index},
                                     decision_budget)['digest'] != expected:
                            raise RuntimeError(f'teacher {other} diverged after step {snapshot["steps"]}')
                    write_json(output/'progress.json', {'step': snapshot['steps'], 'round': snapshot['state']['round'],
                                                        'updated_at': now()})
        if env.is_terminal():
            scores = {str(k): v for k, v in dict(env.final_scores()).items()}
        else:
            scores = {str(seat): p['vp'] for seat, p in enumerate(snapshot['state']['players'])}
            result['stopped_at_round'] = snapshot['state']['round']
        result.update(complete=True, scores=scores, steps=snapshot['steps'])
    except WorkerTimeout as error:
        result.update(failure_kind='timeout', error=str(error), step=snapshot['steps'])
    except Exception as error:
        result.update(failure_kind='error', error=repr(error), step=snapshot['steps'])
    finally:
        for w in workers.values():
            w.close()
        result['finished_at'] = now()
        write_json(output/'result.json', result)
    return result


# ── Match ───────────────────────────────────────────────────────────────────

def run(args):
    output = Path(args.output)
    if output.exists():
        raise SystemExit('A new output directory is required')
    teachers = {'A': resolve_teacher(args.teacher_a), 'B': resolve_teacher(args.teacher_b)}
    for arm, teacher in teachers.items():
        problems = frozen_problems(teacher)
        if problems:
            raise SystemExit(f'Frozen teacher {arm} ({teacher["name"]}) changed: {problems[:5]}')
    clock = budget_clock(args.comparisons) if args.comparisons is not None else dict(CLOCKS[args.clock])
    if args.fast_copy:
        clock['fast_copy'] = True
    plan = schedule(args.seeds, args.games)
    output.mkdir(parents=True)
    from gaia_rl.versions import runtime_versions
    write_json(output/'manifest.json', {
        'created_at': now(), 'teachers': {arm: {**t, 'fingerprint': fingerprint(t)} for arm, t in teachers.items()},
        'clock': {'preset': 'comparisons' if args.comparisons is not None else args.clock, **clock},
        'jobs': args.jobs, 'games': args.games, 'seeds': args.seeds, 'schedule': plan,
        'versions': runtime_versions(), 'training_performed': False})
    jobs = [(pair, g, game) for pair in plan for g, game in enumerate(pair['games'])]
    lock = threading.Lock()
    finished = []

    def play_one(job):
        pair, g, game = job
        for arm, teacher in teachers.items():
            if frozen_problems(teacher):
                raise SystemExit(f'Frozen teacher {arm} changed during the match; stopping')
        path = output/f"pair-{pair['pair']:03d}"/f"game-{g}-A{''.join(map(str, game['a_seats']))}"
        result = play(path, pair['seed'], teachers, set(game['a_seats']), clock, args.stop_round)
        with lock:
            finished.append(str(path))
            write_json(output/'progress.json', {'games_done': len(finished), 'games_planned': len(jobs),
                                                'last': str(path), 'updated_at': now()})
            print(json.dumps({'game': str(path), 'complete': result['complete'],
                              'scores': result.get('scores'), 'failure': result.get('failure_kind')}), flush=True)
        return result

    # Games are independent processes; results are consumed in schedule order.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(play_one, jobs))
    games, pairs_rows = results, []
    for p in range(len(plan)):
        completed = [r for (pair, _, _), r in zip(jobs, results) if pair['pair'] == plan[p]['pair']]
        if all(r['complete'] for r in completed):
            pairs_rows.append(pair_differences(*completed))
    summary = summarize(pairs_rows, games)
    write_json(output/'results.json', {**summary, 'pairs': pairs_rows})
    (output/'report.md').write_text(report_table(summary))
    write_json(output/'progress.json', {'state': 'complete', 'updated_at': now(), 'games_done': len(games)})
    print(report_table(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True)
    match = commands.add_parser('run', help='Play the seat-swapped A/B match')
    match.add_argument('--teacher-a', required=True, help='teachers.json name or spec .json path')
    match.add_argument('--teacher-b', required=True)
    match.add_argument('--games', type=int, required=True, help='N, even: two seat-swapped games per pair')
    match.add_argument('--seeds', nargs='+', required=True, help='Cycled when N/2 exceeds the seed count')
    match.add_argument('--clock', choices=sorted(CLOCKS), default='data')
    match.add_argument('--comparisons', type=int,
                       help='Deterministic budget: completed comparisons per decision; ignores --clock')
    match.add_argument('--jobs', type=int, default=1, help='Games played in parallel')
    match.add_argument('--fast-copy', action='store_true',
                       help='Decision-preserving teacher speedups in workers (tools/fast_teacher.py)')
    match.add_argument('--stop-round', type=int,
                       help='End each game when this round is over; scores are then the VP held')
    match.add_argument('--output', required=True)
    plan =commands.add_parser('plan', help='Resolve teachers and print the schedule; plays nothing')
    for name in ('--teacher-a', '--teacher-b'):
        plan.add_argument(name, required=True)
    plan.add_argument('--games', type=int, required=True)
    plan.add_argument('--seeds', nargs='+', required=True)
    work = commands.add_parser('worker', help=argparse.SUPPRESS)
    work.add_argument('--seed', required=True)
    work.add_argument('--spec', required=True)
    work.add_argument('--clock', required=True)
    args = parser.parse_args()
    if args.command == 'worker':
        worker(args)
    elif args.command == 'plan':
        teachers = {'A': resolve_teacher(args.teacher_a), 'B': resolve_teacher(args.teacher_b)}
        print(json.dumps({'teachers': teachers, 'frozen_problems': {k: frozen_problems(t) for k, t in teachers.items()},
                          'schedule': schedule(args.seeds, args.games)}, ensure_ascii=False, indent=2))
    else:
        run(args)


if __name__ == '__main__':
    main()
