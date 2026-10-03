"""Run a decision's comparisons in parallel processes without changing the decision.

The teacher's `four_factions.preparation.search` compares routes one after another: a route's
first move (`select_goal`) and its rollout to the horizon. Each comparison clones the search's
policies and never changes the parent's state, so the comparisons of one decision are
independent. Before the search starts, this predicts its task list (the same construction as
`search`), computes the first `budget` comparisons in worker processes, and lets the unchanged
sequential search take each finished result instead of recomputing it.

Correctness never depends on the prediction: a result is used only for the same position,
goal, first move and policy memory; anything else falls back to the ordinary sequential call.
`tools/test_parallel_search.py` checks that whole games make identical decisions with and
without it. Workers are forked after the teacher patches are installed, so they run the same
code; the configured horizon is passed with every task.

install(processes) once per process, after the teacher factory has run.
"""
import copy
import json
import math
import multiprocessing
import time

_state = {'pool': None, 'processes': 0, 'prefetch': None, 'root': None, 'horizon': 1}


def _key(snapshot):
    return json.dumps([snapshot['decision_id'], snapshot['steps']])


def _memory_key(memory):
    return json.dumps({k: v for k, v in memory.items() if k != '_plans'}, sort_keys=True)


# ── worker side ───────────────────────────────────────────────────────────────────────

def _compute(job):
    """In a worker: rebuild the position, choose the route's first move, roll it out."""
    import budget_teacher
    from gaia_rl import Environment
    import four_factions.preparation as preparation
    from four_factions.preparation import Policies, PolicyCache, goal_from_dict
    state_json, memory, scores, goal_dict, settings, capture_r1, horizon = job
    budget_teacher.set_horizon(horizon)
    env = Environment.from_state_json(state_json, 2000)
    snapshot = json.loads(env.snapshot_json())
    policies = Policies(memory, cache=PolicyCache(), **settings)
    goal = goal_from_dict(goal_dict)
    first = goal.first
    if first is None:
        select = getattr(preparation.select_goal, '__wrapped__', preparation.select_goal)
        first = select(env, snapshot, scores, goal, policies, math.inf)
    if capture_r1:
        result = preparation.rollout(env, snapshot, first, goal, policies, math.inf, capture_r1=True)
    else:
        result = preparation.rollout(env, snapshot, first, goal, policies, math.inf)
    return first, result


# ── parent side ───────────────────────────────────────────────────────────────────────

def _planned_tasks(env, snapshot, memory, scores, policies, kwargs):
    """`search`'s task list, rebuilt from the same tree functions (prediction only)."""
    from dataclasses import replace  # noqa: F401  (kept parallel to search's imports)
    import four_factions.preparation as p
    from four_factions.preparation import Goal, best_index, blocked, goal_from_dict
    control_first = best_index(scores, range(len(scores)))
    opening_goals = []
    actor_key = str(snapshot.get('player'))
    bgg = kwargs.get('bgg_openings', False)
    if kwargs.get('fixed_openings'):
        from bgg_openings.fixed import TARGETS
        if snapshot['state']['players'][snapshot['player']]['faction'] in TARGETS:
            bgg = False
    capture = False
    if bgg and snapshot['state']['round'] <= 1:
        from bgg_openings.catalog import load_catalog
        from bgg_openings.planning import goals as bgg_goals
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        capture = bool(load_catalog().get(faction, ()))
        remembered = policies.memory.get('_bgg_targets', {}).get(actor_key)
        opening_goals = bgg_goals(snapshot, remembered)
    control = Goal('current-choice', first=control_first)
    faction = snapshot['state']['players'][snapshot['player']]['faction']
    delta = policies.delta_factions
    observed_factions = kwargs.get('observed_factions', ())
    proposals = p.goals_for(snapshot, shared_factions=kwargs.get('shared_factions', False),
                            guide_tracks=bool(delta) and faction in delta,
                            observed=bool(observed_factions) and faction in observed_factions)
    goals = p.interleave_families(proposals, lambda goal: goal.family)
    saved = policies.memory.get('_plans', {}).get(str(snapshot.get('player')))
    if saved:
        previous = goal_from_dict(saved)
        if p.viable(snapshot, snapshot['player'], previous) and not p.achieved(snapshot, snapshot['player'], previous):
            goals.insert(0, previous)
    paired = p.scoring_pairs(snapshot, scores, goals)
    roots = [Goal(f'root-{i}', 'root', first=i)
             for i in sorted(range(len(scores)), key=lambda i: (-scores[i][0], i))
             if not blocked(scores[i]) and i != control_first]
    interleaved = p.interleave_families(roots, lambda goal: snapshot['candidates'][goal.first]['action']['type'])
    tasks = [] if opening_goals else [control]
    for i in range(max(len(goals), len(interleaved), len(paired), len(opening_goals))):
        if i < len(opening_goals):
            tasks.append(opening_goals[i])
        if i == 0 and opening_goals:
            tasks.append(control)
        if i < len(goals):
            tasks.append(goals[i])
        if i < len(interleaved):
            tasks.append(interleaved[i])
        if i < len(paired):
            tasks.append(paired[i])
    return tasks, capture


def _prefetch(env, snapshot, memory, budget, kwargs):
    from dataclasses import asdict
    import four_factions.preparation as p
    from four_factions.preparation import Policies, PolicyCache
    phase = snapshot['state']['phase']
    phases = ('ActionPhase', 'Setup', 'TinkeroidsTileSelectionPending') if kwargs.get('shared_factions') else ('ActionPhase', 'Setup')
    if budget < 2 or not isinstance(phase, dict) or not any(k in phase for k in phases):
        return
    settings = {'shared_factions': kwargs.get('shared_factions', False),
                'delta_factions': kwargs.get('delta_factions', ()),
                'fixed_openings': kwargs.get('fixed_openings', False)}
    policies = Policies(memory, cache=PolicyCache(), **settings)
    memory_before = _memory_key(policies.memory)
    scores = p.Policies.rank.__wrapped__(policies, env, snapshot)
    _state['root'] = (_key(snapshot), memory_before, scores, copy.deepcopy(policies.memory))
    tasks, capture = _planned_tasks(env, snapshot, policies.memory, scores, policies, kwargs)
    state_json = json.dumps(snapshot['state'])
    memory_after = _memory_key(policies.memory)
    # A patch may compare one decision at another boundary (teacher_patches.decision_horizon).
    try:
        from teacher_patches import decision_horizon
        horizon = decision_horizon(snapshot) or _state['horizon']
    except ImportError:
        horizon = _state['horizon']
    pending = {}
    for goal in tasks[:budget]:
        job = (state_json, policies.memory, scores, asdict(goal), settings, capture, horizon)
        pending[goal] = _state['pool'].apply_async(_compute, (job,))
    _state['prefetch'] = (_key(snapshot), memory_after, pending)


def _lookup(snapshot, goal, policies):
    prefetch = _state['prefetch']
    if prefetch is None or prefetch[0] != _key(snapshot) or goal not in prefetch[2]:
        return None
    if prefetch[1] != _memory_key(policies.memory):
        return None
    return prefetch[2][goal]


def install(processes):
    """Patch the tree in this process; `processes` < 2 disables (sequential search).

    Idempotent: a teacher factory may re-install its own wrappers later (one per AI room), so
    every call re-checks each hook and wraps only what is not wrapped yet.
    """
    import budget_teacher
    import four_factions.preparation as p
    _state['processes'] = processes
    if processes < 2:
        return
    if _state['pool'] is None:
        _state['pool'] = multiprocessing.get_context('fork').Pool(processes)

    if not getattr(p.Policies.rank, '_parallel', False):
        original_rank = p.Policies.rank

        def rank(self, env, snapshot):
            root = _state['root']
            if root is not None and root[0] == _key(snapshot) and root[1] == _memory_key(self.memory):
                _state['root'] = None
                self.memory = copy.deepcopy(root[3])
                return root[2]
            return original_rank(self, env, snapshot)
        rank.__wrapped__ = original_rank
        rank._parallel = True
        p.Policies.rank = rank

    if not getattr(p.select_goal, '_parallel', False):
        original_select = p.select_goal

        def select_goal(env, snapshot, scores, goal, policies, deadline):
            future = _lookup(snapshot, goal, policies)
            if future is not None:
                return future.get()[0]
            return original_select(env, snapshot, scores, goal, policies, deadline)
        select_goal.__wrapped__ = original_select
        select_goal._parallel = True
        p.select_goal = select_goal

    if not getattr(p.rollout, '_parallel', False):
        inner_rollout = p.rollout

        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            future = _lookup(snapshot, goal, policies)
            if future is not None:
                wait = None if deadline == math.inf else max(0.0, deadline-time.monotonic())
                try:
                    cached_first, result = future.get(wait)
                except multiprocessing.TimeoutError:
                    raise p.SearchExpired('parallel comparison passed the deadline')
                if cached_first == first:
                    return result
            return inner_rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs)
        # Other patches (e.g. the Geodens look-ahead) unwrap `__wrapped__` to find the tree's
        # rollout, so keep exposing it rather than the wrapper underneath.
        rollout.__wrapped__ = getattr(inner_rollout, '__wrapped__', inner_rollout)
        rollout._inner = inner_rollout
        rollout._parallel = True
        p.rollout = rollout

    if not getattr(p.search, '_parallel', False):
        original_search = p.search

        def search(env, snapshot, memory, publish, **kwargs):
            try:
                _prefetch(env, snapshot, memory, budget_teacher._installed or 0, kwargs)
                return original_search(env, snapshot, memory, publish, **kwargs)
            finally:
                _state['prefetch'] = None
                _state['root'] = None
        search._parallel = True
        p.search = search

    if not getattr(budget_teacher.set_horizon, '_parallel', False):
        original_set_horizon = budget_teacher.set_horizon

        def set_horizon(incomes):
            _state['horizon'] = incomes
            return original_set_horizon(incomes)
        set_horizon._parallel = True
        budget_teacher.set_horizon = set_horizon
