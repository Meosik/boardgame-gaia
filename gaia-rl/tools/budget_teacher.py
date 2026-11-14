"""Deterministic search budget for the timed teachers: a comparison count, not a clock.

`TimedPreparationTeacher.choose` publishes whatever its search subprocess finished
before a wall-clock deadline and falls back to a one-step quick reserve when even
the root ranking is late. The same seed therefore replays differently, and a
slower evaluation silently becomes a shallower one.

`install(comparisons)` replaces that method, for the current process only, with an
in-process call of the tree's own `four_factions.preparation.search`:

- the root ranking always completes (there is no quick fallback);
- the search stops after `comparisons` completed horizon comparisons, or earlier on
  its own deterministic rules (fast reasons, convergence, coverage); 0 keeps only
  the complete root ranking (the teacher's one-step policy);
- no deadline is consulted, so equal inputs give equal decisions.

Candidate generation, rollout policies, leaf evaluation and plan memory are the
teacher tree's unchanged code. Nothing under a teacher tree is edited; the source
tree is still chosen by PYTHONPATH.
"""
import inspect
import json
import math
import sys
import time

_installed = None
_max_seconds = None
_distinct_firsts = False


def count_distinct_firsts(enabled):
    """Count a comparison toward the budget only when its first move is new (distinct_search)."""
    global _distinct_firsts
    _distinct_firsts = bool(enabled)


stages = {}            # seconds per stage of the current decision (115e): _choose and parallel_search add to it


def add_stage(name, seconds):
    """Timing only, never read by the search: where one decision's wall time went (decision log 'timing')."""
    stages[name] = stages.get(name, 0.0)+seconds


budget_hooks = []      # f(snapshot, scores, budget) -> budget; a patch may widen one decision's budget
max_seconds_hooks = []  # f(snapshot, seconds) -> seconds; a patch may widen one decision's safety cap


def budget_for(snapshot, scores, budget=None):
    """The comparison budget of this decision: the installed count passed through budget_hooks. `scores` is the root
    ranking (search publishes it with its first result; parallel_search has it after Policies.rank)."""
    budget = _installed if budget is None else budget
    for hook in budget_hooks:
        budget = hook(snapshot, scores, budget)
    return budget


def _spent(plans):
    return len({p['first'] for p in plans}) if _distinct_firsts else len(plans)


def _root_result(self, snapshot, kwargs):
    """The search's first published result — the complete root ranking and its choice ('local-baseline') — with no
    deadline and no comparison. Used when the safety cap passed before the search could publish anything."""
    from four_factions.preparation import SearchExpired, search
    first = []

    def publish(result):
        first.append(json.loads(json.dumps(result, allow_nan=False)))
        raise SearchExpired('root ranking only')

    parallel = sys.modules.get('parallel_search')
    if parallel is not None:
        parallel._state['no_prefetch'] = True   # nothing goes to the pool; rank still reuses the ranking _prefetch cached
    try:
        search(self.env, snapshot, self.memory, publish, **{**kwargs, 'hard_deadline': math.inf})
    except SearchExpired:
        if not first:
            raise
    finally:
        if parallel is not None:
            parallel._state['no_prefetch'] = False
    return first[0] if first else None


def _choose(self, snapshot):
    from four_factions.preparation import SearchExpired, search
    started = time.monotonic()
    stages.clear()
    if self.env is None or json.loads(self.env.snapshot_json()) != snapshot:
        raise ValueError('Budget teacher must be bound to the current native snapshot')
    if snapshot['steps'] != len(self.prefix):
        raise ValueError('Missing native actions; cannot reconstruct plan memory')
    add_stage('bind_check', time.monotonic()-started)
    budget = _installed
    state = {'latest': None, 'stopped': False}
    published = []     # seconds since `started` of every published result (the first is the root ranking)

    def publish(result):
        nonlocal budget
        published.append(round(time.monotonic()-started, 3))
        # Round-trip exactly like the subprocess worker's JSON hand-off.
        state['latest'] = json.loads(json.dumps(result, allow_nan=False))
        budget = budget_for(snapshot, result.get('scores'), _installed)
        if not state['stopped'] and _spent(result.get('plans', ())) >= budget:
            state['stopped'] = True
            raise SearchExpired('comparison budget reached')

    # Optional wall-clock safety cap: the root ranking always completes, then an unfinished
    # comparison is abandoned at the cap and the best completed result is kept.
    cap = _max_seconds
    for hook in max_seconds_hooks:
        cap = hook(snapshot, cap)
    hard_deadline = math.inf if cap is None else started+cap
    kwargs = dict(soft_deadline=math.inf, hard_deadline=hard_deadline, bgg_openings=self.bgg_openings,
                  shared_factions=self.shared_factions, adaptive=True, allocation=None,
                  delta_factions=self.delta_factions, fixed_openings=self.fixed_openings,
                  observed_factions=self.observed_factions)
    if 'faction_tech_plans' in inspect.signature(search).parameters:
        kwargs['faction_tech_plans'] = self.faction_tech_plans
    mark = time.monotonic()
    try:
        search(self.env, snapshot, self.memory, publish, **kwargs)
    except SearchExpired:
        add_stage('search_call', time.monotonic()-mark)
        mark = None
        if state['latest'] is None:
            retry = time.monotonic()
            # 114 (pair-012 step 224, pair-037 step 111): the cap passed before the frozen search started. With
            # parallel_search the root ranking runs first in _prefetch, and in pair-012 that ranking took 69 s
            # (each OreToPower fork enumerated 17,318 federations, 7 s a fork), so the search's entry check
            # expired with nothing published and the worker died. Keep the promise above — the root ranking
            # always completes: play its choice, the search's first published result, with no comparison.
            state['latest'] = _root_result(self, snapshot, kwargs)
            state['expired_before_search'] = True
            add_stage('root_result', time.monotonic()-retry)
    if mark is not None:
        add_stage('search_call', time.monotonic()-mark)
    latest = state['latest']
    if latest is None:
        raise RuntimeError('Search returned without publishing a ranked decision')
    mark = time.monotonic()
    if json.loads(self.env.snapshot_json()) != snapshot:
        raise ValueError('Parent native state changed during in-process search')
    add_stage('state_check', time.monotonic()-mark)
    index = latest['index']
    if (latest['decision_id'] != snapshot['decision_id'] or type(index) is not int
            or not 0 <= index < len(snapshot['candidates'])):
        raise ValueError('Search result does not belong to the current native decision')
    self.memory = latest['memory']
    self.last_scores = [tuple(score) for score in latest['scores']]
    elapsed = time.monotonic()-started
    self.times[str(snapshot['player'])].append(elapsed)
    self.last_audit = {**{k: v for k, v in latest.items() if k != 'memory'}, 'selected_index': index,
                       'ranking_mode': 'control', 'value_model': 'control',
                       'comparison_budget': budget,
                       'completed_comparisons': len(latest.get('plans', ())),
                       'budget_stopped': state['stopped'],
                       'time_capped': (cap is not None and not state['stopped']
                                       and time.monotonic() >= hard_deadline),
                       'expired_before_search': bool(state.get('expired_before_search')
                                                     or latest.get('expired_before_search')),
                       'timing': {'seconds': elapsed, 'quick_fallback_used': False,
                                  'cap': cap if cap is None or math.isfinite(cap) else None,
                                  'published_at': published,
                                  'stages': {name: round(seconds, 3) for name, seconds in stages.items()}}}
    return snapshot['decision_id'], index


def set_horizon(incomes):
    """Compare every route at the first (1) or second (2, the teacher's own) income boundary.

    The rollout stops when `reached_horizon(state, round+2)`; with 1 the check uses
    round+1 instead, for the baseline route and every alternative alike, so all
    comparisons still end at one shared boundary. This changes decisions and must be
    judged by matches. Late-game routes then stop at the next round instead of game end.
    """
    if incomes not in (1, 2):
        raise ValueError('horizon_incomes must be 1 or 2')
    import four_factions.preparation as preparation
    original = getattr(preparation.reached_horizon, '__wrapped__', preparation.reached_horizon)
    if incomes == 2:
        preparation.reached_horizon = original
        return

    def reached_horizon(state, target_round):
        return original(state, target_round-1)
    reached_horizon.__wrapped__ = original
    preparation.reached_horizon = reached_horizon


def install(comparisons, max_seconds=None):
    """Patch the tree's TimedPreparationTeacher in this process; subclasses inherit it.

    `max_seconds` adds a safety cap for live play. Decisions that hit it are no longer
    deterministic (they depend on machine speed); all others are unchanged.
    """
    global _installed, _max_seconds
    if max_seconds is not None and not (isinstance(max_seconds, (int, float)) and max_seconds > 0):
        raise ValueError('max_seconds must be positive')
    _max_seconds = max_seconds
    if type(comparisons) is not int or comparisons < 0:
        raise ValueError('A nonnegative integer comparison budget is required')
    from four_factions.timed import TimedPreparationTeacher
    _installed = comparisons
    TimedPreparationTeacher.choose = _choose
