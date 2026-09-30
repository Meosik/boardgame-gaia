"""Opt-in, decision-preserving speedups for the shared teacher trees (A and B).

Nothing under a teacher tree is edited. `install()` patches classes of the tree already
on PYTHONPATH, in this process only:

- `fast_copy`: JSON fast path for `copy.deepcopy` (see tools/fast_copy.py).
- `strategy_teacher.distance` memo: a pure function of two "q,r" strings that
  re-parsed both on each of hundreds of thousands of calls per rollout. Patched before
  any other module runs `from strategy_teacher import distance`.
- `IntegratedTeacher.waiting_value` memo. The method reads the state, the acting
  player, the number of satellites and the token of a FormFederation candidate, and
  nothing else. Candidates differing only in planet set or satellite positions (most of
  the federation list) therefore share one result per ranked state. Entries are keyed by
  object identity and hold strong references, so an id is never reused while cached;
  ranked states and players are not mutated in place (see scoring_cache.decision_scope).

Equivalence is checked on whole rollouts and match traces (cycle 016).
"""
from functools import lru_cache
import json

_MAX_ENTRIES = 50_000
_waiting = {}


def _memo_waiting_value(original):
    def waiting_value(self, state, player, action):
        key = (type(self), id(state), id(player), len(action['satellite_hexes']),
               json.dumps(action['token'], sort_keys=True))
        hit = _waiting.get(key)
        if hit is not None and hit[0] is state and hit[1] is player:
            return hit[2]
        value = original(self, state, player, action)
        if len(_waiting) >= _MAX_ENTRIES:
            _waiting.clear()
        _waiting[key] = (state, player, value)
        return value
    waiting_value.__wrapped__ = original
    return waiting_value


def install():
    """Call before any teacher module is imported (distance is bound at import); idempotent."""
    import fast_copy
    fast_copy.install()
    import strategy_teacher
    if not hasattr(strategy_teacher.distance, 'cache_info'):
        strategy_teacher.distance = lru_cache(maxsize=None)(strategy_teacher.distance)
    from integrated.teacher import IntegratedTeacher
    if not hasattr(IntegratedTeacher.waiting_value, '__wrapped__'):
        IntegratedTeacher.waiting_value = _memo_waiting_value(IntegratedTeacher.waiting_value)
