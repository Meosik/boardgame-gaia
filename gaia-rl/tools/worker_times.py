"""Wall seconds per decision of the live AI worker (tools/ai_worker.py), per teacher factory and level.

The worker is driven as a subprocess over its JSON-lines protocol. Every cell (factory x level) plays its
own game from the seed's opening with the moves its worker picks, so cells compare time distributions,
not the same positions.
"""
import argparse
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
            t0 = time.monotonic()
            process.stdin.write(json.dumps(request)+'\n')
            process.stdin.flush()
            ready = select.select([process.stdout], [], [], args.decision_timeout)[0]
            wall = time.monotonic()-t0
            rnd = snapshot['state'].get('round')
            if not ready:
                rows.append({'timed_out': True, 'wall': args.decision_timeout, 'round': rnd})
                cell['stopped'] = 'decision timeout'; break
            line = process.stdout.readline()
            reply = json.loads(line) if line.strip() else None
            if not reply or not reply.get('ok') or reply.get('decision') not in snapshot['candidates']:
                cell['stopped'] = 'error'; cell['error'] = (line or 'worker died')[:300]; break
            rows.append({'wall': wall, 'seconds': reply.get('seconds'),
                         'completed_comparisons': reply.get('completed_comparisons'),
                         'time_capped': reply.get('time_capped'), 'round': rnd,
                         'candidates': len(snapshot['candidates'])})
            env.step(snapshot['decision_id'], snapshot['candidates'].index(reply['decision']))
    finally:
        process.kill()
        process.wait(timeout=30)
    cell['wall_total'] = time.monotonic()-started
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factories', nargs='+', default=['guide_r1_charge3_lf_more_vm_lf_ts_ships',
                                                           'guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier'])
    parser.add_argument('--levels', nargs='+', default=['easy', 'normal', 'hard'])
    parser.add_argument('--seed', default='quartet-e-88365')
    parser.add_argument('--decisions', type=int, default=80)
    parser.add_argument('--seconds', type=float, default=420)
    parser.add_argument('--decision-timeout', type=float, default=180)
    parser.add_argument('--guard', type=float, default=30)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    cells = []
    for factory in args.factories:
        for level in args.levels:
            cell = run_cell(args, factory, level)
            cells.append(cell)
            f = lambda v: 'None' if v is None else f'{v:.2f}'
            print(factory[-24:], level, cell['decisions'], cell['stopped'], cell['last_round'], f(cell['mean']),
                  f(cell['median']), f(cell['p90']), f(cell['max']), cell['over_guard'], flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w') as fh:
        json.dump({'seed': args.seed, 'decisions': args.decisions, 'seconds': args.seconds,
                   'decision_timeout': args.decision_timeout, 'guard': args.guard, 'cells': cells},
                  fh, allow_nan=False, indent=1)


if __name__ == '__main__':
    main()
