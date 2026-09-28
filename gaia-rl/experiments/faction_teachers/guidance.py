"""Two approved source-backed technology proposals; no prices or forced moves."""
import os

from resource_plans.routes import SHIP_IDS
from strategy_teacher import TRACK_KEYS

PILOT_SOURCE = 'faction-tech-pilot'
PRESERVE_SOURCE = 'faction-tech-preserve'  # Internal comparison mode, not a strategy citation.
PILOT_TILES = {'Terrans': (10, 8), 'Ambas': (6,)}


def preserves_plan(goal):
    return PILOT_SOURCE in goal.sources and PRESERVE_SOURCE in goal.sources


def comparison_variants(goal):
    """Keep the original route, then compare preservation without a value bonus."""
    from dataclasses import replace
    if PILOT_SOURCE not in goal.sources:
        return (goal,)
    prefix = 'preserve-plan: '
    original = (replace(goal, name=goal.name.replace(prefix, '', 1),
                        sources=tuple(s for s in goal.sources if s != PRESERVE_SOURCE))
                if preserves_plan(goal) else goal)
    return (original, replace(original, name=prefix + original.name,
                              sources=(*original.sources, PRESERVE_SOURCE)))


def enabled():
    return os.environ.get('GAIA_FACTION_TECH_PLANS', '0') == '1'


def technology_choice(state, action):
    """Return the standard tile and native-aligned track, not an assumed bump."""
    choice = action.get('tech_tile_choice') or action.get('choice') or {}
    if action['type'] == 'RebellionGainTechTile':
        tile, track = action['tile'], action.get('track')
    elif choice.get('kind') == 'Standard':
        tile, track = choice['tile'], choice.get('advance_track')
    else:
        return None
    slots = state['research_board']['tech_tile_slots'][:6]
    if tile in slots:
        track = tuple(TRACK_KEYS)[slots.index(tile)]
    return tile, track


def available_technology(snapshot, tile, actor=None):
    actor = snapshot['player'] if actor is None else actor
    state, player = snapshot['state'], snapshot['state']['players'][actor]
    if tile in player['tech_tiles'] or tile in player['covered_tech_tiles']:
        return False
    return tile in state['research_board']['tech_tiles'] or any(
        SHIP_IDS[board['id']] in player['explored_ships'] and tile in board['tech_tiles']
        for board in state['spaceship_boards'] if board['id'] in SHIP_IDS)


def technology_preparations(snapshot, tile):
    """Existing paid acquisition routes, ranked using the unchanged policy."""
    from four_factions.preparation import Goal, viable, achieved
    actor = snapshot['player']
    player = snapshot['state']['players'][actor]
    routes = []
    for site in player['structures']:
        for target in ('ResearchLab', 'Science', 'Qic'):
            goal = Goal(f'tech-via-{target}@{site["hex"]}', 'upgrade', site['hex'], target, tile=tile)
            if viable(snapshot, actor, goal) and not achieved(snapshot, actor, goal):
                routes.append(goal)
    if any(board['id'] == 'Rebellion' for board in snapshot['state']['spaceship_boards']):
        routes.append(Goal('tech-via-Rebellion', 'ship', target='Rebellion', tile=tile,
                           payoff='RebellionGainTechTile'))
    return routes


def pilot_viable(snapshot, actor, goal):
    """Retain required active effects even after acquisition steps were consumed."""
    from four_factions.preparation import viable
    player = snapshot['state']['players'][actor]
    if goal.payoff == 'cancelled':
        return False
    if goal.target == 'Ambas':
        from faction_teachers.federation_preparation import new_federation_site
        from four_factions.preparation import goal_leaves
        if any(step.family == 'federation-race' and step.coord is not None
               and not new_federation_site(player, step.coord) for step in goal_leaves(goal)):
            return False  # Native rules forbid this target, regardless of future income/power.
    # A colony built before the scoring technology is not its future payoff.
    if goal.target == 'Terrans' and any(step.family == 'technology' for step in goal.steps):
        if any(step.family == 'colony' and any(s['hex'] == step.coord for s in player['structures'])
               for step in goal.steps):
            return False
    return all(tile not in player['covered_tech_tiles'] and
               (tile in player['tech_tiles'] or available_technology(snapshot, tile, actor))
               for tile in PILOT_TILES.get(goal.target, ())) and all(
                   viable(snapshot, actor, step) for step in goal.steps)


def advice_goals(snapshot):
    from federation.teacher import formations
    from four_factions.preparation import Goal, achieved, viable
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    faction = player['faction']
    if faction not in PILOT_TILES:
        return []
    sources = (('B04', 'B4-01', 'B4-03') if faction == 'Terrans' else
               ('B06', 'B18', 'B19', 'A01', 'A02')) + (PILOT_SOURCE,)
    technology = tuple(Goal(f'technology-{tile}', 'technology', tile=tile)
                       for tile in PILOT_TILES[faction])
    result = []

    def add(name, steps):
        pending = list(steps)
        while pending and achieved(snapshot, actor, pending[0]):
            pending.pop(0)
        goal = Goal(name, 'ordered', target=faction, steps=tuple(pending), sources=sources)
        if pending and viable(snapshot, actor, goal):
            result.append(goal)

    if faction == 'Terrans':
        for coord, cell in state['board']['hexes'].items():
            planet = cell['planet']
            if (planet and planet['planet_type'] in ('Gaia', 'Transdim') and
                    planet['owner'] in (None, actor) and not cell['structures']):
                add(f'Terrans-charge-and-Gaia@{coord}',
                    (*technology, Goal(f'Gaia@{coord}', 'colony', coord)))
    else:
        pi = any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])
        sites = [None] if pi else [s['hex'] for s in player['structures']
                                  if s['kind'] in ('Mine', 'TradingStation')]
        for site in sites:
            for mine in player['structures']:
                if mine['kind'] != 'Mine' or mine['hex'] == site or mine['hex'] in player['federated_hexes']:
                    continue
                coord = mine['hex']
                prerequisites = () if pi else (Goal(f'PI@{site}', 'upgrade', site, 'PlanetaryInstitute'),)
                add(f'Ambas-large-power@{site}-relocate@{coord}-federate', (*technology, *prerequisites,
                    Goal(f'relocate@{coord}', 'faction-action', coord, 'AmbasSwapPlanetaryInstitute'),
                    Goal(f'federate@{coord}', 'federation-race', coord, level=formations(player)+1)))
    return result
