"""Paid, conditional Hadsch alternatives; goals never grant resources or score."""
from dataclasses import asdict, dataclass

from current_actions.teacher import construction_cost
from economy.teacher import origins, path_distance, range_qic
from federation.teacher import formations, power
from research_plans.teacher import matches_payoff
from resource_plans.routes import Route, achieved, milestone, routes_for
from strategy_teacher import distance, kind

MAX_GAIA_TARGETS = 2
MAX_DISTANCE_PAIRS = 2
BUILD_ACTIONS = ('Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'TwilightRangeBuild')


@dataclass(frozen=True)
class Plan(Route):
    institute: str | None = None
    academy_coord: str | None = None
    academy_first: bool = False
    gaia_coord: str | None = None
    repeat_rebellion: bool = False
    immediate_only: bool = False
    asteroid_coord: str | None = None
    federation_goal: int = 0


def structure_at(player, coord):
    return next((s['kind'] for s in player['structures'] if s['hex'] == coord), None)


def plans_for(snapshot, scores):
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    plans = [Plan(**asdict(route)) for route in routes_for(snapshot, scores)]
    pi = [s['hex'] for s in player['structures'] if s['kind'] == 'PlanetaryInstitute']
    sites = sorted(s['hex'] for s in player['structures'] if s['kind'] in ('Mine', 'TradingStation'))
    rebellion = any(b['id'] == 'Rebellion' for b in state['spaceship_boards'])
    for coord in sites if not pi else ():
        plans.append(Plan(f'PI@{coord}', institute=coord))
        if rebellion:
            plans.append(Plan(f'PI@{coord}-Rebellion', institute=coord, repeat_rebellion=True))
    if rebellion:
        plans.append(Plan('Rebellion-each-available-round', repeat_rebellion=True))
    pairs = []
    if any(t['condition'] == 'GreatestDistancePiAcademy' for t in state['final_scoring_tiles']):
        for institute in pi or sites:
            for building in player['structures']:
                coord = building['hex']
                if coord != institute and kind(building['kind']) in ('Mine', 'TradingStation', 'ResearchLab', 'Academy'):
                    pairs.append((institute, coord))
        # Bounded geometry samples, not a claim that other pairs are inferior.
        for institute, coord in sorted(pairs, key=lambda pair: (-distance(*pair), pair))[:MAX_DISTANCE_PAIRS]:
            for academy in ('Science', 'Qic'):
                existing = [s['hex'] for s in player['structures'] if s['kind'] == {'Academy': academy}]
                if existing and coord not in existing:
                    continue
                if institute in pi and coord in existing:
                    continue
                for academy_first in (False, True):
                    plans.append(Plan(f'pair-{institute}-{coord}-{academy}-{int(academy_first)}',
                        institute=institute, academy=academy, academy_coord=coord, academy_first=academy_first))
    gaia = [coord for coord, cell in state['board']['hexes'].items()
            if cell['planet'] and cell['planet']['planet_type'] == 'Transdim'
            and cell['planet']['owner'] in (None, actor) and structure_at(player, coord) is None]
    starts = origins(state, player)
    targets = sorted(gaia, key=lambda c: (path_distance(state, starts, c), c))[:MAX_GAIA_TARGETS]
    plans.extend(Plan(f'Gaia-colony@{coord}', gaia_coord=coord) for coord in targets)
    asteroids = [coord for coord, cell in state['board']['hexes'].items()
                 if cell['planet'] and cell['planet']['planet_type'] == 'Asteroid'
                 and cell['planet']['owner'] is None and not cell['structures']]
    for coord in targets:
        plans.append(Plan(f'Immediate-Gaia@{coord}', gaia_coord=coord, immediate_only=True))
        # One nearby asteroid per sampled Gaia colony; unsampled pairs remain unknown.
        if asteroids:
            asteroid = min(asteroids, key=lambda c: (path_distance(state, starts+[coord], c), c))
            plans.append(Plan(f'Immediate-Gaia@{coord}-asteroid@{asteroid}',
                              gaia_coord=coord, immediate_only=True, asteroid_coord=asteroid))
    if formations(player) < 3:
        plans.append(Plan('three-federations-separate-cores', federation_goal=3))
        for coord in sites if not pi else ():
            plans.append(Plan(f'PI@{coord}-three-federations', institute=coord, federation_goal=3))
    return plans, {'gaia_targets_total': len(gaia), 'gaia_targets_sampled': targets,
                   'pair_targets_total': len(pairs), 'max_distance_pairs': MAX_DISTANCE_PAIRS,
                   'asteroid_targets_total': len(asteroids),
                   'unsearched_targets': 'unknown; not ranked as impossible or worse'}


def acquired(snapshot, actor, plan):
    player = snapshot['state']['players'][actor]
    if plan.federation_goal:
        return formations(player) >= plan.federation_goal
    if plan.gaia_coord:
        built = ('Mine', 'TradingStation', 'ResearchLab', 'Academy', 'PlanetaryInstitute')
        return (kind(structure_at(player, plan.gaia_coord)) in built and
                (not plan.asteroid_coord or kind(structure_at(player, plan.asteroid_coord)) in built))
    if plan.repeat_rebellion:
        return False  # Keep testing paid uses after the native round reset.
    if plan.institute:
        return (structure_at(player, plan.institute) == 'PlanetaryInstitute' and
                (not plan.academy_coord or structure_at(player, plan.academy_coord) == {'Academy': plan.academy}))
    if plan.advanced:
        return plan.advanced[1] in player['advanced_tech_tiles']
    if plan.targets and not plan.payoff:
        from strategy_teacher import TRACK_KEYS
        return all(player['research_tracks'][TRACK_KEYS[t]] >= n for t, n in plan.targets)
    return achieved(snapshot, actor, plan)


def available(snapshot, plan):
    """Invalidate lost concrete targets, not temporarily unaffordable actions."""
    from strategy_teacher import TRACK_KEYS
    from resource_plans.routes import SHIP_PAYOFFS
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if plan.institute:
        current = structure_at(player, plan.institute)
        if current not in ('Mine', 'TradingStation', 'PlanetaryInstitute'):
            return False
        if any(s['kind'] == 'PlanetaryInstitute' and s['hex'] != plan.institute
               for s in player['structures']):
            return False
    if plan.academy_coord:
        if any(s['kind'] == {'Academy': plan.academy} and s['hex'] != plan.academy_coord
               for s in player['structures']):
            return False
        if kind(structure_at(player, plan.academy_coord)) not in (
                'Mine', 'TradingStation', 'ResearchLab', 'Academy'):
            return False
        if (kind(structure_at(player, plan.academy_coord)) == 'Academy'
                and structure_at(player, plan.academy_coord) != {'Academy': plan.academy}):
            return False
    for coord in (plan.gaia_coord, plan.asteroid_coord):
        if coord:
            planet = state['board']['hexes'].get(coord, {}).get('planet')
            if not planet or planet['owner'] not in (None, actor):
                return False
    if plan.advanced:
        track, tile = plan.advanced
        if state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(track)] != tile:
            return False
    for track, target in plan.targets:
        if target == 5 and any(p is not player and p['research_tracks'][TRACK_KEYS[track]] == 5
                               for p in state['players']):
            return False
    ship = plan.ship or ('Rebellion' if plan.payoff == 'RebellionGainTechTile' else None)
    if ship and SHIP_PAYOFFS[ship][1] in state['used_spaceship_actions']:
        return False
    return True


def upgrade_at(state, player, coord, target):
    current = structure_at(player, coord)
    if current == target:
        return lambda a: False, {}
    if current == 'Mine':
        next_kind = 'TradingStation'
    elif current == 'TradingStation':
        next_kind = 'PlanetaryInstitute' if target == 'PlanetaryInstitute' else 'ResearchLab'
    elif current == 'ResearchLab' and isinstance(target, dict):
        next_kind = target
    else:
        return lambda a: False, {}
    cost = construction_cost(state, player, {'type': 'Upgrade', 'coord': coord, 'to': next_kind})
    return (lambda a: a['type'] == 'Upgrade' and a['coord'] == coord and a['to'] == next_kind), {
        'ore': cost.ore, 'credits': cost.credits}


def next_milestone(snapshot, plan):
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if plan.institute:
        if any(s['kind'] == 'PlanetaryInstitute' and s['hex'] != plan.institute for s in player['structures']):
            return lambda a: False, {}
        steps = [(plan.institute, 'PlanetaryInstitute')]
        if plan.academy_coord:
            steps.append((plan.academy_coord, {'Academy': plan.academy}))
            if plan.academy_first:
                steps.reverse()
        for coord, target in steps:
            if structure_at(player, coord) != target:
                return upgrade_at(state, player, coord, target)
    if plan.repeat_rebellion:
        return milestone(snapshot, Route('repeat', ship='Rebellion', payoff='RebellionGainTechTile'))
    if plan.federation_goal:
        return federation_milestone(snapshot, plan)
    if plan.institute:
        return lambda a: False, {}
    if plan.gaia_coord:
        coord = plan.gaia_coord
        if structure_at(player, coord) is not None and plan.asteroid_coord:
            coord = plan.asteroid_coord
            planet = state['board']['hexes'].get(coord, {}).get('planet')
            if not planet or planet['owner'] is not None:
                return lambda a: False, {}
            cost = construction_cost(state, player, {'type': 'Build', 'coord': coord})
            # Ordinary native asteroid Build consumes the recovered former. Do not
            # silently substitute the Eclipse credit action for this specific chain.
            return (lambda a: a['type'] == 'Build' and a.get('coord') == coord), {
                'ore': cost.ore, 'credits': cost.credits, 'qic': cost.qic}
        planet = state['board']['hexes'].get(coord, {}).get('planet')
        if not planet or planet['owner'] not in (None, actor) or acquired(snapshot, actor, plan):
            return lambda a: False, {}
        if planet['is_gaia_formed']:
            cost = construction_cost(state, player, {'type': 'Build', 'coord': coord})
            return (lambda a: a['type'] in BUILD_ACTIONS and a.get('coord') == coord), {
                'ore': cost.ore, 'credits': cost.credits, 'qic': cost.qic}
        if planet['owner'] == actor:
            # Actual deployed Gaiaformer; native pass/round phases do the conversion.
            return (lambda a: a['type'] == 'Pass' and state['round'] < 6), {}
        predicate = lambda a: a.get('coord') == coord and (
            a['type'] in ('TFMarsGaiaFormation', 'RoundBoosterImmediateGaiaFormation')
            if plan.immediate_only else matches_payoff(a, 'GaiaFormation'))
        if any(predicate(c['action']) for c in snapshot['candidates']):
            return predicate, {}
        if player['research_tracks']['gaia'] == 0:
            return milestone(snapshot, Route('Gaia-access', (('GaiaProject', 1),)))
        if plan.immediate_only:
            if 2 not in player['explored_ships'] and any(b['id'] == 'TFMars' for b in state['spaceship_boards']):
                return (lambda a: a['type'].endswith('ExploreSpaceship') and a.get('ship') == 'TFMars'), {'qic': 1}
            return predicate, {}  # Taken/unfunded action: no invented normal forming or level2.
        return predicate, {'qic': range_qic(state, player, coord)}
    return milestone(snapshot, plan)


def federation_milestone(snapshot, plan):
    """Separate-core candidate, never a fabricated future federation geometry.

    Only native FormFederation candidates certify a completed group. Preparatory
    upgrades/builds are goals, not proof that three groups can eventually connect.
    The unrestricted control still competes for early advanced-tech/track races.
    """
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if formations(player) >= plan.federation_goal:
        return lambda a: False, {}
    used = set(player['federated_hexes'])
    large = {s['hex'] for s in player['structures'] if kind(s['kind']) in ('Academy', 'PlanetaryInstitute')}
    def federation(action):
        return action['type'] == 'FormFederation' and len(large.intersection(action['hexes'])) <= 1
    if any(federation(c['action']) for c in snapshot['candidates']):
        return federation, {}
    def prepare(action):
        coord = action.get('coord')
        if coord is None or coord in used:
            return False
        if action['type'] == 'Upgrade':
            old = structure_at(player, coord)
            return (power(player, action['to']) > power(player, old)
                    or action['to'] == 'ResearchLab' and not large.difference(used))
        return (action['type'] in BUILD_ACTIONS and
                not any(distance(coord, c) == 1 for c in used))
    return prepare, {}
