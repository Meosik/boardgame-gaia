"""Count standard tech tiles taken per arm and faction over a lab/teacher_ab run.

Companion of upgrade_counts.py: answers "which tiles did Itars take on each arm" (091 tile_prefs
activation check) without listing decisions. Moves are replayed from the seed like upgrade_counts.py
(the decision log holds indices only). Engine tile ids: 2 ore+charge income, 3 four credits income,
4 ore+QIC now, 5 knowledge+credit income, 6 big buildings power 4, 7 VP now, 8 VP per Gaia mine,
9 knowledge per planet type, 10 charge-4 action; Advanced tiles are counted under 'adv'.

  .venv/bin/python tools/tile_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-091-... [--rounds 1-3]
"""
import argparse
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

TILES = list(range(1, 11)) + ['adv']


def tile_of(action):
    choice = action.get('tech_tile_choice')
    if not isinstance(choice, dict):
        return None
    if choice.get('kind') == 'Standard':
        return choice.get('tile')
    return 'adv'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-3')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    counts = Counter()
    seats = Counter()
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        for seat, faction in enumerate(result['factions']):
            seats[('A' if seat in result['a_seats'] else 'B', faction)] += 1
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if state['round'] > high:
                break
            action = snapshot['candidates'][row['index']]['action']
            tile = tile_of(action)
            if state['round'] >= low and tile is not None:
                seat = snapshot['player']
                arm = 'A' if seat in result['a_seats'] else 'B'
                counts[(arm, state['players'][seat]['faction'], tile)] += 1
            env.step(row['decision_id'], row['index'])
    factions = sorted({faction for _, faction in seats})
    print(f"rounds {low}-{high}  (seat-games per row in parentheses)")
    print(f"{'':22s}" + ' '.join(f'{str(t):>4}' for t in TILES) + '  total')
    for arm in ('A', 'B'):
        for faction in factions:
            label = f"{arm} {faction:<12} ({seats[(arm, faction)]})"
            row = [counts[(arm, faction, t)] for t in TILES]
            print(f'{label:22s}' + ' '.join(f'{n:>4}' for n in row) + f'  {sum(row):>5}')


if __name__ == '__main__':
    main()
