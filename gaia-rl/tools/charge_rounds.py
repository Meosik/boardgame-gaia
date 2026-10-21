"""Charges gained in rounds 1-3 per arm and faction over a lab/teacher_ab run.

User (2026-10-06): report A/B results by the power charges a seat collected in rounds 1-3, with
buildings, resources, research and VP all converted to charges. Each seat is valued with the
guide value (LF prices, guide_r1 settings: QIC and research levels priced once) at the first
decision of round 1 and of round 4 (LF table values for ships, green federation tokens and pass
advanced tiles since 2026-10-07); VP held count at 1.5 charges each. Final-goal standings and
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
VP_RATE = None   # --vp-rate: charges per VP held (None = the guide rate, 1.5; 0 = VP left out)
# Income/Gaia pauses that can carry the new round number before the round's income is complete
# (review-000 finding 1: the engine's round-1 IncomeOrderPending already shows round 1, the
# round-4 one still shows round 3). Both snapshots must be taken after income and Gaia phase.
TRANSITION_PHASES = ('IncomeOrderPending', 'GaiaDecisionPending')


def round_started(state, round_number):
    """True once `round_number`'s income and Gaia phase are done (its first action-phase decision)."""
    phase = state['phase']
    name = phase if isinstance(phase, str) else next(iter(phase))
    return state['round'] >= round_number and name not in TRANSITION_PHASES


def charges(state, seat):
    import guide_value as gv
    import teacher_patches as tp
    if VP_RATE is None:
        return tp.charge_value(state, seat, with_vp=True)*gv.CHARGES_PER_VP[4]
    return tp.charge_value(state, seat, with_vp=False)*gv.CHARGES_PER_VP[4] + VP_RATE*state['players'][seat]['vp']


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
        if start is None and round_started(state, START_ROUND):
            start = {s: charges(state, s) for s in seats}
        if round_started(state, END_ROUND):
            return result, {s: (start[s], charges(state, s)) for s in seats}
        env.step(row['decision_id'], row['index'])
    state = json.loads(env.snapshot_json())['state']  # a game stopped at round 4 (teacher_ab --stop-round 3)
    if start is not None and round_started(state, END_ROUND):
        return result, {s: (start[s], charges(state, s)) for s in range(len(state['players']))}
    return result, None


def ci95(values):
    from scipy import stats
    n = len(values)
    if n == 0:
        return math.nan, (math.nan, math.nan)
    mean = sum(values)/n
    if n < 2:
        return mean, (math.nan, math.nan)
    sd = math.sqrt(sum((v-mean)**2 for v in values)/(n-1))
    half = stats.t.ppf(.975, n-1)*sd/math.sqrt(n)
    return mean, (mean-half, mean+half)


def summarize(gained):
    """{faction: row} + 'ALL' from {(pair, faction): {arm: charges gained}}.

    A faction whose every pair is missing one arm (the other game never reached round 4) gets a
    row with 0 pairs instead of stopping the whole table (review-000 finding 3)."""
    every = defaultdict(list)   # pair -> [B-A per seat] for the seat-mean line
    table = {}
    for faction in sorted({f for _, f in gained}):
        rows = [arms for (_, f), arms in gained.items() if f == faction and len(arms) == 2]
        diffs = [arms['B']-arms['A'] for arms in rows]
        for (pair, f), arms in gained.items():
            if f == faction and len(arms) == 2:
                every[pair].append(arms['B']-arms['A'])
        mean, (low, high) = ci95(diffs)
        a = sum(r['A'] for r in rows)/len(rows) if rows else math.nan
        b = sum(r['B'] for r in rows)/len(rows) if rows else math.nan
        table[faction] = {'pairs': len(rows), 'A': a, 'B': b, 'mean_B_minus_A': mean, 'ci95': [low, high]}
    seat_means = [sum(d)/len(d) for d in every.values()]
    mean, (low, high) = ci95(seat_means)
    table['ALL'] = {'pairs': len(seat_means), 'mean_B_minus_A': mean, 'ci95': [low, high]}
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--games', action='store_true', help='Also print every game')
    parser.add_argument('--json', type=Path, help='Also write the table and games here (lab.py reads it)')
    parser.add_argument('--vp-rate', type=float,
                        help='Charges per VP held (default the guide rate 1.5; 0 leaves VP out). '
                             'Only the measure changes, not what the teachers played.')
    args = parser.parse_args()
    global VP_RATE
    VP_RATE = args.vp_rate
    import teacher_patches as tp
    tp._guide.update(qic_reach=False, track_income=False, lf_tables=True)
    gained = defaultdict(dict)   # (pair, faction) -> {arm: charges gained}
    games = []
    seats = {}   # 'pair-000/game-0-A02' -> [{'faction', 'arm', 'charges'} per seat] (lab.py picks a replay)
    # Rounds 1-3 are complete once round 4 starts, so a game that failed later still counts here
    # (unlike the final-VP table, which needs the whole game); the count is reported, not hidden.
    incomplete = 0
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result, values = game_charges(game_dir)
        if values is None:
            continue
        incomplete += not result.get('complete', True)
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
            seats.setdefault(f'{game_dir.parent.name}/{game_dir.name}', []).append(
                {'faction': factions[seat], 'arm': arm, 'charges': r4-r1})
        games.append(f'{game_dir.parent.name}/{game_dir.name}  ' + ', '.join(line))
        if args.games:
            print(games[-1])
    rate = 1.5 if VP_RATE is None else VP_RATE
    print(f'Charges gained, rounds 1-3 (round-1 start to round-4 start, 1 VP = {rate:g} charges; '
          f'{len(games)} games reached round 4, {incomplete} of them did not finish)')
    print(f"{'faction':<9} {'pairs':>5} {'A':>7} {'B':>7} {'B-A':>7}  95% CI")
    table = summarize(gained)
    for faction, r in table.items():
        low, high = r['ci95']
        a, b = (f"{r[arm]:7.1f}" if arm in r else ' '*7 for arm in 'AB')
        print(f"{faction:<9} {r['pairs']:>5} {a} {b} {r['mean_B_minus_A']:>+7.1f}  [{low:+.1f}, {high:+.1f}]")
    if args.json:
        args.json.write_text(json.dumps({'factions': table, 'games': games, 'seats': seats,
                                         'games_incomplete': incomplete}, indent=1)+'\n')


if __name__ == '__main__':
    main()
