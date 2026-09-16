"""Opt-in compatibility adapter; historical teachers and coefficients stay frozen."""
from dataclasses import replace

from action_purpose.costs import CorrectedContextTeacher, construction_cost as previous_cost
from action_purpose.teacher import CHAINS, PurposeTeacher, key, productive
from economy.teacher import ORE_PER_STEP
from integrated.boosters import evaluate_booster as previous_booster, funded, next_income
from integrated.features import resource_value
from scoring_cache import decision_scope, reuse, shared_rank
from current_actions.conservation import Conserving, FORBIDDEN

BOOSTER_BUILD = 'RoundBoosterTerraformBuild'


def construction_cost(state, player, action):
    if action['type'] != BOOSTER_BUILD:
        return previous_cost(state, player, action)
    cost = previous_cost(state, player, {**action, 'type': 'Build'})
    if cost is None:
        return None
    free_steps = min(1, cost.terraform_steps)
    saved = free_steps * ORE_PER_STEP[player['research_tracks']['terraforming']]
    return replace(cost, ore=cost.ore-saved, terraform_ore=cost.terraform_ore-saved,
                   terraform_steps=cost.terraform_steps-free_steps)


def terraform_action_value(state, player):
    """One funded use on the present board; no invented resources or tier bonus."""
    if sum(s['kind'] == 'Mine' for s in player['structures']) >= 8:
        return 0.0
    best = 0.0
    for coord, cell in state['board']['hexes'].items():
        planet = cell['planet']
        if not planet or planet['owner'] is not None or cell['structures']:
            continue
        action = {'type': BOOSTER_BUILD, 'coord': coord}
        cost = construction_cost(state, player, action)
        if not funded(player, cost):
            continue
        ordinary = previous_cost(state, player, {**action, 'type': 'Build'})
        best = max(best, resource_value(player, {'ore': ordinary.ore-cost.ore}))
    return best


def evaluate_booster(state, player, booster, *, starting=False):
    value = previous_booster(state, player, booster, starting=starting)
    if booster != 12 or (not starting and state['round'] >= 6):
        return value
    # Match the existing one-income forecast. Prior-round use resets; ownership
    # is supplied by the actual selection candidate, not a hypothetical action.
    projected = next_income(state, player)
    projected['resources']['credits'] += 2
    return replace(value, action=terraform_action_value(state, projected))


class BoosterScoring:
    """Share the correction across control and purpose stages without retuning them."""

    def research(self, state, player, track):
        # Keep all existing arithmetic, including corrected-minus-pinned terms.
        calculate = super().research
        key = (track, repr(player), repr(getattr(self, '_candidate', None)))
        return reuse(state, ('contextual-research', type(self)), key,
                     lambda: calculate(state, player, track))

    def score(self, snapshot, action):
        if action['type'] in ('Pass', 'SelectStartingBooster') and action.get('booster_id') == 12:
            state, player, _ = self.context(snapshot)
            starting = action['type'] == 'SelectStartingBooster'
            value = evaluate_booster(state, player, 12, starting=starting)
            score = value.total if starting else 3*value.total/(1+value.total)
            return score, (f'booster: next-round components={value}; total={value.total:.3f}; '
                           'booster12: funded one-step terraform saving, mine costs retained')
        if action['type'] != BOOSTER_BUILD:
            return super().score(snapshot, action)
        ordinary = {**action, 'type': 'Build'}
        value, reason = super().score(snapshot, ordinary)
        state, player, resources = self.context(snapshot)
        old = previous_cost(state, player, ordinary)
        cost = construction_cost(state, player, action)
        if old is None or cost is None:
            return 0.0, 'unmodeled booster12 target; excluded from demonstrations'
        # Reuse the inherited mine/location/round/federation score and ore price.
        # This surrogate is scoring-only: execution still uses the native candidate.
        ore_price = 2.5 if resources['ore'] >= 5 else 3.5
        saving = (old.ore-cost.ore)*ore_price
        return value+saving, (f'booster12: ordinary-build baseline [{reason}]; '
                              f'one free terraform step; actual cost={cost}; saving={saving:.2f}')


class CurrentContextTeacher(Conserving, BoosterScoring, CorrectedContextTeacher):
    """Stage0 control with the same booster12 selection/build correction."""

    def bind(self, env):
        self.env = env
        return self

    def rank(self, snapshot):
        def calculate():
            with decision_scope(snapshot['state']):
                return super(CurrentContextTeacher, self).rank(snapshot)
        # A subclass may add mutable policy state; do not memoize its whole rank.
        scores = shared_rank(snapshot, calculate) if type(self) is CurrentContextTeacher else calculate()
        # Stateful conversion commitments must never enter the shared score cache.
        return self.apply_conservation(snapshot, scores)


class CurrentActionTeacher(Conserving, BoosterScoring, PurposeTeacher):
    """Existing Xenos/HH strategy with paid-mine booster12 and purposeful batches."""

    def score(self, snapshot, action):
        route = getattr(self, '_route_context', None)
        if route is not None and snapshot is route[0]:
            if not productive(action) or key(action) in route[1]:
                # route_value discards these entries. Keep the full snapshot for
                # research opportunity scoring and all inherited rank lifecycles.
                return 0.0, 'purpose: unused route score'
        return super().score(snapshot, action)

    def base_rank(self, snapshot):
        with decision_scope(snapshot['state']):
            return super().base_rank(snapshot)

    def route_value(self, before, after, already_legal, actions):
        # Charge the same existing per-unit overhead for a batch and its unbatched
        # equivalent. Physical token savings still come from the native after-state.
        units = [{**action, 'count': 1} for action in actions
                 for _ in range(action.get('count', 1))]
        # Subclasses can attach score-side effects; retain their existing behavior.
        if type(self) is not CurrentActionTeacher:
            return super().route_value(before, after, already_legal, units)
        previous = getattr(self, '_route_context', None)
        self._route_context = (after, already_legal)
        try:
            return super().route_value(before, after, already_legal, units)
        finally:
            self._route_context = previous

    def rank(self, snapshot):
        # Keep the frozen purpose stages/budget/order. Only the first free-action
        # count gate changes; no new chains, batch bonus or compulsory conversion.
        scores = self.base_rank(snapshot)
        self.preview_count = 0
        state, _, _ = self.context(snapshot)
        if not isinstance(state['phase'], dict) or 'ActionPhase' not in state['phase']:
            self.last_scores = scores
            return scores
        before_main = {key(c['action']) for c in snapshot['candidates'] if productive(c['action'])}
        if any(c['action']['type'] == 'FreeAction' for c in snapshot['candidates']) and self.env is None:
            raise ValueError('CurrentActionTeacher requires its current native environment for previews')
        for i, candidate in enumerate(snapshot['candidates']):
            action = candidate['action']
            if action['type'] != 'FreeAction':
                continue
            if action['kind'] in FORBIDDEN:
                continue  # Mask below; do not waste native preview budget on a ban.
            # The old Xenos recovery exception was defined for one ore only.
            if action['kind'] == 'OreToPowerBowl3' and action.get('count', 1) == 1:
                continue
            scores[i] = (-12.0, 'purpose: no verified productive follow-up')
            if self.stage >= 4 and self.preview_count >= 18:
                continue
            branch, after = self.preview(self.env, snapshot, i)
            if after is None or after['player'] != snapshot['player']:
                continue
            best, target = self.route_value(snapshot, after, before_main, [action])
            for j, next_candidate in enumerate(after['candidates']):
                second = next_candidate['action']
                if (second['type'] != 'FreeAction' or second.get('count', 1) != 1
                        or second['kind'] in FORBIDDEN
                        or second['kind'] not in CHAINS.get(action['kind'], set())):
                    continue
                _, last = self.preview(branch, after, j)
                if last is None or last['player'] != snapshot['player']:
                    continue
                value, followup = self.route_value(snapshot, last, before_main, [action, second])
                if value > best:
                    best, target = value, followup
            if target:
                scores[i] = (best, f'purpose: native-legal follow-up {key(target)}; net={best:.3f}')
        if self.stage >= 2:
            self.adjust_pass(snapshot, scores)
        if self.stage >= 3:
            self.adjust_research_order(snapshot, scores)
        if self.stage >= 4:
            self.adjust_ship_entry(snapshot, scores)
        scores = self.apply_conservation(snapshot, scores)
        self.last_scores = scores
        return scores
