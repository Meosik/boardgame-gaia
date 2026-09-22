"""Which mirrored games to learn from, and which seats in them are worth learning from.

The target is four players with the Lost Fleet expansion. The site has almost none of
those, so the policy widens to four-player base game rather than returning an empty set,
and says so instead of quietly pretending the corpus matched.

Strength is filtered **per seat, not per game**. A strong player's moves are a strong
player's moves even when a beginner is at the table, so a mixed game contributes the
seats that clear the floor and drops the ones that do not. The table is not thrown away
for one weak player. What the rest of the table was rated still matters for weighing a
row, so every row carries it; `require_all_seats` restores the stricter reading for a
consumer that wants only games where everyone was strong.

The rating used is the one each player carried *into* the game. The post-game rating
already knows how the game went.
"""
from dataclasses import dataclass

#: Ratings cluster on a floor near 100 — new and barely-rated accounts. Above it means
#: the player has at least played enough for the rating to move.
DEFAULT_MIN_ELO = 120
#: Below this many games, the Lost Fleet target is treated as too thin to learn from.
DEFAULT_FALLBACK_BELOW = 30


@dataclass(frozen=True)
class Selection:
    #: Ids of the chosen games, not the games themselves — the caller streams those.
    game_ids: tuple[str, ...]
    players: int
    lost_fleet: bool
    min_elo: int
    require_all_seats: bool
    considered: int
    dropped_setup: int
    dropped_rating: int
    seats_kept: int
    seats_dropped: int
    widened_from: int | None = None

    def describe(self) -> str:
        target = f'{self.players}p' + (' + lost-fleet' if self.lost_fleet else ' base game')
        rule = ('every seat rated' if self.require_all_seats
                else 'learning only from seats rated')
        lines = [f'selected {len(self.game_ids)} of {self.considered} mirrored games '
                 f'({target}, {rule} {self.min_elo}+)']
        if self.widened_from is not None:
            lines.append(
                f'  NOTE: only {self.widened_from} games matched 4p + lost-fleet, below the '
                f'threshold, so the selection widened to 4p base game. These rows are not '
                f'evidence about the expansion.')
        lines.append(f'  dropped {self.dropped_setup} games for setup, '
                     f'{self.dropped_rating} for rating')
        lines.append(f'  seats: {self.seats_kept} kept, {self.seats_dropped} below the floor '
                     f'or unrated')
        return '\n'.join(lines)


def qualifying_seats(record, min_elo: int) -> frozenset[int]:
    """Seats that carried at least `min_elo` into the game. An unrated seat never counts."""
    return frozenset(seat.seat for seat in record.seats
                     if seat.elo_initial is not None and seat.elo_initial >= min_elo)


def _qualifying(ratings, min_elo: int) -> int:
    return sum(1 for rating in ratings if rating is not None and rating >= min_elo)


def table_ratings(record) -> list[int | None]:
    """Every seat's starting rating, in seat order, so a row can be weighed by its table."""
    return [seat.elo_initial for seat in record.seats]


def _filter(entries, players, lost_fleet, min_elo, require_all_seats):
    kept, dropped_setup, dropped_rating = [], 0, 0
    seats_kept = seats_dropped = 0
    for entry in entries:
        if entry.nb_players != players or entry.is_lost_fleet != lost_fleet:
            dropped_setup += 1
            continue
        seats = len(entry.elo) or entry.nb_players
        qualifying = _qualifying(entry.elo, min_elo)
        needed = seats if require_all_seats else 1
        if qualifying < needed:
            dropped_rating += 1
            seats_dropped += seats
            continue
        kept.append(entry.game_id)
        seats_kept += qualifying
        seats_dropped += seats - qualifying
    return kept, dropped_setup, dropped_rating, seats_kept, seats_dropped


def select(entries, *, players: int = 4, min_elo: int = DEFAULT_MIN_ELO,
           require_all_seats: bool = False,
           fallback_below: int = DEFAULT_FALLBACK_BELOW,
           allow_fallback: bool = True) -> Selection:
    """Pick the Lost Fleet games at this player count, widening to base game if too few.

    `entries` are `corpus.Stored` index rows, not rebuilt games: deciding what to learn
    from must not cost a rebuild of the whole mirror.
    """
    if players < 2 or min_elo < 0 or fallback_below < 0:
        raise ValueError('Invalid selection')
    entries = list(entries)

    def run(lost_fleet):
        return _filter(entries, players, lost_fleet, min_elo, require_all_seats)

    kept, setup, rating, seats_in, seats_out = run(True)
    if len(kept) >= fallback_below or not allow_fallback:
        return Selection(tuple(kept), players, True, min_elo, require_all_seats,
                         len(entries), setup, rating, seats_in, seats_out)
    thin = len(kept)
    kept, setup, rating, seats_in, seats_out = run(False)
    return Selection(tuple(kept), players, False, min_elo, require_all_seats, len(entries),
                     setup, rating, seats_in, seats_out, widened_from=thin)
