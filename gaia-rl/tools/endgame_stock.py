"""End-of-game stock per arm and faction, and the late free actions that turned stock into VP, in a lab run.

Cycle 096 (endgame_prices): in round 6 the B arm prices its stock at the final-scoring rates (1 VP per 3 ore +
credits + knowledge, QIC and power 0). Replays every complete game and reads, per seat: the stock held at the
last decision (ore / credits / knowledge / QIC / power in bowl 3), what the final scoring pays for it, and the
FreeAction kinds played in the given rounds (QicToOre, PowerToCredit, ...), per arm and faction.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python \\
      tools/endgame_stock.py ~/projects/gaia-lab/gaia-rl/runs/lab-096-... [--rounds 5-6]
"""
import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

STOCK = ('ore', 'credits', 'knowledge', 'qic')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='5-6', help='rounds whose FreeAction kinds are counted')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    stock = defaultdict(lambda: defaultdict(float))
    kinds = defaultdict(Counter)
    games = 0
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        games += 1
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        arms = {}
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            seat = snapshot['player']
            arm = 'A' if seat in result['a_seats'] else 'B'
            arms[seat] = arm
            action = snapshot['candidates'][row['index']]['action']
            if low <= state['round'] <= high and action.get('type') == 'FreeAction':
                kinds[(arm, state['players'][seat]['faction'])][action.get('kind')] += 1
                kinds[(arm, 'ALL')][action.get('kind')] += 1
            env.step(row['decision_id'], row['index'])
        state = json.loads(env.snapshot_json())['state']
        for seat, player in enumerate(state['players']):
            arm = 'A' if seat in result['a_seats'] else 'B'
            res = player['resources']
            for key in ((arm, player['faction']), (arm, 'ALL')):
                r = stock[key]
                r['seats'] += 1
                for name in STOCK:
                    r[name] += res.get(name, 0)
                r['bowl3'] += res['power'].get('bowl3', 0) if isinstance(res.get('power'), dict) else 0
                r['stock_vp'] += (res.get('ore', 0) + res.get('credits', 0) + res.get('knowledge', 0))//3
    print(f'games {games}; per seat-game means at the last decision (before final scoring)')
    print(f"{'':16s}{'seats':>6}{'ore':>6}{'cred':>6}{'knw':>6}{'QIC':>6}{'bowl3':>6}{'stockVP':>8}")
    for key in sorted(stock, key=lambda k: (k[0], k[1] != 'ALL', k[1])):
        r = stock[key]
        n = r['seats']
        print(f"{key[0]+' '+key[1]:16s}{int(n):>6}{r['ore']/n:>6.1f}{r['credits']/n:>6.1f}{r['knowledge']/n:>6.1f}"
              f"{r['qic']/n:>6.1f}{r['bowl3']/n:>6.1f}{r['stock_vp']/n:>8.1f}")
    print(f'\nFreeAction kinds in rounds {low}-{high} (seat-game totals)')
    for key in sorted(kinds, key=lambda k: (k[0], k[1] != 'ALL', k[1])):
        items = ', '.join(f'{kind} {n}' for kind, n in kinds[key].most_common())
        print(f"{key[0]+' '+key[1]:16s}{items}")


if __name__ == '__main__':
    main()
