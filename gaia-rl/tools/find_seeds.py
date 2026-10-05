"""Print fixed-quartet seeds in a numeric range (Python twin of examples/faction_lineups.rs).

  .venv/bin/python tools/find_seeds.py 400000 600000 >> lab/seeds.txt

Same rule as the Rust example: geo-quartet-<n> whose native lineup contains all four
factions (default Xenos, Taklons, Terrans, Geodens).
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'python'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start', type=int)
    parser.add_argument('stop', type=int)
    parser.add_argument('--prefix', default='geo-quartet')
    parser.add_argument('--factions', default='Xenos,Taklons,Terrans,Geodens')
    args = parser.parse_args()
    from gaia_rl import Environment
    targets = set(args.factions.split(','))
    for n in range(args.start, args.stop):
        seed = f'{args.prefix}-{n}'
        players = json.loads(Environment(seed, 2000).snapshot_json())['state']['players']
        if targets <= {p['faction'] for p in players}:
            print(seed, flush=True)


if __name__ == '__main__':
    main()
