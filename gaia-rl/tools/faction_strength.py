"""Expected faction strength on a seed's map and the turn order it gives (user 2026-10-25 night, HANDOFF E117).

"게임 시작 전 잘 풀릴 것 같은 종족부터 4·3·2·1턴": the strongest faction moves last. Features, all from the setup state
before any placement (a faction's candidate starts are the free planets of its home type):
  tier     SH09 expansion tier table (sources.md:53): A 4, B 3, C 2, D 1, F 0.
  planets  cheap planets within 3 of the two best candidate starts (home type or one step; Gaia/Transdim for a
           Gaia-track faction; Asteroid/proto for Lost Fleet factions).
  techs    standard tiles under the faction's tracks that it prefers (TILE_PREFS, the charge-4 tile) plus good
           advanced tiles (GOOD_ADVANCED) on those tracks.
  ships    ships within SHIP_SETUP_RANGE of the best start, the tech-federation ship counting double.
  power    other factions' home-type planets within 2 of the best start (charges from neighbours).
  rounds   round tiles 1-3 and the two final goals that fit the faction (ROUND_FIT, bot's first reading; to be
           replaced by the faction round-scoring claims).
Each feature is turned into a z-score over the four seats and summed with WEIGHTS (equal at first; a later
regression on lab games is meant to set them). The order lists seats weakest first.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools \\
    gaia-rl/.venv/bin/python gaia-rl/tools/faction_strength.py quartet-d-113082 geo-quartet-1075607 [--table]

Prints one `<seed>@order=a,b,c,d` per seed (the engine reads it, gaia-rl/src/env.rs split_order).
"""
import argparse
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

TIER = {'Ivits': 4, 'Bescods': 4, 'Ambas': 4, 'Xenos': 4,
        'Gleens': 3, 'Firaks': 3, 'HadschHallas': 3,
        'Moweyds': 2, 'Geodens': 2, 'Taklons': 2, 'Nevlas': 2, 'SpaceGiants': 2, 'Itars': 2,
        'Lantids': 1, 'Terrans': 1, 'BalTaks': 1, 'Tinkeroids': 1,
        'Darkanians': 0}
TRACKS = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')   # tech_tile_slots / advanced order
LOST_FLEET = {'Moweyds', 'SpaceGiants', 'Tinkeroids', 'Darkanians'}
# Bot's first reading of which round / final conditions suit a faction (no source table yet).
ROUND_FIT = {
    'BuildMineOnGaia': {'Terrans', 'Gleens', 'Itars', 'Nevlas', 'Xenos', 'Ivits'},
    'TerraformingStep': {'Geodens', 'Gleens', 'Darkanians', 'Tinkeroids'},
    'UpgradeLargeBuilding': {'Ivits', 'Lantids', 'Nevlas', 'SpaceGiants', 'Tinkeroids', 'Geodens', 'Bescods'},
    'UpgradeResearchLab': {'Bescods', 'Firaks', 'Xenos', 'Taklons', 'Nevlas', 'Moweyds'},
    'ResearchAdvance': {'Bescods', 'Nevlas', 'Firaks', 'Itars'},
    'BuildMineOnNewPlanetType': {'Geodens', 'Moweyds', 'Gleens'},
    'BuildMineInNewSector': {'Ivits', 'Lantids', 'Darkanians', 'SpaceGiants'},
    'FormFederation': {'Ivits', 'Taklons', 'Xenos'},
    'UpgradeTradingStation': {'HadschHallas', 'Ambas', 'BalTaks'},
    'MostAsteroids': LOST_FLEET | {'Ambas'},
    'MostSatellites': {'Ivits', 'Taklons', 'Xenos'},
    'MostGaiaPlanets': {'Terrans', 'Gleens', 'Itars', 'Nevlas'},
    'MostPlanetTypes': {'Geodens', 'Moweyds', 'Gleens'},
    'MostSectors': {'Ivits', 'Lantids', 'Darkanians'},
    'MostBuildings': {'Xenos', 'Ambas', 'Gleens'},           # engine FinalScoringCondition names (game_state.rs:259-269)
    'MostStructuresInFederation': {'Ivits', 'Taklons', 'Xenos'},
    'MostDeepSpaceSectors': LOST_FLEET,
    'GreatestDistancePiAcademy': {'Ivits', 'Lantids'},
}
# strength_fit.py --from 060 --target vp (2026-10-26): 225 complete 6-round lab games, 900 seats, final VP centred per
# game on per-game z-scores — corr tier +0.43, rounds +0.25, planets +0.20, power +0.03, ships -0.01, techs -0.25.
# Debate 1/1: a non-negative fit (scipy nnls) tier 9.7, power 2.7, rounds 2.5 VP per z, R2 0.204; seed-split halves
# (57 seeds each) held-out R2 0.197 / 0.198 against tier alone 0.189 / 0.174 — the map terms add about 0.01-0.02.
# Mostly the geo quartet, and the teacher's own faction skill is inside the tier term. Rounds 1-3 charges (runs that
# reached round 4, 710 games) are not explained by these features (held-out R2 <= 0.007).
WEIGHTS = {'tier': 9.7, 'planets': 0.0, 'techs': 0.0, 'ships': 0.0, 'power': 2.7, 'rounds': 2.5}
NEAR = 3
NEIGHBOUR = 2


def features(state):
    import teacher_patches as tp
    from strategy_teacher import distance
    tp._guide['mj01'] = True       # debate 1/1: the all teacher's track table (MJ_FACTION_TRACKS) and Lost Fleet costs
    hexes = state['board']['hexes']
    homes = {}
    for p in state['players']:
        homes[p['player_id']] = tp._home_type(p)
    free = {c: cell['planet']['planet_type'] for c, cell in hexes.items() if tp._free_planet(cell)}
    ships = state['board'].get('spaceship_tiles') or {}
    fed_ship = next((b.get('id') for b in state.get('spaceship_boards') or ()
                     if b.get('federation_token') == tp.TECH_FEDERATION_TOKEN), None)
    slots = state['research_board']['tech_tile_slots']
    advanced = state['research_board']['advanced_tech_tiles']
    rounds = [t['condition'] for t in state['round_tiles'][:3]] + [t['condition'] for t in state['final_scoring_tiles']]
    rows = {}
    for p in state['players']:
        seat, faction, home = p['player_id'], p['faction'], homes[p['player_id']]
        tracks = set(tp._faction_tracks(p))
        kinds = {'Gaia', 'Transdim'} if 'gaia' in tracks else set()
        if faction in LOST_FLEET:
            kinds |= {'Asteroid', 'ProtoPlanet'}

        def cheap(c, kind, start):
            # debate 1/1: _terraform_steps prices Lost Fleet factions (Darkanians 1, SpaceGiants 2, Moweyds /
            # Tinkeroids 1 or 3) where _cheap_planet needs a home colour on the ring
            steps = tp._terraform_steps(state, p, kind)
            return c != start and ((steps is not None and steps <= 1) or kind in kinds)
        starts = [c for c, kind in free.items() if kind == home] or list(free)
        room = sorted((sum(1 for c, kind in free.items() if cheap(c, kind, s) and distance(s, c) <= NEAR), s)
                      for s in starts)[::-1]
        best = room[0][1] if room else None
        planets = statistics.mean(n for n, _ in room[:2]) if room else 0
        prefs = tp.TILE_PREFS.get(faction, {})
        good = (tp.GOOD_GAIA_TILES | set(prefs.get('prefer', ()))) - set(prefs.get('avoid', ()))
        techs = sum(1 for i, tile in enumerate(slots[:6]) if TRACKS[i] in tracks and tile in good) \
            + sum(1 for i, tile in enumerate(advanced[:6]) if TRACKS[i] in tracks and tile in tp.GOOD_ADVANCED)
        near_ships = [ship for ship, at in ships.items() if best and distance(best, at) <= tp.SHIP_SETUP_RANGE]
        ship_score = len(near_ships) + (1 if fed_ship in near_ships else 0)
        others = {homes[q['player_id']] for q in state['players'] if q['player_id'] != seat}
        power = sum(1 for c, kind in free.items() if best and kind in others and distance(best, c) <= NEIGHBOUR)
        fit = sum(1 for cond in rounds if faction in ROUND_FIT.get(cond, ()))
        rows[seat] = {'faction': faction, 'tier': TIER.get(faction, 2), 'planets': planets, 'techs': techs,
                      'ships': ship_score, 'power': power, 'rounds': fit}
    return rows


def strength(rows):
    total = {seat: 0.0 for seat in rows}
    for key, weight in WEIGHTS.items():
        values = [rows[s][key] for s in rows]
        mean, spread = statistics.mean(values), statistics.pstdev(values) or 1.0
        for seat in rows:
            total[seat] += weight * (rows[seat][key] - mean) / spread
    return total


def order_for(seed):
    from gaia_rl import Environment
    env = Environment(seed.split('@')[0], 2000)
    state = json.loads(env.snapshot_json())['state']
    rows = features(state)
    total = strength(rows)
    return sorted(rows, key=lambda s: (total[s], s)), rows, total


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('seeds', nargs='+')
    parser.add_argument('--table', action='store_true', help='print the features of every seat')
    args = parser.parse_args()
    for seed in args.seeds:
        order, rows, total = order_for(seed)
        print(f"{seed.split('@')[0]}@order={','.join(str(s) for s in order)}")
        if args.table:
            for s in order:
                r = rows[s]
                print(f"  s{s} {r['faction']:<12} {total[s]:+.2f}  " +
                      ' '.join(f"{k} {r[k]:g}" for k in WEIGHTS))


if __name__ == '__main__':
    main()
