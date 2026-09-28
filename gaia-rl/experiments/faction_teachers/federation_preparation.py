"""Native-paid power building for an unfinished Ambas preservation comparison."""
import json

from current_actions.conservation import blocked
from economy.teacher import BUILD_TYPES
from federation.teacher import minimum, power
from strategy_teacher import distance

BUILDING_ACTIONS = BUILD_TYPES | {
    'RoundBoosterTerraformBuild', 'Upgrade',
    'RebellionFreeTradingStation', 'TwilightFreeResearchLab',
}
FUNDING_ACTIONS = {'FreeAction', 'PowerAction', 'AcademyQicAction', 'TechTileSpecialAction'}


def unfederated_power(player):
    used = set(player['federated_hexes'])
    return sum(power(player, site['kind']) for site in player['structures'] if site['hex'] not in used)


def new_federation_site(player, coord):
    # Ambas forms separate federations, unlike Ivits. Native Graph::new and
    # validate_form_federation exclude old federation nodes AND their neighbors.
    return coord not in player['federated_hexes'] and all(
        distance(coord, old) != 1 for old in player['federated_hexes'])


def preparation_power(player):
    return sum(power(player, site['kind']) for site in player['structures']
               if new_federation_site(player, site['hex']))


def needs_power(snapshot):
    player = snapshot['state']['players'][snapshot['player']]
    return (player['faction'] == 'Ambas' and 'ActionPhase' in snapshot['state']['phase']
            and preparation_power(player) < minimum(player))


def building_action(action):
    return action['type'] in BUILDING_ACTIONS or (
        action['type'] == 'PowerAction' and action.get('coord') is not None)


def construction_index(env, snapshot, scores, goal, deadline):
    from four_factions.preparation import check_time, viable
    actor = snapshot['player']
    before = preparation_power(snapshot['state']['players'][actor])
    eligible = sorted((i for i, score in enumerate(scores) if not blocked(score)),
                      key=lambda i: (-scores[i][0], i))
    for index in eligible:
        action = snapshot['candidates'][index]['action']
        if not building_action(action):
            continue
        check_time(deadline)
        # Preview pays the real costs and includes automatic federation absorption,
        # covered technology and ancillary effects; a printed building value is not proof.
        after = json.loads(env.preview_state_json(snapshot['decision_id'], index))
        check_time(deadline)
        if (preparation_power(after['players'][actor]) > before
                and viable({**snapshot, 'state': after}, actor, goal)):
            return index
    return None


def select_preparation(env, snapshot, scores, goal, policies, deadline):
    """Return a proved first action, not a score bonus or a completed federation."""
    from four_factions.preparation import check_time
    actor = snapshot['player']
    if not needs_power(snapshot):
        return None
    ready = construction_index(env, snapshot, scores, goal, deadline)
    if ready is not None:
        return ready
    eligible = sorted((i for i, score in enumerate(scores) if not blocked(score)),
                      key=lambda i: (-scores[i][0], i))
    examined = 0
    for index in eligible:
        action = snapshot['candidates'][index]['action']
        if action['type'] not in FUNDING_ACTIONS or building_action(action):
            continue
        if examined >= 32:
            break
        check_time(deadline)
        examined += 1
        branch = env.fork(snapshot['decision_id'], index)
        after = json.loads(branch.snapshot_json())
        check_time(deadline)
        if after['player'] != actor or 'ActionPhase' not in after['state']['phase']:
            continue  # Do not impersonate the actor or skip opponents to prove affordability.
        follow = policies.clone().rank(branch, after)
        if construction_index(branch, after, follow, goal, deadline) is not None:
            return index
    return None
