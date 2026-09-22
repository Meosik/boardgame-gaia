"""Opt-in Xenos resource/continuation comparison; existing teachers stay frozen."""
import math

from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from integrated.boosters import next_income
from research_plans.teacher import best_index, forecast, goal_index
from resource_plans.funding import funded_paths, resource_actions
from resource_plans.routes import Route, achieved, milestone, routes_for, upgrade_stage
from strategy_teacher import TRACK_KEYS
from scoring_cache import ranking_scope
from current_actions.conservation import blocked


def wait_for_funding(snapshot, scores, need):
    state, actor = snapshot['state'], snapshot['player']
    if state['round'] >= 6 or not need:
        return None
    player = state['players'][actor]
    later = next_income(state, player)['resources']
    # This is only a candidate reservation. The subsequent native pass/income
    # actually pays/receives everything; no forecast income is injected here.
    if (any(player['resources'][k] < n for k, n in need.items())
            and all(later[k] >= n for k, n in need.items())):
        return best_index(scores, [i for i, c in enumerate(snapshot['candidates'])
                                  if c['action']['type'] == 'Pass'])
    return None


def select_route(env, snapshot, scores, route, completed=False, *, audit=None):
    fallback = best_index(scores, range(len(scores)))
    state = snapshot['state']
    if completed or not isinstance(state['phase'], dict) or 'ActionPhase' not in state['phase']:
        return fallback
    if route.name == 'current-choice':
        return fallback
    if route.defer_until:
        return goal_index(snapshot, scores, route, completed)
    predicate, need = milestone(snapshot, route)
    direct = best_index(scores, [i for i, c in enumerate(snapshot['candidates']) if predicate(c['action'])])
    if direct is not None:
        return direct
    if not need:
        return fallback
    paths, _ = funded_paths(env, snapshot, predicate, need, audit=audit)
    paths = [p for p in paths if not blocked(scores[p['first']])]
    if paths:
        return paths[0]['first']
    funding = resource_actions(env, snapshot, scores, need)
    if funding is not None:
        return funding
    # Bootstrap research through a real TS/lab and its actual tile-granted advance.
    player = state['players'][snapshot['player']]
    for track, target in route.targets:
        if player['research_tracks'][TRACK_KEYS[track]] < target:
            predicate, need = upgrade_stage(player, track=track, state=state)
            direct = best_index(scores, [i for i, c in enumerate(snapshot['candidates']) if predicate(c['action'])])
            if direct is not None:
                return direct
            paths, _ = funded_paths(env, snapshot, predicate, need, audit=audit)
            paths = [p for p in paths if not blocked(scores[p['first']])]
            if paths:
                return paths[0]['first']
            funding = resource_actions(env, snapshot, scores, need)
            if funding is not None:
                return funding
            wait = wait_for_funding(snapshot, scores, need)
            return fallback if wait is None else wait
    if route.payoff == 'RebellionGainTechTile' and 1 in player['explored_ships']:
        if 12 not in state['used_spaceship_actions'] and player['resources']['qic'] < 3:
            # Only native QIC-producing research is offered; no fictional Xenos C->Q.
            qic = best_index(scores, [i for i, c in enumerate(snapshot['candidates'])
                if c['action']['type'] == 'ResearchAdvance' and
                (c['action']['track'] == 'Navigation' and player['research_tracks']['navigation'] == 0)])
            if qic is not None:
                return qic
            if not any(s['kind'] == {'Academy': 'Qic'} for s in player['structures']):
                return select_route(env, snapshot, scores, Route('fund-QIC', academy='Qic'), audit=audit)
    wait = wait_for_funding(snapshot, scores, need)
    # Failed funding search is not proof of impossibility. The ordinary route
    # still competes against any explicit reservation/pass forecast.
    return fallback if wait is None else wait


def run_route(env, snapshot, scores, route):
    audit = []
    first = route.first if route.first is not None else select_route(env, snapshot, scores, route, audit=audit)
    firsts = [first]
    if route.first is None and route.name != 'current-choice':
        predicate, need = milestone(snapshot, route)
        if not any(predicate(c['action']) for c in snapshot['candidates']):
            paths, _ = funded_paths(env, snapshot, predicate, need, audit=audit)
            # Compare distinct actual funding choices, not just the locally
            # cheapest conversion. Remaining prefixes are explicitly unsearched.
            firsts = list(dict.fromkeys([first, *(p['first'] for p in paths
                                                 if not blocked(scores[p['first']]))]))[:3]
    results = []
    for index in firsts:
        def selector(env, snapshot, scores, goal, completed):
            return select_route(env, snapshot, scores, goal, completed, audit=audit)
        result = forecast(env, snapshot, index, route, CurrentContextTeacher(),
                          selector=selector, achieved=achieved)
        results.append({'first': index, **result})
    complete = [result for result in results if result['complete']]
    winner = max(complete, key=lambda r: (r['value'], r['first'] == first, -r['first'])) if complete else results[0]
    return {**winner, 'funding_searches': audit, 'max_root_funding_choices': 3,
            'funding_alternatives': results}


class ResourcePlanTeacher(CurrentActionTeacher):
    def __init__(self, stage=1):
        super().__init__(stage)
        self.plan_history = []
        self.on_plan = None

    @ranking_scope()
    def rank(self, snapshot):
        scores = super().rank(snapshot)
        state, player, _ = self.context(snapshot)
        if (player['faction'] != 'Xenos' or not isinstance(state['phase'], dict)
                or 'ActionPhase' not in state['phase']):
            return scores
        if self.env is None:
            raise ValueError('ResourcePlanTeacher requires a native environment')
        plans = [{'goal': route.name, **run_route(self.env, snapshot, scores, route)}
                 for route in routes_for(snapshot, scores)]
        control = next(p for p in plans if p['goal'] == 'current-choice')
        audit = {'decision_id': snapshot['decision_id'], 'round': state['round'],
                 'horizon_incomes': 2, 'plans': plans, 'selected': control['goal'],
                 'selected_first': control['first'],
                 'opponents': 'common deterministic uniform-random forecast'}
        if control['complete']:
            winner = max((p for p in plans if p['complete'] and not blocked(scores[p['first']])),
                         key=lambda p: (p['value'], p['goal'] == 'current-choice', -p['first']))
            index = winner['first']
            scores[index] = (math.nextafter(max(v for v, _ in scores), math.inf),
                f'conditional resource plan={winner["goal"]}; utility={winner["value"]:.3f}; '
                f'control={control["value"]:.3f}; paid two-income forecast, not guaranteed; '
                + scores[index][1])
            audit.update(selected=winner['goal'], selected_first=index)
        else:
            audit['fallback'] = 'incomplete control; preserve current ranks'
        self.plan_history.append(audit)
        if self.on_plan is not None:
            self.on_plan(audit)
        scores = self.apply_conservation(snapshot, scores)
        self.last_scores = scores
        return scores
