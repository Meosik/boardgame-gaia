"""Count Upgrade targets (building kind) per arm, faction and round over a lab/teacher_ab run.

  .venv/bin/python tools/upgrade_targets.py ~/projects/gaia-lab/gaia-rl/runs/lab-064-... [--rounds 1-1] [--faction Geodens]
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
    parser.add_argument('--rounds', default='1-1')
    parser.add_argument('--faction', default=None)
    parser.add_argument('--verbose', action='store_true', help='print every matching upgrade')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    counts = Counter()
    per_game = {}
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        label = '/'.join(game_dir.parts[-2:])
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if state['round'] > high:
                break
            action = snapshot['candidates'][row['index']]['action']
            kind = action.get('type') if isinstance(action, dict) else None
            seat = snapshot['player']
            faction = state['players'][seat]['faction']
            if state['round'] >= low and kind == 'Upgrade' and (args.faction is None or faction == args.faction):
                arm = 'A' if seat in result['a_seats'] else 'B'
                target = json.dumps({k: v for k, v in action.items() if k not in ('type', 'coord')}, sort_keys=True)
                counts[(arm, faction, state['round'], target)] += 1
                per_game.setdefault((label, arm, faction), []).append((state['round'], target))
                if args.verbose:
                    print(label, arm, faction, 'R%d' % state['round'], json.dumps(action, sort_keys=True))
            env.step(row['decision_id'], row['index'])
    for key in sorted(counts):
        print(key, counts[key])
    print()
    for key in sorted(per_game):
        print(key, per_game[key])


if __name__ == '__main__':
    main()
