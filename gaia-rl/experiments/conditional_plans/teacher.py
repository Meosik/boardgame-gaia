"""Hadsch conditional PI/Gaia/research/expansion comparison; no fixed opening."""
import math
from dataclasses import replace

from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from research_plans.teacher import best_index, forecast
from resource_plans.funding import funded_paths, resource_actions
from resource_plans.routes import Route
from resource_plans.teacher import select_route, wait_for_funding
from conditional_plans.routes import Plan, acquired, available, next_milestone, plans_for, structure_at
from current_actions.conservation import blocked
from scoring_cache import ranking_scope
from strategy_teacher import kind


def select_plan(env, snapshot, scores, plan, completed=False, *, audit=None):
    custom = plan.institute or plan.gaia_coord or plan.repeat_rebellion or plan.federation_goal
    if not custom:
        return select_route(env, snapshot, scores, plan, completed, audit=audit)
    state, actor = snapshot['state'], snapshot['player']
    allowed = list(range(len(scores)))
    if plan.federation_goal and not completed:
        large = {s['hex'] for s in state['players'][actor]['structures']
                 if kind(s['kind']) in ('Academy', 'PlanetaryInstitute')}
        allowed = [i for i in allowed if not (snapshot['candidates'][i]['action']['type'] == 'FormFederation'
                   and len(large.intersection(snapshot['candidates'][i]['action']['hexes'])) > 1)]
    if plan.immediate_only and not completed:
        allowed = [i for i in allowed if not (snapshot['candidates'][i]['action'].get('coord') == plan.gaia_coord
                   and snapshot['candidates'][i]['action']['type'] in
                   ('GaiaFormation', 'RoundBoosterRangeGaiaFormation', 'TwilightRangeGaiaFormation'))]
    fallback = best_index(scores, allowed)
    if fallback is None:
        # An already paid conversion commitment takes precedence over this
        # hypothetical goal's preference. Never bypass conservation or deadlock.
        fallback = best_index(scores, range(len(scores)))
    if completed or not isinstance(state['phase'], dict) or 'ActionPhase' not in state['phase']:
        return fallback
    predicate, need = next_milestone(snapshot, plan)
    direct = best_index(scores, [i for i,c in enumerate(snapshot['candidates']) if predicate(c['action'])])
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
    player = state['players'][actor]
    if plan.gaia_coord and player['research_tracks']['gaia'] == 0:
        return select_route(env, snapshot, scores, Route('Gaia-access', (('GaiaProject', 1),)), audit=audit)
    pi_ready = not plan.institute or structure_at(player, plan.institute) == 'PlanetaryInstitute'
    if plan.repeat_rebellion and pi_ready:
        return select_route(env, snapshot, scores, Route('repeat', ship='Rebellion', payoff='RebellionGainTechTile'), audit=audit)
    wait = wait_for_funding(snapshot, scores, need)
    return fallback if wait is None else wait


def run_plan(env, snapshot, scores, plan):
    audit = []
    first = plan.first if plan.first is not None else select_plan(env, snapshot, scores, plan, audit=audit)
    firsts = [first]
    if plan.first is None and plan.name != 'current-choice':
        predicate, need = next_milestone(snapshot, plan)
        if need and not any(predicate(c['action']) for c in snapshot['candidates']):
            paths, _ = funded_paths(env, snapshot, predicate, need, audit=audit)
            firsts = list(dict.fromkeys([first, *(p['first'] for p in paths if not blocked(scores[p['first']]))]))[:3]
    results = []
    for index in firsts:
        def selector(env, snapshot, scores, goal, completed):
            return select_plan(env, snapshot, scores, goal, completed, audit=audit)
        result = forecast(env, snapshot, index, plan, CurrentContextTeacher(), selector=selector, achieved=acquired)
        result['rebellion_tech_uses'] = sum(a['action']['type'] == 'RebellionGainTechTile' for a in result['actions'])
        results.append({'first': index, **result})
    complete = [r for r in results if r['complete']]
    winner = max(complete, key=lambda r: (r['value'], r['first'] == first, -r['first'])) if complete else results[0]
    return {**winner, 'funding_searches': audit, 'max_root_funding_choices': 3, 'funding_alternatives': results}


class HadschPlanTeacher(CurrentActionTeacher):
    factions = ('HadschHallas',)
    def __init__(self, stage=1):
        super().__init__(stage)
        self.plan_history = []
        self.on_plan = None

    def plan_routes(self, snapshot, scores):
        return plans_for(snapshot, scores)

    def evaluate_plans(self, snapshot, scores, routes):
        return [{'goal': route.name, **run_plan(self.env, snapshot, scores, route)} for route in routes]

    @ranking_scope()
    def rank(self, snapshot):
        scores = super().rank(snapshot)
        state, player, _ = self.context(snapshot)
        if (player['faction'] not in self.factions or not isinstance(state['phase'], dict)
                or 'ActionPhase' not in state['phase']):
            return scores
        if self.env is None:
            raise ValueError('HadschPlanTeacher requires a native environment')
        routes, sampling = self.plan_routes(snapshot, scores)
        plans = self.evaluate_plans(snapshot, scores, routes)
        control = next(p for p in plans if p['goal'] == 'current-choice')
        audit = {'decision_id': snapshot['decision_id'], 'round': state['round'], 'horizon_incomes': 2,
                 'plans': plans, 'sampling': sampling, 'selected': control['goal'], 'selected_first': control['first'],
                 'opponents': 'common deterministic uniform-random forecast'}
        if control['complete']:
            winner = max((p for p in plans if p['complete'] and not blocked(scores[p['first']])),
                         key=lambda p: (p['value'], p['goal'] == 'current-choice', -p['first']))
            index = winner['first']
            scores[index] = (math.nextafter(max(v for v,_ in scores), math.inf),
                f'conditional Paia plan={winner["goal"]}; utility={winner["value"]:.3f}; '
                f'control={control["value"]:.3f}; paid two-income forecast, not guaranteed; ' + scores[index][1])
            audit.update(selected=winner['goal'], selected_first=index)
            self.selected_plan = next(route for route in routes if route.name == winner['goal'])
        else:
            audit['fallback'] = 'incomplete control; preserve current ranks'
            self.selected_plan = None
        self.plan_history.append(audit)
        if hasattr(self, 'shared_stats'):
            audit['shared_prefixes'] = self.shared_stats
        if self.on_plan is not None:
            self.on_plan(audit)
        scores = self.apply_conservation(snapshot, scores)
        self.last_scores = scores
        return scores


class PaiaPlanTeacher(HadschPlanTeacher):
    """Current two-faction candidate; no all-faction support or trained PPO claim."""
    factions = ('Xenos', 'HadschHallas')
    continue_goals = True

    @ranking_scope()
    def rank(self, snapshot):
        state, player, _ = self.context(snapshot)
        action_phase = (player['faction'] in self.factions and isinstance(state['phase'], dict)
                        and 'ActionPhase' in state['phase'])
        previous = getattr(self, 'selected_plan', None)
        if (self.continue_goals and action_phase and previous
                and getattr(self, 'planning_round', None) == state['round']
                and not acquired(snapshot, snapshot['player'], previous) and available(snapshot, previous)):
            # Reuse the chosen goal, never a stale candidate index or hypothetical
            # resource balance. Income, achievement and lost targets reopen the
            # comparison; each intervening step still uses the current native menu.
            scores = CurrentActionTeacher.rank(self, snapshot)
            audit = []
            index = select_plan(self.env, snapshot, scores, previous, audit=audit)
            if index is not None and not blocked(scores[index]):
                _, reason = scores[index]
                scores[index] = (math.nextafter(max(v for v, _ in scores), math.inf),
                    f'continue Paia goal={previous.name}; forecast root={self.planning_decision}; '
                    'current native costs, no new forecast; ' + reason)
                entry = {'decision_id': snapshot['decision_id'], 'round': state['round'],
                    'selected': previous.name, 'selected_first': index, 'continued': True,
                    'forecast_origin': self.planning_decision, 'plans': [], 'funding_searches': audit}
                self.plan_history.append(entry)
                if self.on_plan is not None:
                    self.on_plan(entry)
                self.last_scores = scores
                return scores
        scores = super().rank(snapshot)
        if action_phase:
            self.planning_round = state['round']
            self.planning_decision = snapshot['decision_id']
            selected = getattr(self, 'selected_plan', None)
            if selected and selected.first is not None:
                # The initial federation choice belongs only to this snapshot.
                # Retain its follow-up goal, never reuse its old candidate index.
                remaining = replace(selected, first=None)
                self.selected_plan = None if remaining == Plan(remaining.name) else remaining
        return scores

    def plan_routes(self, snapshot, scores):
        routes, sampling = plans_for(snapshot, scores)
        previous = getattr(self, 'selected_plan', None)
        if (previous and previous.name != 'current-choice' and available(snapshot, previous)
                and not acquired(snapshot, snapshot['player'], previous)):
            # Preserve the original target, rather than moving the goalpost after
            # every research bump. It still competes; no arbitrary switch penalty.
            routes = [r for r in routes if r.name != previous.name] + [previous]
            sampling['previous_goal_still_competes'] = previous.name
        return routes, sampling

    def evaluate_plans(self, snapshot, scores, routes):
        from conditional_plans.forecast import forecast_many
        tasks, audits, starts = [], {}, {}
        for route in routes:
            audit = audits[route.name] = []
            first = route.first if route.first is not None else select_plan(self.env, snapshot, scores, route, audit=audit)
            firsts = [first]
            if route.first is None and route.name != 'current-choice':
                predicate, need = next_milestone(snapshot, route)
                if need and not any(predicate(c['action']) for c in snapshot['candidates']):
                    paths, _ = funded_paths(self.env, snapshot, predicate, need, audit=audit)
                    firsts = list(dict.fromkeys([first, *(p['first'] for p in paths
                                                        if not blocked(scores[p['first']]))]))[:3]
            starts[route.name] = first
            tasks.extend((route, index) for index in firsts)

        if len({first for _, first in tasks}) == 1:
            # No proposed forecast can change this real action. Skipping their
            # evaluation does not rank unsearched future plans or assign fake VP.
            self.shared_stats = {'skipped': 'all sampled plans have the same first action'}
            return [{'goal': r.name, 'first': starts[r.name], 'complete': False, 'value': None,
                     'actions': [], 'reason': 'same first action; future not evaluated',
                     'funding_searches': audits[r.name]} for r in routes]

        def selector(env, snapshot, scores, route, completed):
            return select_plan(env, snapshot, scores, route, completed, audit=audits[route.name])

        values, self.shared_stats = forecast_many(self.env, snapshot, tasks, selector, acquired)
        grouped = {route.name: [] for route in routes}
        for (route, first), value in zip(tasks, values):
            grouped[route.name].append({'first': first, **value,
                'rebellion_tech_uses': sum(a['action']['type'] == 'RebellionGainTechTile' for a in value['actions'])})
        result = []
        for route in routes:
            alternatives = grouped[route.name]
            complete = [r for r in alternatives if r['complete']]
            winner = max(complete, key=lambda r: (r['value'], r['first'] == starts[route.name], -r['first'])) if complete else alternatives[0]
            result.append({'goal': route.name, **winner, 'funding_searches': audits[route.name],
                           'max_root_funding_choices': 3, 'funding_alternatives': alternatives})
        return result


class PaiaReplanTeacher(PaiaPlanTeacher):
    """Matched control: reconsider all sampled plans at each actual action."""
    continue_goals = False
