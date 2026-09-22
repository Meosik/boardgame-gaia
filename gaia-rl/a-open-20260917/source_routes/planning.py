"""Small, funded route forecasts, not a legal-action generator or search proof."""
import copy
from dataclasses import dataclass

from economy.teacher import RING, SHIP_IDS, construction_cost, range_qic, origins, path_distance
from federation.teacher import power, minimum
from integrated.features import active, income, remaining, advanced_value, counters
from integrated.boosters import next_income, round_vp
from integrated.teacher import prospective
from strategy_teacher import TRACK_KEYS, kind


def free_formers(player):
    return max(0, player['gaiaformers_total'] - player['gaiaformers_deployed']
               - player['gaiaformers_in_gaia_area'] - player['resources']['spent_gaia_formers'])


def asteroid_opportunity(state, player):
    """One expendable former -> one immediate mine, without ore/credit/power costs."""
    if not free_formers(player) or sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
        return 0.0
    r = player['resources']
    values = []
    for coord, cell in state['board']['hexes'].items():
        p = cell['planet']
        if not p or p['owner'] is not None or p['planet_type'] != 'Asteroid' or p['is_gaia_formed']:
            continue
        qic = range_qic(state, player, coord)
        if qic <= r['qic']:
            # Marginal mine income follows the printed 1,1,0,1,... track, not flat growth.
            mines = sum(s['kind'] == 'Mine' for s in player['structures'])
            ore_income = (1, 1, 0, 1, 1, 1, 1, 1)[mines]
            goal = 2 * any(t['condition'] == 'MostAsteroids' for t in state['final_scoring_tiles'])
            values.append(max(0, 3 + ore_income * remaining(state) * 1.5 + goal
                              + round_vp(state, player, coord, 'Mine', max(1, state['round'])) - 2.5*qic))
    return max(values, default=0.0)


def available_standard(state, player):
    tiles = set(state['research_board']['tech_tiles'])
    for board in state['spaceship_boards']:
        if SHIP_IDS[board['id']] in player['explored_ships']:
            tiles.update(board['tech_tiles'])
    return tiles - set(player['tech_tiles'])


def rebellion_funding(state, player):
    """Additional QIC matters only if it completes an accessible, available 3-QIC action."""
    return (1 in player['explored_ships'] and 12 not in state['used_spaceship_actions'] and bool(available_standard(state, player))
            and 2 <= player['resources']['qic'] < 3
            and any(v < 4 for v in player['research_tracks'].values()))


@dataclass(frozen=True)
class Route:
    track: str
    tile: int
    first_coord: str
    first_kind: str
    steps: int
    rounds: int
    net: float
    utility: float
    federation_needed: bool


def acquisition_paths(state, player):
    """At most two upgrades; reserve shared ore/credits, respect building supply."""
    need_standard = not active(player)
    standard = available_standard(state, player)
    if need_standard and not standard:
        return
    for structure in player['structures']:
        name = kind(structure['kind'])
        if name == 'TradingStation':
            targets = ['ResearchLab']
            if need_standard:
                targets.append({'Academy': 'Science'})
        elif name == 'ResearchLab' and not need_standard:
            targets = [{'Academy': 'Science'}]
        elif name == 'Mine' and not need_standard:
            targets = ['TradingStation', 'ResearchLab']
        else:
            continue
        p = copy.deepcopy(player)
        ore = credits = 0
        valid = True
        for target in targets:
            if kind(target) == 'Academy':
                target = next(({'Academy': side} for side in ('Science', 'Qic')
                               if not any(s['kind'] == {'Academy': side} for s in p['structures'])), None)
                if target is None:
                    valid = False
                    break
            limit = {'ResearchLab': 3, 'TradingStation': 4, 'Academy': 2}[kind(target)]
            if sum(kind(s['kind']) == kind(target) for s in p['structures']) >= limit:
                valid = False
                break
            action = {'type': 'Upgrade', 'coord': structure['hex'], 'to': target}
            cost = construction_cost(state, p, action)
            ore += cost.ore
            credits += cost.credits
            p = prospective(p, action)
        if valid:
            yield structure['hex'], kind(targets[0]), p, ore, credits, len(targets), need_standard


def federation_readiness(state, player):
    """Conservative local star proxy; still cannot certify a legal federation route."""
    if player['federation_tokens']:
        return 1.0
    used = set(player['federated_hexes'])
    own = [s for s in player['structures'] if s['hex'] not in used]
    budget = sum(player['resources']['power'][k] for k in ('bowl1', 'bowl2', 'bowl3')) - 4
    for anchor in own:
        total = power(player, anchor['kind'])
        satellites = 0
        for distance, contribution in sorted((path_distance(state, [anchor['hex']], s['hex']), power(player, s['kind']))
                                             for s in own if s is not anchor):
            if total >= minimum(player):
                break
            if distance > 3:
                break
            total += contribution
            satellites += max(0, distance - 1)
        if total >= minimum(player) and satellites <= budget:
            return .5
    return 0.0


def best_route(state, player, retained):
    """Recompute on actual state: abandon depleted/unfundable/late race targets."""
    if state['round'] == 0:
        return None
    horizon = min(2, max(0, 3-state['round'])) if state['round'] <= 3 else min(1, remaining(state))
    budget = copy.deepcopy(player)
    for _ in range(horizon):
        budget = next_income(state, budget)
    paths = list(acquisition_paths(state, player))
    best = None
    for track, key in TRACK_KEYS.items():
        level = player['research_tracks'][key]
        tile = state['research_board']['advanced_tech_tiles'][list(TRACK_KEYS).index(track)]
        if tile is None or level > 4:
            continue
        for coord, first_kind, after, ore, credits, actions, needs_standard in paths:
            # A first standard acquisition can advance this track if aligned or flexible.
            tiles = active(player)
            if needs_standard:
                slots = state['research_board']['tech_tile_slots'][:6]
                tiles = {t for t in available_standard(state, player)
                         if t not in slots or slots.index(t) == list(TRACK_KEYS).index(track)}
            if not tiles:
                continue
            paid = max(0, 4-level-int(needs_standard))
            if (ore > budget['resources']['ore'] or credits > budget['resources']['credits']
                    or paid*4 > budget['resources']['knowledge']):
                continue
            readiness = federation_readiness(state, after)
            if not readiness:
                continue
            # Missing green token requires an actual token still in a reachable supply.
            if not player['federation_tokens'] and not state['research_board']['federation_tokens']:
                if not any(b['federation_token'] is not None and SHIP_IDS[b['id']] in player['explored_ships']
                           for b in state['spaceship_boards']):
                    continue
            delay = 0
            now = player['resources']
            inc = income(player, state)
            for resource, cost in (('ore', ore), ('credits', credits), ('knowledge', paid*4)):
                missing = max(0, cost-now[resource])
                if missing:
                    delay = max(delay, (missing+max(1, inc[resource])-1)//max(1, inc[resource]))
            if delay > horizon:
                continue
            projected = dict(state, round=min(6, state['round']+delay))
            cover = min(retained(projected, after, t) for t in tiles)
            net = advanced_value(projected, after, tile) - cover - 4
            if net <= 0:
                continue
            # Opponents already poised can beat a multi-action plan; do not call it secure.
            rival_ready = any(p['player_id'] != player['player_id'] and p['research_tracks'][key] >= 4
                              and p['federation_tokens'] and active(p) for p in state['players'])
            steps = paid + actions + int(not player['federation_tokens'])
            race = .35 if rival_ready and steps > 1 else 1.0
            utility = net * readiness * race / (1 + .4*max(0, steps-1) + delay)
            route = Route(track, tile, coord, first_kind, steps, delay, net, utility, not player['federation_tokens'])
            if best is None or route.utility > best.utility:
                best = route
    return best


def immediate_funding(state, player, reward):
    """Does this printed immediate reward enable a real same-round colony/3QIC path?"""
    after = copy.deepcopy(player)
    for key, amount in reward.items():
        cap = {'ore': 15, 'credits': 30, 'knowledge': 15, 'qic': 255}[key]
        after['resources'][key] = min(cap, after['resources'][key] + amount)
    for coord, cell in state['board']['hexes'].items():
        p = cell['planet']
        if not p or p['owner'] is not None or p['planet_type'] not in (*RING, 'Gaia'):
            continue
        if sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
            break
        cost = construction_cost(state, player, {'type': 'Build', 'coord': coord})
        funded = lambda who: all(getattr(cost, k) <= who['resources'][k] for k in ('ore', 'credits', 'qic'))
        if not funded(player) and funded(after):
            return 6.0
    if rebellion_funding(state, player) and after['resources']['qic'] >= 3:
        return 6.0
    if player['resources']['knowledge'] < 4 <= after['resources']['knowledge']:
        if any(v < 4 for v in player['research_tracks'].values()):
            return 4.0
    return 0.0
