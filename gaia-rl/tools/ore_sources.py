"""Where the ore came from: sum of ore gains per source over a lab/teacher_ab run.

Replays every game with the engine and attributes each player's ore increase to the move that
produced it: the acting seat's move (free action, power action, tech tile, federation token, ...)
or, when the round changes, round income. Gains only; spending is not counted.

  .venv/bin/python tools/ore_sources.py ~/projects/gaia-lab/gaia-rl/runs/lab-066-... [--rounds 1-3]
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


def source_key(action):
    kind = action.get('type', '?')
    if kind == 'FreeAction':
        return f"FreeAction {action.get('kind')}"
    if kind == 'PowerAction':
        return f"PowerAction {action.get('id')}"
    if kind == 'Upgrade' and action.get('tech_tile_choice'):
        return 'Upgrade+tech tile'
    if kind == 'ResearchAdvance':
        return f"ResearchAdvance {action.get('track')}"
    return kind


def ore_of(state):
    return [p['resources']['ore'] for p in state['players']]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-3', help='Round range, inclusive (0 = setup)')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    gains = defaultdict(Counter)   # (arm, faction) -> source -> ore
    games = 0
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        games += 1
        snapshot = json.loads(env.snapshot_json())
        for row in rows:
            state = snapshot['state']
            seat = snapshot['player']
            if state['round'] > high:
                break
            action = snapshot['candidates'][row['index']]['action']
            before = ore_of(state)
            env.step(row['decision_id'], row['index'])
            snapshot = json.loads(env.snapshot_json())
            after_state = snapshot['state']
            after = ore_of(after_state)
            round_changed = after_state['round'] != state['round']
            counted_round = after_state['round'] if round_changed else state['round']
            if not low <= counted_round <= high:
                continue
            for i, player in enumerate(state['players']):
                delta = after[i] - before[i]
                if delta <= 0:
                    continue
                arm = 'A' if i in result['a_seats'] else 'B'
                if round_changed:
                    source = 'round income'
                elif i == seat:
                    source = source_key(action)
                else:
                    source = f'other seat: {source_key(action)}'
                gains[(arm, player['faction'])][source] += delta
    print(f'ore gained in rounds {low}-{high}, {games} games, summed over seats')
    totals = Counter()
    for (arm, faction), counter in sorted(gains.items()):
        total = sum(counter.values())
        print(f'\n{arm} {faction}: {total} ore')
        for source, ore in counter.most_common():
            print(f'  {ore:5d}  {100*ore/total:5.1f}%  {source}')
            totals[source] += ore
    grand = sum(totals.values())
    print(f'\nall seats: {grand} ore')
    for source, ore in totals.most_common():
        print(f'  {ore:5d}  {100*ore/grand:5.1f}%  {source}')


if __name__ == '__main__':
    main()
