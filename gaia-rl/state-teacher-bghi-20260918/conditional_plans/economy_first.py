"""Contextual Hadsch research with opt-in Economy5 timing comparison."""
import math
from dataclasses import replace

from conditional_plans.forecast import forecast_many
from conditional_plans.opening import OpeningPlanTeacher
from conditional_plans.routes import Plan, acquired, available
from conditional_plans.teacher import select_plan
from research_plans.teacher import best_index, research_track
from scoring_cache import ranking_scope


def select_timing(env, snapshot, scores, goal, completed):
    state, actor = snapshot['state'], snapshot['player']
    player = state['players'][actor]
    if completed or not available(snapshot, goal):
        return best_index(scores, range(len(scores)))
    if state['round'] < goal.defer_until and player['research_tracks']['economy'] == 4:
        # Preserve every other track, including Science5, and all native indices.
        return best_index(scores, [i for i, c in enumerate(snapshot['candidates'])
                                  if research_track(state, c['action']) != 'Economy'])
    return select_plan(env, snapshot, scores, replace(goal, defer_until=0), completed)


def compare_five(env, snapshot, scores, first):
    now = Plan('economy-five-now', targets=(('Economy', 5),))
    tasks = [(now, first)]
    for rnd in sorted({snapshot['state']['round'] + 1, 6}):
        later = Plan(f'economy-five-after-income-{rnd}', targets=now.targets, defer_until=rnd)
        index = select_timing(env, snapshot, scores, later, False)
        if index is not None:
            tasks.append((later, index))
    # Compare actual terminal VP on BOTH sides, not early cash against a delayed
    # benefit beyond the usual two-income cutoff. Opponent races remain native.
    values, stats = forecast_many(env, snapshot, tasks, select_timing, acquired, finish_game=True)
    return ([{'goal': goal.name, 'first': index, 'defer_until': goal.defer_until, **value}
             for (goal, index), value in zip(tasks, values)], stats)


def timing_winner(plans):
    if not plans[0]['complete']:
        return None
    return max((plan for plan in plans if plan['complete']),
               key=lambda plan: (plan['value'], plan['defer_until']))


class EconomyFirstTeacher(OpeningPlanTeacher):
    """Keep the mode name, not a compulsory Economy4 target in arbitrary states."""

    def promote(self, snapshot, scores, index, reason, audit):
        scores = list(scores)
        scores[index] = (math.nextafter(max(value for value, _ in scores), math.inf),
                         reason + '; ' + scores[index][1])
        audit.update(decision_id=snapshot['decision_id'], round=snapshot['state']['round'],
                     selected_first=index)
        self.plan_history.append(audit)
        if self.on_plan is not None:
            self.on_plan(audit)
        scores = self.apply_conservation(snapshot, scores)
        self.last_scores = scores
        return scores

    @ranking_scope()
    def rank(self, snapshot):
        state, player, _ = self.context(snapshot)
        if (player['faction'] != 'HadschHallas' or not isinstance(state['phase'], dict)
                or 'ActionPhase' not in state['phase']):
            return super().rank(snapshot)
        scores = super().rank(snapshot)
        index = best_index(scores, range(len(scores)))
        if (index is None or state['round'] >= 6 or player['research_tracks']['economy'] != 4
                or research_track(state, snapshot['candidates'][index]['action']) != 'Economy'):
            return scores
        plans, stats = compare_five(self.env, snapshot, scores, index)
        winner = timing_winner(plans)
        audit = {'scope': 'economy-five-timing', 'horizon': 'native game end',
                 'plans': plans, 'shared_prefixes': stats,
                 'opponents': 'common deterministic uniform-random forecast',
                 'selected': winner['goal'] if winner else 'incomplete-control'}
        if winner is None:
            audit['fallback'] = 'incomplete control; preserve original action; alternatives remain unknown'
        elif winner['first'] != index:
            self.selected_plan = None  # The parent's selected goal did not choose this action.
        selected = index if winner is None else winner['first']
        reason = ('economy-five timing incomplete; preserve parent' if winner is None else
                  f'economy-five timing={winner["goal"]}; native forecast VP={winner["value"]:.3f}, not guaranteed')
        return self.promote(snapshot, scores, selected, reason, audit)
