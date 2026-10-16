"""List the moves of a lab/teacher_ab game: step, round, seat, faction, arm, move.

The first column is the 0-based decision step — the --step of explain_decision.py and the
--steps of explain_ab_decisions.py. The replay viewer's frame number is step + 1
(explain_ab_decisions prints "step N (frame N+1)"). Steps count every seat's decisions,
so --steps 52 after a seat-1 move at step 51 is usually another seat's decision.

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


def _qr(coord):
    if isinstance(coord, str):
        q, r = coord.split(',')
        return int(q), int(r)
    return coord['q'], coord['r']


def sector_of(state, coord):
    """Sector tile number of a hex (the user's "N번 스타트" = a start on sector N's home planet)."""
    q, r = _qr(coord)
    for sector in state['board'].get('sectors', []):
        oq, or_ = _qr(sector['origin'])
        if (abs(q-oq)+abs(r-or_)+abs(q+r-oq-or_))//2 <= 2:
            return sector['id']
    return None


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
            line = (f"{step:4d} R{state['round']} s{seat} {player['faction']:<8} {arm} "
                    f"vp{player['vp']:<4} {short(action, 120)}")
            if action.get('type') == 'PlaceStartingStructure':
                options = sorted((sector_of(state, c['action']['coord']) or 0, c['action']['coord'])
                                 for c in snapshot['candidates'] if c['action'].get('type') == 'PlaceStartingStructure')
                line += (f"  sector {sector_of(state, action['coord'])} (open: "
                         + ', '.join(f'{sector}={coord}' for sector, coord in options) + ')')
            print(line)
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
