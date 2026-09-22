"""Conditional goals and native-paid funding; no fixed faction opening."""
from dataclasses import asdict, dataclass

from action_purpose.teacher import key
from current_actions.teacher import construction_cost
from research_plans.teacher import (Goal, best_index, goals_for, is_advanced,
                                   matches_payoff, research_track)
from strategy_teacher import TRACK_KEYS, kind

SHIP_IDS = {'Twilight': 0, 'Rebellion': 1, 'TFMars': 2, 'Eclipse': 3}
SHIP_PAYOFFS = {'Rebellion': ('RebellionGainTechTile', 12),
               'TFMars': ('SpaceshipCreditTerraform', 1),
               'Eclipse': ('EclipseAsteroidMine', 9),
               'Twilight': ('TwilightFreeResearchLab', 2)}


@dataclass(frozen=True)
class Route(Goal):
    academy: str | None = None
    ship: str | None = None
    first: int | None = None
    lab_first: bool = False
    minimum_structures: int | None = None


def routes_for(snapshot, scores):
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    routes = [Route(**asdict(goal)) for goal in goals_for(snapshot)]
    names = {r.name for r in routes}
    # Offer research before it is affordable, including a lab-granted first advance.
    for track in TRACK_KEYS:
        level = player['research_tracks'][TRACK_KEYS[track]]
        if level >= 5:
            continue
        if track in ('Navigation', 'GaiaProject'):
            target = max(2, level+1)
        elif track in ('Economy', 'Science'):
            target = 2 if level < 2 else 4 if level < 4 else 5
        elif track == 'Terraforming':
            target = 3 if level in (1, 2) else level+1
        else:
            target = level+1
        name = f'{track}-{target}'
        if player['research_tracks'][TRACK_KEYS[track]] < target and name not in names:
            routes.append(Route(name, ((track, target),),
                                payoff='GaiaFormation' if track == 'GaiaProject' else None))
    for academy in ('Science', 'Qic'):
        if not any(s['kind'] == {'Academy': academy} for s in player['structures']):
            routes.append(Route(f'academy-{academy}', academy=academy))
    if not any(s['kind'] == 'ResearchLab' for s in player['structures']):
        for route in tuple(routes):
            if route.name in ('Navigation-2', 'Economy-2', 'Science-2', 'range-then-QIC-tech'):
                routes.append(Route(**{**asdict(route), 'name': 'lab-then-'+route.name, 'lab_first': True}))
    for board in state['spaceship_boards']:
        ship = board['id']
        if ship in SHIP_PAYOFFS:
            payoff, action_id = SHIP_PAYOFFS[ship]
            if action_id not in state['used_spaceship_actions']:
                routes.append(Route(f'{ship}-use', payoff=payoff, ship=ship))
    routes.append(Route('expand', payoff='Build', minimum_structures=len(player['structures'])+1))
    # Every actually legal cargo/supply choice participates. Keep one native shape
    # per token using the existing tie order, not a hypothetical future federation.
    tokens = {}
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        if action['type'] == 'FormFederation':
            tokens.setdefault(key(action['token']), []).append(i)
    for token, indices in sorted(tokens.items()):
        first = best_index(scores, indices)
        routes.append(Route(f'federation-{token}', first=first))
        for followup in tuple(routes):
            if followup.first is None and (followup.academy or followup.name == 'Rebellion-use'):
                routes.append(Route(**{**asdict(followup),
                    'name': f'federation-{token}-then-{followup.name}', 'first': first}))
    return routes


def achieved(snapshot, actor, route):
    player = snapshot['state']['players'][actor]
    return bool((route.academy and any(s['kind'] == {'Academy': route.academy}
                                     for s in player['structures'])) or
                (route.minimum_structures is not None and
                 len(player['structures']) >= route.minimum_structures))


def upgrade_stage(player, academy=None, track=None, state=None):
    """Funding thresholds guide search only; the native menu proves actual costs."""
    buildings = {kind(s['kind']) for s in player['structures']}
    if academy and 'ResearchLab' in buildings:
        target, origin = {'Academy': academy}, 'ResearchLab'
    elif 'TradingStation' in buildings:
        target, origin = 'ResearchLab', 'TradingStation'
    else:
        target, origin = 'TradingStation', 'Mine'
    costs = [construction_cost(state, player, {'type': 'Upgrade', 'coord': s['hex'], 'to': target})
             for s in player['structures'] if s['kind'] == origin]
    if not costs:
        return lambda a: False, {}
    cheapest = min(costs, key=lambda c: (c.ore, c.credits))
    need = {'ore': cheapest.ore, 'credits': cheapest.credits}

    def matches(action):
        return (action['type'] == 'Upgrade' and action['to'] == target
                and (not track or target == 'TradingStation' or research_track(state, action) == track))
    return matches, need


def milestone(snapshot, route):
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    actions = [c['action'] for c in snapshot['candidates']]
    ship = route.ship or ('Rebellion' if route.payoff == 'RebellionGainTechTile' else None)
    if ship and SHIP_PAYOFFS[ship][1] in state['used_spaceship_actions']:
        return lambda a: False, {}
    if route.academy and not achieved(snapshot, snapshot['player'], route):
        return upgrade_stage(player, route.academy, state=state)
    if (route.lab_first and any(player['research_tracks'][TRACK_KEYS[t]] < n for t, n in route.targets)
            and not any(s['kind'] == 'ResearchLab' for s in player['structures'])):
        return upgrade_stage(player, track=route.targets[0][0], state=state)
    if route.advanced:
        track, tile = route.advanced
        if state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(track)] != tile:
            return lambda a: False, {}
        if any(is_advanced(a, route.advanced) for a in actions):
            return lambda a: is_advanced(a, route.advanced), {}
    for track, level in route.targets:
        if player['research_tracks'][TRACK_KEYS[track]] < level:
            return lambda a: research_track(state, a) == track, {'knowledge': 4}
    payoff = route.payoff
    if ship:
        payoff, action_id = SHIP_PAYOFFS[ship]
        if SHIP_IDS[ship] not in player['explored_ships']:
            return lambda a: (a['type'].endswith('ExploreSpaceship') and a.get('ship') == ship), {'qic': 1}
        need = {'Rebellion': {'qic': 3}, 'Twilight': {'ore': 2},
                'TFMars': {'credits': 3, 'ore': 1}, 'Eclipse': {'credits': 6}}[ship]
        return lambda a: a['type'] == payoff, need
    if route.advanced and not player['federation_tokens']:
        return lambda a: a['type'] == 'FormFederation', {}
    if payoff == 'Build':
        return lambda a: a['type'] in ('Build', 'RoundBoosterTerraformBuild',
            'RoundBoosterRangeBuild', 'TwilightRangeBuild'), {'ore': 1, 'credits': 2}
    if payoff:
        return lambda a: matches_payoff(a, payoff), {}
    return lambda a: False, {}
