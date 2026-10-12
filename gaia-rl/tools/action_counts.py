"""Count moves of given types per arm and faction over a lab/teacher_ab run.

  .venv/bin/python tools/action_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-048-... \\
      --types FormFederation ExploreSpaceship Build Upgrade Pass [--rounds 1-3]
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--types', nargs='+', required=True)
    parser.add_argument('--rounds', default='1-3')
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
            kind = snapshot['candidates'][row['index']]['action'].get('type')
            if state['round'] >= low and kind in args.types:
                seat = snapshot['player']
                arm = 'A' if seat in result['a_seats'] else 'B'
                counts[(arm, state['players'][seat]['faction'], kind)] += 1
            env.step(row['decision_id'], row['index'])
    factions = sorted({faction for _, faction, _ in counts})
    width = max(len(t) for t in args.types)
    print(f"rounds {low}-{high}  " + ' '.join(f'{t:>{width}}' for t in args.types))
    for arm in ('A', 'B'):
        for faction in factions:
            print(f'{arm} {faction:<9}  ' + ' '.join(f'{counts[(arm, faction, t)]:>{width}}' for t in args.types))


if __name__ == '__main__':
    main()
