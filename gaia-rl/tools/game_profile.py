"""Profile full lab games the way a spectator reads a human game (research/strategy/observed-uiqoo-20260916.md):
per seat the turns taken, buildings, tech tiles, research advances, federations, Gaia projects, ship entries
and actions, artifacts, and the VP gained by the kind of move that gained it (the engine keeps no VP-reason
log in the snapshot, so VP is attributed to the acting player's move: a Pass gains the booster's pass VP, a
Build the round tile, a FormFederation the token, a ship entry its cost, a charge its cost; the end-of-game
scoring is one bucket). User (2026-10-18): "관전 마지막에 뭘로 몇점 벌었는지도 나오는데 리플레이랑 비교해서
어느 부분이 떨어지나 봐도 되고".

  .venv/bin/python tools/game_profile.py ~/projects/gaia-lab/gaia-rl/runs/lab-060-... [--arm A] [--games]
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

NOT_A_TURN = ('ChargePower', 'FreeAction', 'ChooseIncomeOrder', 'PlaceStartingStructure', 'SelectStartingBooster',
              'SelectFaction', 'Bid')
SHIPS = ('Twilight', 'Rebellion', 'TFMars', 'Eclipse')
KINDS = {'Mine': 'mine', 'TradingStation': 'ts', 'ResearchLab': 'lab', 'PlanetaryInstitute': 'pi'}


def bucket(action):
    t = action.get('type', '')
    if t == 'Pass':
        return 'pass(booster)'
    if t == 'ChargePower':
        return 'charge'
    if t.endswith('ExploreSpaceship'):
        return 'ship entry'
    if t == 'FormFederation':
        return 'federation'
    if t == 'ResearchAdvance' or t == 'EclipseResearchBoost':
        return 'research'
    if 'GaiaFormation' in t:
        return 'gaia forming'
    if t in ('Build', 'EclipseAsteroidMine') or t.endswith('Build'):
        return 'build'
    if t == 'Upgrade' or t in ('TwilightFreeResearchLab', 'RebellionFreeTradingStation'):
        return 'upgrade'
    if any(s in t for s in SHIPS):
        return 'ship action'
    if t == 'ExamineArtifact':
        return 'artifact'
    if t in ('PowerAction', 'AcademyQicAction', 'TechTileSpecialAction', 'FreeAction'):
        return 'actions/conversions'
    return 'other'


def profile_game(game_dir):
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    a_seats = set(result.get('a_seats', ()))
    snap = json.loads(env.snapshot_json())
    seats = {}
    for p in snap['state']['players']:
        seats[p['player_id']] = {'faction': p['faction'], 'arm': 'A' if p['player_id'] in a_seats else 'B',
                                 'turns': 0, 'vp_by': Counter(), 'count': Counter(), 'start_vp': p['vp']}
    for row in rows:
        before = snap
        actor = before['player']
        action = before['candidates'][row['index']]['action']
        t = action.get('type', '')
        vp_before = {p['player_id']: p['vp'] for p in before['state']['players']}
        env.step(row['decision_id'], row['index'])
        snap = json.loads(env.snapshot_json())
        vp_after = {p['player_id']: p['vp'] for p in snap['state']['players']}
        seat = seats[actor]
        if before['state']['round'] >= 1 and t not in NOT_A_TURN:
            seat['turns'] += 1
        seat['vp_by'][bucket(action)] += vp_after[actor]-vp_before[actor]
        for pid in vp_after:
            if pid != actor and vp_after[pid] != vp_before[pid]:
                seats[pid]['vp_by']['other player\'s move'] += vp_after[pid]-vp_before[pid]
        if before['state']['round'] >= 1:
            c = seat['count']
            if t in ('Build', 'EclipseAsteroidMine') or t.endswith('Build'):
                c['mines built'] += 1
            if t == 'ResearchAdvance':
                c['research'] += 1
            if 'GaiaFormation' in t:
                c['gaia'] += 1
            if t.endswith('ExploreSpaceship'):
                c['ship entries'] += 1
            elif any(s in t for s in SHIPS):
                c['ship actions'] += 1
            if t == 'FormFederation':
                c['federations'] += 1
            if t == 'ExamineArtifact':
                c['artifacts'] += 1
            if t == 'Pass':
                c['passes'] += 1
    state = snap['state']
    final = dict(state['phase']['Ended']['final_scores']) if isinstance(state['phase'], dict) and 'Ended' in state['phase'] else None
    for p in state['players']:
        seat = seats[p['player_id']]
        kinds = Counter()
        for s in p['structures']:
            k = s['kind']
            kinds['academy' if isinstance(k, dict) else KINDS.get(k, k)] += 1
        seat['buildings'] = dict(kinds)
        seat['tech'] = len(p['tech_tiles'])
        seat['adv'] = len(p.get('advanced_tech_tiles') or [])
        seat['fed_tokens'] = len(p.get('federation_tokens') or [])+len(p.get('gray_federation_tokens') or [])
        seat['tracks'] = dict(p['research_tracks'])
        seat['track_sum'] = sum(p['research_tracks'].values())
        seat['vp'] = p['vp']
        # Rulebook end scoring: 4 VP per research level from level 3 up (level 3 = 4, 4 = 8, 5 = 12).
        research_vp = sum(4*max(0, level-2) for level in p['research_tracks'].values())
        if final is not None:
            key = p['player_id'] if p['player_id'] in final else str(p['player_id'])
            seat['final'] = final.get(key, p['vp'])
            seat['vp_by']['end: research'] += research_vp
            seat['vp_by']['end: missions+rest'] += seat['final']-p['vp']-research_vp
        else:
            seat['final'] = p['vp']
    return result, seats


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path)
    parser.add_argument('--arm', choices=('A', 'B'))
    parser.add_argument('--games', action='store_true', help='print every seat')
    args = parser.parse_args()
    games = sorted(p for p in args.run.glob('pair-*/game-*') if (p/'decisions.jsonl.gz').exists())
    rows = []
    for game in games:
        result, seats = profile_game(game)
        for pid, seat in sorted(seats.items()):
            if args.arm and seat['arm'] != args.arm:
                continue
            seat['game'] = f'{game.parent.name}/{game.name}'
            rows.append(seat)
    if not rows:
        print('no games')
        return
    buckets = ['pass(booster)', 'build', 'upgrade', 'federation', 'research', 'ship entry', 'ship action',
               'charge', 'gaia forming', 'artifact', 'actions/conversions', 'other', "other player's move",
               'end: research', 'end: missions+rest']
    if args.games:
        for s in rows:
            print(f"{s['game']} {s['faction']}({s['arm']}) final {s['final']} turns {s['turns']} "
                  f"buildings {s['buildings']} tech {s['tech']} feds {s['fed_tokens']} tracks {s['track_sum']} "
                  f"counts {dict(s['count'])} vp {dict(s['vp_by'])}")
        print()
    groups = defaultdict(list)
    for s in rows:
        groups[(s['arm'], s['faction'])].append(s)

    def mean(values):
        return sum(values)/len(values)
    print('End-of-game board (mean per seat): buildings on the board, mines built in rounds 1-6, tiles, federation tokens, research levels')
    print(f"{'arm faction':<16}{'n':>3}{'final':>7}{'turns':>7}{'mines':>7}{'built':>7}{'ts':>5}{'lab':>5}{'pi':>4}{'ac':>4}"
          f"{'tech':>6}{'adv':>5}{'feds':>6}{'trk':>5}{'res':>5}{'gaia':>6}{'ships':>7}{'shact':>7}{'art':>5}")
    for (arm, faction), group in sorted(groups.items()):
        b = lambda k: mean([s['buildings'].get(k, 0) for s in group])
        c = lambda k: mean([s['count'].get(k, 0) for s in group])
        print(f"{arm+' '+faction:<16}{len(group):>3}{mean([s['final'] for s in group]):>7.1f}{mean([s['turns'] for s in group]):>7.1f}"
              f"{b('mine'):>7.1f}{c('mines built'):>7.1f}{b('ts'):>5.1f}{b('lab'):>5.1f}{b('pi'):>4.1f}{b('academy'):>4.1f}"
              f"{mean([s['tech'] for s in group]):>6.1f}{mean([s['adv'] for s in group]):>5.1f}{mean([s['fed_tokens'] for s in group]):>6.1f}"
              f"{mean([s['track_sum'] for s in group]):>5.1f}{c('research'):>5.1f}{c('gaia'):>6.1f}"
              f"{c('ship entries'):>7.1f}{c('ship actions'):>7.1f}{c('artifacts'):>5.1f}")
    print()
    print('VP by the move that gained it (mean per seat)')
    print(f"{'arm faction':<16}" + ''.join(f'{k[:9]:>10}' for k in buckets))
    for (arm, faction), group in sorted(groups.items()):
        print(f"{arm+' '+faction:<16}" + ''.join(f"{mean([s['vp_by'].get(k, 0) for s in group]):>10.1f}" for k in buckets))


if __name__ == '__main__':
    main()
