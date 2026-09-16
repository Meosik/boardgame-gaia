"""Native-preview Terrans/Taklons plus unchanged Xenos/Hadsch planning policies."""
import json
import math

from conditional_plans.economy_first import EconomyFirstTeacher
from current_actions.conservation import BLOCKED, PREFIX, FORBIDDEN, blocked, identity
from four_factions import FACTIONS
from four_factions.audit import capture_decision
from four_factions.value import HOME, placement, potential

FUNDING_PREVIEWS = 24


def brainstone_committed(before, after, actor):
    return (before['state']['players'][actor]['resources']['power']['brainstone'] != 'Gaia'
            and after['state']['players'][actor]['resources']['power']['brainstone'] == 'Gaia')


def critical_proofs(env, snapshot, index, branch, after):
    """Same minimum QIC->ore exceptions as the current teacher, using real factions."""
    actor = snapshot['player']
    before = snapshot['state']['players'][actor]
    count = snapshot['candidates'][index]['action'].get('count', 1)
    if after['player'] != actor:
        return {}
    new = after['state']['players'][actor]['resources']
    if new['ore']-before['resources']['ore'] != count or before['resources']['qic']-new['qic'] != count:
        return {}
    existing = {identity(c['action']) for c in snapshot['candidates']}
    targets, paths = set(), {}
    for candidate in after['candidates']:
        action = candidate['action']
        if action['type'] != 'Upgrade' or identity(action) in existing:
            continue
        target = action.get('to')
        cost = 4 if target == 'PlanetaryInstitute' else 6 if isinstance(target, dict) and 'Academy' in target else None
        # These two standard costs apply to both new factions; native legality
        # verifies the full paid action, technology choice and remaining credits.
        if cost is not None and cost-before['resources']['ore'] == count:
            targets.add(identity(action))
    if not any(c['action']['type'] == 'FormFederation' for c in snapshot['candidates']):
        for j, candidate in enumerate(after['candidates']):
            action = candidate['action']
            if (action['type'] != 'FreeAction' or action.get('kind') != 'OreToPowerBowl3'
                    or action.get('count', 1) != count or before['resources']['ore'] != 0):
                continue
            last = json.loads(branch.fork(after['decision_id'], j).snapshot_json())
            if last['player'] != actor or brainstone_committed(after, last, actor):
                continue
            federations = {identity(c['action']) for c in last['candidates'] if c['action']['type'] == 'FormFederation'}
            if federations:
                targets.add(identity(action))
                paths[identity(last)] = federations
    if targets:
        paths[identity(after)] = targets
    return paths


class NativeFactionTeacher:
    """All root actions get native previews; funding has an explicit bounded sample."""
    def __init__(self, *, profile=None, state_delta=False):
        self.profile = profile
        self.state_delta = state_delta
        self.env = None
        self.commitments = {}
        self.last_scores = []
        self.last_audit = {}

    def value(self, state, actor, *, guide_tracks=False):
        return potential(state, actor, home=self.profile.home if self.profile else None,
                         guide_tracks=guide_tracks)

    def bind(self, env):
        self.env = env
        return self

    def rank(self, snapshot):
        actor = snapshot['player']
        if actor is None or not snapshot['candidates']:
            raise ValueError('No live decision')
        player = snapshot['state']['players'][actor]
        if ((self.profile is None and player['faction'] not in HOME)
                or (self.profile is not None and player['faction'] != self.profile.faction)):
            raise ValueError('Native faction teacher supports only Terrans/Taklons')
        if self.env is None:
            raise ValueError('Bind the current native environment before ranking')
        if json.loads(self.env.snapshot_json()) != snapshot:
            raise ValueError('Teacher snapshot differs from the bound environment')
        if self.state_delta and player['faction'] not in HOME:
            raise ValueError('Native state-delta ablation is limited to Terrans/Taklons')
        delta_only = self.state_delta and 'Setup' not in snapshot['state']['phase']
        required = self.commitments.get(identity(snapshot))
        if not required:
            self.commitments = {}
        base = self.value(snapshot['state'], actor, guide_tracks=delta_only)
        scores, previews = [], {}
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            forbidden = action['type'] == 'FreeAction' and action['kind'] in FORBIDDEN
            if forbidden or (required and identity(action) not in required):
                scores.append((BLOCKED, PREFIX+'preserve resource/verified-follow-up constraint'))
                continue
            qic_conversion = action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'
            if delta_only and not qic_conversion:
                branch = None
                after = {'state': json.loads(self.env.preview_state_json(snapshot['decision_id'], i))}
            else:
                branch = self.env.fork(snapshot['decision_id'], i)
                after = json.loads(branch.snapshot_json())
            if brainstone_committed(snapshot, after, actor):
                scores.append((BLOCKED, PREFIX+'standing policy: no Brainstone Gaia commitment'))
                continue
            if qic_conversion:
                proofs = critical_proofs(self.env, snapshot, i, branch, after)
                if not proofs:
                    scores.append((BLOCKED, PREFIX+'no minimum-cost paid critical completion'))
                    continue
                for state, targets in proofs.items():
                    self.commitments.setdefault(state, set()).update(targets)
            value = self.value(after['state'], actor, guide_tracks=delta_only)-base
            if delta_only:
                scores.append((value, 'state-delta: same B19-guided endpoint; no action bonus or funding mix'))
                continue
            if action['type'] == 'PlaceStartingStructure':
                value += placement(snapshot['state'], player, action['coord'],
                                   home=self.profile.home if self.profile else None)
            if action['type'] == 'FreeAction':
                value -= .25*action.get('count', 1)
            scores.append((value, 'native faction preview: paid state delta + explicit soft opportunity terms'))
            previews[i] = (branch, after)

        # Unlike a full strategic search this samples one extra own action after
        # conversions. Unsearched continuations keep their actual one-step value.
        existing = {identity(c['action']) for c in snapshot['candidates']}
        budget = FUNDING_PREVIEWS
        for i in sorted(previews, key=lambda j: (-scores[j][0], j)):
            action = snapshot['candidates'][i]['action']
            branch, after = previews[i]
            if action['type'] != 'FreeAction' or after['player'] != actor or not budget:
                continue
            followups = self.commitments.get(identity(after))
            for j, candidate in enumerate(after['candidates']):
                target = candidate['action']
                if (target['type'] in ('FreeAction', 'Pass') or identity(target) in existing
                        or (followups and identity(target) not in followups)):
                    continue
                last = json.loads(branch.fork(after['decision_id'], j).snapshot_json())
                budget -= 1
                if not brainstone_committed(after, last, actor):
                    value = self.value(last['state'], actor)-base-.25*action.get('count', 1)
                    if value > scores[i][0]:
                        scores[i] = (value, f'native funded follow-up sample: {identity(target)}; not a full search')
                if not budget:
                    break
        if not any(not blocked(score) for score in scores):
            raise ValueError('No policy-eligible native action; never auto-pass')
        if not all(math.isfinite(score) for score, _ in scores):
            raise ValueError('Nonfinite teacher score')
        self.last_scores = scores
        self.last_audit = {'faction': player['faction'], 'decision_id': snapshot['decision_id'],
                           'native_root_previews': sum(not blocked(score) for score in scores),
                           'funding_previews': FUNDING_PREVIEWS-budget,
                           'funding_limit': FUNDING_PREVIEWS,
                           'forecast': ('one native action; pure endpoint delta' if delta_only else
                                        'one native action, bounded one-own-action funding extension')}
        return scores


class QuartetTeacher:
    """Separate per-seat mutable planners; old factions retain their exact policy."""
    def __init__(self):
        self.env = None
        self.policies = {}
        self.last_scores = []
        self.last_audit = None

    def bind(self, env):
        if env is not self.env:
            self.policies = {}
            self.last_audit = None
        self.env = env
        return self

    def rank(self, snapshot):
        actor = snapshot['player']
        if actor is None or not snapshot['candidates'] or self.env is None:
            raise ValueError('A current bound native decision is required')
        faction = snapshot['state']['players'][actor]['faction']
        if faction not in FACTIONS:
            raise ValueError('Outside the approved quartet')
        if actor not in self.policies:
            policy = EconomyFirstTeacher() if faction in FACTIONS[:2] else NativeFactionTeacher()
            self.policies[actor] = policy.bind(self.env)
        policy = self.policies[actor]
        history = getattr(policy, 'plan_history', [])
        start = len(history)
        self.last_audit = None
        self.last_scores = policy.rank(snapshot)
        self.last_audit = capture_decision(snapshot, self.last_scores, history[start:],
                                          getattr(policy, 'last_audit', None))
        return self.last_scores

    def choose(self, snapshot):
        scores = self.rank(snapshot)
        index = max((i for i, score in enumerate(scores) if not blocked(score)),
                    key=lambda i: (scores[i][0], -i))
        return snapshot['decision_id'], index
