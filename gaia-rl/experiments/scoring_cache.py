"""Bounded, context-local memoization; never changes the searched plans or RNG."""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy
from dataclasses import dataclass, field
from functools import wraps
import json
import sys
from typing import Callable, Hashable, TypeVar, cast

T = TypeVar('T')
_enabled = ContextVar('scoring_cache_enabled', default=True)


@dataclass
class DecisionCache:
    state: object
    max_entries: int = 4096
    entries: dict[tuple[Hashable, Hashable], object] = field(default_factory=dict)
    hits: int = 0

    def compute(self, namespace: Hashable, key: Hashable, calculate: Callable[[], T]) -> T:
        identity = (namespace, key)
        if identity in self.entries:
            self.hits += 1
            return copy(cast(T, self.entries[identity]))
        value = calculate()
        if len(self.entries) < self.max_entries:
            self.entries[identity] = copy(value)
        return value


_decision: ContextVar[DecisionCache | None] = ContextVar('decision_cache', default=None)


@contextmanager
def decision_scope(state: object, *, max_entries: int = 4096):
    """State stays immutable inside ranking; prospective player copies may differ."""
    previous = _decision.get()
    if not _enabled.get() or previous is not None and previous.state is state:
        yield previous
        return
    cache = DecisionCache(state, max_entries)
    token = _decision.set(cache)
    try:
        yield cache
    finally:
        _decision.reset(token)
        cache.entries.clear()


def reuse(state: object, namespace: Hashable, key: Hashable, calculate: Callable[[], T]) -> T:
    cache = _decision.get()
    if not _enabled.get() or cache is None or cache.state is not state:
        return calculate()
    return cache.compute(namespace, key, calculate)


def memoized(namespace: str, key: Callable[..., Hashable]):
    """For flat value objects only: lists of coordinates, scalar costs or numbers."""
    def decorate(function):
        @wraps(function)
        def wrapped(state, *args, **kwargs):
            cache = _decision.get()
            if not _enabled.get() or cache is None or cache.state is not state:
                return function(state, *args, **kwargs)
            return cache.compute(namespace, key(*args, **kwargs),
                                 lambda: function(state, *args, **kwargs))
        return wrapped
    return decorate


@dataclass
class RankingCache:
    max_entries: int = 128
    max_bytes: int = 8 * 1024 * 1024
    entries: dict[str, tuple[tuple[float, str], ...]] = field(default_factory=dict)
    bytes_used: int = 0
    hits: int = 0


_rankings: ContextVar[RankingCache | None] = ContextVar('ranking_cache', default=None)


@contextmanager
def ranking_scope(*, max_entries: int = 128, max_bytes: int = 8 * 1024 * 1024):
    """Share deterministic context scores only within one real planning decision."""
    previous = _rankings.get()
    if not _enabled.get() or previous is not None:
        yield previous
        return
    cache = RankingCache(max_entries, max_bytes)
    token = _rankings.set(cache)
    try:
        yield cache
    finally:
        _rankings.reset(token)
        cache.entries.clear()
        cache.bytes_used = 0


def shared_rank(snapshot: dict, calculate: Callable[[], list[tuple[float, str]]]) -> list[tuple[float, str]]:
    cache = _rankings.get()
    if not _enabled.get() or cache is None:
        return calculate()
    # Include the whole snapshot and candidate order, not just a turn/seed/first move.
    key = json.dumps(snapshot, separators=(',', ':'), ensure_ascii=False)
    if key in cache.entries:
        cache.hits += 1
        return list(cache.entries[key])
    scores = calculate()
    stored = tuple(scores)
    size = sys.getsizeof(key) + sys.getsizeof(stored)
    size += sum(sys.getsizeof(pair) + sys.getsizeof(pair[0]) + sys.getsizeof(pair[1]) for pair in stored)
    if len(cache.entries) < cache.max_entries and cache.bytes_used + size <= cache.max_bytes:
        cache.entries[key] = stored
        cache.bytes_used += size
    return scores


@contextmanager
def uncached():
    """Diagnostic control: identical computation without any of these caches."""
    token = _enabled.set(False)
    try:
        yield
    finally:
        _enabled.reset(token)
