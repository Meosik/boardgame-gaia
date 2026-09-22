"""Evaluate distinct goals together while sharing identical native action prefixes.

No beam pruning, new depth limit, changed RNG, or merged nonidentical histories.
The tree lives only during this ranking call; parents are never stepped in place.
"""
import copy
import json
import random

from current_actions.conservation import blocked
from current_actions.teacher import CurrentContextTeacher
from research_plans.teacher import (MAX_FORECAST_DECISIONS, is_advanced,
                                   matches_payoff, reached_horizon)
from research_plans.value import endpoint_value


def forecast_many(env, snapshot, tasks, selector, achieved, *, limit=MAX_FORECAST_DECISIONS,
                  summarize=None, finish_game=False):
    if limit < 1:
        raise ValueError('Forecast decision limit must be positive')
    actor = snapshot['player']
    target = 7 if finish_game else snapshot['state']['round'] + 2
    root_policy = CurrentContextTeacher().bind(env)
    protected = root_policy.apply_conservation(snapshot, [(0.0, '')] * len(snapshot['candidates']))
    results = [None] * len(tasks)
    stats = {'native_prefix_steps': 0, 'context_rank_calls': 0, 'income_reconstructions': 0}
    rngs = [random.Random(f'research-plan:{snapshot["decision_id"]}:{p}') for p in range(4)]

    def visit(parent_env, before, index, group, frames, actions, inherited, streams, depth):
        branch = parent_env.fork(before['decision_id'], index)
        current = json.loads(branch.snapshot_json())
        stats['native_prefix_steps'] += 1
        chosen = before['candidates'][index]['action']
        frames = frames + [{'state': current['state'], 'action': chosen, 'player': before['player']}]
        policy = CurrentContextTeacher().bind(branch)
        policy._conservation = copy.deepcopy(inherited)
        if before['player'] == actor:
            p, q = before['state']['players'][actor], current['state']['players'][actor]
            actions = actions + [{'round': before['state']['round'], 'action': chosen,
                'resources_before': {k: p['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')},
                'resources_after': {k: q['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')},
                'tracks_after': q['research_tracks'], 'green_after': len(q['federation_tokens'])}]
            group = [(task, done or bool(goal.payoff and matches_payoff(chosen, goal.payoff))
                      or bool(goal.advanced and is_advanced(chosen, goal.advanced))
                      or achieved(current, actor, goal))
                     for task, done in group for goal, _ in [tasks[task]]]
        if reached_horizon(current['state'], target):
            from replay_income import recover_income
            recovered = recover_income(frames)
            stats['income_reconstructions'] += 1
            incomes = [e['IncomeReceived'] for events in recovered.values() for e in events
                       if 'IncomeReceived' in e and e['IncomeReceived']['player'] == actor]
            value = endpoint_value(current['state'], actor, snapshot['state']['players'][actor], policy)
            diagnostics = {} if summarize is None else {
                'diagnostics': summarize(current['state'], actor, frames)}
            for task, done in group:
                results[task] = {'complete': True, 'decisions': depth, 'round': current['state']['round'],
                    'value': value, 'goal_acquired': done, 'actions': actions, 'incomes': incomes,
                    'end_tracks': current['state']['players'][actor]['research_tracks'],
                    'end_resources': current['state']['players'][actor]['resources'], **diagnostics}
            return
        if depth == limit:
            for task, _ in group:
                results[task] = {'complete': False, 'decisions': limit, 'value': None, 'actions': actions,
                                 'reason': 'forecast decision limit; not a losing route'}
            return
        children = {}
        if current['player'] == actor:
            scores = policy.rank(current)
            stats['context_rank_calls'] += 1
            for task, done in group:
                next_index = selector(branch, current, scores, tasks[task][0], done)
                if next_index is None:
                    raise ValueError('A forecast has no eligible native decision')
                if blocked(scores[next_index]):
                    raise ValueError('A selector bypassed conservation')
                children.setdefault(next_index, []).append((task, done))
        else:
            streams = copy.deepcopy(streams)
            next_index = streams[current['player']].randrange(len(current['candidates']))
            children[next_index] = group
        for next_index, next_group in children.items():
            visit(branch, current, next_index, next_group, frames, actions,
                  policy._conservation, streams, depth+1)

    roots = {}
    for task, (_, first) in enumerate(tasks):
        if blocked(protected[first]):
            results[task] = {'complete': False, 'decisions': 0, 'value': None, 'actions': [],
                            'reason': 'conservation policy excludes this first action'}
        else:
            roots.setdefault(first, []).append((task, False))
    for first, group in roots.items():
        visit(env, snapshot, first, group, [{'state': snapshot['state']}], [],
              root_policy._conservation, rngs, 1)
    stats['independent_prefix_steps'] = sum(r['decisions'] for r in results)
    return results, stats
