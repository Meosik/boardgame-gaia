"""Small native one-step reserve for adaptive timeouts, not a deep forecast."""
import state_evaluation_bridge as state_bridge
from copy import deepcopy
import json
import math
import os
import time

from current_actions.conservation import BLOCKED, PREFIX, FORBIDDEN, identity
from four_factions.teacher import brainstone_committed
from four_factions.value import placement
from state_evaluation_bridge import potential


def fallback(env, snapshot, memory, *, deadline, fixed_openings=False):
    from faction_teachers.profiles import profiles
    from four_factions.preparation import interleave_families

    actor = snapshot['player']
    player = snapshot['state']['players'][actor]
    home = profiles()[player['faction']].home
    required = memory.get(str(actor), {}).get(identity(snapshot))
    base = potential(snapshot['state'], actor, home=home)
    candidates = snapshot['candidates']
    federation_five = os.environ.get('GAIA_FEDERATION_TOP_FIVE') == '1'
    scores = [(BLOCKED, 'quick fallback: not evaluated; value unknown') for _ in candidates]
    eligible, skipped, evaluated = [], [], []
    for i, candidate in enumerate(candidates):
        action = candidate['action']
        reason = None
        if action['type'] == 'FreeAction' and action['kind'] in FORBIDDEN:
            reason = 'ore/knowledge cannot be liquidated to credits'
        elif required and identity(action) not in required:
            reason = 'preserve verified follow-up constraint'
        elif (action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'
              and not state_bridge.conservation_off()):
            # No deep funding proof fits in this reserve. The normal teacher
            # still considers the existing minimum-cost critical exceptions.
            reason = 'quick fallback has no verified critical QIC funding proof'
        if reason:
            scores[i] = (BLOCKED, PREFIX+reason)
            skipped.append(i)
        else:
            eligible.append(i)
    # Sample different native action families rather than hundreds of variants
    # of one federation. No scripted pass, hand-authored action or extra turn.
    ordered = interleave_families(eligible, lambda i: candidates[i]['action']['type'])
    if state_bridge.active():
        # Price the pending booster and at least one paid continuation before
        # considering irreversible resource liquidation in a bounded reserve.
        priority = {'Pass': 0, 'Build': 1, 'Upgrade': 2, 'GaiaFormation': 3,
                    'ResearchAdvance': 4, 'PowerAction': 5, 'FreeAction': 9}
        ordered.sort(key=lambda i: (priority.get(candidates[i]['action']['type'], 6), i))
    if fixed_openings:
        # A tiny reserve must see a payable core upgrade before spending its
        # entire slice evaluating conversions. Do not alter historical controls.
        ordered.sort(key=lambda i: (candidates[i]['action']['type'] != 'Upgrade',
                                   candidates[i]['action'].get('kind') == 'BurnPower'))
    if federation_five:
        ordered.sort(key=lambda i: (candidates[i]['action']['type'] != 'FormFederation', i))
    mandatory = {i for i in ordered if federation_five and candidates[i]['action']['type'] == 'FormFederation'}
    for i in ordered:
        if evaluated and time.monotonic() >= deadline and not mandatory:
            break
        action = candidates[i]['action']
        mandatory.discard(i)
        after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())
        if brainstone_committed(snapshot, after, actor):
            scores[i] = (BLOCKED, PREFIX+'standing policy: no Brainstone Gaia commitment')
            skipped.append(i)
            continue
        value = potential(after['state'], actor, home=home)-base
        if action['type'] == 'PlaceStartingStructure':
            value += placement(snapshot['state'], player, action['coord'], home=home)
        if action['type'] == 'FreeAction' and not state_bridge.active():
            value -= .25*action.get('count', 1)
        if not math.isfinite(value):
            raise ValueError('Nonfinite quick native evaluation')
        scores[i] = (value, 'quick native paid state delta; no continuation search')
        evaluated.append(i)
    if not evaluated:
        raise ValueError('No eligible quick native action; preserve constraints, never invent a pass')
    fixed_audit = None
    memory = deepcopy(memory)
    if fixed_openings:
        from bgg_openings.fixed import enforce
        for i in range(len(scores)):
            if i not in evaluated and i not in skipped:
                scores[i] = (BLOCKED, PREFIX+'quick reserve did not evaluate this candidate')
        scores, fixed_audit = enforce(env, snapshot, scores, memory)
    index = max((i for i in evaluated if not scores[i][1].startswith(PREFIX)),
                key=lambda i: (scores[i][0], -i))
    visited = set(evaluated) | set(skipped)
    return {'decision_id': snapshot['decision_id'], 'index': index,
            'scores': scores, 'memory': deepcopy(memory), 'plans': [],
            **({'fixed_opening': fixed_audit} if fixed_openings else {}),
            'selected': 'quick-native-fallback', 'opponents': 'none; one-step evaluation only',
            'horizon_incomes': 0, 'coverage_complete': False,
            'quick_evaluated_indices': evaluated, 'quick_excluded_indices': skipped,
            'quick_unevaluated_indices': [i for i in range(len(candidates)) if i not in visited],
            'stop_reason': 'no normal ranking before deadline; use evaluated quick native reserve'}
