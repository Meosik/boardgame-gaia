"""Approved thinking-time allocation, not action scores or artificial delays.

Forecast gaps are uncalibrated scheduling heuristics, never win probabilities.
All plans still use the existing native-paid comparison and conservation rules.
"""
from collections import Counter
import math

from current_actions.conservation import blocked, identity

REACTIONS = {'ChargePower', 'TaklonsChargePower', 'ChooseIncomeOrder'}


def completed_values(result):
    values = {}
    for plan in result.get('plans', ()):
        if plan.get('complete') and plan.get('value') is not None:
            first = plan['first']
            values[first] = max(values.get(first, -math.inf), plan['value'])
    return values


def important(action):
    choice = action.get('tech_tile_choice') or action.get('choice')
    return (bool(choice) or action['type'] in {
        'PlaceStartingStructure', 'SelectStartingBooster', 'FormFederation',
        'ResearchAdvance', 'SelectTinkeringTile', 'PlaceLostPlanet',
        'AmbasSwapPlanetaryInstitute', 'RebellionGainTechTile',
        'SpaceGiantsGainTechTile', 'ItarsGaiaTechChoice'} or
        action['type'].endswith('ExploreSpaceship') or
        (action['type'] == 'Upgrade' and
         (action.get('to') == 'PlanetaryInstitute' or isinstance(action.get('to'), dict))))


def fast_reason(snapshot, memory, result):
    """Only return an already evaluated incumbent, never force a remembered index."""
    if not result:
        return None
    eligible = [i for i, score in enumerate(result['scores']) if not blocked(score)]
    if result['index'] not in eligible:
        return None
    if len(eligible) == 1:
        return 'single eligible action'
    if {snapshot['candidates'][i]['action']['type'] for i in eligible} <= REACTIONS:
        return 'evaluated power reaction'
    actor = str(snapshot['player'])
    committed = memory.get(actor, {}).get(identity(snapshot), ())
    selected = snapshot['candidates'][result['index']]['action']
    if identity(selected) in committed:
        return 'verified resource follow-up'
    saved = memory.get('_plans', {}).get(actor)
    if saved:
        from four_factions.preparation import achieved, goal_from_dict, predicate_for, viable
        goal = goal_from_dict(saved)
        if not achieved(snapshot, snapshot['player'], goal) and viable(snapshot, snapshot['player'], goal):
            matches = predicate_for(snapshot, goal)
            ready = [i for i in eligible if matches(snapshot['candidates'][i]['action'])]
            if ready == [result['index']]:
                return 'unique evaluated next step of saved plan'
    return None


def converged(snapshot, result, history):
    """Stop a stable comparison early without claiming exhaustive coverage."""
    selected = result['index']
    if len(history) < 3 or history[-3:] != [selected]*3:
        return False
    if result.get('bgg_opening', {}).get('status') == 'fallback-no-verified-route':
        return False
    if not any(p.get('family') == 'current' and p.get('complete') for p in result['plans']):
        return False
    values = completed_values(result)
    if len(values) < 3 or selected not in values:
        return False
    others = [value for first, value in values.items() if first != selected]
    second = max(others)
    margin = (values[selected]-second)/max(1, abs(values[selected]), abs(second))
    available = {snapshot['candidates'][i]['action']['type']
                 for i, score in enumerate(result['scores']) if not blocked(score)}
    compared = {snapshot['candidates'][i]['action']['type'] for i in values}
    return margin >= .03 and len(compared) >= min(2, len(available))


class AdaptiveClock:
    def __init__(self, *, target_seconds=10, long_seconds=120, uses=6, state=None):
        if (not 0 < target_seconds <= long_seconds or not math.isfinite(long_seconds)
                or type(uses) is not int or uses < 0):
            raise ValueError('Finite positive target <= long limit and nonnegative integer uses required')
        self.target_seconds, self.long_seconds, self.uses = target_seconds, long_seconds, uses
        self.spent = []
        if state is not None:
            if not isinstance(state, dict) or set(state) != {'spent'} or not isinstance(state['spent'], list):
                raise ValueError('Invalid adaptive clock state')
            for entry in state['spent']:
                if (not isinstance(entry, list) or len(entry) != 2 or entry[0] not in ('0', '1', '2', '3')
                        or type(entry[1]) is not int or entry[1] < 0 or entry in self.spent):
                    raise ValueError('Invalid or duplicate long-think receipt')
                self.spent.append(entry.copy())
            if any(count > uses for count in Counter(s for s, _ in self.spent).values()):
                raise ValueError('Long-think uses exceed per-seat allowance')

    def state(self):
        return {'spent': [entry.copy() for entry in self.spent]}

    def remaining(self, actor):
        return self.uses-sum(seat == str(actor) for seat, _ in self.spent)

    def spend(self, snapshot):
        entry = [str(snapshot['player']), snapshot['decision_id']]
        if entry in self.spent:
            return True
        if self.remaining(snapshot['player']) <= 0:
            return False
        self.spent.append(entry)
        return True

    def base_seconds(self, snapshot, memory):
        if len(snapshot['candidates']) <= 1:
            return min(1, self.target_seconds)
        actions = {candidate['action']['type'] for candidate in snapshot['candidates']}
        if actions <= REACTIONS or memory.get(str(snapshot['player']), {}).get(identity(snapshot)):
            return min(3, self.target_seconds)
        return self.target_seconds

    def extension_reason(self, snapshot, memory, result):
        if (len(snapshot['candidates']) <= 1 or self.remaining(snapshot['player']) <= 0 or
                {c['action']['type'] for c in snapshot['candidates']} <= REACTIONS or
                (result and (result.get('coverage_complete') or fast_reason(snapshot, memory, result)))):
            return None
        saved = memory.get('_plans', {}).get(str(snapshot['player']))
        if saved:
            from four_factions.preparation import achieved, goal_from_dict, viable
            goal = goal_from_dict(saved)
            if not achieved(snapshot, snapshot['player'], goal) and not viable(snapshot, snapshot['player'], goal):
                return 'previous plan blocked; compare replacements'
        candidates = [c['action'] for i, c in enumerate(snapshot['candidates'])
                      if not result or not blocked(result['scores'][i])]
        if not any(important(action) for action in candidates):
            return None
        values = completed_values(result or {})
        if len(values) < 2:
            return 'important alternatives lack completed comparable forecasts'
        ordered = sorted(values.values(), reverse=True)
        gap = (ordered[0]-ordered[1])/max(1, abs(ordered[0]), abs(ordered[1]))
        # Soft conservation, not a per-round quota: scarce uses require a closer
        # contest, but a severely disrupted/unexamined critical plan may still use one.
        stages_left = max(1, 7-snapshot['state']['round'])
        threshold = .03*min(1, self.remaining(snapshot['player'])/stages_left)
        if gap <= threshold:
            return 'close completed alternatives; remaining-game allowance considered'
        return None
