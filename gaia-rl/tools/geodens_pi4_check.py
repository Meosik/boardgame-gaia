"""Where does teacher_patches.geodens_pi4_ready hold? Checks Geodens' first round-1 decision of
every game in a lab/teacher_ab run and prints the facts behind the answer.

  .venv/bin/python tools/geodens_pi4_check.py ~/projects/gaia-lab/gaia-rl/runs/lab-035-...
"""
import argparse
import gzip
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    from gaia_rl import Environment
    from four_factions.value import targets
    from teacher_patches import GEODENS_NEW_TYPES, geodens_pi4_ready
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state, actor = snapshot['state'], snapshot['player']
            player = state['players'][actor]
            if state['round'] == 1 and player['faction'] == 'Geodens':
                unlimited = {**player, 'resources': {**player['resources'], 'qic': 99}}
                reach = {t: min((q for _, _, q in targets(state, unlimited, (t,))), default=None)
                         for t in (*GEODENS_NEW_TYPES, 'Gaia')}
                power = player['resources']['power']
                arm = 'A' if actor in result['a_seats'] else 'B'
                print(f"{game_dir.parent.name}/{game_dir.name} {arm} vp_end={result['scores'][str(actor)]:<4} "
                      f"ready={geodens_pi4_ready(snapshot)!s:<5} qic_needed(red,yellow,gaia)={reach} "
                      f"qic={player['resources']['qic']} booster={player['booster']} "
                      f"power={power['bowl1']}/{power['bowl2']}/{power['bowl3']}")
                break
            env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
