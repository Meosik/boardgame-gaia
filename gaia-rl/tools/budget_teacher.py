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
import time

_installed = None


def _choose(self, snapshot):
    from four_factions.preparation import SearchExpired, search
    started = time.monotonic()
    if self.env is None or json.loads(self.env.snapshot_json()) != snapshot:
        raise ValueError('Budget teacher must be bound to the current native snapshot')
    if snapshot['steps'] != len(self.prefix):
        raise ValueError('Missing native actions; cannot reconstruct plan memory')
    budget = _installed
    state = {'latest': None, 'stopped': False}

    def publish(result):
        # Round-trip exactly like the subprocess worker's JSON hand-off.
        state['latest'] = json.loads(json.dumps(result, allow_nan=False))
        if not state['stopped'] and len(result.get('plans', ())) >= budget:
            state['stopped'] = True
            raise SearchExpired('comparison budget reached')

    kwargs = dict(soft_deadline=math.inf, hard_deadline=math.inf, bgg_openings=self.bgg_openings,
                  shared_factions=self.shared_factions, adaptive=True, allocation=None,
                  delta_factions=self.delta_factions, fixed_openings=self.fixed_openings,
                  observed_factions=self.observed_factions)
    if 'faction_tech_plans' in inspect.signature(search).parameters:
        kwargs['faction_tech_plans'] = self.faction_tech_plans
    try:
        search(self.env, snapshot, self.memory, publish, **kwargs)
    except SearchExpired:
        if state['latest'] is None:
            raise
    latest = state['latest']
    if latest is None:
        raise RuntimeError('Search returned without publishing a ranked decision')
    if json.loads(self.env.snapshot_json()) != snapshot:
        raise ValueError('Parent native state changed during in-process search')
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
                       'timing': {'seconds': elapsed, 'quick_fallback_used': False}}
    return snapshot['decision_id'], index


def install(comparisons):
    """Patch the tree's TimedPreparationTeacher in this process; subclasses inherit it."""
    global _installed
    if type(comparisons) is not int or comparisons < 0:
        raise ValueError('A nonnegative integer comparison budget is required')
    from four_factions.timed import TimedPreparationTeacher
    _installed = comparisons
    TimedPreparationTeacher.choose = _choose
