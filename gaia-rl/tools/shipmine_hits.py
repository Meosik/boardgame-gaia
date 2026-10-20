"""Where did the ship_adjacent_mine condition hold in a lab run, and what did each arm play there?

Condition (teacher_patches.ship_adjacent_mine_scores): an ExploreSpaceship candidate whose range needs
QIC > 0, and a Build candidate on a non-gaiaformed ring planet 0-1 steps from home at hex distance 1 from
that ship tile whose own range QIC is <= the entry's. Scores (blocked / value order) are not reproduced:
this lists opportunities per decision and what was chosen, not the swaps themselves.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python \\
      tools/shipmine_hits.py ~/projects/gaia-lab/gaia-rl/runs/lab-095-... [--rounds 1-3]
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
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]


def _qr(coord):
    if isinstance(coord, str):
        q, r = coord.split(',')
        return int(q), int(r)
    return coord['q'], coord['r']


def hexdist(a, b):
    aq, ar = _qr(a)
    bq, br = _qr(b)
    return (abs(aq-bq) + abs(ar-br) + abs(aq+ar-bq-br)) // 2


def _rows(game_dir):
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        return [json.loads(line) for line in f]


def first_split(run_dir, Environment):
    """Same seed, arms swapped: the first differing decision is where one arm (or timing noise) changed a move."""
    for pair_dir in sorted(run_dir.glob('pair-*')):
        games = sorted(pair_dir.glob('game-*'))
        if len(games) != 2:
            continue
        results = [json.loads((g/'result.json').read_text()) for g in games]
        rows = [_rows(g) for g in games]
        env = Environment(results[0]['seed'], 2000)
        split = None
        for k, (r0, r1) in enumerate(zip(rows[0], rows[1])):
            snap = json.loads(env.snapshot_json())
            if r0['index'] != r1['index'] or r0['decision_id'] != r1['decision_id']:
                state = snap['state']
                seat = snap['player']
                cands = snap['candidates']
                arm0 = 'A' if seat in results[0]['a_seats'] else 'B'
                a0 = json.dumps(cands[r0['index']]['action'], sort_keys=True) if r0['index'] < len(cands) else '?'
                a1 = json.dumps(cands[r1['index']]['action'], sort_keys=True) if r1['index'] < len(cands) else '?'
                split = (f"{pair_dir.name} first split at step {r0['step']} R{state['round']} seat {seat} "
                         f"{state['players'][seat]['faction']} ({games[0].name}={arm0}, cmp {r0['completed_comparisons']}"
                         f"/{r1['completed_comparisons']}):\n   {games[0].name}: {a0[:150]}\n   {games[1].name}: {a1[:150]}")
                break
            env.step(r0['decision_id'], r0['index'])
        print(split or f'{pair_dir.name}: identical through the recorded decisions')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-3')
    parser.add_argument('--first-split', action='store_true',
                        help='per pair, print the first decision where game-0 and game-1 (seats swapped) differ')
    args = parser.parse_args()
    from gaia_rl import Environment
    if args.first_split:
        return first_split(args.run_dir.expanduser(), Environment)
    from economy.teacher import RING, HOME, range_qic
    from faction_teachers.profiles import profiles
    prof = profiles()

    def home_type(player):
        return HOME.get(player['faction']) or prof[player['faction']].home

    def ring_steps(home, planet):
        if home not in RING or planet.get('planet_type') not in RING:
            return None
        gap = abs(RING.index(home) - RING.index(planet['planet_type']))
        return min(gap, 7-gap)

    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    tally = Counter()
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for row in rows:
            snap = json.loads(env.snapshot_json())
            state = snap['state']
            if state['round'] > high:
                break
            if state['round'] >= low and 'ActionPhase' in state['phase']:
                seat = snap['player']
                player = state['players'][seat]
                arm = 'A' if seat in result['a_seats'] else 'B'
                cands = snap['candidates']
                tiles = state['board'].get('spaceship_tiles', {})
                entries = []
                for c in cands:
                    a = c['action']
                    if a.get('type') == 'ExploreSpaceship' and a.get('ship') in tiles:
                        q = range_qic(state, player, tiles[a['ship']])
                        if q > 0:
                            entries.append((q, a['ship']))
                opp = []
                if entries:
                    home = home_type(player)
                    for q, ship in entries:
                        for c in cands:
                            a = c['action']
                            coord = a.get('coord')
                            if a.get('type') != 'Build' or coord is None:
                                continue
                            if hexdist(coord, tiles[ship]) != 1:
                                continue
                            planet = (state['board']['hexes'].get(coord) or {}).get('planet')
                            if not planet or planet.get('is_gaia_formed'):
                                continue
                            s = ring_steps(home, planet)
                            if s is None or s > 1 or range_qic(state, player, coord) > q:
                                continue
                            opp.append((ship, q, coord, s))
                if opp:
                    chosen = cands[row['index']]['action']
                    kind = chosen.get('type')
                    if kind == 'ExploreSpaceship' and any(chosen.get('ship') == o[0] for o in opp):
                        what = 'ENTRY-QIC'
                    elif kind == 'Build' and any(chosen.get('coord') == o[2] for o in opp):
                        what = 'ADJ-MINE'
                    else:
                        what = 'other:' + str(kind)
                    tally[(arm, what)] += 1
                    print(f"{game_dir.parent.name}/{game_dir.name} step {row['step']} R{state['round']} seat {seat} "
                          f"{player['faction']:<8} {arm} -> {what:<14} opp={opp} cmp={row['completed_comparisons']}")
            env.step(row['decision_id'], row['index'])
    print()
    for key in sorted(tally):
        print(key, tally[key])


if __name__ == '__main__':
    main()
