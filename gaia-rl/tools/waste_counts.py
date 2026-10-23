"""Count costly moves per arm and faction in rounds low-high over a lab/teacher_ab run:
how much ore a Build paid, how many credits an Upgrade to a trading station paid,
and which free-action conversions were taken.

  .venv/bin/python tools/waste_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-048-... [--rounds 1-3] [--examples]
"""
import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]


def resources(snapshot, seat):
    values = snapshot['state']['players'][seat]['resources']
    return {k: v for k, v in values.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}


def show(counter):
    return '{' + ', '.join(f'{k}: {counter[k]}' for k in sorted(counter, key=str)) + '}'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-3')
    parser.add_argument('--examples', action='store_true')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    run_dir = args.run_dir.expanduser()
    build_ore, ts_credits, free = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    first_free = {}
    big = {'ore': [], 'credits': []}
    games = 0
    for game_dir in sorted(run_dir.glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        games += 1
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if state['round'] > high:
                break
            action = snapshot['candidates'][row['index']]['action']
            kind = action.get('type')
            seat = snapshot['player']
            before = resources(snapshot, seat)
            env.step(row['decision_id'], row['index'])
            if state['round'] < low or kind not in ('Build', 'Upgrade', 'FreeAction'):
                continue
            after = resources(json.loads(env.snapshot_json()), seat)
            delta = {k: after.get(k, 0) - before.get(k, 0) for k in before}
            arm = 'A' if seat in result['a_seats'] else 'B'
            faction = state['players'][seat]['faction']
            key = (arm, faction)
            where = (str(game_dir.relative_to(run_dir)), row['decision_id'], state['round'], faction, arm)
            if kind == 'Build':
                paid = -delta.get('ore', 0)
                build_ore[key][paid] += 1
                if paid >= 3:
                    big['ore'].append(where)
            elif kind == 'Upgrade' and 'TradingStation' in json.dumps(action):
                paid = -delta.get('credits', 0)
                ts_credits[key][paid] += 1
                if paid >= 6:
                    big['credits'].append(where)
            elif kind == 'FreeAction':
                name = action['kind'] if isinstance(action['kind'], str) else json.dumps(action['kind'])
                free[key][name] += action.get('count', 1)
                first_free.setdefault(name, where)
    print(f'rounds {low}-{high}  games {games}')
    for arm in ('A', 'B'):
        for faction in sorted({f for a, f in list(build_ore) + list(ts_credits) + list(free) if a == arm}):
            key = (arm, faction)
            print(f'{arm} {faction}')
            print(f'  Build ore paid {show(build_ore[key])}')
            print(f'  TS credits paid {show(ts_credits[key])}')
            print(f'  free {show(free[key])}')
    print('examples')
    for name, where in sorted(first_free.items()):
        print(f'  free {name}: {where}')
    if args.examples:
        for label, paid in (('Build ore>=3', big['ore']), ('TS credits>=6', big['credits'])):
            print(label)
            for where in paid[:5]:
                print(f'  {where}')


if __name__ == '__main__':
    main()
