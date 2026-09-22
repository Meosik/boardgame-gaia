"""Counted observations over the mirrored corpus. Counts and scores only, never advice.

Every figure here is a tally with the sample size attached, in the spirit of the
`bgg_openings` catalog: a teacher may read "Terrans opened 2M+1TS in 40 of 55 recorded
games, averaging 148 points" and weigh it, but nothing in this module decides anything,
fits a weight, or claims a move is good. Small samples stay small and visible rather
than being smoothed into confidence the corpus does not contain.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass

from .state import trajectory
from .timeline import GameRecord, SETUP_ROUND

#: Below this many games, a per-faction figure is reported but flagged as thin.
THIN_SAMPLE = 10


@dataclass(frozen=True)
class Observation:
    """One counted outcome: how often, and how it went when it happened."""
    label: str
    games: int
    average_score: float
    wins: int

    @property
    def is_thin(self) -> bool:
        return self.games < THIN_SAMPLE

    @property
    def win_rate(self) -> float:
        return self.wins / self.games

    def as_dict(self) -> dict:
        return {'label': self.label, 'games': self.games,
                'average_score': round(self.average_score, 1),
                'wins': self.wins, 'win_rate': round(self.win_rate, 3),
                'thin_sample': self.is_thin}


class Tally:
    """Accumulates (score, won) pairs per label so every figure keeps its sample size."""

    def __init__(self):
        self._scores: dict[str, list[int]] = defaultdict(list)
        self._wins: Counter[str] = Counter()

    def add(self, label: str, score: int, won: bool) -> None:
        self._scores[label].append(score)
        self._wins[label] += bool(won)

    def observations(self) -> tuple[Observation, ...]:
        return tuple(sorted(
            (Observation(label, len(scores), sum(scores) / len(scores), self._wins[label])
             for label, scores in self._scores.items()),
            key=lambda o: (-o.games, o.label)))

    def as_dicts(self) -> list[dict]:
        return [o.as_dict() for o in self.observations()]


# Ordered the way the BGG opening tables write them — biggest building first —
# so a label here is the same string as the one in `bgg_openings`, and the two
# sources can be compared without a translation step.
SYMBOLS = (('ac1', 'AC'), ('PI', 'PI'), ('lab', 'RL'), ('ts', 'TS'), ('m', 'M'))


def _label(state) -> str:
    counts = state.buildings()
    counts['ac1'] = counts.get('ac1', 0) + counts.pop('ac2', 0)
    parts = [f'{counts[key]}{symbol}' for key, symbol in SYMBOLS if counts.get(key)]
    return '+'.join(parts) or 'none'


def _openings(record: GameRecord) -> dict[int, str]:
    """What each seat had standing when round 1 ended, in the BGG article's notation.

    One replay for the whole table: the trajectory is the expensive part of a report, and
    walking it once per seat multiplies that by the player count for no new information.
    """
    last = None
    for turn, states in trajectory(record):
        last = states
        if turn.round > 1:
            # This snapshot is taken before the first round-2 move, so it is exactly the
            # position at the end of round 1 — including round 1's final move, which
            # stopping one turn earlier would miss.
            break
    if last is None:
        return {seat.seat: 'none' for seat in record.seats}
    return {seat: _label(state) for seat, state in last.items()}


@dataclass(frozen=True)
class Catalog:
    """Every tally the corpus supports, keyed by what the observation is about."""
    games: int
    seats: int
    setups: list[dict]
    factions: list[dict]
    openings: dict[str, list[dict]]
    boosters_by_round: dict[str, list[dict]]
    first_tech: dict[str, list[dict]]
    research_by_round: dict[str, list[dict]]
    federation_round: list[dict]
    vp_sources: list[dict]

    def as_dict(self) -> dict:
        return {
            'games': self.games, 'seats': self.seats, 'setups': self.setups,
            'factions': self.factions, 'openings': self.openings,
            'boosters_by_round': self.boosters_by_round, 'first_tech': self.first_tech,
            'research_by_round': self.research_by_round,
            'federation_round': self.federation_round, 'vp_sources': self.vp_sources,
        }


def build(records, seat_filter=None) -> Catalog:
    """Tally the corpus. `seat_filter(record)` returns the seats to count, or None for all.

    The filter exists so a report counts exactly the seats the dataset would learn from.
    A report that says it is using strong seats only, then averages over everyone, is
    quietly describing a different corpus from the one being trained on.
    """
    # Consumed as a stream. A whole four-player corpus is gigabytes of rebuilt records,
    # so nothing here may hold more than the game it is currently counting.
    games = 0
    setups, factions, federation, per_round_research = Tally(), Tally(), Tally(), defaultdict(Tally)
    openings = defaultdict(Tally)
    boosters = defaultdict(Tally)
    first_tech = defaultdict(Tally)
    vp_totals: Counter[str] = Counter()
    vp_games: Counter[str] = Counter()
    seats = 0

    for record in records:
        games += 1
        counted = (frozenset(s.seat for s in record.seats) if seat_filter is None
                   else frozenset(seat_filter(record)))
        winners = set(record.winners)
        openings_here = _openings(record)
        # An unrecorded variant is its own bucket, never pooled into 'standard'.
        setup_label = (f'{record.options.nb_players}p/'
                       f'{record.options.faction_variant or "variant-unrecorded"}'
                       + ('/lost-fleet' if record.options.is_lost_fleet else ''))
        for seat in record.seats:
            if seat.seat not in counted:
                continue
            seats += 1
            won = seat.seat in winners
            setups.add(setup_label, seat.victory_points, won)
            factions.add(seat.faction, seat.victory_points, won)
            openings[seat.faction].add(openings_here[seat.seat], seat.victory_points,
                                       won)

        taken_tech: dict[int, str] = {}
        first_federation: dict[int, int] = {}
        research_seen: dict[tuple[int, int], str] = {}
        for turn in record.turns:
            if turn.move.faction is None:
                continue
            if turn.seat not in counted:
                continue
            for clause in turn.move.clauses:
                if clause.command == 'booster' or (clause.command == 'pass' and clause.args
                                                   and clause.args[0]):
                    label = clause.args[0]
                    key = 'setup' if turn.round == SETUP_ROUND else f'round{turn.round}'
                    boosters[key].add(label, _score(record, turn.seat),
                                      turn.seat in winners)
                elif clause.command == 'tech' and turn.seat not in taken_tech:
                    taken_tech[turn.seat] = clause.args[0]
                elif clause.command == 'up' and (turn.seat, turn.round) not in research_seen:
                    research_seen[(turn.seat, turn.round)] = clause.args[0]
                    per_round_research[f'round{turn.round}'].add(
                        clause.args[0], _score(record, turn.seat), turn.seat in winners)
                elif clause.command == 'federation' and turn.seat not in first_federation:
                    first_federation[turn.seat] = turn.round

        for seat in record.seats:
            if seat.seat not in counted:
                continue
            if seat.seat in taken_tech:
                first_tech[seat.faction].add(taken_tech[seat.seat], seat.victory_points,
                                             seat.seat in winners)
            round_reached = first_federation.get(seat.seat)
            federation.add('none' if round_reached is None else f'round{round_reached}',
                           seat.victory_points, seat.seat in winners)

        for effect in record.effects:
            if effect.resource == 'vp' and effect.seat in counted:
                vp_totals[effect.source] += effect.delta
        for source in {e.source for e in record.effects
                       if e.resource == 'vp' and e.seat in counted}:
            vp_games[source] += 1

    vp_sources = [{'source': source, 'total_vp': total, 'games': vp_games[source],
                   'average_vp_per_game': round(total / vp_games[source], 1)}
                  for source, total in sorted(vp_totals.items(), key=lambda kv: -kv[1])]
    if not games:
        raise ValueError('An empty corpus supports no observations')
    return Catalog(
        games=games, seats=seats,
        setups=setups.as_dicts(), factions=factions.as_dicts(),
        openings={faction: tally.as_dicts() for faction, tally in sorted(openings.items())},
        boosters_by_round={key: boosters[key].as_dicts()
                           for key in sorted(boosters, key=_round_key)},
        first_tech={faction: tally.as_dicts() for faction, tally in sorted(first_tech.items())},
        research_by_round={key: per_round_research[key].as_dicts()
                           for key in sorted(per_round_research, key=_round_key)},
        federation_round=federation.as_dicts(), vp_sources=vp_sources)


def _round_key(label: str) -> tuple[int, str]:
    return (0, label) if label == 'setup' else (int(label.removeprefix('round')), label)


def _score(record: GameRecord, seat: int) -> int:
    for entry in record.seats:
        if entry.seat == seat:
            return entry.victory_points
    raise KeyError(seat)


def summarise(catalog: Catalog, *, top: int = 5) -> str:
    """A short plain-text read of the catalog, for a terminal rather than a trainer."""
    lines = [f'{catalog.games} games, {catalog.seats} seats',
             '', 'setups:']
    for row in catalog.setups[:top]:
        lines.append(f"  {row['label']:28} {row['games']:5} seats  "
                     f"avg {row['average_score']:6}  win {row['win_rate']:.0%}")
    lines += ['', f'factions (top {top} by sample):']
    for row in catalog.factions[:top]:
        flag = '  [thin]' if row['thin_sample'] else ''
        lines.append(f"  {row['label']:28} {row['games']:5} seats  "
                     f"avg {row['average_score']:6}  win {row['win_rate']:.0%}{flag}")
    lines += ['', f'largest VP sources (whole corpus, top {top * 2}):']
    for row in catalog.vp_sources[:top * 2]:
        lines.append(f"  {row['source']:28} {row['total_vp']:7} vp over {row['games']:4} games"
                     f"  ({row['average_vp_per_game']}/game)")
    lines += ['', 'first federation:']
    for row in catalog.federation_round:
        lines.append(f"  {row['label']:28} {row['games']:5} seats  "
                     f"avg {row['average_score']:6}  win {row['win_rate']:.0%}")
    return '\n'.join(lines)
