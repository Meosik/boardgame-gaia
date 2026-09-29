"""Opt-in speedup for teacher trees: a JSON-data fast path for `copy.deepcopy`.

The teachers copy parsed game-state dictionaries (player records, resources) tens of
thousands of times per rollout. `copy.deepcopy` pays for a memo table, `__reduce__`
dispatch and alias tracking that plain JSON data never needs.

`install()` replaces `copy.deepcopy` in this process before the teacher modules are
imported (so `from copy import deepcopy` also binds the fast version). dict, list and
tuple containers are rebuilt recursively and str/int/float/bool/None are shared, exactly
as `copy.deepcopy` treats them. Any other type is handed to the original `deepcopy`.

The one behavioural difference is aliasing: if the same list/dict object appears twice
inside one copied value, `copy.deepcopy` keeps one shared copy, this makes two. Parsed
JSON has no aliases; equivalence of whole teacher decisions is checked by
`tools/test_fast_copy.py` and by identical match traces (cycle 017).
"""
import copy

_original = copy.deepcopy
_ATOMS = (str, int, float, bool, type(None))


def fast_deepcopy(value, memo=None, _nil=None):
    if memo is not None:
        # Called from inside another object's __deepcopy__: keep full semantics.
        return _original(value, memo)
    return _copy(value)


def _copy(value):
    kind = type(value)
    if kind is dict:
        return {k: _copy(v) for k, v in value.items()}
    if kind is list:
        return [_copy(v) for v in value]
    if kind in _ATOMS:
        return value
    if kind is tuple:
        return tuple(_copy(v) for v in value)
    return _original(value)


def install():
    """Patch before importing teacher modules; idempotent."""
    copy.deepcopy = fast_deepcopy
