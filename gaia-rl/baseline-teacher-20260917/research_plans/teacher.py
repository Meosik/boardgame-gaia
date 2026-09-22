"""Hadsch Hallas candidate plans over two actual native income transitions.

Only the first native action is executed. Subsequent actions/opponents are
forecasts and are discarded; the next real decision is planned afresh.
"""
from dataclasses import dataclass
import json
import math
import random

from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from integrated.features import advanced_value
from strategy_teacher import TRACK_KEYS
from research_plans.value import endpoint_value
from scoring_cache import ranking_scope
from current_actions.conservation import blocked

MAX_FORECAST_DECISIONS = 192


@dataclass(frozen=True)
class Goal:
    name: str
    targets: tuple[tuple[str, int], ...] = ()
    advanced: tuple[str, int] | None = None
    payoff: str | None = None
    defer_until: int = 0


def research_track(state, action):
    if action['type'] in ('ResearchAdvance', 'EclipseResearchBoost', 'RebellionGainTechTile'):
        return action.get('track')
    choice = action.get('tech_tile_choice')
    if not choice:
        return None
    if choice.get('advance_track'):
        return choice['advance_track']
    if choice['kind'] == 'Standard':
        slots = state['research_board']['tech_tile_slots'][:6]
        if choice['tile'] in slots:
            return tuple(TRACK_KEYS)[slots.index(choice['tile'])]
    return None


def is_advanced(action, target=None):
    choice = action.get('tech_tile_choice')
    if not choice or choice['kind'] not in ('Advanced', 'LostFleetAdvanced'):
        return False
    return target is None or choice.get('track') == target[0]


def best_index(scores, indices):
    return max((i for i in indices if not blocked(scores[i])),
               key=lambda i: (scores[i][0], -i), default=None)


def matches_payoff(action, payoff):
    if payoff == 'AdvancedTechnology':
        return is_advanced(action)
    if payoff == 'GaiaFormation':
        return action['type'] in ('GaiaFormation', 'TFMarsGaiaFormation',
            'RoundBoosterImmediateGaiaFormation', 'RoundBoosterRangeGaiaFormation',
            'TwilightRangeGaiaFormation')
    return action['type'] == payoff


def goal_index(snapshot, scores, goal, completed=False):
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    actions = [c['action'] for c in snapshot['candidates']]
    allowed = list(range(len(actions)))
    if goal.defer_until > state['round']:
        allowed = [i for i in allowed if not (
            research_track(state, actions[i]) in ('Economy', 'Science') and
            player['research_tracks'][TRACK_KEYS[research_track(state, actions[i])]] == 4)]
    fallback = best_index(scores, allowed)
    if completed:
        return fallback
    if goal.advanced:
        track, tile = goal.advanced
        if state['research_board']['advanced_tech_tiles'][tuple(TRACK_KEYS).index(track)] != tile:
            return fallback  # Taken by a rival: abandon, do not substitute a fictitious reward.
        acquire = best_index(scores, [i for i in allowed if is_advanced(actions[i], goal.advanced)])
        if acquire is not None:
            return acquire
    for track, target in goal.targets:
        if player['research_tracks'][TRACK_KEYS[track]] >= target:
            continue
        match = best_index(scores, [i for i in allowed if research_track(state, actions[i]) == track])
        if match is not None:
            return match
        # A legal conversion supplies only the missing knowledge, not a free budget.
        need = 4-player['resources']['knowledge']
        funding = best_index(scores, [i for i in allowed if actions[i]['type'] == 'FreeAction'
            and actions[i]['kind'] in ('PowerToKnowledge', 'CreditsToKnowledge')
            and actions[i].get('count', 1) == need and need > 0])
        return fallback if funding is None else funding
    if goal.advanced and not player['federation_tokens']:
        federation = best_index(scores, [i for i in allowed if actions[i]['type'] == 'FormFederation'])
        if federation is not None:
            return federation
    if goal.payoff:
        payoff = best_index(scores, [i for i in allowed if matches_payoff(actions[i], goal.payoff)])
        if payoff is not None:
            return payoff
        if goal.payoff == 'RebellionGainTechTile':
            if 1 not in player['explored_ships']:
                entry = best_index(scores, [i for i in allowed if actions[i].get('ship') == 'Rebellion'
                                           and actions[i]['type'].endswith('ExploreSpaceship')])
                return fallback if entry is None else entry
            if 12 not in state['used_spaceship_actions']:
                need = 3-player['resources']['qic']
                funding = best_index(scores, [i for i in allowed if actions[i]['type'] == 'FreeAction'
                    and actions[i]['kind'] in ('PowerToQic', 'CreditsToQic')
                    and actions[i].get('count', 1) == need and need > 0])
                if funding is not None:
                    return funding
    return fallback


def goals_for(snapshot):
    state = snapshot['state']
    player = state['players'][snapshot['player']]
    tracks = player['research_tracks']
    goals = [Goal('current-choice')]
    if any(is_advanced(c['action']) for c in snapshot['candidates']):
        goals.append(Goal('available-advanced', payoff='AdvancedTechnology'))
    available = {research_track(state, c['action']) for c in snapshot['candidates']}
    for track in TRACK_KEYS:
        if track not in available:
            continue
        level = tracks[TRACK_KEYS[track]]
        if level >= 5:
            continue
        if track in ('Economy', 'Science'):
            target = 2 if level < 2 else 4 if level < 4 else 5
        elif track in ('Navigation', 'GaiaProject'):
            target = max(2, level+1)
        elif track == 'Terraforming':
            target = 3 if level in (1, 2) else level+1
        else:
            target = level+1
        goals.append(Goal(f'{track}-{target}', ((track, target),),
                          payoff='GaiaFormation' if track == 'GaiaProject' else None))
    if tracks['gaia'] < 2 and tracks['navigation'] < 2 and any(
            h['planet'] and h['planet']['owner'] is None and h['planet']['planet_type'] == 'Transdim'
            for h in state['board']['hexes'].values()):
        goals.extend((Goal('Gaia-then-range', (('GaiaProject', 2), ('Navigation', 2)), payoff='GaiaFormation'),
                      Goal('range-then-Gaia', (('Navigation', 2), ('GaiaProject', 2)), payoff='GaiaFormation')))
    advanced = [(advanced_value(state, player, tile), track, tile)
                for track, tile in zip(TRACK_KEYS, state['research_board']['advanced_tech_tiles'])
                if tile is not None and tracks[TRACK_KEYS[track]] <= 4]
    for _, track, tile in sorted(advanced, reverse=True)[:2]:
        goals.append(Goal(f'advanced-{tile}', ((track, 4),), (track, tile)))
    if (any(board['id'] == 'Rebellion' for board in state['spaceship_boards'])
            and any(h['planet'] and h['planet']['owner'] is None for h in state['board']['hexes'].values())):
        goals.append(Goal('range-then-QIC-tech', (('Navigation', 2),), payoff='RebellionGainTechTile'))
    if state['round'] < 6 and any(tracks[k] == 4 for k in ('economy', 'science')):
        goals.append(Goal('income-before-five', defer_until=state['round']+1))
    return goals


def reached_horizon(state, target_round):
    phase = state['phase']
    return isinstance(phase, dict) and ('Ended' in phase or
        state['round'] >= target_round and 'ActionPhase' in phase)


def forecast(env, snapshot, first, goal, policy, *, limit=MAX_FORECAST_DECISIONS,
             selector=None, achieved=None):
    if limit < 1:
        raise ValueError('Forecast decision limit must be positive')
    actor = snapshot['player']
    start_round = snapshot['state']['round']
    # At R5/R6 finish the game instead of comparing pre-action R6 with final VP.
    target = start_round+2
    if isinstance(policy, CurrentContextTeacher):
        policy.bind(env)
        protected = policy.apply_conservation(snapshot, [(0.0, '')] * len(snapshot['candidates']))
        if blocked(protected[first]):
            return {'complete': False, 'decisions': 0, 'value': None, 'actions': [],
                    'reason': 'conservation policy excludes this first action'}
    branch = env.fork(snapshot['decision_id'], first)
    rngs = [random.Random(f'research-plan:{snapshot["decision_id"]}:{p}') for p in range(4)]
    actions = []
    frames = [{'state': snapshot['state']}]
    completed = False
    last = snapshot
    chosen = snapshot['candidates'][first]['action']
    for step in range(limit):
        current = json.loads(branch.snapshot_json())
        frames.append({'state': current['state'], 'action': chosen, 'player': last['player']})
        if last['player'] == actor:
            before = last['state']['players'][actor]
            after = current['state']['players'][actor]
            actions.append({'round': last['state']['round'], 'action': chosen,
                'resources_before': {k: before['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')},
                'resources_after': {k: after['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')},
                'tracks_after': after['research_tracks'], 'green_after': len(after['federation_tokens'])})
            completed |= bool(goal.payoff and matches_payoff(chosen, goal.payoff))
            completed |= bool(goal.advanced and is_advanced(chosen, goal.advanced))
            if achieved is not None:
                completed |= achieved(current, actor, goal)
        if reached_horizon(current['state'], target):
            # Offline Environment does not append returned events to event_log.
            # Reuse the exact-state/action-verified native income reconstruction,
            # rather than calling a Pass's mixed resource/VP delta "income".
            from replay_income import recover_income
            recovered = recover_income(frames)
            incomes = [event['IncomeReceived'] for events in recovered.values() for event in events
                       if 'IncomeReceived' in event and event['IncomeReceived']['player'] == actor]
            return {'complete': True, 'decisions': step+1, 'round': current['state']['round'],
                    'value': endpoint_value(current['state'], actor, snapshot['state']['players'][actor], policy),
                    'goal_acquired': completed, 'actions': actions, 'incomes': incomes,
                    'end_tracks': current['state']['players'][actor]['research_tracks'],
                    'end_resources': current['state']['players'][actor]['resources']}
        if step+1 == limit:
            break
        if current['player'] == actor:
            if isinstance(policy, CurrentContextTeacher):
                policy.bind(branch)
            scores = policy.rank(current)
            index = (goal_index(current, scores, goal, completed) if selector is None else
                     selector(branch, current, scores, goal, completed))
            if index is None:
                raise ValueError('A forecast has no eligible native decision')
        else:
            index = rngs[current['player']].randrange(len(current['candidates']))
        last = current
        chosen = current['candidates'][index]['action']
        branch.step(current['decision_id'], index)
    return {'complete': False, 'decisions': limit, 'value': None, 'actions': actions,
            'reason': 'forecast decision limit; not a losing route'}


class ResearchPlanTeacher(CurrentActionTeacher):
    """No new legality, rewards or faction-wide script; Xenos stays byte-for-byte ranked."""
    def __init__(self, stage=1):
        super().__init__(stage)
        self.plan_history = []
        self.forecast_policy = CurrentContextTeacher()
        self.on_plan = None

    @ranking_scope()
    def rank(self, snapshot):
        scores = super().rank(snapshot)
        state, player, _ = self.context(snapshot)
        if (player['faction'] != 'HadschHallas' or not isinstance(state['phase'], dict)
                or 'ActionPhase' not in state['phase'] or not any(
                    research_track(state, c['action']) or is_advanced(c['action'])
                    for c in snapshot['candidates'])):
            return scores
        if self.env is None:
            raise ValueError('ResearchPlanTeacher requires a native environment for shared-budget plans')
        plans = []
        for goal in goals_for(snapshot):
            first = goal_index(snapshot, scores, goal)
            if first is None:
                continue
            result = forecast(self.env, snapshot, first, goal, self.forecast_policy)
            plans.append({'goal': goal.name, 'first': first, **result})
        control = next(p for p in plans if p['goal'] == 'current-choice')
        audit = {'decision_id': snapshot['decision_id'], 'round': state['round'],
                 'horizon_incomes': 2, 'opponents': 'common deterministic uniform-random forecast',
                 'plans': plans, 'selected': control['goal'], 'selected_first': control['first']}
        if control['complete']:
            eligible = [p for p in plans if p['complete'] and not blocked(scores[p['first']])]
            winner = max(eligible, key=lambda p: (p['value'], p['goal'] == 'current-choice', -p['first']))
            audit['selected'] = winner['goal']
            audit['selected_first'] = winner['first']
            index = winner['first']
            # Leaf utility is NOT on the old action-score scale. Explicitly select
            # the best sampled plan, retaining legacy ranks only for unexamined actions.
            value = math.nextafter(max(v for v, _ in scores), math.inf)
            reason = (f'two-income native plan={winner["goal"]}; utility={winner["value"]:.3f}; '
                      f'control={control["value"]:.3f}; sampled={len(eligible)}/{len(plans)}; '
                      'opponents/continuation forecast, not guaranteed; ' + scores[index][1])
            scores[index] = (value, reason)
        else:
            audit['fallback'] = 'control did not reach common horizon; preserve current ranks'
        self.plan_history.append(audit)
        if self.on_plan is not None:
            self.on_plan(audit)
        scores = self.apply_conservation(snapshot, scores)
        self.last_scores = scores
        return scores
