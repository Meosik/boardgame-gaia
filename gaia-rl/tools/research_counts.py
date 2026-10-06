"""Count research advances per arm, faction and track over a lab/teacher_ab run.

Counts ResearchAdvance moves and the advance_track of tech-tile choices, split by round range.

  .venv/bin/python tools/research_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-035-... [--rounds 1-2]
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

TRACKS = ['Terraforming', 'Navigation', 'ArtificialIntelligence', 'GaiaProject', 'Economy', 'Science']


def advanced_track(action):
    if not isinstance(action, dict):
        return None
    if action.get('type') == 'ResearchAdvance':
        return action.get('track')
    choice = action.get('tech_tile_choice')
    if isinstance(choice, dict):
        return choice.get('advance_track')
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-6')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    counts = Counter()
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if state['round'] > high:
                break
            if state['round'] >= low:
                track = advanced_track(snapshot['candidates'][row['index']]['action'])
                if track:
                    seat = snapshot['player']
                    arm = 'A' if seat in result['a_seats'] else 'B'
                    counts[(arm, state['players'][seat]['faction'], track)] += 1
            env.step(row['decision_id'], row['index'])
    factions = sorted({faction for _, faction, _ in counts})
    short = {'Terraforming': 'TF', 'Navigation': 'Nav', 'ArtificialIntelligence': 'AI',
             'GaiaProject': 'Gaia', 'Economy': 'Eco', 'Science': 'Sci'}
    print(f"rounds {low}-{high}  " + ' '.join(f'{short[t]:>5}' for t in TRACKS))
    for arm in ('A', 'B'):
        for faction in factions:
            print(f'{arm} {faction:<9}  ' + ' '.join(f'{counts[(arm, faction, t)]:>5}' for t in TRACKS))


if __name__ == '__main__':
    main()
