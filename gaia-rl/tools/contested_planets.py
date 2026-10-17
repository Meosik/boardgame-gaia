"""Planet competition per seat and round over a lab/teacher_ab run.

User (2026-10-18): "항해술을 나중에 올려도 땅 뺏길 걱정이 없다 싶을 때 올리는 게 경제" — the signal that
decides Economy-before-Navigation is whether the planets a seat wants can be taken by someone else.
At the start of each round (the seat's first decision of that round) the seat's cheap targets are
the empty planets of its home type, the ring types one terraforming step away, Gaia and Transdim
planets, within its range plus the QIC it holds (four_factions.value.targets). Counted:

  reach      cheap targets now
  contested  of those, the ones an opponent also has among its own cheap targets
  safe       reach - contested
  lost       planets in reach at the round start that another player owns at the next round start
             (or at the end of the game for round 6)

Means per arm, faction and round; --games prints every seat.

  .venv/bin/python tools/contested_planets.py ~/projects/gaia-lab/gaia-rl/runs/lab-071-... [--rounds 1-6] [--games]
"""
import argparse
import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]


def cheap_types(home):
    from economy.teacher import RING
    types = {home, 'Gaia', 'Transdim'}
    if home in RING:
        i = RING.index(home)
        types |= {RING[(i-1) % len(RING)], RING[(i+1) % len(RING)]}
    return tuple(types)


def home_type(player):
    from four_factions import value
    from faction_teachers.profiles import profiles
    return value.HOME.get(player['faction']) or profiles()[player['faction']].home


def cheap_reach(state, player):
    from four_factions.value import targets
    return {coord for coord, _, _ in targets(state, player, cheap_types(home_type(player)))}


def round_start_counts(state, seat):
    player = state['players'][seat]
    mine = cheap_reach(state, player)
    theirs = set()
    for other in state['players']:
        if other is not player:
            theirs |= cheap_reach(state, other)
    contested = mine & theirs
    return mine, {'reach': len(mine), 'contested': len(contested), 'safe': len(mine - contested)}


def lost_since(state, seat, reach):
    me = state['players'][seat]['player_id']
    hexes = state['board']['hexes']
    return sum(1 for coord in reach
               if hexes[coord]['planet'] is not None and hexes[coord]['planet']['owner'] not in (None, me))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--rounds', default='1-6')
    parser.add_argument('--games', action='store_true', help='print every seat')
    args = parser.parse_args()
    from gaia_rl import Environment
    low, _, high = args.rounds.partition('-')
    low, high = int(low), int(high or low)
    rows_out = []                                   # (game, arm, faction, round, counts)
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        seen = {}                                   # (seat, round) -> (reach set, counts dict)
        factions = {}
        for row in rows:
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            seat = snapshot['player']
            rnd = state['round']
            if 1 <= rnd <= 6 and 'ActionPhase' in state['phase'] and seat is not None and (seat, rnd) not in seen:
                factions[seat] = state['players'][seat]['faction']
                if (seat, rnd-1) in seen:
                    reach, counts = seen[(seat, rnd-1)]
                    counts['lost'] = lost_since(state, seat, reach)
                seen[(seat, rnd)] = round_start_counts(state, seat)
            env.step(row['decision_id'], row['index'])
        state = json.loads(env.snapshot_json())['state']
        for (seat, rnd), (reach, counts) in seen.items():
            if 'lost' not in counts:
                counts['lost'] = lost_since(state, seat, reach)
            if low <= rnd <= high:
                arm = 'A' if seat in result['a_seats'] else 'B'
                rows_out.append((game_dir.parent.name+'/'+game_dir.name, arm, factions[seat], rnd, counts))
    keys = ('reach', 'contested', 'safe', 'lost')
    if args.games:
        for game, arm, faction, rnd, counts in sorted(rows_out):
            print(f'{game}  {arm} {faction:<9} R{rnd}  ' + '  '.join(f'{k} {counts[k]:>2}' for k in keys))
        print()
    sums = defaultdict(lambda: defaultdict(float))
    n = defaultdict(int)
    for _, arm, faction, rnd, counts in rows_out:
        n[(arm, faction, rnd)] += 1
        for k in keys:
            sums[(arm, faction, rnd)][k] += counts[k]
    print(f'arm faction    round  seats  ' + '  '.join(f'{k:>9}' for k in keys) + '   (means per seat at round start)')
    for arm in ('A', 'B'):
        for faction in sorted({f for _, f, _ in n}):
            for rnd in range(low, high+1):
                key = (arm, faction, rnd)
                if n[key]:
                    print(f'{arm}   {faction:<9}  R{rnd}    {n[key]:>3}   '
                          + '  '.join(f'{sums[key][k]/n[key]:>9.2f}' for k in keys))


if __name__ == '__main__':
    main()
