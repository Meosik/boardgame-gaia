"""Rebuild the state a decision was made in, using only what the log actually pins down.

Measured against the final board of every mirrored game, the log supports three tiers:

    exact        victory points, every structure on the map, QICs
    close        credits, ore and knowledge (~1% of seats drift; some gains go unlogged)
    unavailable  the power bowls, whose tokens move between areas the log never names

Only the exact tier is reconstructed here. The close tier is deliberately left out
rather than shipped as a feature that is wrong once in a hundred seats, and the power
bowls cannot be recovered from a log at all. `verify` re-checks the rebuild against the
final recorded board, so a future engine release that changes the notation fails loudly
instead of quietly producing plausible, wrong training rows.
"""
from dataclasses import dataclass, field, replace
import re

from .notation import TRACKS
from .timeline import GameRecord, STARTING_VP

LEVEL_ANNOTATION = re.compile(r'^([0-9]+) ⇒ ([0-9]+)$')
#: Structures that sit on a map hex and replace whatever the seat had there. These are
#: the kinds the site also counts in a player's `buildings`.
PLACED = frozenset(('m', 'ts', 'lab', 'PI', 'ac1', 'ac2', 'gf', 'sp'))
#: The Navigation-5 Lost Planet holds a hex and colonises it, but the site tracks it
#: apart from `buildings`, so counting it as a mine overstates the mine total.
LOST_PLANET = 'lost'


@dataclass(frozen=True)
class SeatState:
    """One seat's reconstructed position immediately before a move."""
    seat: int
    faction: str
    victory_points: int
    #: Map coordinate to the structure this seat has standing there.
    structures: dict[str, str] = field(default_factory=dict)
    #: Track to level, for tracks this seat has advanced. A track that is absent was
    #: never advanced and still sits at the faction board's starting level.
    research: dict[str, int] = field(default_factory=dict)
    tech_tiles: tuple[str, ...] = ()
    booster: str | None = None
    federations: tuple[str, ...] = ()

    def count(self, structure: str) -> int:
        return sum(1 for kind in self.structures.values() if kind == structure)

    def buildings(self) -> dict[str, int]:
        return {kind: self.count(kind) for kind in sorted(PLACED)}

    @property
    def colonised(self) -> int:
        """Planets held. Gaiaformers and space stations occupy hexes but colonise nothing."""
        return sum(1 for kind in self.structures.values() if kind not in ('gf', 'sp'))

    @property
    def has_lost_planet(self) -> bool:
        return LOST_PLANET in self.structures.values()


def _apply(seats: dict[int, SeatState], turn, effects_by_move) -> None:
    seat = seats[turn.seat]
    structures = dict(seat.structures)
    research = dict(seat.research)
    tech_tiles, federations, booster = list(seat.tech_tiles), list(seat.federations), seat.booster
    levels = [LEVEL_ANNOTATION.match(a) for a in turn.move.annotations]
    levels = [m for m in levels if m]
    for clause in turn.move.clauses:
        command = clause.command
        if command == 'build':
            structures[clause.args[1]] = clause.args[0]
        elif command == 'swap-PI':
            # Ambas trades its Planetary Institute with one of its own mines. Older
            # records omit the '(from X)' annotation that names the institute's old hex,
            # so the origin is taken from the position being rebuilt, which knows it
            # regardless. The annotation, where present, only restates the same hex.
            destination = clause.args[0]
            origin = next((coord for coord, kind in structures.items() if kind == 'PI'),
                          None)
            if origin is not None:
                structures[origin] = structures.get(destination, 'm')
                structures[destination] = 'PI'
        elif command == 'lostPlanet':
            structures[clause.args[0]] = LOST_PLANET
        elif command == 'up' and clause.args[0] in TRACKS and levels:
            # The site annotates the resulting level, which beats counting steps:
            # tech tiles and faction boards start tracks above zero.
            research[clause.args[0]] = int(levels.pop(0).group(2))
        elif command == 'tech':
            tech_tiles.append(clause.args[0])
        elif command == 'cover':
            # An advanced tile is laid over a standard one the seat already had, which
            # stops counting: 'tech adv-gaia. cover gaia' is a swap, not a second tile.
            if clause.args[0] in tech_tiles:
                tech_tiles.remove(clause.args[0])
        elif command == 'booster':
            booster = clause.args[0]
        elif command == 'pass' and clause.args and clause.args[0]:
            booster = clause.args[0]
        elif command in ('federation', 'fedtile'):
            federations.append(clause.args[-1])
    gained = sum(e.delta for e in effects_by_move.get(turn.move_index, ())
                 if e.resource == 'vp' and e.seat == turn.seat)
    seats[turn.seat] = replace(
        seat, structures=structures, research=research, tech_tiles=tuple(tech_tiles),
        booster=booster, federations=tuple(federations),
        victory_points=seat.victory_points + gained)


def _other_effects(seats: dict[int, SeatState], turn, effects_by_move) -> None:
    """Charging and round scoring move VP for seats that are not the one acting."""
    for effect in effects_by_move.get(turn.move_index, ()):
        if effect.resource == 'vp' and effect.seat != turn.seat:
            seat = seats[effect.seat]
            seats[effect.seat] = replace(
                seat, victory_points=seat.victory_points + effect.delta)


def _replay(record: GameRecord):
    """Walk the game once, yielding the snapshot taken before each move.

    Returns (via StopIteration's value) the state after everything the log attributes,
    including round income and end-game scoring, which sit outside any move.
    """
    seats = {s.seat: SeatState(s.seat, s.faction, STARTING_VP) for s in record.seats}
    by_move: dict[int, list] = {}
    for effect in record.effects:
        by_move.setdefault(effect.move_index, []).append(effect)
    for turn in record.turns:
        yield turn, dict(seats)
        _apply(seats, turn, by_move)
        _other_effects(seats, turn, by_move)
    seen = {turn.move_index for turn in record.turns}
    for index, effects in by_move.items():
        if index in seen:
            continue
        for effect in effects:
            if effect.resource == 'vp':
                seats[effect.seat] = replace(
                    seats[effect.seat],
                    victory_points=seats[effect.seat].victory_points + effect.delta)
    return seats


def trajectory(record: GameRecord):
    """Yield `(turn, states_before)` for every move, states keyed by seat.

    `states_before` is a snapshot taken before the move resolves, which is what a policy
    would have seen. Resources the log cannot pin down are simply absent from it.
    """
    yield from _replay(record)


def final_states(record: GameRecord) -> dict[int, SeatState]:
    """The position after the last logged effect, for checking the rebuild against."""
    walk = _replay(record)
    while True:
        try:
            next(walk)
        except StopIteration as done:
            return done.value


def verify(record: GameRecord, final_board: dict) -> tuple[str, ...]:
    """Compare the rebuild with the game's recorded final board.

    Returns the fields that reconciled. A field missing from the result reconstructed
    wrongly for this game and must not be used as a training feature from it.
    """
    states = final_states(record)
    verified = []
    if all(states[s.seat].victory_points == s.victory_points for s in record.seats):
        verified.append('victory_points')
    players = final_board.get('players') or []
    if len(players) == len(record.seats):
        if all(states[p['player']].buildings()
               == {k: (p['data'].get('buildings') or {}).get(k, 0) for k in sorted(PLACED)}
               for p in players):
            verified.append('structures')
        # Only tracks the seat actually advanced are compared. A track absent from the
        # rebuild was never advanced, and its level is the faction's starting one, which
        # the log never states — treating that as agreement would verify nothing.
        if all(all(level == (p['data'].get('research') or {}).get(track)
                   for track, level in states[p['player']].research.items())
               for p in players):
            verified.append('research')
    return tuple(verified)
