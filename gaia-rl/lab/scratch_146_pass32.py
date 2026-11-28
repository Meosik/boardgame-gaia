"""146 known-bad 32: Itars R2 first-turn Pass (step 75). Read only.

  scratch_146_pass32.py <game dir> <step> [<last step to trace>]
Prints at <step>: resources, buildings, research, all candidates (non-free), the decision row keys/compared plans;
then traces every later decision of the same seat up to <last step> (action + resources).
"""
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(LAB/'baseline-teacher-20260917'), str(LAB/'tools')]


def short(a):
    return json.dumps(a, ensure_ascii=False)[:160]


def main():
    game, step = Path(sys.argv[1]), int(sys.argv[2])
    last = int(sys.argv[3]) if len(sys.argv) > 3 else step
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    seat0 = None
    for row in rows:
        snap = json.loads(env.snapshot_json())
        state, seat = snap['state'], snap.get('player')
        if row['step'] == step:
            seat0 = seat
            p = state['players'][seat]
            print(f"step {step} seat {seat} {p['faction']} round {state['round']}")
            for k in p:
                if k not in ('resources',):
                    print(f'  {k}', json.dumps(p[k], ensure_ascii=False)[:300])
            print('  resources', p['resources'])
            kinds = Counter(c['action'].get('type') for c in snap['candidates'])
            print('  candidate types', dict(kinds))
            for i, c in enumerate(snap['candidates']):
                a = c['action']
                if a.get('type') != 'FreeAction':
                    print(f"  {'*' if i == row['index'] else ' '}[{i}]", short(a))
            print('  row keys', list(row))
            for key in ('compared', 'plan', 'chosen_plan', 'reason', 'menu', 'values', 'menu_pool', 'menu_dropped', 'menu_forgot',
                        'selected', 'prune_blocked', 'unsearched_comparisons'):
                if key in row:
                    print(f'  row.{key}', json.dumps(row[key], ensure_ascii=False)[:1500])
        elif seat0 is not None and step < row['step'] <= last:
            if seat == seat0 or state['round'] != rows[0].get('round'):
                p = state['players'][seat]
                r = p['resources']
                a = snap['candidates'][row['index']]['action']
                if seat == seat0:
                    print(f"  {row['step']} R{state['round']} ore {r['ore']} cr {r['credits']} k {r['knowledge']} q {r['qic']} pw {r['power']['bowl1']}/{r['power']['bowl2']}/{r['power']['bowl3']}", short(a))
        env.step(row['decision_id'], row['index'])
        if row['step'] >= last:
            break


if __name__ == '__main__':
    main()
