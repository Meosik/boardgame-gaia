"""List the moves of a lab/teacher_ab game: frame, round, seat, faction, arm, move.

Frame = decision number in the replay viewer (the --step of explain_decision.py).

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:tools .venv/bin/python tools/list_decisions.py \\
    ~/projects/gaia-lab/gaia-rl/runs/lab-035-.../pair-001/game-0-A23 [--rounds 0-2] [--seat N]
"""
import argparse
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

from explain_decision import short  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game_dir', type=Path)
    parser.add_argument('--rounds', default='0-2', help='Round range, inclusive (0 = setup)')
    parser.add_argument('--seat', type=int)
    args = parser.parse_args()
    from gaia_rl import Environment
    game_dir = args.game_dir.expanduser()
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for step, row in enumerate(rows):
        snapshot = json.loads(env.snapshot_json())
        state = snapshot['state']
        seat = snapshot['player']
        if state['round'] > high:
            break
        if state['round'] >= low and (args.seat is None or seat == args.seat):
            player = state['players'][seat]
            arm = 'A' if seat in result['a_seats'] else 'B'
            action = snapshot['candidates'][row['index']]['action']
            print(f"{step:4d} R{state['round']} s{seat} {player['faction']:<8} {arm} "
                  f"vp{player['vp']:<4} {short(action, 120)}")
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
