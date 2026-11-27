"""146 (user 11-27 「발타크 1라운드 가이아 4렙이 중요한데 과학 고른건 아쉽다」): BalTaks R1 tech-tile choices.

Replays with the lab checkout modules (same as scratch_146_pass.py) and at the given steps prints the standard tech tile
layout (tile -> track), the seat's research levels, and every candidate that takes a tech tile. Read only.

  scratch_146_baltaks.py <game dir> <step> [<step> ...] [--tech]
  (default: resources, chosen action, legal Build coords; --tech adds the tech-tile / research candidates)
"""
import gzip
import json
import os
import sys
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(LAB/'baseline-teacher-20260917'), str(LAB/'tools')]


def main():
    game, steps = Path(sys.argv[1]), {int(s) for s in sys.argv[2:] if s != '--tech'}
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows:
        snap = json.loads(env.snapshot_json())
        if row['step'] in steps:
            state, seat = snap['state'], snap.get('player')
            p = state['players'][seat]
            print(f"step {row['step']} seat {seat} {p['faction']} round {state['round']}")
            r = p['resources']
            print('  resources', {k: r[k] for k in r if k != 'power'}, 'power', r['power'])
            print('  chosen', json.dumps(snap['candidates'][row['index']]['action'], ensure_ascii=False))
            builds = [c['action'].get('coord') for c in snap['candidates'] if c['action'].get('type') == 'Build']
            print('  legal Build', builds)
            print('  legal FreeAction', [c['action'].get('kind') for c in snap['candidates'] if c['action'].get('type') == 'FreeAction'])
            if '--tech' not in sys.argv:
                env.step(row['decision_id'], row['index'])
                if row['step'] >= max(steps):
                    break
                continue
            for key in state:
                if 'tech' in key.lower():
                    print(f'  {key}', json.dumps(state[key], ensure_ascii=False)[:600])
            for i, c in enumerate(snap['candidates']):
                a = c['action']
                if a.get('tech_tile_choice') or a.get('type') == 'ResearchAdvance':
                    mark = '*' if i == row['index'] else ' '
                    print(f'  {mark}[{i}]', json.dumps(a, ensure_ascii=False))
        env.step(row['decision_id'], row['index'])
        if row['step'] >= max(steps):
            break


if __name__ == '__main__':
    main()
