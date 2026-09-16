"""Opt-in native opening forecasts; no fixed sectors or extra mine-count reward."""
import math

from conditional_plans.forecast import forecast_many
from conditional_plans.routes import Plan, acquired
from conditional_plans.teacher import PaiaReplanTeacher
from economy.teacher import neighbors
from research_plans.teacher import MAX_FORECAST_DECISIONS, best_index
from scoring_cache import ranking_scope


def starting_choice(snapshot):
    return bool(snapshot['candidates']) and all(
        c['action']['type'] == 'PlaceStartingStructure' for c in snapshot['candidates'])


def opening_summary(state, actor, frames):
    """Diagnostics only; native structures distinguish colonies from upgrades."""
    round1 = [f['state'] for f in frames if f['state']['round'] == 1]
    if not round1:
        raise ValueError('Completed opening forecast did not reach round one')
    start, end = round1[0], round1[-1]
    first, last = start['players'][actor], end['players'][actor]
    initial_sites = {s['hex'] for s in first['structures']}
    end_sites = {s['hex'] for s in last['structures']}
    return {
        'starting_neighbors': [{'coord': s['hex'], 'opponents': sorted({
            structure['owner'] for _, structure in neighbors(start, first, s['hex'])})}
            for s in first['structures']],
        'round1_new_colonies': len(end_sites-initial_sites),
        'round1_mines': sum(s['kind'] == 'Mine' for s in last['structures']),
        'round1_buildings': len(last['structures']),
        'round1_structures': last['structures'],
        'round1_ships': last['explored_ships'],
        'round1_artifacts': last['artifacts'],
    }


@ranking_scope()
def compare_openings(env, snapshot, *, limit=MAX_FORECAST_DECISIONS):
    if not starting_choice(snapshot) or snapshot['state']['round'] != 0:
        raise ValueError('Opening comparison requires a native starting-placement decision')
    tasks = [(Plan(f"opening@{c['action']['coord']}"), i)
             for i, c in enumerate(snapshot['candidates'])]

    def selector(branch, current, scores, goal, completed):
        # Same context policy as other forecasts, not recursively nested full plans.
        return best_index(scores, range(len(scores)))

    values, stats = forecast_many(env, snapshot, tasks, selector, acquired,
                                  limit=limit, summarize=opening_summary)
    plans = [{'goal': goal.name, 'first': first, 'placement': snapshot['candidates'][first]['action'],
              **value} for (goal, first), value in zip(tasks, values)]
    return {'plans': plans, 'shared_prefixes': stats}


class OpeningPlanTeacher(PaiaReplanTeacher):
    """Compare every legal initial mine; preserve the per-action teacher afterward."""
    @ranking_scope()
    def rank(self, snapshot):
        scores = super().rank(snapshot)
        if not starting_choice(snapshot):
            return scores
        if self.env is None:
            raise ValueError('OpeningPlanTeacher requires a native environment')
        report = compare_openings(self.env, snapshot)
        control_index = best_index(scores, range(len(scores)))
        control = next(p for p in report['plans'] if p['first'] == control_index)
        audit = {'decision_id': snapshot['decision_id'], 'round': snapshot['state']['round'],
                 'scope': 'starting-placement', 'horizon_incomes': 2,
                 'opponents': 'common deterministic uniform-random forecast; neighbors not guaranteed',
                 'selected': control['goal'], 'selected_first': control_index, **report}
        if control['complete']:
            complete = [p for p in report['plans'] if p['complete']]
            if not all(math.isfinite(p['value']) for p in complete):
                raise ValueError('Nonfinite opening forecast utility')
            winner = max(complete, key=lambda p: (p['value'], scores[p['first']][0], -p['first']))
            index = winner['first']
            scores[index] = (math.nextafter(max(v for v, _ in scores), math.inf),
                f'opening forecast={winner["goal"]}; utility={winner["value"]:.3f}; '
                f'control={control["value"]:.3f}; native R1 play and R2 income, not final VP; ' + scores[index][1])
            audit.update(selected=winner['goal'], selected_first=index)
        else:
            audit['fallback'] = 'incomplete control; preserve placement ranks; unsearched outcomes unknown'
        self.plan_history.append(audit)
        if self.on_plan is not None:
            self.on_plan(audit)
        self.last_scores = scores
        return scores
