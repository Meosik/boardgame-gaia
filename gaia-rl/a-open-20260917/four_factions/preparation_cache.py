"""Bounded exact results, shared only by branches of one native search root."""
import json
import sys

Scores = list[tuple[float, str]]
Commitments = dict[str, list[str]]


class PolicyCache:
    def __init__(self, *, max_entries: int = 128, max_bytes: int = 8 * 1024 * 1024):
        if max_entries < 0 or max_bytes < 0:
            raise ValueError('Cache limits must be nonnegative')
        self.max_entries = max_entries
        self.max_bytes = max_bytes
        self._entries: dict[str, str] = {}
        self.bytes_used = 0
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> tuple[Scores, Commitments] | None:
        value = self._entries.get(key)
        if value is None:
            self.misses += 1
            return None
        self.hits += 1
        scores, memory = json.loads(value)
        return [(value, reason) for value, reason in scores], memory

    def put(self, key: str, scores: Scores, memory: Commitments) -> None:
        if key in self._entries or len(self._entries) >= self.max_entries:
            return
        value = json.dumps((scores, memory), separators=(',', ':'), allow_nan=False)
        # Strings own the full payload; reads cannot share mutable commitments.
        # Include conservative per-entry dictionary overhead in the byte budget.
        size = sys.getsizeof(key) + sys.getsizeof(value) + 128
        if self.bytes_used + size <= self.max_bytes:
            self._entries[key] = value
            self.bytes_used += size

    def stats(self) -> dict[str, int]:
        return {'hits': self.hits, 'misses': self.misses, 'entries': len(self._entries),
                'bytes_used': self.bytes_used, 'max_entries': self.max_entries,
                'max_bytes': self.max_bytes}
