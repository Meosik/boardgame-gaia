"""Teacher-only conservation constraints. Native/human action legality is unchanged."""
import json

from action_purpose.costs import construction_cost

BLOCKED = -1e12  # Finite: ranks are persisted in JSON and validated by the evaluator.
PREFIX = 'conservation blocked: '
FORBIDDEN = {'OreToCredit', 'KnowledgeToCredit'}


def blocked(score):
    return score[1].startswith(PREFIX)


def identity(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def critical(action):
    return action['type'] == 'FormFederation' or (action['type'] == 'Upgrade' and
        (action.get('to') == 'PlanetaryInstitute' or isinstance(action.get('to'), dict)
         and 'Academy' in action['to']))


def critical_paths(env, snapshot, index):
    """Prove minimum QIC spending and a paid critical follow-up, not a future wish.

    The only extra free-action link is ore->power for an immediately legal
    federation. Never reserve a building across hypothetical opposing turns.
    """
    if env is None:
        return {}
    action = snapshot['candidates'][index]['action']
    count = action.get('count', 1)
    actor = snapshot['player']
    before = snapshot['state']['players'][actor]
    branch = env.fork(snapshot['decision_id'], index)
    after = json.loads(branch.snapshot_json())
    if after['player'] != actor:
        return {}
    resources = after['state']['players'][actor]['resources']
    if (resources['ore'] - before['resources']['ore'] != count or
            before['resources']['qic'] - resources['qic'] != count):
        return {}
    already = {identity(c['action']) for c in snapshot['candidates']}
    paths = {}
    targets = set()
    for candidate in after['candidates']:
        target = candidate['action']
        if not critical(target) or identity(target) in already:
            continue
        cost = construction_cost(snapshot['state'], before, target)
        if cost and cost.ore - before['resources']['ore'] == count:
            targets.add(identity(target))
    # Only missing token funding for a genuinely new federation, no stockpiling.
    has_federation = any(c['action']['type'] == 'FormFederation' for c in snapshot['candidates'])
    if not has_federation:
        for j, candidate in enumerate(after['candidates']):
            token = candidate['action']
            if (token['type'] != 'FreeAction' or token.get('kind') != 'OreToPowerBowl3'
                    or token.get('count', 1) != count or before['resources']['ore'] != 0):
                continue
            last = json.loads(branch.fork(after['decision_id'], j).snapshot_json())
            if last['player'] != actor:
                continue
            federations = {identity(c['action']) for c in last['candidates']
                           if c['action']['type'] == 'FormFederation'}
            if federations:
                targets.add(identity(token))
                paths[identity(last)] = federations
    if targets:
        paths[identity(after)] = targets
    return paths


class Conservation:
    """At most one decision's candidate proofs; no persistent/replay cache."""
    def __init__(self):
        self.continuations = {}

    def protect(self, env, snapshot, scores):
        phase = snapshot['state']['phase']
        if not isinstance(phase, dict) or 'ActionPhase' not in phase:
            return scores
        # A chosen free conversion keeps the turn. Honor its verified purpose;
        # hypothetical proofs for unchosen candidates cannot match another state.
        required = self.continuations.get(identity(snapshot)) if self.continuations else None
        if required:
            return [score if identity(c['action']) in required else
                    (BLOCKED, PREFIX+'complete the verified QIC conversion follow-up')
                    for c, score in zip(snapshot['candidates'], scores)]
        self.continuations = {}
        result = list(scores)
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            if action['type'] != 'FreeAction':
                continue
            if action['kind'] in FORBIDDEN:
                result[i] = (BLOCKED, PREFIX+'ore/knowledge cannot be liquidated to credits')
            elif action['kind'] == 'QicToOre':
                paths = critical_paths(env, snapshot, i)
                if not paths:
                    result[i] = (BLOCKED, PREFIX+'no minimum-cost native PI/Academy/federation completion')
                else:
                    for state, targets in paths.items():
                        self.continuations.setdefault(state, set()).update(targets)
                    value, reason = result[i]
                    suffix = '; conservation: verified critical follow-up required'
                    result[i] = (value, reason if reason.endswith(suffix) else reason+suffix)
        return result


class Conserving:
    def apply_conservation(self, snapshot, scores):
        if not hasattr(self, '_conservation'):
            self._conservation = Conservation()
        return self._conservation.protect(getattr(self, 'env', None), snapshot, scores)
