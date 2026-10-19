"""Who took the Lost Fleet extra Advanced Tech tile in lab/teacher_ab games.

User 2026-10-19 "저 조건의 고급기술을 먹는 판이 존재했나?": each game is replayed from its seed with
the logged decisions (no per-step snapshot, so it is fast), and the end state says whether the tile
left the Scoring Board Extension, which seat holds it, and that seat's explored ships.

  .venv/bin/python tools/lf_advanced_tile.py ~/projects/gaia-lab/gaia-rl/runs [--glob 'lab-*']
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
    parser.add_argument('runs', type=Path)
    parser.add_argument('--glob', default='lab-*')
    args = parser.parse_args()
    from gaia_rl import Environment
    games = taken = 0
    by_faction = Counter()
    for run in sorted(args.runs.expanduser().glob(args.glob)):
        for game_dir in sorted(run.glob('pair-*/game-*')):
            log = game_dir/'decisions.jsonl.gz'
            result_file = game_dir/'result.json'
            if not log.exists() or not result_file.exists():
                continue
            result = json.loads(result_file.read_text())
            env = Environment(result['seed'], 2000)
            start = json.loads(env.snapshot_json())['state']['research_board']
            tile = start.get('lost_fleet_advanced_tech_tile')
            try:
                with gzip.open(log, 'rt') as f:
                    for line in f:
                        row = json.loads(line)
                        env.step(row['decision_id'], row['index'])
            except Exception as error:   # a log that does not replay is reported, not fatal
                print(f'{game_dir}: replay stopped ({error})')
            games += 1
            state = json.loads(env.snapshot_json())['state']
            if tile is None or state['research_board'].get('lost_fleet_advanced_tech_tile') is not None:
                continue
            taken += 1
            for seat, player in enumerate(state['players']):
                if tile in player.get('advanced_tech_tiles', []):
                    arm = 'A' if seat in result.get('a_seats', []) else 'B'
                    by_faction[player['faction']] += 1
                    print(f"{game_dir.relative_to(args.runs.expanduser())}: round {state['round']} seat {seat} "
                          f"{player['faction']} ({arm}) ships {sorted(set(player.get('explored_ships', [])))} "
                          f"vp {player['vp']}")
    print(f'games {games}, tile taken in {taken}; by faction {dict(by_faction)}')


if __name__ == '__main__':
    main()
