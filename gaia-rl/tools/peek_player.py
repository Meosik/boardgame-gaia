"""Print one seat's formers, power and the planet types of its structures after a decision.

  .venv/bin/python tools/peek_player.py <game_dir> --step N --seat S
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game_dir', type=Path)
    parser.add_argument('--step', type=int, required=True, help='Show the state after this decision')
    parser.add_argument('--seat', type=int, required=True)
    args = parser.parse_args()
    from gaia_rl import Environment
    game_dir = args.game_dir.expanduser()
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows[:args.step+1]:
        env.step(row['decision_id'], row['index'])
    state = json.loads(env.snapshot_json())['state']
    player = state['players'][args.seat]
    keys = ('gaiaformers_total', 'gaiaformers_deployed', 'gaiaformers_in_gaia_area', 'tech_tiles')
    print({k: player.get(k) for k in keys}, 'spent', player['resources'].get('spent_gaia_formers'))
    print('power', player['resources']['power'], 'research', player['research_tracks'])
    for s in player['structures']:
        cell = state['board']['hexes'].get(s['hex']) or {}
        print(s['hex'], s['kind'], (cell.get('planet') or {}).get('planet_type'))


if __name__ == '__main__':
    main()
