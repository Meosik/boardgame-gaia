"""Explicit soft hypotheses for Terrans/Taklons, never engine rewards or rules."""
import json
import copy
from collections import Counter
from pathlib import Path

from economy.teacher import NAV_RANGE, ORE_PER_STEP, RING, path_distance
from research_plans.value import final_metric
from integrated.features import counters, PASS, EVENT, RESOURCE_ACTIONS
from strategy_teacher import kind, distance

ROOT = Path(__file__).resolve().parents[3]
INCOME_PATH = ROOT / 'gaia-frontend/src/data/income.json'
INCOME = json.loads(INCOME_PATH.read_text())
HOME = {'Terrans': 'Terra', 'Taklons': 'Swamp'}
RESOURCE_KEYS = ('ore', 'credits', 'knowledge', 'qic')


def production(state, player, *, include_booster=True):
    """Gross current income, including the held booster; no charge-order simulation.

    Reuse the native-generated oracle already consumed by the sidebar. The run
    manifest pins that file and a separate test regenerates it from Rust.
    """
    rules = INCOME['factions'][player['faction']]
    result = list(rules['base'])

    def add(vector):
        for i, value in enumerate(vector):
            result[i] += value

    counts = Counter(next(iter(s['kind'].values())) if isinstance(s['kind'], dict)
                     else s['kind'] for s in player['structures'])
    for name, curve in rules['structures'].items():
        add(curve[min(counts[name], len(curve)-1)])
    add(INCOME['economy'][state['research_board']['economy_research_tile_side']][player['research_tracks']['economy']])
    add(INCOME['science'][player['research_tracks']['science']])
    if include_booster:
        add(INCOME['boosters'].get(str(player['booster']), [0]*7))
    for tile in set(player['tech_tiles']) - set(player['covered_tech_tiles']):
        add(INCOME['tech'].get(str(tile), [0]*7))
    for artifact in set(player['artifacts']):
        add(INCOME['artifacts'].get(str(artifact), [0]*7))
    return result


def materials(resources):
    # A monotone concave potential, not root-dependent prices that could reward
    # repeatedly crossing a scarcity threshold with reversible conversions.
    thresholds = {'ore': (5, 3.0, 1.0), 'credits': (10, 1.2, .35),
                  'knowledge': (8, 2.0, .8), 'qic': (3, 2.5, 1.0)}
    return sum(min(resources[k], n)*high + max(0, resources[k]-n)*low
               for k, (n, high, low) in thresholds.items())


def power_value(power):
    # Normal tokens and the distinct Brainstone are not interchangeable. Native
    # forks, rather than this potential, determine charging and payment order.
    stone = {'Area1': .5, 'Area2': 1.5, 'Area3': 4.2, 'Gaia': 0, None: 0}[power['brainstone']]
    return .2*power['bowl1'] + .6*power['bowl2'] + 1.4*power['bowl3'] + stone


def navigation(player):
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    return NAV_RANGE[player['research_tracks']['navigation']] + int(12 in active)


def targets(state, player, planet_types):
    starts = [s['hex'] for s in player['structures']]
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] is not None or cell['structures']:
            continue
        if planet['planet_type'] not in planet_types:
            continue
        needed_qic = max(0, (path_distance(state, starts, coord)-navigation(player)+1)//2)
        if needed_qic <= player['resources']['qic']:
            yield coord, planet, needed_qic


def gaia_value(state, player):
    """Feasible colony opportunity, not a promise that an opponent leaves it free."""
    horizon = max(0, 6-max(1, state['round']))
    if not horizon:
        return 0.0
    level = player['research_tracks']['gaia']
    if not level:
        return 0.0
    resources = player['resources']
    power = resources['power']
    # Standing policy excludes committing the Brainstone to Gaia.
    normal_tokens = sum(power[k] for k in ('bowl1', 'bowl2', 'bowl3'))
    required = (255, 6, 6, 4, 3, 3)[level]
    available = max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
                    - player['gaiaformers_in_gaia_area'] - resources['spent_gaia_formers'])
    recurring = production(state, player, include_booster=player['passed'])
    stock = min(resources['ore']+recurring[0], (resources['credits']+recurring[1])//2)
    mines = sum(s['kind'] == 'Mine' for s in player['structures'])
    candidates = list(targets(state, player, ('Transdim',)))
    capacity = min(available, normal_tokens//required, stock, max(0, 8-mines), len(candidates), 2)
    # Already-paid forming projects retain value until the paid colony is built.
    reserved = sum(cell['planet'] is not None and cell['planet']['owner'] == player['player_id']
                   and cell['planet']['planet_type'] == 'Transdim' and not cell['structures']
                   for cell in state['board']['hexes'].values())
    projects = min(max(player['gaiaformers_deployed'], reserved), stock, max(0, 8-mines))
    # A Terrans project also recirculates tokens to Area II; with PI it opens
    # Gaia-phase resource choices. This is a soft option value, not free income.
    terrans = player['faction'] == 'Terrans'
    pi = any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])
    per_colony = 6 + 2*horizon + 2*terrans + 2*(terrans and pi)
    return per_colony*(projects + .65*capacity)


def expansion_value(state, player, *, home=None):
    recurring = production(state, player, include_booster=player['passed'])
    ore = player['resources']['ore'] + recurring[0]
    credits = player['resources']['credits'] + recurring[1]
    if credits < 2 or sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
        return 0.0
    home = HOME[player['faction']] if home is None else home
    if home not in RING:
        # Asteroid/ProtoPlanet factions do not use this seven-color estimate.
        # Their real construction costs/effects are evaluated by native forks.
        return 0.0
    home = RING.index(home)
    values = []
    for _, planet, qic in targets(state, player, RING):
        gap = abs(home-RING.index(planet['planet_type']))
        steps = min(gap, 7-gap)
        cost = 1 + steps*ORE_PER_STEP[player['research_tracks']['terraforming']]
        if cost <= ore:
            values.append(4/(cost+qic+1))
    return sum(sorted(values, reverse=True)[:3])


def standings(state, actor):
    total = 0
    for tile in state['final_scoring_tiles']:
        def metric(p):
            if tile['condition'] == 'MostStructuresInFederation':
                return sum(s['hex'] in p['federated_hexes'] for s in p['structures'])
            return final_metric(state, p, tile['condition'])
        values = [metric(p) for p in state['players']]
        focal = values[actor]
        start, tied = sum(v > focal for v in values), values.count(focal)
        awards = (tile.get('vp_1st', 18), tile.get('vp_2nd', 12), tile.get('vp_3rd', 6), 0)
        total += sum(awards[start:start+tied])//tied
    return total


def advanced_option(state, player, tile):
    """Current-board pass/action value; unearned immediate payouts stay native."""
    horizon = max(0, 6-state['round'])
    passes = horizon + int(not player['passed'])
    if tile in PASS:
        counter, vp = PASS[tile]
        return .6*passes*vp*counters(state, player)[counter]
    if tile in RESOURCE_ACTIONS:
        available = tile not in player['advanced_tech_tile_special_actions_used_this_round']
        uses = horizon + int(available and not player['passed'])
        return .6*uses*materials({**dict.fromkeys(RESOURCE_KEYS, 0), **RESOURCE_ACTIONS[tile]})
    if tile in EVENT:
        return .5*horizon*EVENT[tile][1]
    return 0.0


def research_options(state, player):
    """Soft fundable next-income research steps and still-available advanced tiles."""
    horizon = max(0, 6-state['round'])
    if not horizon:
        return 0.0
    result = 0.0
    current = production(state, player, include_booster=False)
    if player['resources']['knowledge']+current[2] >= 4:
        for track in ('economy', 'science'):
            # Do not assign this option to an unfunded abstract research ladder.
            if player['research_tracks'][track] != 1:
                continue
            after = copy.deepcopy(player)
            after['research_tracks'][track] = 2
            future = production(state, after, include_booster=False)
            delta = {k: max(0, future[i]-current[i]) for i, k in enumerate(RESOURCE_KEYS)}
            result += .5*horizon*materials(delta)
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    if player['federation_tokens'] and active:
        tracks = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')
        options = []
        for track, tile in zip(tracks, state['research_board']['advanced_tech_tiles']):
            if tile is not None:
                proximity = (0, 0, .1, .25, .4, .4)[player['research_tracks'][track]]
                options.append(proximity*advanced_option(state, player, tile))
        result += max(options, default=0)
    return result


def potential(state, actor, *, home=None, guide_tracks=False):
    phase = state['phase']
    if isinstance(phase, dict) and 'Ended' in phase:
        return float(dict(phase['Ended']['final_scores'])[actor])
    player = state['players'][actor]
    horizon = max(0, 6-state['round'])
    income = production(state, player, include_booster=False)
    future = dict(zip(RESOURCE_KEYS, income[:4]))
    result = player['vp'] + standings(state, actor)
    result += 4*sum(max(0, level-2) for level in player['research_tracks'].values())
    resources, power = player['resources'], player['resources']['power']
    if horizon:
        result += materials(resources) + power_value(power)
        # Committed normal tokens are delayed, not destroyed. Gaia-phase
        # destination is Area II for Terrans, Area I for Taklons.
        result += (.6 if player['faction'] == 'Terrans' else .2)*power['gaia_forming']
    else:
        # Native terminal scoring counts ore/credits/knowledge, not raw QIC.
        result += sum(resources[k] for k in ('ore', 'credits', 'knowledge'))/3
        result += (power['bowl3'] + 3*(power['brainstone'] == 'Area3'))/3
    result += .7*horizon*(materials(future) + .5*income[4] + .4*income[5] + income[6])
    if horizon and (player['passed'] or state['round'] == 0):
        # A newly selected booster has one known next income, not six repeats.
        booster = INCOME['boosters'].get(str(player['booster']), [0]*7)
        result += .7*(materials(dict(zip(RESOURCE_KEYS, booster[:4]))) + .5*booster[4] + .4*booster[5])
    # Buildings/ships are future options, not extra engine points. Income is
    # already counted; these soft terms express expansion/federation access.
    result += min(horizon, 2)*2*len(player['structures'])
    result += min(horizon, 2)*2*len(player['explored_ships'])
    if player['faction'] == 'Taklons' and any(s['kind'] == 'PlanetaryInstitute' for s in player['structures']):
        owners = {b['owner'] for c, cell in state['board']['hexes'].items()
                  if any(distance(c, s['hex']) <= 2 for s in player['structures'])
                  for b in cell['structures'] if b['owner'] != actor}
        result += horizon*min(2, len(owners))
    if guide_tracks:
        from four_factions.track_guidance import expansion_potential
        result += gaia_value(state, player) + expansion_potential(state, player)
    else:
        result += gaia_value(state, player) + (expansion_value(state, player, home=home) if horizon else 0)
    result += research_options(state, player)
    result += sum(advanced_option(state, player, tile) for tile in player['advanced_tech_tiles'])
    active = set(player['tech_tiles'])-set(player['covered_tech_tiles'])
    # Non-income tile optionality; native immediate payouts are never counted twice.
    result += .5*horizon*len(active - {2, 3, 5, 4, 7, 9, 11, 13})
    return result


def placement(state, player, coord, *, home=None):
    """Soft local opening preference; not the legacy teacher's two-income search."""
    home = HOME[player['faction']] if home is None else home
    sites = [s['hex'] for s in player['structures']]
    value = 0.0
    for target, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] is not None or target == coord:
            continue
        d = distance(coord, target)
        if 1 <= d <= 3 and not any(distance(old, target) <= d for old in sites):
            if planet['planet_type'] == home:
                value += 3/d
            elif home in RING and planet['planet_type'] in RING:
                gap = abs(RING.index(home)-RING.index(planet['planet_type']))
                if min(gap, 7-gap) <= 1:
                    value += 1.5/d
            if player['faction'] == 'Terrans' and planet['planet_type'] == 'Transdim':
                value += 2/d
    owners = {s['owner'] for c, cell in state['board']['hexes'].items() if distance(c, coord) <= 2
              for s in cell['structures'] if s['owner'] != player['player_id']}
    return value + 2*len(owners) - .25*min(distance(coord, c) for c in state['board']['spaceship_tiles'].values())
