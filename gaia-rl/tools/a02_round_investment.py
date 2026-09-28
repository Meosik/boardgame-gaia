"""Default-off frozen-A search experiment; all values and native rules stay unchanged."""
from copy import deepcopy
from dataclasses import dataclass
import heapq
import json
import math
import os
import time

from current_actions.conservation import blocked
from four_factions import preparation as prep
from four_factions.preparation_cache import PolicyCache
from research_plans.teacher import best_index


FLAG = 'GAIA_A02_ROUND_INVESTMENT'
TRANSITION_LIMIT = 192  # Inherited native-transition safety bound, not an investment quota.
FACTIONS = ('Terrans', 'Taklons')


class Incomplete(Exception):
    """A legal continuation was not established within the inherited search boundary."""


@dataclass
class Node:
    env: object
    snapshot: dict
    policies: object
    actions: list
    investments: list
    first: int | None


def action_phase(snapshot):
    phase = snapshot['state']['phase']
    return isinstance(phase, dict) and 'ActionPhase' in phase


def endpoint(snapshot, round_number):
    phase = snapshot['state']['phase']
    ended = isinstance(phase, dict) and 'Ended' in phase
    return ended or (snapshot['state']['round'] == round_number + 1 and action_phase(snapshot))


def _check(deadline):
    if time.monotonic() >= deadline():
        raise prep.SearchExpired('A02 inherited time allocation used')


def _step(node, index, deadline):
    _check(deadline)
    if len(node.actions) >= TRANSITION_LIMIT:
        raise Incomplete('native transition limit; uncompleted route remains unknown')
    before = node.snapshot
    action = before['candidates'][index]['action']
    branch = node.env.fork(before['decision_id'], index)
    snapshot = json.loads(branch.snapshot_json())
    _check(deadline)
    return Node(branch, snapshot, node.policies.clone(),
                node.actions + [dict(actor=before['player'], round=before['state']['round'],
                                     action=action)],
                list(node.investments), index if node.first is None else node.first)


def _advance(node, actor, round_number, deadline, *, until_own_turn):
    while not endpoint(node.snapshot, round_number):
        if node.snapshot['state']['round'] > round_number + 1:
            raise Incomplete('next-round action boundary was not observed')
        if (until_own_turn and node.snapshot['player'] == actor and
                node.snapshot['state']['round'] == round_number and action_phase(node.snapshot)):
            return node
        _check(deadline)
        scores = node.policies.rank(node.env, node.snapshot)
        _check(deadline)
        index = best_index(scores, range(len(scores)))
        if index is None:
            raise Incomplete('no policy-eligible native continuation')
        node = _step(node, index, deadline)
    return node


def _complete(node, scores, actor, round_number, deadline):
    # Each prefix can stop investing; it never has to consume all resources.
    index = best_index(scores, [i for i, candidate in enumerate(node.snapshot['candidates'])
                               if candidate['action']['type'] == 'Pass'])
    if index is None:
        raise Incomplete('no eligible native pass from this investment prefix')
    branch = _step(node, index, deadline)
    return _advance(branch, actor, round_number, deadline, until_own_turn=False)


def _outcome(node, actor):
    from four_factions.value import production
    player = node.snapshot['state']['players'][actor]
    candidates = node.snapshot['candidates'] if node.snapshot['player'] == actor else []
    return dict(resources=deepcopy(player['resources']),
                income=production(node.snapshot['state'], player, include_booster=False),
                structures=deepcopy(player['structures']),
                research_tracks=deepcopy(player['research_tracks']),
                next_actor=node.snapshot['player'],
                next_legal_builds=(sum(c['action']['type'] == 'Build' for c in candidates)
                                   if node.snapshot['player'] == actor else None),
                next_legal_upgrades=(sum(c['action']['type'] == 'Upgrade' for c in candidates)
                                     if node.snapshot['player'] == actor else None),
                next_legal_research=(sum(c['action']['type'] == 'ResearchAdvance' for c in candidates)
                                     if node.snapshot['player'] == actor else None))


def search_round(env, snapshot, policies, scores, publish, *, soft_deadline,
                 hard_deadline, allocation=None, bgg_openings=False):
    actor = snapshot['player']
    round_number = snapshot['state']['round']
    control = best_index(scores, range(len(scores)))
    root = Node(env, snapshot, policies, [], [], None)
    root_memory = deepcopy(policies.memory)
    root_player = snapshot['state']['players'][actor]
    result = dict(decision_id=snapshot['decision_id'], index=control, scores=scores,
                  memory=deepcopy(root_memory), plans=[], selected='local-baseline',
                  horizon_incomes=1, comparison_depth='next-round-action',
                  coverage_complete=False, planned_comparisons=0, unsearched_comparisons=0,
                  a02=True, expanded_prefixes=0, maximum_investments_completed=0,
                  incomplete_paths=[], opponents='unchanged A shallow continuation',
                  stop_reason='comparison not completed')
    opening_rows = ()
    remembered = root_memory.get('_bgg_targets', {}).get(str(actor))
    if bgg_openings and round_number == 1:
        from bgg_openings.catalog import load_catalog
        opening_rows = load_catalog().get(root_player['faction'], ())
        if remembered is not None and remembered not in {o.label for o in opening_rows}:
            raise ValueError('Saved BGG target does not belong to actual faction')
    elif bgg_openings:
        result['memory'].pop('_bgg_targets', None)

    def deadline():
        return min(hard_deadline, allocation() if allocation is not None else soft_deadline)

    def emit():
        _check(deadline)
        publish(deepcopy(result))

    def accept(node):
        if not endpoint(node.snapshot, round_number):
            raise AssertionError('A02 cannot score an unmatched endpoint')
        value = prep.leaf_value(node.snapshot, actor, root_player)
        if not math.isfinite(value):
            raise ValueError('Nonfinite unchanged leaf value')
        _check(deadline)
        row = dict(goal=f'a02-route-{len(result["plans"])}', family='a02-round',
                   first=node.first, complete=True, value=value,
                   comparison_depth='next-round-action', actions=node.actions,
                   investments=node.investments, end_round=node.snapshot['state']['round'],
                   end_phase=node.snapshot['state']['phase'], outcome=_outcome(node, actor))
        if opening_rows:
            from dataclasses import asdict
            from bgg_openings.inventory import building_counts
            row['r1_buildings'] = asdict(building_counts(node.snapshot['state']['players'][actor]))
        result['plans'].append(row)
        result['stop_reason'] = 'search running; incomplete frontier remains unknown'
        result['maximum_investments_completed'] = max(
            result['maximum_investments_completed'], len(node.investments))
        # The first complete row is always the immediate-pass control.
        winner = max(result['plans'], key=lambda p: p['value'])
        selected = winner['goal']
        if opening_rows:
            from bgg_openings.planning import select_forecast
            opening = select_forecast(opening_rows, remembered, result['plans'])
            if opening is not None:
                winner, target = opening
                result['memory'].setdefault('_bgg_targets', {})[str(actor)] = target.label
                selected = f'BGG-R1-{target.label} via {winner["goal"]}'
                result['bgg_opening'] = dict(status='kept' if target.label == remembered else
                                            'switched' if remembered else 'selected', target=target.label)
            else:
                result['bgg_opening'] = dict(status='fallback-no-verified-route', target=remembered)
        result.update(index=winner['first'], selected=selected)
        emit()

    queue = []
    serial = 0

    def enqueue(node, local_scores):
        nonlocal serial
        _check(deadline)
        base = prep.leaf_value(node.snapshot, actor, root_player)
        for i, candidate in enumerate(node.snapshot['candidates']):
            if candidate['action']['type'] not in ('Build', 'Upgrade') or blocked(local_scores[i]):
                continue
            # Local values order work only; no prefix is selected on this heuristic.
            priority = base + local_scores[i][0]
            if not math.isfinite(priority):
                raise ValueError('Nonfinite investment ordering value')
            heapq.heappush(queue, (-priority, serial, node, i))
            serial += 1
        result['planned_comparisons'] = 1 + serial
        result['unsearched_comparisons'] = len(queue)

    emit()
    try:
        baseline = _complete(root, scores, actor, round_number, deadline)
        accept(baseline)
        enqueue(root, scores)
        while queue:
            _check(deadline)
            _, _, node, index = heapq.heappop(queue)
            result['unsearched_comparisons'] = len(queue)
            action = node.snapshot['candidates'][index]['action']
            try:
                child = _step(node, index, deadline)
                child.investments.append(action)
                child = _advance(child, actor, round_number, deadline, until_own_turn=True)
                if endpoint(child.snapshot, round_number):
                    accept(child)
                    continue
                child_scores = child.policies.rank(child.env, child.snapshot)
                _check(deadline)
                result['expanded_prefixes'] += 1
                # Keep longer investments available even if this prefix has no pass.
                enqueue(child, child_scores)
                accept(_complete(child, child_scores, actor, round_number, deadline))
            except Incomplete as error:
                result['incomplete_paths'].append(dict(investments=node.investments + [action],
                                                      reason=str(error), value=None))
        result['coverage_complete'] = not result['incomplete_paths']
        result['stop_reason'] = 'investment frontier exhausted'
    except Incomplete as error:
        result['stop_reason'] = str(error)
        result['incomplete_paths'].append(dict(investments=[], reason=str(error), value=None))
    except prep.SearchExpired:
        # The timed parent already owns the last published eligible choice.
        result['stop_reason'] = 'deadline; unfinished routes remain unknown'
        result['coverage_complete'] = False
    result['unsearched_comparisons'] = len(queue)
    if time.monotonic() < deadline():
        emit()
    return result


def dispatch(original, env, snapshot, memory, publish, **kwargs):
    if (os.environ.get(FLAG, '0') != '1' or not action_phase(snapshot) or
            snapshot['state']['players'][snapshot['player']]['faction'] not in FACTIONS or
            kwargs.get('fixed_openings') or kwargs.get('delta_factions') or
            kwargs.get('observed_factions')):
        return original(env, snapshot, memory, publish, **kwargs)
    policies = prep.Policies(memory, cache=PolicyCache(),
                             shared_factions=kwargs.get('shared_factions', False))
    prep.check_time(kwargs['hard_deadline'])
    scores = policies.rank(env, snapshot)
    prep.check_time(kwargs['hard_deadline'])
    control = best_index(scores, range(len(scores)))
    if control is None or snapshot['candidates'][control]['action']['type'] != 'Pass':
        return original(env, snapshot, memory, publish, **kwargs)
    return search_round(env, snapshot, policies, scores, publish,
                        soft_deadline=kwargs['soft_deadline'], hard_deadline=kwargs['hard_deadline'],
                        allocation=kwargs.get('allocation'), bgg_openings=kwargs.get('bgg_openings', False))
