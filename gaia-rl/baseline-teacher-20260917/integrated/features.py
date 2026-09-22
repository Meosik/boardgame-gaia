"""Auditable two-faction forecasts; estimates are not engine actions or rewards."""
from collections import Counter
from pathlib import Path
import tomllib
from strategy_teacher import distance, kind

ROOT = Path(__file__).resolve().parents[3]
TRACKS = {t['id']: {l['level']: l for l in t['levels']}
          for t in tomllib.loads((ROOT/'gaia-engine/data/research_tracks.toml').read_text())['tracks']}


def active(player):
    return set(player['tech_tiles']) - set(player['covered_tech_tiles'])


def remaining(state):
    return max(0, 6 - max(1, state['round']))


def income(player, state=None):
    """Permanent Xenos/HH income only; next booster is unknown until chosen."""
    if player['faction'] not in ('Xenos', 'HadschHallas'):
        raise ValueError('Integrated teacher supports only Xenos/HadschHallas')
    buildings = Counter(kind(s['kind']) for s in player['structures'])
    science = player['research_tracks']['science']
    economy = player['research_tracks']['economy']
    e = TRACKS['Economy'].get(economy, {}) if economy < 5 else {}
    tiles = active(player)
    economy_credits = e.get('credits', 0)
    if state and economy in (3, 4) and state['research_board']['economy_research_tile_side']=='Power':
        economy_credits = 2
    return {'knowledge': 1 + min(3, buildings['ResearchLab'])
            + 2 * sum(s['kind'] == {'Academy': 'Science'} for s in player['structures'])
            + (science if science < 5 else 0) + int(5 in tiles) + int(3 in player['artifacts']),
            'ore': 1 + sum((1, 1, 0, 1, 1, 1, 1, 1)[:buildings['Mine']]) + e.get('ore', 0)
            + int(2 in tiles) + int(3 in player['artifacts']),
            'credits': sum((3, 4, 4, 5)[:buildings['TradingStation']]) + economy_credits
            + 4 * int(3 in tiles) + int(5 in tiles)}


def knowledge_budget_value(stock, per_round, rounds, spend=0):
    """Realizable paid advances over <=2 forecast incomes; remainder retains value."""
    horizon = min(2, max(0, rounds))
    available = max(0, stock + horizon * per_round - spend)
    return 4 * (available // 4) + .35 * (available % 4)


def sector_at(state, coord):
    q, r = map(int, coord.split(','))
    for sector in state['board']['sectors']:
        origin = sector['origin']
        if not 11 <= sector['id'] <= 18:
            if distance(coord, origin) <= 2:
                return sector['id']
        else:
            oq, or_ = map(int, origin.split(','))
            for x, y in ((0, 0), (1, 0), (0, 1)):
                for _ in range(sector['rotation'] % 6):
                    x, y = -y, x+y
                if (q, r) == (oq+x, or_+y):
                    return sector['id']
    return None


def counters(state, player):
    buildings = Counter(kind(s['kind']) for s in player['structures'])
    sectors = {sector_at(state, s['hex']) for s in player['structures']}
    planets = [state['board']['hexes'][s['hex']]['planet'] for s in player['structures']]
    planets = [p for p in planets if p]
    types = {('Gaia' if p['is_gaia_formed'] else p['planet_type']) for p in planets}
    types.update(player['artifact_mines'])
    lost = state['board'].get('lost_planet')
    lost_planet = state['board']['hexes'].get(lost, {}).get('planet')
    untracked_lost = bool(lost_planet and lost_planet['owner']==player['player_id'] and not any(s['hex']==lost for s in player['structures']))
    return {'ts': buildings['TradingStation'], 'labs': buildings['ResearchLab'],
            'large': buildings['Academy']+buildings['PlanetaryInstitute'],
            'mines': buildings['Mine']+len(player['artifact_mines'])+int(untracked_lost),
            'federations': len(player['federation_tokens'])+len(player['gray_federation_tokens']),
            'standard': sum(s is not None and s <= 10 for s in sectors),
            'deep': sum(s is not None and 11 <= s <= 18 for s in sectors),
            'gaia': sum(p['is_gaia_formed'] for p in planets), 'types': len(types),
            'asteroids': sum(not p['is_gaia_formed'] and p['planet_type']=='Asteroid' for p in planets)
            + player['artifact_mines'].count('Asteroid')}


# Engine ids: immediate / pass / event / repeatable resource action. 18 is absent.
IMMEDIATE = {1: ('ts', 4), 2: ('federations', 5), 6: ('standard', 2), 9: ('gaia', 2),
             10: ('mines', 2), 12: ('deep', 4), 13: ('large', 6)}
PASS = {7: ('labs', 3), 11: ('federations', 3), 14: ('asteroids', 2), 15: ('deep', 2), 19: ('types', 1)}
EVENT = {3: ('ts', 3), 4: ('mines', 3), 8: ('research', 2), 16: ('qic_actions', 4), 17: ('terraform', 2)}
RESOURCE_ACTIONS = {20: {'knowledge': 3}, 21: {'ore': 3}, 22: {'qic': 1, 'credits': 5}}
ADVANCED_IDS = set(IMMEDIATE) | set(PASS) | set(EVENT) | set(RESOURCE_ACTIONS) | {5}


def resource_value(player, resources):
    stock = player['resources']
    prices = {'ore': 2.5 if stock['ore'] < 5 else 1.5,
              'credits': 1.2 if stock['credits'] < 10 else .6,
              'knowledge': 2, 'qic': 2.5}
    return sum(prices[k]*v for k, v in resources.items())


def forecast_events(state, player):
    """Affordable growth proxy, not guaranteed future actions/trigger counts."""
    horizon = min(2, remaining(state))
    recurring = income(player, state)
    ore = player['resources']['ore'] + horizon*recurring['ore']
    credits = player['resources']['credits'] + horizon*recurring['credits']
    c = counters(state, player)
    mines = min(max(0, 8-c['mines']), ore/3, credits/4, 1+remaining(state))
    ts = min(max(0, 4-c['ts']), ore/4, credits/6, 1+remaining(state))
    room = 0
    for track, level in player['research_tracks'].items():
        rivals_at_five = any(p['player_id']!=player['player_id'] and p['research_tracks'][track]==5
                             for p in state['players'])
        ceiling = 4 if rivals_at_five or not player['federation_tokens'] else 5
        room += max(0, ceiling-level)
    research = min(room, 2*(1+remaining(state)),
                   (player['resources']['knowledge']+horizon*recurring['knowledge'])/4)
    return {'mines': mines, 'ts': ts, 'research': research,
            'terraform': mines * (0.5 if player['research_tracks']['terraforming'] < 2 else 1),
            'qic_actions': min(1+remaining(state), player['resources']['qic']/2) if player['explored_ships'] else 0}


def advanced_value(state, player, tile):
    if tile not in ADVANCED_IDS:
        raise ValueError(f'Unmapped advanced technology: {tile}')
    c = counters(state, player)
    if tile in IMMEDIATE:
        key, vp = IMMEDIATE[tile]
        return c[key]*vp
    if tile == 5:
        return resource_value(player, {'ore': c['standard']})
    if tile in PASS:
        key, vp = PASS[tile]
        # Current-round pass remains; future passes discounted because the board may change.
        return c[key]*vp*(1 + .6*remaining(state))
    if tile in EVENT:
        key, vp = EVENT[tile]
        return forecast_events(state, player)[key]*vp
    return resource_value(player, RESOURCE_ACTIONS[tile])*(1+.6*remaining(state))
