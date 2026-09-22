"""Join `moveHistory` with `advancedLog` into rounds, seats and attributed resource deltas.

`moveHistory` says what was declared; `advancedLog` says when and to whom it applied.
Interleaved in order, the log carries three kinds of entry:

    {'round': 3}                                  a round boundary
    {'phase': 'roundIncome'}                      a phase boundary
    {'player': 0, 'move': 42}                     moveHistory[42] was seat 0's
    {'player': 1, 'changes': {'charge': {...}}}   resources that move moved, by source

Nothing here re-derives game rules. A round number is read off the log, never counted
from passes, because a dropped player would silently shift every later round.
"""
from dataclasses import dataclass
import re

from .notation import ENGINE_FACTIONS, FACTIONS, Move, NotationError, parse_history

SETUP_ROUND = 0
PHASES = frozenset(('roundIncome', 'roundGaia', 'roundMove', 'endGame'))
LAST_ROUND = 6
#: Every faction opens on 10 VP (rulebook p.9, "Victory Points").
STARTING_VP = 10
RESOURCES = frozenset(('vp', 'c', 'o', 'k', 'q', 'pw', 't', 'tg', 'brainstone',
                       'tg->t', 'gf->t', 'burn-token'))


class RecordError(ValueError):
    """A downloaded game this package will not turn into training data."""


@dataclass(frozen=True)
class Seat:
    seat: int
    faction: str
    name: str
    victory_points: int
    #: Final placement and rating change, which only the listing endpoint reports.
    ranking: int | None = None
    elo_initial: int | None = None
    elo_delta: int | None = None
    dropped: bool = False
    quit: bool = False

    @property
    def engine_faction(self) -> str:
        return ENGINE_FACTIONS[self.faction]


@dataclass(frozen=True)
class Turn:
    """One recorded move, placed in the game's round and phase.

    `move_index` is the 0-based `moveHistory` offset, matching `Move.index`.
    """
    move_index: int
    round: int
    phase: str
    seat: int
    move: Move

    @property
    def is_setup(self) -> bool:
        return self.round == SETUP_ROUND


@dataclass(frozen=True)
class Effect:
    """One resource delta the log attributes to a move, a seat and a named source."""
    move_index: int
    round: int
    seat: int
    source: str
    resource: str
    delta: int


@dataclass(frozen=True)
class Options:
    """How the game was set up. The metadata fields are `None` on older records.

    Most of the archive predates the site recording its engine version, faction variant
    or layout. Those games are otherwise complete, so refusing them would throw away the
    bulk of the corpus; they are carried with the field unknown instead, and a consumer
    filtering on a variant simply will not match them.
    """
    nb_players: int
    expansions: tuple[str, ...]
    faction_variant: str | None
    faction_variant_version: int
    layout: str | None
    auction: str | None
    advanced_rules: bool
    engine_version: str | None

    @property
    def is_lost_fleet(self) -> bool:
        return 'lost-fleet' in self.expansions


# The site sends `expansions` as a bitmask on the gameplay endpoint and as a name list
# on the listing endpoint. Bits confirmed against games that declare each name in the
# listing; an unknown bit is refused rather than dropped, because silently mislabelling
# an expansion game as base-game poisons every count built on the setup filters.
EXPANSION_BITS = ((2, 'frontiers'), (4, 'lost-fleet'))
#: Frontiers adds colony ships, customs posts and trade ships, none of which this
#: engine models or this parser reads. Two such games turned up in 14,000 scanned
#: listing entries, so they are refused by name rather than supported — a refusal
#: that names the expansion beats one that names whichever token happened to fail.
UNSUPPORTED_EXPANSIONS = frozenset(('frontiers',))


def decode_expansions(raw) -> tuple[str, ...]:
    if isinstance(raw, list):
        return tuple(sorted(str(name) for name in raw))
    if not isinstance(raw, int) or raw < 0:
        raise RecordError(f'Unreadable expansion field: {raw!r}')
    names, remaining = [], raw
    for bit, name in EXPANSION_BITS:
        if remaining & bit:
            names.append(name)
            remaining -= bit
    if remaining:
        raise RecordError(f'Unknown expansion bits set: {raw!r}')
    return tuple(sorted(names))


@dataclass(frozen=True)
class GameRecord:
    game_id: str
    options: Options
    seats: tuple[Seat, ...]
    turns: tuple[Turn, ...]
    effects: tuple[Effect, ...]
    round_scorings: tuple[str, ...]
    final_scorings: tuple[str, ...]
    #: Factions in the order the site recorded them at setup, which is round 1's order.
    setup_order: tuple[str, ...] = ()

    def seat_of(self, faction: str) -> int:
        for seat in self.seats:
            if seat.faction == faction:
                return seat.seat
        raise RecordError(f'{self.game_id}: no seat plays {faction!r}')

    @property
    def winners(self) -> tuple[int, ...]:
        """Seats sharing the top score. Ties are reported, not broken."""
        best = max(seat.victory_points for seat in self.seats)
        return tuple(s.seat for s in self.seats if s.victory_points == best)

    def turns_in(self, round_number: int) -> tuple[Turn, ...]:
        return tuple(t for t in self.turns if t.round == round_number)


#: Clauses that are a reaction to someone else's move, not a turn of one's own.
REACTION_COMMANDS = frozenset(('charge', 'decline', 'income', 'brainstone', 'burn'))


def turn_orders(record: 'GameRecord') -> dict[int, tuple[int, ...]]:
    """Seat order for each round.

    Round 1 follows the setup order. Every later round follows the order in which seats
    passed the round before (rulebook p.17, "Pass": the first to pass goes first next
    round). Checked against the order seats actually acted in: exact on every round of
    every mirrored game.
    """
    orders = {1: tuple(record.seat_of(faction) for faction in record.setup_order)}
    passes: dict[int, list[int]] = {}
    for turn in record.turns:
        if turn.round == SETUP_ROUND or turn.move.faction is None:
            continue
        if 'pass' in turn.move.commands():
            seats = passes.setdefault(turn.round, [])
            if turn.seat not in seats:
                seats.append(turn.seat)
    for round_number in range(2, LAST_ROUND + 1):
        previous = passes.get(round_number - 1)
        if previous:
            orders[round_number] = tuple(previous)
    return orders


def _options(data: dict) -> Options:
    raw = data.get('options') or {}

    def text(value):
        return value if isinstance(value, str) and value else None

    players = data.get('players')
    if not isinstance(players, list) or not 2 <= len(players) <= 5:
        raise RecordError(
            f'{len(players) if isinstance(players, list) else "no"} seats have a final '
            'record; a game needs 2 to 5')
    return Options(
        nb_players=len(players),
        expansions=decode_expansions(data.get('expansions', 0)),
        faction_variant=text(raw.get('factionVariant')),
        faction_variant_version=int(raw.get('factionVariantVersion') or 0),
        layout=text(raw.get('layout')),
        auction=text(raw.get('auction')),
        advanced_rules=bool(raw.get('advancedRules')),
        engine_version=text(data.get('version')))


def _seats(data: dict, summary: dict | None) -> tuple[Seat, ...]:
    """Read the final record of every seat, and insist that every seat has one.

    Part of the older archive keeps final data for only some seats — a player who left
    is dropped from `players` while staying in `setup` and in the log. Those games are
    refused: without that seat's score, whether anyone else won is a guess, and a guessed
    outcome label is worse than a missing game.
    """
    declared = data.get('setup')
    if isinstance(declared, list) and len(declared) != len(data['players']):
        raise RecordError(
            f'{len(data["players"])} of {len(declared)} seats have a final record '
            f'({", ".join(map(str, declared))} played); outcomes would be guesses')
    by_name = {}
    for entry in ((summary or {}).get('players') or []):
        if isinstance(entry, dict) and isinstance(entry.get('name'), str):
            by_name[entry['name']] = entry
    seats = []
    for index, player in enumerate(data['players']):
        faction = player.get('faction')
        if faction not in FACTIONS:
            raise RecordError(f'Seat {index} plays unknown faction {faction!r}')
        if player.get('player') != index:
            raise RecordError(
                f'seat {index} is recorded as {player.get("player")!r}; the log indexes '
                'seats from zero and a mismatch would misattribute every move')
        points = (player.get('data') or {}).get('victoryPoints')
        if not isinstance(points, int):
            raise RecordError(f'Seat {index} has no final score')
        listed = by_name.get(player.get('name'), {})
        elo = listed.get('elo') or {}
        seats.append(Seat(
            seat=index, faction=faction, name=str(player.get('name') or ''),
            victory_points=points,
            ranking=listed.get('ranking'),
            elo_initial=elo.get('initial'), elo_delta=elo.get('delta'),
            dropped=bool(listed.get('dropped')), quit=bool(listed.get('quit'))))
    return tuple(seats)


def _walk_log(data: dict, moves: tuple[Move, ...], game_id: str):
    """Assign every move a round and phase, and every change a move, seat and source."""
    log = data.get('advancedLog')
    if not isinstance(log, list) or not log:
        raise RecordError(f'{game_id}: advancedLog is missing or empty')
    rounds, phase, current = SETUP_ROUND, 'setup', 0
    turns, effects, seen = [], [], set()
    for entry in log:
        if not isinstance(entry, dict):
            raise RecordError(f'{game_id}: advancedLog entry is not an object')
        if 'round' in entry:
            number = entry['round']
            if number != rounds + 1 or not 1 <= number <= LAST_ROUND:
                raise RecordError(f'{game_id}: rounds jump from {rounds} to {number!r}')
            rounds = number
            continue
        if 'phase' in entry:
            if entry['phase'] not in PHASES:
                raise RecordError(f'{game_id}: unknown phase {entry["phase"]!r}')
            phase = entry['phase']
            continue
        seat = entry.get('player')
        if not isinstance(seat, int) or not 0 <= seat < len(data['players']):
            raise RecordError(f'{game_id}: change attributed to seat {seat!r}')
        if 'move' in entry:
            index = entry['move']
            if not isinstance(index, int) or not 0 <= index < len(moves):
                raise RecordError(f'{game_id}: log points at move {index!r}')
            if index in seen:
                raise RecordError(f'{game_id}: move {index} logged twice')
            seen.add(index)
            current = index
            turns.append(Turn(index, rounds, phase, seat, moves[index]))
        changes = entry.get('changes')
        if changes is None:
            # A move entry may carry no changes; a bare entry must carry some.
            if 'move' in entry:
                continue
            raise RecordError(f'{game_id}: log entry is neither a move nor a change')
        if not isinstance(changes, dict):
            raise RecordError(f'{game_id}: source list for move {current} is not an object')
        for source, delta in changes.items():
            if not isinstance(delta, dict):
                raise RecordError(f'{game_id}: source {source!r} has no resource deltas')
            for resource, amount in delta.items():
                if resource not in RESOURCES:
                    raise RecordError(f'{game_id}: unknown resource {resource!r}')
                if not isinstance(amount, int):
                    raise RecordError(f'{game_id}: {resource} delta is {amount!r}')
                effects.append(Effect(current, rounds, seat, source, resource, amount))
    if rounds != LAST_ROUND:
        raise RecordError(f'{game_id}: ended in round {rounds}, not {LAST_ROUND}')
    return tuple(turns), tuple(effects)


def _check_scores(game_id: str, seats: tuple[Seat, ...], effects: tuple[Effect, ...]) -> None:
    """Replay the attributed VP and demand it lands on the recorded final score.

    This is the one end-to-end check available without a rules engine: if a move were
    assigned to the wrong seat or a log entry dropped, the totals would not close.
    """
    totals = dict.fromkeys((seat.seat for seat in seats), STARTING_VP)
    for effect in effects:
        if effect.resource == 'vp':
            totals[effect.seat] += effect.delta
    for seat in seats:
        if totals[seat.seat] != seat.victory_points:
            raise RecordError(
                f'{game_id}: seat {seat.seat} ({seat.faction}) scores {seat.victory_points} '
                f'but its logged VP sums to {totals[seat.seat]}')


def build(game_id: str, data: dict, summary: dict | None = None) -> GameRecord:
    """Normalise one downloaded game. Raises rather than repairing an unexpected record."""
    if not isinstance(data, dict):
        raise RecordError(f'{game_id}: gameplay data is not an object')
    if data.get('ended') is not True:
        # The listing reports abandoned games as 'ended' too; this flag is the real one.
        raise RecordError(f'{game_id}: game has not ended')
    options = _options(data)
    unsupported = UNSUPPORTED_EXPANSIONS.intersection(options.expansions)
    if unsupported:
        raise RecordError(f'{game_id}: {", ".join(sorted(unsupported))} is not supported')
    try:
        moves = parse_history(data.get('moveHistory'))
    except NotationError as error:
        # One record the parser cannot read is one game to skip, not a dead crawl: a
        # 14,000-game fetch must not end because the site logged a move in a new shape.
        raise RecordError(f'{game_id}: {error}') from error
    seats = _seats(data, summary)
    turns, effects = _walk_log(data, moves, game_id)
    moving = {m.faction for m in moves if m.faction is not None}
    playing = {s.faction for s in seats}
    if not moving <= playing:
        raise RecordError(f'{game_id}: moves by factions not seated: {sorted(moving - playing)}')
    for turn in turns:
        faction = turn.move.faction
        if faction is not None and seats[turn.seat].faction != faction:
            raise RecordError(
                f'{game_id}: move {turn.move_index} says {faction}, log says seat {turn.seat}')
    _check_scores(game_id, seats, effects)
    scorings = (data.get('tiles') or {}).get('scorings') or {}
    round_tiles = tuple(scorings.get('round') or ())
    final_tiles = tuple(scorings.get('final') or ())
    if len(round_tiles) != LAST_ROUND:
        raise RecordError(f'{game_id}: {len(round_tiles)} round scoring tiles, not {LAST_ROUND}')
    setup = data.get('setup')
    order = tuple(setup) if isinstance(setup, list) else tuple(s.faction for s in seats)
    if sorted(order) != sorted(s.faction for s in seats):
        raise RecordError(f'{game_id}: setup order {order} does not match the seats')
    return GameRecord(game_id, options, seats, turns, effects, round_tiles, final_tiles,
                      order)
