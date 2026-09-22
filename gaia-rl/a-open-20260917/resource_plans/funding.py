"""Bounded legal free-action paths plus actual resource-action alternatives."""
from collections import deque
import json

from current_actions.teacher import CurrentContextTeacher
from research_plans.teacher import best_index
from research_plans.value import endpoint_value
from current_actions.conservation import FORBIDDEN, blocked, critical_paths, identity

MAX_FUNDING_NODES = 32
FREE_OUTPUT = {'PowerToOre': 'ore', 'QicToOre': 'ore', 'CreditsToOre': 'ore',
               'PowerToCredit': 'credits', 'OreToCredit': 'credits',
               'KnowledgeToCredit': 'credits', 'PowerToKnowledge': 'knowledge',
               'CreditsToKnowledge': 'knowledge', 'PowerToQic': 'qic', 'CreditsToQic': 'qic'}


def funding_indices(snapshot, need):
    resources = snapshot['state']['players'][snapshot['player']]['resources']
    missing = {k: n-resources[k] for k, n in need.items() if n > resources[k]}
    for i, candidate in enumerate(snapshot['candidates']):
        action = candidate['action']
        if action['type'] != 'FreeAction':
            continue
        if action['kind'] in FORBIDDEN:
            continue
        output = FREE_OUTPUT.get(action['kind'])
        if output in missing and action.get('count', 1) <= missing[output]:
            yield i
        elif action['kind'] == 'BurnPower' and missing:
            yield i


def path_value(before, after, actor):
    """Only orders sampled funding paths; final selection uses the full forecast."""
    return endpoint_value(after, actor, before['players'][actor], CurrentContextTeacher())


def funded_paths(env, snapshot, predicate, need, *, max_nodes=MAX_FUNDING_NODES, audit=None):
    """Prove a goal is legal after <=2 free actions; never skip opposing turns."""
    actor = snapshot['player']
    queue = deque([(env, snapshot, (), {})])
    paths, examined = [], 0
    seen = set()
    while queue and examined < max_nodes:
        branch, current, path, commitments = queue.popleft()
        required = commitments.get(identity(current)) if commitments else None
        for i in funding_indices(current, need):
            if examined >= max_nodes:
                break
            action = current['candidates'][i]['action']
            if required and identity(action) not in required:
                continue
            examined += 1
            proofs = commitments
            if action['kind'] == 'QicToOre':
                proofs = critical_paths(branch, current, i)
                if not proofs:
                    continue
            fork = branch.fork(current['decision_id'], i)
            after = json.loads(fork.snapshot_json())
            if after['player'] != actor:
                continue
            signature = (json.dumps(after['state']['players'][actor], sort_keys=True), bool(proofs))
            if signature in seen:
                continue
            seen.add(signature)
            sequence = path+(i,)
            matches = [j for j, c in enumerate(after['candidates']) if predicate(c['action'])]
            required_after = proofs.get(identity(after)) if proofs else None
            if required_after:
                matches = [j for j in matches if identity(after['candidates'][j]['action']) in required_after]
            if matches:
                ranks = CurrentContextTeacher().rank(after)
                target = best_index(ranks, matches)
                paths.append({'first': sequence[0], 'depth': len(sequence),
                    'value': path_value(snapshot['state'], after['state'], actor),
                    'target': after['candidates'][target]['action']})
            elif len(sequence) < 2:
                queue.append((fork, after, sequence, proofs))
    if audit is not None:
        audit.append({'decision_id': snapshot['decision_id'], 'examined': examined,
                      'node_limit_reached': examined >= max_nodes, 'verified_paths': len(paths),
                      'max_free_actions': 2})
    return sorted(paths, key=lambda p: (-p['value'], p['depth'], p['first'])), examined


def resource_actions(env, snapshot, scores, need):
    """Actual gains, not guessed resource-action IDs or faction conversion powers."""
    actor = snapshot['player']
    before = snapshot['state']['players'][actor]['resources']
    missing = {k: n-before[k] for k, n in need.items() if n > before[k]}
    options = []
    for i, candidate in enumerate(snapshot['candidates']):
        if blocked(scores[i]):
            continue
        action = candidate['action']
        if not missing or action['type'] not in ('PowerAction', 'AcademyQicAction',
                'TechTileSpecialAction') or action.get('coord') is not None:
            continue
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())['state']
        resources = after['players'][actor]['resources']
        if any(resources[k] > before[k] for k in missing):
            options.append((path_value(snapshot['state'], after, actor), scores[i][0], -i, i))
    return max(options)[-1] if options else None
