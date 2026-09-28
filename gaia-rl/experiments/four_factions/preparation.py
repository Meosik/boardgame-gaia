"""Opt-in paid preparation paths with purposeful opponents and unchanged leaf prices.

Goals propose continuations, never grant resources, override native legality, or
award points for intentions. Historical teachers remain available as controls.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
import json
import time

from current_actions.conservation import blocked, identity
from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from current_actions.state_delta import StateDeltaTeacher
from federation.teacher import formations
from four_factions import FACTIONS
from four_factions.preparation_cache import PolicyCache
from four_factions.teacher import NativeFactionTeacher
from four_factions.value import potential
from integrated.features import EVENT, PASS
from research_plans.teacher import best_index, research_track, reached_horizon
from research_plans.value import endpoint_value
from resource_plans.routes import SHIP_IDS, SHIP_PAYOFFS
from strategy_teacher import TRACK_KEYS, distance, kind


class SearchExpired(Exception):
    pass


def check_time(deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise SearchExpired('No more search time; incomplete alternatives remain unknown')


class Policies:
    """Per-faction proof maps; `_plans` are proposals, never legality commitments."""
    def __init__(self, memory=None, *, cache: PolicyCache | None = None, shared_factions=False,
                 delta_factions=(), fixed_openings=False, faction_tech_plans=False):
        if set(delta_factions) - set(FACTIONS):
            raise ValueError('State-delta experiment is limited to the approved quartet')
        self.memory = deepcopy(memory or {})
        self.cache = cache
        self.shared_factions = shared_factions
        self.delta_factions = tuple(sorted(set(delta_factions)))
        self.fixed_openings = fixed_openings
        self.fixed_audit = None
        self.faction_tech_plans = bool(shared_factions and faction_tech_plans)

    def clone(self):
        return Policies(self.memory, cache=self.cache, shared_factions=self.shared_factions,
                        delta_factions=self.delta_factions, fixed_openings=self.fixed_openings,
                        faction_tech_plans=self.faction_tech_plans)

    def rank(self, env, snapshot):
        actor = snapshot['player']
        faction = snapshot['state']['players'][actor]['faction']
        profile = None
        if self.shared_factions:
            from faction_teachers.profiles import profiles
            profile = profiles().get(faction)
        if faction not in FACTIONS and profile is None:
            raise ValueError('Preparation search is scoped to the approved quartet')
        saved = self.memory.get(str(actor), {})
        cache_key = None
        if self.cache is not None and not self.fixed_openings:
            if json.loads(env.snapshot_json()) != snapshot:
                raise ValueError('Cached policy snapshot differs from the native branch')
            # Both scores AND resulting commitments depend on the exact incoming
            # proof map. A snapshot-only cache could silently bypass QIC purpose.
            cache_key = identity((snapshot, saved, self.delta_factions))
            if self.faction_tech_plans:
                cache_key = identity((cache_key, 'faction-tech-pilot'))
            cached = self.cache.get(cache_key)
            if cached is not None:
                scores, self.memory[str(actor)] = cached
                return scores
        policy = (StateDeltaTeacher() if faction in self.delta_factions and faction in FACTIONS[:2] else
                  CurrentActionTeacher() if faction in FACTIONS[:2] else
                  NativeFactionTeacher(profile=profile if faction not in FACTIONS else None,
                                       state_delta=faction in self.delta_factions)).bind(env)
        saved = {state: set(targets) for state, targets in saved.items()}
        if isinstance(policy, NativeFactionTeacher):
            policy.commitments = saved
        else:
            from current_actions.conservation import Conservation
            policy._conservation = Conservation()
            policy._conservation.continuations = saved
        scores = policy.rank(snapshot)
        memory = policy.commitments if isinstance(policy, NativeFactionTeacher) else policy._conservation.continuations
        self.memory[str(actor)] = {state: sorted(targets) for state, targets in memory.items()}
        if self.fixed_openings:
            from bgg_openings.fixed import enforce
            scores, self.fixed_audit = enforce(env, snapshot, scores, self.memory)
        if self.cache is not None and cache_key is not None:
            self.cache.put(cache_key, scores, self.memory[str(actor)])
        return scores


@dataclass(frozen=True)
class Goal:
    name: str
    family: str = 'current'
    coord: str | None = None
    target: str | None = None
    level: int = 0
    tile: int | None = None
    first: int | None = None
    payoff: str | None = None
    steps: tuple['Goal', ...] = ()
    sources: tuple[str, ...] = ()


def goal_from_dict(value):
    return Goal(**{**value, 'steps': tuple(goal_from_dict(s) for s in value.get('steps', ())),
                   'sources': tuple(value.get('sources', ()))})


def advance_goal(snapshot, actor, goal, action, *, before=None):
    """Keep only unfinished work, based on this actor's actual paid action/state."""
    if 'faction-tech-pilot' in goal.sources and before is not None and not viable(before, actor, goal):
        return replace(goal, first=None, payoff='cancelled')
    if goal.family == 'ordered':
        steps = list(goal.steps)
        while steps and achieved(before if before is not None else snapshot, actor, steps[0]):
            steps.pop(0)
        if steps:
            steps[0] = advance_goal(snapshot, actor, steps[0], action, before=before)
        while steps and achieved(snapshot, actor, steps[0]):
            steps.pop(0)
        return replace(goal, first=None, steps=tuple(steps))
    if goal.family == 'faction-action':
        from faction_teachers.paths import action_matches
        return replace(goal, first=None, level=1 if action_matches(goal, action) else goal.level)
    if goal.family == 'sequence':
        steps = tuple(advance_goal(snapshot, actor, step, action) for step in goal.steps)
        return replace(goal, first=None, steps=tuple(s for s in steps if not achieved(snapshot, actor, s)))
    if goal.family == 'ship' and action['type'] == (goal.payoff or SHIP_PAYOFFS[goal.target][0]):
        return replace(goal, level=1)
    return replace(goal, first=None)


def viable(snapshot, actor, goal):
    if 'faction-tech-pilot' in goal.sources:
        from faction_teachers.guidance import pilot_viable
        if not pilot_viable(snapshot, actor, goal):
            return False
    if goal.family == 'bgg-opening':
        from bgg_openings.catalog import parse_buildings
        from bgg_openings.inventory import building_counts
        from bgg_openings.planning import distance_to
        player = snapshot['state']['players'][actor]
        return snapshot['state']['round'] <= 1 and distance_to(
            building_counts(player), parse_buildings(goal.target), player['faction']) is not None
    if achieved(snapshot, actor, goal):
        return True
    player = snapshot['state']['players'][actor]
    if goal.family == 'technology':
        from faction_teachers.guidance import available_technology
        return available_technology(snapshot, goal.tile, actor)
    if goal.family == 'faction-action' and goal.target == 'AmbasSwapPlanetaryInstitute' and goal.coord:
        return owned(player, goal.coord) == 'Mine' and goal.coord not in player['federated_hexes']
    if goal.family == 'federation-race' and goal.coord:
        return goal.coord not in player['federated_hexes'] and owned(player, goal.coord) is not None
    if goal.family == 'ordered':
        if 'B19' in goal.sources and any(not viable(snapshot, actor, step) for step in goal.steps):
            return False  # Do not keep researching for a colony an opponent took.
        return not goal.steps or viable(snapshot, actor, goal.steps[0])
    if goal.family == 'sequence':
        return all(viable(snapshot, actor, step) for step in goal.steps)
    if goal.family == 'upgrade':
        old = owned(player, goal.coord)
        target = {'Academy': goal.target} if goal.target in ('Science', 'Qic') else goal.target
        return old in ('Mine', 'TradingStation', 'ResearchLab') and not (
            target != 'ResearchLab' and any(s['kind'] == target for s in player['structures'])) and not (
                goal.target == 'PlanetaryInstitute' and old == 'ResearchLab' and player['faction'] != 'Bescods')
    if goal.family == 'colony':
        cell = snapshot['state']['board']['hexes'].get(goal.coord)
        return bool(cell and cell['planet'] and cell['planet']['owner'] in (None, actor) and not cell['structures'])
    if goal.family == 'advanced':
        return snapshot['state']['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(goal.target)] == goal.tile
    if goal.family == 'lost-fleet':
        return snapshot['state']['research_board'].get('lost_fleet_advanced_tech_tile') == goal.tile
    return True


def owned(player, coord):
    return next((s['kind'] for s in player['structures'] if s['hex'] == coord), None)


def achieved(snapshot, actor, goal):
    player = snapshot['state']['players'][actor]
    if goal.family == 'ordered':
        return not goal.steps
    if goal.family == 'faction-action':
        return goal.level == 1
    if goal.family == 'bgg-opening':
        from bgg_openings.catalog import parse_buildings
        from bgg_openings.inventory import building_counts
        return snapshot['state']['round'] == 1 and building_counts(player) == parse_buildings(goal.target)
    if goal.family == 'sequence':
        return all(achieved(snapshot, actor, step) for step in goal.steps)
    if goal.family == 'upgrade':
        target = {'Academy': goal.target} if goal.target in ('Science', 'Qic') else goal.target
        if target == 'ResearchLab' and kind(owned(player, goal.coord)) == 'Academy':
            return True  # A subsequent Academy does not erase the paid Lab milestone.
        return owned(player, goal.coord) == target
    if goal.family == 'expansion':
        return len(player['structures']) >= goal.level
    if goal.family == 'explore':
        return SHIP_IDS[goal.target] in player['explored_ships']
    if goal.family == 'ship':
        return goal.level == 1
    if goal.family == 'research':
        return player['research_tracks'][TRACK_KEYS[goal.target]] >= goal.level
    if goal.family == 'technology':
        return goal.tile in player['tech_tiles'] and goal.tile not in player['covered_tech_tiles']
    if goal.family == 'colony':
        return owned(player, goal.coord) is not None
    if goal.family == 'federations':
        return formations(player) >= 3
    if goal.family == 'federation-race':
        return formations(player) >= goal.level and (goal.coord is None or goal.coord in player['federated_hexes'])
    if goal.family in ('advanced', 'lost-fleet'):
        return goal.tile in player['advanced_tech_tiles']
    return False


def goals_for(snapshot, *, shared_factions=False, guide_tracks=False, observed=False, faction_tech_plans=False):
    """No nearest-two colony filter or one-shape-per-token filter in this lane."""
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    goals = []
    for target in ('Science', 'Qic', 'PlanetaryInstitute'):
        building = {'Academy': target} if target in ('Science', 'Qic') else target
        if any(s['kind'] == building for s in player['structures']):
            continue
        for s in player['structures']:
            if s['kind'] in ('Mine', 'TradingStation') or (s['kind'] == 'ResearchLab' and
                    (target != 'PlanetaryInstitute' or player['faction'] == 'Bescods')):
                goals.append(Goal(f'{target}@{s["hex"]}', 'upgrade', s['hex'], target))
    for track, key in TRACK_KEYS.items():
        level = player['research_tracks'][key]
        # Reuse the existing research-route milestones, not a fixed faction order.
        target = (max(2, level+1) if track in ('Navigation', 'GaiaProject') else
                  (2 if level < 2 else 4 if level < 4 else 5) if track in ('Economy', 'Science') else
                  3 if track == 'Terraforming' and level in (1, 2) else level+1)
        if level < 5:
            goals.append(Goal(f'{track}-{target}', 'research', target=track, level=target))
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if (planet and planet['planet_type'] in ('Gaia', 'Transdim')
                and planet['owner'] in (None, actor) and not cell['structures']):
            goals.append(Goal(f'colony@{coord}', 'colony', coord))
    for ship in state['spaceship_boards']:
        if ship['id'] in SHIP_PAYOFFS:
            goals.append(Goal(f'{ship["id"]}-use', 'ship', target=ship['id']))
    for track, tile in zip(TRACK_KEYS, state['research_board']['advanced_tech_tiles']):
        if tile is not None:
            goals.append(Goal(f'advanced-{tile}', 'advanced', target=track, tile=tile))
    if player['faction'] == 'Ivits':
        goals.append(Goal('extend-single-federation', 'federation-race', level=formations(player)+1,
                          sources=('B12',)))
    elif formations(player) < 3:
        goals.append(Goal('three-federations-separate-cores', 'federations'))
    tile = state['research_board'].get('lost_fleet_advanced_tech_tile')
    if tile is not None and tile not in player['advanced_tech_tiles']:
        goals.append(Goal(f'lost-fleet-advanced-{tile}', 'lost-fleet', tile=tile,
                          sources=('PG25', 'LF04', 'user-three-shuttles')))
    from four_factions.source_paths import opening_goals, expansion_goals
    # Compare source-backed multi-step openings early, while retaining every
    # existing goal/root as an alternative and reporting unsearched comparisons.
    goals = opening_goals(snapshot)+goals
    if shared_factions:
        from faction_teachers.paths import goals as faction_goals
        goals = faction_goals(snapshot)+goals
        if faction_tech_plans:
            from faction_teachers.guidance import advice_goals
            goals = advice_goals(snapshot)+goals
    goals.extend(expansion_goals(snapshot))
    if guide_tracks:
        from four_factions.track_guidance import guide_goals
        goals = guide_goals(snapshot)+goals
    if observed:
        from observed_games.ob01 import goals as observed_goals
        goals = observed_goals(snapshot)+goals
    return [goal for goal in goals if viable(snapshot, actor, goal) and not achieved(snapshot, actor, goal)]


def scoring_pairs(snapshot, scores, goals, *, nested=True):
    """Compare a currently legal scoring-tile acquisition with its intended work.

    This proposes comparisons, not a scoring-tile bonus. Ordinary native VP in
    the resulting actions determines the payoff; no predicted trigger is paid.
    """
    pairs = []
    state = snapshot['state']
    for i, candidate in enumerate(snapshot['candidates']):
        if blocked(scores[i]):
            continue
        action = candidate['action']
        choice = action.get('tech_tile_choice') or (action.get('choice') if nested else None) or {}
        families = set()
        standard = (choice.get('tile') if choice.get('kind') == 'Standard' else
                    action.get('tile') if action['type'] == 'RebellionGainTechTile' else None)
        if standard == 8:  # Existing ordinary Gaia-construction scoring tile.
            families.add('colony')
        if choice.get('kind') == 'Advanced' and choice.get('track') in TRACK_KEYS:
            tile = state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(choice['track'])]
            counter = EVENT.get(tile, PASS.get(tile, (None, 0)))[0]
            families.update({'mines': {'colony'}, 'research': {'research'},
                             'ts': {'upgrade'}, 'federations': {'federations'}}.get(counter, set()))
        for goal in goals:
            work = goal_leaves(goal) if nested else goal.steps if goal.family == 'sequence' else (goal,)
            if any(step.family in families or (step.family == 'expansion' and 'colony' in families)
                   for step in work):
                pairs.append(replace(goal, name=f'tile-action-{i}-then-{goal.name}', first=i))
    return pairs


def goal_leaves(goal):
    if goal.family in ('ordered', 'sequence'):
        return tuple(leaf for step in goal.steps for leaf in goal_leaves(step))
    return (goal,)


def reserved_pilot_sites(goal):
    if 'faction-tech-pilot' not in goal.sources:
        return set()
    return {leaf.coord for leaf in goal_leaves(goal) if (
        leaf.family == 'upgrade' and leaf.target == 'PlanetaryInstitute' or
        leaf.family == 'faction-action' and leaf.target == 'AmbasSwapPlanetaryInstitute')}


def predicate_for(snapshot, goal):
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if goal.family == 'ordered':
        pending = list(goal.steps)
        while pending and achieved(snapshot, actor, pending[0]):
            pending.pop(0)
        if not pending:
            return lambda a: False
        matches = predicate_for(snapshot, pending[0])
        if any(leaf.family == 'technology' for leaf in goal_leaves(pending[0])):
            from faction_teachers.guidance import technology_choice
            reserved = reserved_pilot_sites(goal)
            if reserved:
                base_matches = matches
                matches = lambda a: base_matches(a) and not (a['type'] == 'Upgrade' and a.get('coord') in reserved)
            research = next((leaf for step in pending[1:] for leaf in goal_leaves(step)
                             if leaf.family == 'research' and not achieved(snapshot, actor, leaf)), None)
            if research is not None:
                def aligned(action):
                    choice = technology_choice(state, action)
                    return matches(action) and choice is not None and choice[1] == research.target
                if any(aligned(c['action']) for c in snapshot['candidates']):
                    return aligned
        return matches
    if goal.family == 'technology':
        from faction_teachers.guidance import technology_choice
        return lambda a: (choice := technology_choice(state, a)) is not None and choice[0] == goal.tile
    if goal.family == 'faction-action':
        from faction_teachers.paths import action_matches
        return lambda a: action_matches(goal, a)
    if goal.family == 'sequence':
        pending = [step for step in goal.steps if not achieved(snapshot, actor, step)]
        if not pending:
            return lambda a: False
        matches = predicate_for(snapshot, pending[0])
        # A Lab/Academy/ship tech can pay for the NEXT research milestone too.
        # Prefer such native variants only if present; never invent a free bump.
        research = next((g for g in pending if g.family == 'research'), None)
        if research is not None and any(matches(c['action']) and
                research_track(state, c['action']) == research.target for c in snapshot['candidates']):
            return lambda a: matches(a) and research_track(state, a) == research.target
        return matches
    if goal.family == 'upgrade':
        target = next_upgrade(player, goal)
        def upgrade(a):
            if a.get('coord') != goal.coord:
                return False
            if goal.tile is not None and target != 'TradingStation':
                from faction_teachers.guidance import technology_choice
                choice = technology_choice(state, a)
                if choice is None or choice[0] != goal.tile:
                    return False
            return ((a['type'] == 'Upgrade' and a['to'] == target) or
                    (target == 'TradingStation' and a['type'] == 'RebellionFreeTradingStation') or
                    (target == 'ResearchLab' and a['type'] == 'TwilightFreeResearchLab'))
        return upgrade
    if goal.family == 'expansion':
        return lambda a: a['type'] in ('Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild',
                                       'TwilightRangeBuild', 'SpaceshipCreditTerraform', 'EclipseAsteroidMine')
    if goal.family == 'research':
        return lambda a: research_track(state, a) == goal.target
    if goal.family == 'colony':
        planet = state['board']['hexes'][goal.coord]['planet']
        if planet['owner'] not in (None, actor):
            return lambda a: False
        forming = planet['planet_type'] == 'Transdim' and not planet['is_gaia_formed']
        return lambda a: (a.get('coord') == goal.coord and
                          ('GaiaFormation' in a['type'] if forming else
                           a['type'] in ('Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild',
                                         'TwilightRangeBuild', 'SpaceshipCreditTerraform')))
    if goal.family in ('ship', 'explore'):
        if goal.payoff == 'SpaceshipCreditTerraform' and player['explored_ships']:
            return lambda a: a['type'] == goal.payoff
        if SHIP_IDS[goal.target] not in player['explored_ships']:
            return lambda a: a['type'].endswith('ExploreSpaceship') and a.get('ship') == goal.target
        if goal.family == 'explore':
            return lambda a: False
        payoff = goal.payoff or SHIP_PAYOFFS[goal.target][0]
        return lambda a: a['type'] == payoff and (goal.tile is None or a.get('tile') == goal.tile)
    if goal.family == 'lost-fleet':
        board = state['research_board']
        if board.get('lost_fleet_advanced_tech_tile') != goal.tile:
            return lambda a: False
        def acquire(a):
            return (a.get('tech_tile_choice') or {}).get('kind') == 'LostFleetAdvanced'
        if any(acquire(c['action']) for c in snapshot['candidates']):
            return acquire
        if board.get('lost_fleet_advanced_tech_requirement') == 'exploration-shuttles' and len(player['explored_ships']) < 3:
            return lambda a: a['type'].endswith('ExploreSpaceship')
        # Other access conditions and green token/cover requirements are native.
        return lambda a: a['type'] == 'FormFederation'
    if goal.family == 'advanced':
        if state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(goal.target)] != goal.tile:
            return lambda a: False
        def acquire(a):
            choice = a.get('tech_tile_choice') or {}
            return choice.get('kind') == 'Advanced' and choice.get('track') == goal.target
        if any(acquire(c['action']) for c in snapshot['candidates']):
            return acquire
        if state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(goal.target)] != goal.tile:
            return lambda a: False
        if player['research_tracks'][TRACK_KEYS[goal.target]] < 4:
            return lambda a: research_track(state, a) == goal.target
        return lambda a: a['type'] == 'FormFederation'
    if goal.family == 'federations':
        large = {s['hex'] for s in player['structures'] if kind(s['kind']) in ('Academy', 'PlanetaryInstitute')}
        if any(c['action']['type'] == 'FormFederation' for c in snapshot['candidates']):
            return lambda a: a['type'] == 'FormFederation' and len(large.intersection(a['hexes'])) <= 1
        used = set(player['federated_hexes'])
        return lambda a: (a['type'] == 'Upgrade' and a['coord'] not in used and
                          (a['to'] in ('TradingStation', 'PlanetaryInstitute') if isinstance(a['to'], str)
                           else 'Academy' in a['to'])) or (
                              a['type'] == 'Build' and not any(distance(a['coord'], c) == 1 for c in used))
    if goal.family == 'federation-race':
        # Contrast immediate tech access with the separate-core plan; don't
        # forbid a two-large-building federation in all source proposals.
        return lambda a: a['type'] == 'FormFederation' and (goal.coord is None or goal.coord in a['hexes'])
    return lambda a: False


def next_upgrade(player, goal):
    old = owned(player, goal.coord)
    if old == 'Mine':
        return 'TradingStation'
    if player['faction'] == 'Bescods':
        if goal.target == 'PlanetaryInstitute':
            return 'ResearchLab' if old == 'TradingStation' else 'PlanetaryInstitute'
        if old == 'TradingStation' and goal.target in ('Science', 'Qic'):
            return {'Academy': goal.target}
    return ('PlanetaryInstitute' if old == 'TradingStation' and goal.target == 'PlanetaryInstitute'
            else 'ResearchLab' if old == 'TradingStation' else {'Academy': goal.target})


def funding_need(snapshot, goal):
    """Existing native-aligned costs guide proposals, never create legal actions."""
    player = snapshot['state']['players'][snapshot['player']]
    if goal.family == 'ordered':
        pending = list(goal.steps)
        while pending and achieved(snapshot, snapshot['player'], pending[0]):
            pending.pop(0)
        return funding_need(snapshot, pending[0]) if pending else {}
    if goal.family == 'sequence':
        goal = next((g for g in goal.steps if not achieved(snapshot, snapshot['player'], g)), goal)
    if goal.family == 'research':
        return {'knowledge': 4}
    if goal.family == 'colony' and 'B19' in goal.sources:
        from four_factions.track_guidance import costs
        cost = costs(snapshot['state'], player).get(goal.coord)
        if cost is not None:
            return {key: getattr(cost, key) for key in ('ore', 'credits', 'qic')}
    if goal.family == 'upgrade':
        target = next_upgrade(player, goal)
        # engine.rs::upgrade_cost includes Bescods' alternate upgrade edges.
        # Do not impersonate HH/Xenos to call the legacy two-faction estimator.
        if target == 'TradingStation':
            neighbor = any(distance(coord, goal.coord) <= 2 and
                           any(s['owner'] != snapshot['player'] for s in cell['structures'])
                           for coord, cell in snapshot['state']['board']['hexes'].items())
            return {'ore': 2, 'credits': 3 if neighbor else 6}
        costs = {'ResearchLab': (3, 5), 'PlanetaryInstitute': (4, 6), 'Academy': (6, 6)}
        ore, credits = costs[kind(target)]
        return {'ore': ore, 'credits': credits}
    if goal.family == 'ship' and goal.target == 'Rebellion' and SHIP_IDS['Rebellion'] in player['explored_ships']:
        return {'qic': 3}  # Current engine's paid Rebellion action, not base-game 4 QIC.
    return {}


def select_goal(env, snapshot, scores, goal, policies, deadline, *, allow_fallback=True):
    from faction_teachers.guidance import preserves_plan
    actor = snapshot['player']
    if (not policies.faction_tech_plans or not preserves_plan(goal)
            or achieved(snapshot, actor, goal) or not viable(snapshot, actor, goal)):
        return _select_goal(env, snapshot, scores, goal, policies, deadline,
                            allow_fallback=allow_fallback)
    # Restrict only this hypothetical continuation, never the native legal set,
    # ordinary route, cached ranks, or other players' choices.
    from current_actions.conservation import PREFIX
    eligible = list(scores)
    swap_sites = {step.coord for step in goal_leaves(goal)
                  if step.family == 'faction-action' and step.target == 'AmbasSwapPlanetaryInstitute'
                  and step.coord is not None and not achieved(snapshot, actor, step)}
    federation_sites = {step.coord for step in goal_leaves(goal)
                        if step.family == 'federation-race' and step.coord is not None}
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        # pilot_viable requires an unfederated swap mine. Reject all equivalent
        # token/satellite variants at once rather than repeating funding search.
        if action['type'] == 'FormFederation' and swap_sites.intersection(action['hexes']):
            eligible[i] = (scores[i][0], PREFIX + 'federates the reserved swap mine')
        elif action['type'] == 'FormFederation' and any(
                site not in action['hexes'] and any(distance(site, coord) == 1
                    for coord in (*action['hexes'], *action['satellite_hexes']))
                for site in federation_sites):
            eligible[i] = (scores[i][0], PREFIX + 'makes the target adjacent to an old federation')
    while True:
        check_time(deadline)
        index = _select_goal(env, snapshot, eligible, goal, policies, deadline,
                             allow_fallback=allow_fallback)
        if index is None or keeps_plan(env, snapshot, index, goal, deadline):
            return index
        eligible[index] = (scores[index][0], PREFIX + 'invalidates this preservation comparison')


def keeps_plan(env, snapshot, index, goal, deadline):
    """Check actual paid effects against unfinished prerequisites, not intentions."""
    actor = snapshot['player']
    if achieved(snapshot, actor, goal) or not viable(snapshot, actor, goal):
        return True  # Completed/external-invalidated plans use the existing fallback.
    check_time(deadline)
    after = json.loads(env.fork(snapshot['decision_id'], index).snapshot_json())
    action = snapshot['candidates'][index]['action']
    remaining = advance_goal(after, actor, goal, action, before=snapshot)
    check_time(deadline)
    return viable(after, actor, remaining)


def _select_goal(env, snapshot, scores, goal, policies, deadline, *, allow_fallback=True):
    if goal.family == 'bgg-opening':
        from bgg_openings.catalog import parse_buildings
        from bgg_openings.planning import select_action
        return select_action(env, snapshot, scores, parse_buildings(goal.target), policies, deadline)
    fallback = best_index(scores, range(len(scores))) if allow_fallback else None
    if achieved(snapshot, snapshot['player'], goal) or not viable(snapshot, snapshot['player'], goal):
        return fallback
    phase = snapshot['state']['phase']
    if (not isinstance(phase, dict) or 'ActionPhase' not in phase) and goal.family not in ('ordered', 'faction-action', 'technology'):
        return fallback
    predicate = predicate_for(snapshot, goal)
    direct = best_index(scores, [i for i, c in enumerate(snapshot['candidates']) if predicate(c['action'])])
    if direct is not None:
        return direct
    pending = goal
    while pending.family in ('ordered', 'sequence'):
        pending = next((step for step in pending.steps if not achieved(snapshot, snapshot['player'], step)), None)
        if pending is None:
            return fallback
    if (policies.faction_tech_plans and pending.family == 'federation-race'
            and pending.coord is not None and goal.target == 'Ambas'):
        from faction_teachers.guidance import preserves_plan
        if preserves_plan(goal):
            from faction_teachers.federation_preparation import needs_power, select_preparation
            if needs_power(snapshot):
                prepared = select_preparation(env, snapshot, scores, goal, policies, deadline)
                return prepared if prepared is not None else fallback
    if pending.family == 'technology':
        from faction_teachers.guidance import technology_preparations
        candidates = []
        for route in technology_preparations(snapshot, pending.tile):
            check_time(deadline)
            # Do not dismantle this proposal's future PI site or swap mine just
            # to obtain its prerequisite tile. Ordinary roots remain available.
            if route.family == 'upgrade' and route.coord in reserved_pilot_sites(goal):
                continue
            index = select_goal(env, snapshot, scores, route, policies, deadline, allow_fallback=False)
            if index is not None:
                candidates.append(index)
        return best_index(scores, candidates) if candidates else fallback
    if goal.family in ('current', 'root'):
        return fallback
    before_resources = snapshot['state']['players'][snapshot['player']]['resources']
    need = funding_need(snapshot, goal)
    missing = {k: n-before_resources[k] for k, n in need.items() if n > before_resources[k]}
    # Prove that paid resource/ship actions unlock the actual next milestone.
    # The historical funding budget is retained; no fictional missing resources.
    eligible = sorted((i for i, score in enumerate(scores) if not blocked(score)), key=lambda i: (-scores[i][0], i))
    examined = 0
    for i in eligible:
        action = snapshot['candidates'][i]['action']
        if action['type'] not in ('FreeAction', 'PowerAction', 'AcademyQicAction', 'TechTileSpecialAction'):
            continue
        if examined >= 32:
            break
        check_time(deadline)
        examined += 1
        branch = env.fork(snapshot['decision_id'], i)
        after = json.loads(branch.snapshot_json())
        # Main resource actions end the turn. Judge actual useful funding here;
        # the full rollout still executes every opponent reply before spending.
        # Previously these were ignored merely because the actor changed.
        if action['type'] != 'FreeAction' and missing:
            resources = after['state']['players'][snapshot['player']]['resources']
            if any(resources[k] > before_resources[k] for k in missing):
                return i
        if after['player'] == snapshot['player']:
            follow = policies.clone().rank(branch, after)
            ready = predicate_for(after, goal)
            if any(ready(c['action']) and not blocked(follow[j]) for j, c in enumerate(after['candidates'])):
                return i
    return fallback


def leaf_value(snapshot, actor, root_player, *, guide_tracks=False):
    state = snapshot['state']
    if state['players'][actor]['faction'] in FACTIONS[:2]:
        return endpoint_value(state, actor, root_player, CurrentContextTeacher(), guide_tracks=guide_tracks)
    faction = state['players'][actor]['faction']
    if faction not in FACTIONS:
        from faction_teachers.profiles import profiles
        return potential(state, actor, home=profiles()[faction].home)
    return potential(state, actor, guide_tracks=guide_tracks)


def rollout(env, snapshot, first, goal, policies, deadline, limit=192, *, capture_r1=False,
            decision_depth=None):
    if decision_depth is not None and not 1 <= decision_depth <= limit:
        raise ValueError('Decision depth must be within the existing rollout limit')
    from faction_teachers.guidance import preserves_plan
    preserving = policies.faction_tech_plans and preserves_plan(goal)
    # Fixed-first scoring-tile alternatives must satisfy the same guard too.
    if preserving and not keeps_plan(env, snapshot, first, goal, deadline):
        return {'complete': False, 'value': None, 'actions': [],
                'remaining_goal': asdict(goal),
                'reason': 'fixed first action invalidates preservation; no comparable horizon'}
    actor = snapshot['player']
    root_player = snapshot['state']['players'][actor]
    target_round = snapshot['state']['round'] + 2
    current, branch, index = snapshot, env, first
    policies = policies.clone()
    actions = []
    remaining = goal
    capture_r1 = capture_r1 or goal.family == 'bgg-opening'
    r1_buildings = None
    opening_loss = 0.0
    for step in range(1, limit+1):
        check_time(deadline)
        before = current
        action = before['candidates'][index]['action']
        if step == 1:
            branch = branch.fork(before['decision_id'], index)
        else:
            # This branch is privately owned by this rollout. Keep the first
            # root fork, but do not clone a second time before every later step.
            branch.step(before['decision_id'], index)
        current = json.loads(branch.snapshot_json())
        if policies.fixed_openings:
            from bgg_openings.fixed import boundary_loss
            opening_loss += boundary_loss(before['state'], current['state'], actor)
        if capture_r1 and before['state']['round'] == 1 and current['state']['round'] == 2:
            from bgg_openings.inventory import building_counts
            r1_buildings = asdict(building_counts(before['state']['players'][actor]))
        if before['player'] == actor:
            p, q = before['state']['players'][actor], current['state']['players'][actor]
            actions.append({'round': before['state']['round'], 'action': action,
                            'resources_before': p['resources'], 'resources_after': q['resources'],
                            'vp_before': p['vp'], 'vp_after': q['vp']})
            remaining = advance_goal(current, actor, remaining, action, before=before)
        full_horizon = reached_horizon(current['state'], target_round)
        if full_horizon or (decision_depth is not None and step >= decision_depth):
            goal_acquired = achieved(current, actor, remaining)
            if goal.family == 'bgg-opening':
                from bgg_openings.catalog import parse_buildings
                goal_acquired = r1_buildings == asdict(parse_buildings(goal.target))
            return {'complete': True, 'value': leaf_value(current, actor, root_player,
                    guide_tracks=root_player['faction'] in policies.delta_factions)-opening_loss,
                    'fixed_opening_utility_loss': opening_loss,
                    'goal_acquired': goal_acquired, 'actions': actions,
                    'remaining_goal': asdict(remaining),
                    'end_round': current['state']['round'], 'decisions': step,
                    'end_player': current['state']['players'][actor],
                    **({'r1_buildings': r1_buildings} if capture_r1 else {}),
                    **({'full_horizon_reached': full_horizon} if decision_depth is not None else {})}
        check_time(deadline)
        scores = policies.rank(branch, current)
        # Every simulated seat is purposeful, but uses a cheaper continuation,
        # not a recursively nested five-minute search or an optimality claim.
        index = (select_goal(branch, current, scores, remaining, policies, deadline)
                 if current['player'] == actor else best_index(scores, range(len(scores))))
        if index is None:
            if preserving and current['player'] == actor:
                return {'complete': False, 'value': None, 'actions': actions,
                        'remaining_goal': asdict(remaining),
                        'reason': 'no policy-eligible preserving continuation; unknown, not inferior'}
            raise ValueError('No eligible continuation; do not silently pass')
    return {'complete': False, 'value': None, 'actions': actions,
            'reason': '192-decision horizon cap; unknown, not inferior'}


def interleave_families(items, family):
    groups = {}
    for item in items:
        groups.setdefault(family(item), []).append(item)
    return [group[i] for i in range(max(map(len, groups.values()), default=0))
            for group in groups.values() if i < len(group)]


def search(env, snapshot, memory, publish, *, soft_deadline, hard_deadline, bgg_openings=False,
           shared_factions=False, adaptive=False, allocation=None, delta_factions=(), fixed_openings=False,
           observed_factions=(), faction_tech_plans=False):
    cache = PolicyCache()
    policies = Policies(memory, cache=cache, shared_factions=shared_factions,
                        delta_factions=delta_factions, fixed_openings=fixed_openings,
                        faction_tech_plans=faction_tech_plans)
    check_time(hard_deadline)
    scores = policies.rank(env, snapshot)
    control_first = best_index(scores, range(len(scores)))
    if control_first is None:
        raise ValueError('No eligible root action')
    opening_rows, opening_goals, remembered = (), [], None
    actor_key = str(snapshot.get('player'))
    tech_plans = policies.faction_tech_plans and snapshot['state']['players'][snapshot['player']]['faction'] in ('Terrans', 'Ambas')
    if fixed_openings:
        from bgg_openings.fixed import TARGETS
        if snapshot['state']['players'][snapshot['player']]['faction'] in TARGETS:
            bgg_openings = False
    if bgg_openings and snapshot['state']['round'] <= 1:
        from bgg_openings.catalog import load_catalog
        from bgg_openings.planning import goals as bgg_goals
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        opening_rows = load_catalog().get(faction, ())
        remembered = policies.memory.get('_bgg_targets', {}).get(actor_key)
        if remembered is not None and remembered not in {o.label for o in opening_rows}:
            raise ValueError('Saved BGG target does not belong to the actual faction')
        opening_goals = bgg_goals(snapshot, remembered)
    elif bgg_openings:
        policies.memory.pop('_bgg_targets', None)
    # A complete baseline exists before any long forecast is attempted.
    result = {'decision_id': snapshot['decision_id'], 'index': control_first,
              'scores': scores, 'memory': policies.memory, 'plans': [],
              'selected': 'local-baseline', 'opponents': 'purposeful faction-aware continuation',
              'horizon_incomes': 2, 'coverage_complete': False}
    result['delta_factions'] = list(policies.delta_factions)
    if policies.faction_tech_plans:
        result['faction_tech_plans'] = True
    if fixed_openings:
        result['fixed_opening'] = policies.fixed_audit
    normal_index, normal_selected = control_first, 'local-baseline'
    def publish_current(*, remember_plan=False):
        result.update(index=normal_index, selected=normal_selected)
        if opening_rows:
            from bgg_openings.planning import select_forecast
            selection = select_forecast(opening_rows, remembered, result['plans'])
            if selection is not None:
                plan, opening = selection
                policies.memory.setdefault('_bgg_targets', {})[actor_key] = opening.label
                result.update(index=plan['first'], selected=f'BGG-R1-{opening.label} via {plan["goal"]}')
                result['bgg_opening'] = {'status': 'kept' if opening.label == remembered else
                    'switched' if remembered else 'selected', 'target': opening.label,
                    'previous_target': remembered, 'source': asdict(opening),
                    'forecast_r1_buildings': plan['r1_buildings'], 'observed_completion': False}
            else:
                result['bgg_opening'] = {'status': 'fallback-no-verified-route',
                    'target': remembered, 'observed_completion': False,
                    'note': 'No completed matching forecast yet; unsearched is not impossible'}
        elif bgg_openings:
            result['bgg_opening'] = {'status': 'outside-r1-or-source-scope', 'target': None}
        selected_plan = None
        if remember_plan:
            selected_name = result['selected'].split(' via ', 1)[-1]
            matches = [p for p in result['plans'] if p['complete'] and
                       p['first'] == result['index'] and p['goal'] == selected_name]
            selected_plan = max(matches, key=lambda p: p['value'])
            selected_goal = goal_from_dict(selected_plan['goal_spec'])
            if selected_goal.family not in ('current', 'root'):
                policies.memory.setdefault('_plans', {})[actor_key] = asdict(replace(selected_goal, first=None))
        result['policy_cache'] = cache.stats()
        publish(result)
        return selected_plan

    publish_current()
    if adaptive:
        from faction_teachers.clock import fast_reason
        reason = fast_reason(snapshot, memory, result)
        if reason:
            result['stop_reason'] = reason
            result['coverage_complete'] = sum(not blocked(score) for score in scores) == 1
            publish_current()
            return result
    phase = snapshot['state']['phase']
    search_phases = ('ActionPhase', 'Setup', 'TinkeroidsTileSelectionPending') if shared_factions else ('ActionPhase', 'Setup')
    if not isinstance(phase, dict) or not any(k in phase for k in search_phases):
        result['coverage_complete'] = True
        publish_current()
        return result
    control = Goal('current-choice', first=control_first)
    # A short budget must not spend every goal comparison on Academy locations
    # before ever considering research, a colony or a ship.
    guide_tracks = bool(policies.delta_factions) and (
        snapshot['state']['players'][snapshot['player']]['faction'] in policies.delta_factions)
    observed = bool(observed_factions) and (
        snapshot['state']['players'][snapshot['player']]['faction'] in observed_factions)
    proposals = goals_for(snapshot, shared_factions=shared_factions, guide_tracks=guide_tracks,
                          observed=observed, faction_tech_plans=tech_plans)
    goals = interleave_families(proposals, lambda goal: goal.family)
    saved = policies.memory.get('_plans', {}).get(str(snapshot.get('player')))
    if saved:
        previous = goal_from_dict(saved)
        enabled_plan = tech_plans or 'faction-tech-pilot' not in previous.sources
        if enabled_plan and viable(snapshot, snapshot['player'], previous) and not achieved(snapshot, snapshot['player'], previous):
            goals.insert(0, previous)
        else:
            del policies.memory['_plans'][str(snapshot['player'])]
    paired = scoring_pairs(snapshot, scores, goals, nested=tech_plans)
    roots = [Goal(f'root-{i}', 'root', first=i)
             for i in sorted(range(len(scores)), key=lambda i: (-scores[i][0], i))
             if not blocked(scores[i]) and i != control_first]
    # Round-robin action families avoids consuming the whole budget on the many
    # technology variants of one upgrade. No root is declared illegal by pruning.
    interleaved = interleave_families(roots, lambda goal: snapshot['candidates'][goal.first]['action']['type'])
    tasks = [] if opening_goals else [control]
    # Interleave explicit preparation routes and ordinary root alternatives.
    for i in range(max(len(goals), len(interleaved), len(paired), len(opening_goals))):
        if i < len(opening_goals):
            tasks.append(opening_goals[i])
        if i == 0 and opening_goals:
            tasks.append(control)
        if i < len(goals):
            tasks.append(goals[i])
        if i < len(interleaved):
            tasks.append(interleaved[i])
        if i < len(paired):
            tasks.append(paired[i])
    if tech_plans:
        from faction_teachers.guidance import comparison_variants
        tasks = [variant for goal in tasks for variant in comparison_variants(goal)]
        from faction_teachers.progressive import progressive_search
        def publish_depth(rows, depth):
            nonlocal normal_index, normal_selected
            winner = max((row for row in rows if row['complete'] and row['family'] != 'bgg-opening'),
                         key=lambda row: row['value'])
            normal_index, normal_selected = winner['first'], winner['goal']
            result.update(plans=rows, comparison_depth=depth)
            return publish_current(remember_plan=True)
        return progressive_search(env, snapshot, scores, tasks, control, policies, result,
                                  publish_depth, publish_current, soft_deadline=soft_deadline,
                                  hard_deadline=hard_deadline, allocation=allocation,
                                  capture_r1=bool(opening_rows))
    best_value = None
    result['extended_reason'] = None
    result['extension_policy'] = 'finish-current-comparison-only'
    result['planned_comparisons'] = len(tasks)
    history = []
    try:
        for goal in tasks:
            allocated = min(hard_deadline, allocation()) if allocation is not None else soft_deadline
            if time.monotonic() >= allocated:
                result['stop_reason'] = 'soft time allocation used'
                break
            check_time(hard_deadline)
            first = goal.first if goal.first is not None else select_goal(env, snapshot, scores, goal, policies, hard_deadline)
            if first is None:
                comparison = {'complete': False, 'value': None, 'actions': [],
                              'remaining_goal': asdict(goal),
                              'reason': 'no policy-eligible preserving first action; unknown, not inferior'}
            else:
                comparison = (rollout(env, snapshot, first, goal, policies, hard_deadline, capture_r1=True)
                              if opening_rows else rollout(env, snapshot, first, goal, policies, hard_deadline))
            if time.monotonic() >= soft_deadline:
                result['extended_reason'] = 'finish comparison started before soft deadline'
            result['plans'].append({'goal': goal.name, 'goal_spec': asdict(goal),
                                     'family': goal.family, 'first': first, **comparison})
            if goal == control:
                if not comparison['complete']:
                    break  # Preserve baseline; do not compare unmatched horizons.
                best_value = comparison['value']
                normal_index, normal_selected = first, goal.name
            elif (goal.family != 'bgg-opening' and comparison['complete']
                  and best_value is not None and comparison['value'] > best_value):
                best_value = comparison['value']
                normal_index, normal_selected = first, goal.name
                if goal.family not in ('current', 'root'):
                    policies.memory.setdefault('_plans', {})[str(snapshot['player'])] = asdict(replace(goal, first=None))
            publish_current()
            if adaptive:
                from faction_teachers.clock import converged
                history.append(result['index'])
                if converged(snapshot, result, history):
                    result['stop_reason'] = 'stable completed alternatives; no artificial wait'
                    break
        else:
            result['coverage_complete'] = all(plan['complete'] for plan in result['plans'])
    except SearchExpired:
        result['stop_reason'] = 'deadline; partially evaluated route remains unknown'
        result['extended_reason'] = 'in-progress comparison reached hard deadline'
    result['unsearched_comparisons'] = len(tasks)-len(result['plans'])
    publish_current()
    return result
