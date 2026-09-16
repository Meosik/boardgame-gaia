"""Shared paid search; existing quartet rankings remain unchanged."""
from dataclasses import asdict

from four_factions.timed import TimedPreparationTeacher
from .profiles import profiles


class SharedTeacher(TimedPreparationTeacher):
    def __init__(self, seed, *, prefix=(), target_seconds=60, maximum_seconds=300, adaptive_clock=None):
        if adaptive_clock is not None:
            target_seconds, maximum_seconds = adaptive_clock.target_seconds, adaptive_clock.long_seconds
        super().__init__(seed, prefix=prefix, target_seconds=target_seconds,
                         maximum_seconds=maximum_seconds, bgg_openings=True, shared_factions=True,
                         adaptive_clock=adaptive_clock)

    def choose(self, snapshot):
        unsupported = {p['faction'] for p in snapshot['state']['players']} - profiles().keys()
        if unsupported:
            raise ValueError(f'No approved shared teacher profile for {sorted(unsupported)}')
        decision = super().choose(snapshot)
        faction = snapshot['state']['players'][snapshot['player']]['faction']
        profile = profiles()[faction]
        self.last_audit['faction_profile'] = {k: v for k, v in asdict(profile).items() if k != 'openings'}
        return decision
