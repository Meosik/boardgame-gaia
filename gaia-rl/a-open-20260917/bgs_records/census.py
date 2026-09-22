"""Count what setups the archive actually holds, using the listing alone.

The listing already states each game's player count and expansions, so the whole archive
can be counted without downloading a single gameplay record. That is the only way to
answer "is there enough Lost Fleet data to learn from" with a number rather than an
extrapolation from whichever pages happened to be sampled — and the answer matters,
because the share of Gaia Project games varies a lot with depth.
"""
from collections import Counter
from dataclasses import dataclass, field

from . import source


@dataclass(frozen=True)
class Census:
    listed: int
    scanned: int
    gaia: int
    #: (players, expansions) to how many games had that setup.
    setups: dict[tuple[int, tuple[str, ...]], int] = field(default_factory=dict)
    #: Ids of games carrying an expansion, which are too rare to find any other way.
    expansion_games: tuple[tuple[str, int, tuple[str, ...]], ...] = ()

    def count(self, players: int | None = None, expansion: str | None = None) -> int:
        return sum(total for (seats, expansions), total in self.setups.items()
                   if (players is None or seats == players)
                   and (expansion is None or expansion in expansions))

    def describe(self) -> str:
        lines = [f'scanned {self.scanned} of {self.listed} listed games; '
                 f'{self.gaia} are finished Gaia Project games', '', 'setups:']
        for (players, expansions), total in sorted(self.setups.items()):
            label = f'{players}p' + (' + ' + '+'.join(expansions) if expansions else '')
            lines.append(f'  {label:28} {total:6}')
        if self.expansion_games:
            lines += ['', f'{len(self.expansion_games)} games carry an expansion:']
            for game_id, players, expansions in self.expansion_games:
                lines.append(f'  {game_id:32} {players}p  {"+".join(expansions)}')
        return '\n'.join(lines)


def take(fetcher: source.Fetcher, *, start: int = 0, limit: int | None = None,
         log=lambda message: None) -> Census:
    """Page the listing and tally. `limit` caps how many entries to read, for a sample."""
    if start < 0 or (limit is not None and limit < 0):
        raise ValueError('Invalid census window')
    listed = source.ended_count(fetcher)
    ceiling = listed if limit is None else min(listed, start + limit)
    setups: Counter = Counter()
    expansion_games = []
    scanned = gaia = 0
    skip = start
    while skip < ceiling:
        page = source.ended_page(fetcher, skip=skip,
                                 count=min(source.PAGE_LIMIT, ceiling - skip))
        if not page:
            break
        scanned += len(page)
        for summary in page:
            if not source.is_wanted(summary):
                continue
            gaia += 1
            game = summary.get('game') or {}
            expansions = tuple(sorted(game.get('expansions') or ()))
            players = len(summary.get('players') or ())
            setups[(players, expansions)] += 1
            if expansions:
                expansion_games.append((summary['_id'], players, expansions))
        skip += source.PAGE_LIMIT
        if scanned % 5000 < source.PAGE_LIMIT:
            log(f'  {scanned} scanned, {gaia} Gaia Project, '
                f'{len(expansion_games)} with an expansion')
    return Census(listed, scanned, gaia, dict(setups), tuple(expansion_games))
