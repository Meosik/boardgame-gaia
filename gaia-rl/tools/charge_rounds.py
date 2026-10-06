"""Charges gained in rounds 1-3 per arm and faction over a lab/teacher_ab run.

User (2026-10-06): report A/B results by the power charges a seat collected in rounds 1-3, with
buildings, resources, research and VP all converted to charges. Each seat is valued with the
guide value (LF prices, guide_r1 settings: QIC and research levels priced once) at the first
decision of round 1 and of round 4; VP held count at 1.5 charges each. Final-goal standings and
the held booster's pass VP are left out (projections, not gains). Pairs are the two seat-swapped
games of a seed, as in teacher_ab.

  .venv/bin/python tools/charge_rounds.py ~/projects/gaia-lab/gaia-rl/runs/lab-036-... [--games]
"""
import argparse
import gzip
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]

START_ROUND, END_ROUND = 1, 4


def charges(state, seat):
    import guide_value as gv
    import teacher_patches as tp
    vp = tp.charge_value(state, seat) + state['players'][seat]['vp']
    return vp*gv.CHARGES_PER_VP[4]


def game_charges(game_dir):
    """{seat: (charges at round 1, charges at round 4)} or None if round 4 is never reached."""
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    start = None
    for row in rows:
        state = json.loads(env.snapshot_json())['state']
        seats = range(len(state['players']))
        if start is None and state['round'] >= START_ROUND:
            start = {s: charges(state, s) for s in seats}
        if state['round'] >= END_ROUND:
            return result, {s: (start[s], charges(state, s)) for s in seats}
        env.step(row['decision_id'], row['index'])
    return result, None


def ci95(values):
    from scipy import stats
    n = len(values)
    mean = sum(values)/n
    if n < 2:
        return mean, (math.nan, math.nan)
    sd = math.sqrt(sum((v-mean)**2 for v in values)/(n-1))
    half = stats.t.ppf(.975, n-1)*sd/math.sqrt(n)
    return mean, (mean-half, mean+half)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--games', action='store_true', help='Also print every game')
    args = parser.parse_args()
    import teacher_patches as tp
    tp._guide.update(qic_reach=False, track_income=False)
    gained = defaultdict(dict)   # (pair, faction) -> {arm: charges gained}
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result, values = game_charges(game_dir)
        if values is None:
            continue
        factions = {s: f for s, f in enumerate(result.get('factions') or [])}
        if not factions:
            from gaia_rl import Environment
            state = json.loads(Environment(result['seed'], 2000).snapshot_json())['state']
            factions = {s: p['faction'] for s, p in enumerate(state['players'])}
        line = []
        for seat, (r1, r4) in values.items():
            arm = 'A' if seat in result['a_seats'] else 'B'
            gained[(game_dir.parent.name, factions[seat])][arm] = r4-r1
            line.append(f'{factions[seat]}({arm}) {r4-r1:.0f}')
        if args.games:
            print(f'{game_dir.parent.name}/{game_dir.name}  ' + ', '.join(line))
    print('Charges gained, rounds 1-3 (round-1 start to round-4 start, 1 VP = 1.5 charges)')
    print(f"{'faction':<9} {'pairs':>5} {'A':>7} {'B':>7} {'B-A':>7}  95% CI")
    every = defaultdict(list)
    for faction in sorted({f for _, f in gained}):
        rows = [arms for (_, f), arms in gained.items() if f == faction and len(arms) == 2]
        diffs = [arms['B']-arms['A'] for arms in rows]
        for (pair, f), arms in gained.items():
            if f == faction and len(arms) == 2:
                every[pair].append(arms['B']-arms['A'])
        mean, (low, high) = ci95(diffs)
        a = sum(r['A'] for r in rows)/len(rows)
        b = sum(r['B'] for r in rows)/len(rows)
        print(f'{faction:<9} {len(rows):>5} {a:>7.1f} {b:>7.1f} {mean:>+7.1f}  [{low:+.1f}, {high:+.1f}]')
    seat_means = [sum(d)/len(d) for d in every.values()]
    mean, (low, high) = ci95(seat_means)
    print(f"{'ALL':<9} {len(seat_means):>5} {'':>7} {'':>7} {mean:>+7.1f}  [{low:+.1f}, {high:+.1f}]")


if __name__ == '__main__':
    main()
