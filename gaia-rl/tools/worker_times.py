"""Wall seconds per decision of the live AI worker (tools/ai_worker.py), per teacher factory and level.

The worker is driven as a subprocess over its JSON-lines protocol. Two modes:

play (default): every cell (factory x level) plays its own game from the seed's opening with the moves its
worker picks, so cells compare time distributions, not the same positions. Only reaches rounds 1-2.

replay (--replay <recorded game folders>): each folder holds result.json (seed) and decisions.jsonl.gz of a
recorded lab game. The game is replayed with the recorded moves and the worker is asked only at chosen
positions: every --every-th decision of --rounds, the --slowest recorded decisions of those rounds and the
explicit --steps. All cells see the same recorded positions, so cells are comparable position by position,
and late rounds are reached. The game continues with the recorded moves, never the worker's. Limit: the
worker's teacher only sees the asked positions, so its plan memory between decisions is thinner than in a
live game where it is asked every decision of its seats.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import select
import statistics
import subprocess
import sys
import time

from gaia_rl import Environment

GAIA_RL = Path(__file__).resolve().parents[1]


def start_worker(factory):
    env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1', 'GAIA_AI_TEACHER': factory,
           'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
    return subprocess.Popen([sys.executable, str(GAIA_RL/'tools'/'ai_worker.py')], cwd=GAIA_RL, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)


def ask(process, request, timeout):
    """Send one request; returns (reply_or_None, wall_seconds, raw_line, timed_out)."""
    t0 = time.monotonic()
    process.stdin.write(json.dumps(request)+'\n')
    process.stdin.flush()
    ready = select.select([process.stdout], [], [], timeout)[0]
    wall = time.monotonic()-t0
    if not ready:
        return None, wall, '', True
    line = process.stdout.readline()
    reply = json.loads(line) if line.strip() else None
    return reply, wall, line, False


def summarise(cell, rows, args):
    answered = [r for r in rows if not r.get('timed_out')]
    walls = sorted(r['wall'] for r in answered)
    n = len(walls)
    by_round = {}
    for r in answered:
        by_round.setdefault(str(r['round']), []).append(r['wall'])
    cell.update(decisions=n, last_round=rows[-1]['round'] if rows else None,
                mean=statistics.fmean(walls) if n else None, median=statistics.median(walls) if n else None,
                p90=walls[min(n-1, int(0.9*n))] if n else None, max=walls[-1] if n else None,
                over_guard=sum(1 for w in walls if w > args.guard),
                timed_out=sum(1 for r in rows if r.get('timed_out')),
                time_capped=sum(1 for r in answered if r.get('time_capped')),
                by_round={k: {'n': len(v), 'mean': statistics.fmean(v), 'max': max(v)} for k, v in by_round.items()},
                rows=rows)
    return cell


def answered_row(reply, wall, rnd, snapshot):
    return {'wall': wall, 'seconds': reply.get('seconds'),
            'completed_comparisons': reply.get('completed_comparisons'),
            'time_capped': reply.get('time_capped'), 'round': rnd,
            'candidates': len(snapshot['candidates'])}


def run_cell(args, factory, level):
    rows, cell = [], {'factory': factory, 'level': level, 'stopped': None, 'error': None}
    process = start_worker(factory)
    started = time.monotonic()
    try:
        env = Environment(args.seed, 2000)
        while True:
            snapshot = json.loads(env.snapshot_json())
            if not snapshot.get('candidates'):
                cell['stopped'] = 'game over'; break
            if len(rows) >= args.decisions:
                cell['stopped'] = 'decisions'; break
            if time.monotonic()-started > args.seconds:
                cell['stopped'] = 'seconds'; break
            request = {'op': 'choose', 'room': f'times-{level}', 'level': level,
                       'state': snapshot['state'], 'player': snapshot['player']}
            reply, wall, line, timed_out = ask(process, request, args.decision_timeout)
            rnd = snapshot['state'].get('round')
            if timed_out:
                rows.append({'timed_out': True, 'wall': args.decision_timeout, 'round': rnd})
                cell['stopped'] = 'decision timeout'; break
            if not reply or not reply.get('ok') or reply.get('decision') not in snapshot['candidates']:
                cell['stopped'] = 'error'; cell['error'] = (line or 'worker died')[:300]; break
            rows.append(answered_row(reply, wall, rnd, snapshot))
            env.step(snapshot['decision_id'], snapshot['candidates'].index(reply['decision']))
    finally:
        process.kill()
        process.wait(timeout=30)
    cell['wall_total'] = time.monotonic()-started
    return summarise(cell, rows, args)


def replay_positions(rows, rounds, every, steps, slowest):
    """Steps of a recorded game to ask the worker about: every `every`-th decision of `rounds` (counted
    inside those rounds, starting with their first decision; 0 = none), the `slowest` decisions of those
    rounds by recorded seconds, and the explicit `steps` that exist."""
    in_rounds = [i for i, row in enumerate(rows) if row.get('round') in rounds]
    picked = set(in_rounds[::every]) if every > 0 else set()
    picked.update(sorted(in_rounds, key=lambda i: -(rows[i].get('seconds') or 0))[:max(slowest, 0)])
    picked.update(s for s in steps if 0 <= s < len(rows))
    return sorted(picked)


def load_record(game_dir):
    game_dir = Path(game_dir)
    result = json.loads((game_dir/'result.json').read_text())
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    return result, rows


def run_replay_cell(args, factory, level):
    rows, cell = [], {'factory': factory, 'level': level, 'stopped': None, 'error': None}
    process = start_worker(factory)
    started = time.monotonic()
    try:
        for g, game_dir in enumerate(args.replay):
            result, records = load_record(game_dir)
            positions = replay_positions(records, set(args.rounds), args.every, args.steps, args.slowest)
            if not positions:
                continue
            last = positions[-1]
            wanted = set(positions)
            name = '/'.join(Path(game_dir).parts[-2:])
            env = Environment(result['seed'], 2000)
            for step, row in enumerate(records[:last+1]):
                snapshot = json.loads(env.snapshot_json())
                if (snapshot.get('decision_id') != row['decision_id']
                        or row['index'] >= len(snapshot['candidates'])
                        or ('chosen' in row and snapshot['candidates'][row['index']] != row['chosen'])):
                    cell['stopped'] = 'error'
                    cell['error'] = f'replay diverged from the record: {game_dir} step {step}'
                    break
                if step in wanted:
                    if time.monotonic()-started > args.seconds:
                        cell['stopped'] = 'seconds'; break
                    rnd = snapshot['state'].get('round')
                    request = {'op': 'choose', 'room': f'times-{level}-{g}', 'level': level,
                               'state': snapshot['state'], 'player': snapshot['player']}
                    reply, wall, line, timed_out = ask(process, request, args.decision_timeout)
                    if timed_out:
                        rows.append({'timed_out': True, 'wall': args.decision_timeout, 'round': rnd,
                                     'game': name, 'step': step})
                        process.kill()
                        process.wait(timeout=30)
                        process = start_worker(factory)
                    elif (not reply or not reply.get('ok')
                            or reply.get('decision') not in snapshot['candidates']):
                        cell['stopped'] = 'error'; cell['error'] = (line or 'worker died')[:300]; break
                    else:
                        out = answered_row(reply, wall, rnd, snapshot)
                        out.update(game=name, step=step, seat=snapshot['player'],
                                   recorded_seconds=row.get('seconds'),
                                   same_as_recorded=reply['decision'] == snapshot['candidates'][row['index']])
                        rows.append(out)
                env.step(row['decision_id'], row['index'])
            if cell['stopped']:
                break
        else:
            cell['stopped'] = 'positions'
    finally:
        process.kill()
        process.wait(timeout=30)
    cell['wall_total'] = time.monotonic()-started
    return summarise(cell, rows, args)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--factories', nargs='+', default=['guide_r1_charge3_lf_more_vm_lf_ts_ships',
                                                           'guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier'])
    parser.add_argument('--levels', nargs='+', default=['easy', 'normal', 'hard'])
    parser.add_argument('--seed', default='quartet-e-88365')
    parser.add_argument('--decisions', type=int, default=80)
    parser.add_argument('--seconds', type=float, default=420)
    parser.add_argument('--decision-timeout', type=float, default=180)
    parser.add_argument('--guard', type=float, default=30)
    parser.add_argument('--replay', nargs='+', default=None)
    parser.add_argument('--rounds', type=int, nargs='+', default=[4, 5, 6])
    parser.add_argument('--every', type=int, default=8)
    parser.add_argument('--steps', type=int, nargs='*', default=[])
    parser.add_argument('--slowest', type=int, default=5)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    cells = []
    for factory in args.factories:
        for level in args.levels:
            cell = (run_replay_cell if args.replay else run_cell)(args, factory, level)
            cells.append(cell)
            f = lambda v: 'None' if v is None else f'{v:.2f}'
            print(factory[-24:], level, cell['decisions'], cell['stopped'], cell['last_round'], f(cell['mean']),
                  f(cell['median']), f(cell['p90']), f(cell['max']), cell['over_guard'], flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    head = {'seed': args.seed, 'decisions': args.decisions, 'seconds': args.seconds,
            'decision_timeout': args.decision_timeout, 'guard': args.guard}
    if args.replay:
        head.update(mode='replay', replay=args.replay, rounds=args.rounds, every=args.every,
                    steps=args.steps, slowest=args.slowest)
    else:
        head.update(mode='play')
    with out.open('w') as fh:
        json.dump({**head, 'cells': cells}, fh, allow_nan=False, indent=1)


if __name__ == '__main__':
    main()
