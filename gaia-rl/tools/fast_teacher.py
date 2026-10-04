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
- `NativeFactionTeacher` previews (Terrans/Taklons): non-free-action candidates are ranked
  from `preview_state_json` instead of a full fork (see `_PreviewForks`); Taklons with 259
  federation candidates rank in 0.46 s instead of 1.08 s (tools/test_fast_teacher.py).

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


class _StateOnlyBranch:
    """A previewed candidate: its exact post-move state, without the next decision's candidates."""
    __slots__ = ('_json',)

    def __init__(self, state_json):
        self._json = '{"state":' + state_json + '}'

    def snapshot_json(self):
        return self._json

    def fork(self, *_):
        raise RuntimeError('a state-only preview has no candidates to fork')


class _PreviewForks:
    """Environment proxy for `NativeFactionTeacher.rank`.

    The ranking forks every root candidate (step = apply the move and the automatic transitions,
    then enumerate the NEXT decision's candidates) but, except for free actions (whose follow-up
    funding sample and QIC proofs read the branch's candidates), reads only the resulting state.
    `Environment.preview_state_json` computes that same state without the candidate enumeration,
    which for 250+ federation or upgrade candidates is most of the ranking time. Free actions
    still get a real fork. Only failure behaviour differs: a fork whose NEXT candidate generation
    fails raised, the preview does not (no decision is affected).
    """
    __slots__ = ('_env', '_types')

    def __init__(self, env):
        self._env = env
        self._types = (None, None)

    def __getattr__(self, name):
        return getattr(self._env, name)

    def _type(self, decision_id, index):
        if self._types[0] != decision_id:
            snapshot = json.loads(self._env.snapshot_json())
            self._types = (snapshot['decision_id'],
                           [c['action'].get('type') if isinstance(c.get('action'), dict) else None
                            for c in snapshot['candidates']])
        return self._types[1][index]

    def fork(self, decision_id, index):
        if self._type(decision_id, index) == 'FreeAction':
            return self._env.fork(decision_id, index)
        return _StateOnlyBranch(self._env.preview_state_json(decision_id, index))


def _preview_bind(original):
    def bind(self, env):
        if env is not None and not isinstance(env, _PreviewForks):
            env = _PreviewForks(env)
        return original(self, env)
    bind.__wrapped__ = original
    return bind


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
    from four_factions.teacher import NativeFactionTeacher
    if not hasattr(NativeFactionTeacher.bind, '__wrapped__'):
        NativeFactionTeacher.bind = _preview_bind(NativeFactionTeacher.bind)
