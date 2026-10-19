"""Count Upgrade moves by target building per arm and faction over a lab/teacher_ab run.

Companion of action_counts.py (which counts move types only): answers "how many round-1 academies
did Taklons finish on each arm" (077 "AC 6/6", 084 faction-table verdict) without listing decisions.
Moves are replayed from the seed like action_counts.py (the decision log holds indices only).

  .venv/bin/python tools/upgrade_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-084-... [--rounds 1-1]
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

TARGETS = ['TradingStation', 'ResearchLab', 'PlanetaryInstitute', 'Academy']


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-1')
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
            if state['round'] >= low and action.get('type') == 'Upgrade':
                target = action.get('to')
                if isinstance(target, dict):
                    target = next(iter(target))
                seat = snapshot['player']
                arm = 'A' if seat in result['a_seats'] else 'B'
                counts[(arm, state['players'][seat]['faction'], target)] += 1
            env.step(row['decision_id'], row['index'])
    factions = sorted({faction for _, faction in seats})
    print(f"rounds {low}-{high}  (seat-games per row in parentheses)")
    print(f"{'':16s}" + ' '.join(f'{t:>18}' for t in TARGETS))
    for arm in ('A', 'B'):
        for faction in factions:
            label = f"{arm} {faction:<8} ({seats[(arm, faction)]})"
            print(f'{label:16s}' + ' '.join(f'{counts[(arm, faction, t)]:>18}' for t in TARGETS))


if __name__ == '__main__':
    main()
