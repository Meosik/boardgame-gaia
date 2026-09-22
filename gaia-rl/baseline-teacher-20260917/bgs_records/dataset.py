"""Emit one JSONL row per recorded decision, with verified context and final outcomes.

A row is what a policy saw and what the human then did, plus how the game ended. That
supports imitation and outcome-weighted learning; it does not support anything needing
the legal-move list or the power bowls, because a log cannot recover either. The
`features` block therefore holds only fields `state.verify` reconciled against the
game's own final board, and a game that fails that check contributes no rows at all.

Rows are labelled with the setup they came from — player count, expansion, faction
variant, auction, engine version — because a 2-player standard-variant game is not
evidence about a 4-player Lost Fleet one, and the consumer must be able to filter.
"""
from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import time
from pathlib import Path

from .notation import ENGINE_FACTIONS
from .selection import qualifying_seats, table_ratings
from .state import trajectory, verify
from .timeline import GameRecord, SETUP_ROUND, turn_orders

SCHEMA_VERSION = 1
REQUIRED_FIELDS = ('victory_points', 'structures', 'research')
#: Clauses that record a reaction or bookkeeping rather than a chosen turn.
REACTIONS = frozenset(('charge', 'decline', 'income', 'brainstone', 'burn'))


def player_key(name: str) -> str:
    """A stable, non-identifying handle for one account.

    Rows from the same player must not be split across a train/test boundary: a handful
    of regulars play a large share of the games, and a model that has seen their style on
    one side of the split is not being tested on unseen play. The name itself is not
    carried — grouping is all a consumer needs, and the mirror keeps the real record.
    """
    return hashlib.sha256(name.encode()).hexdigest()[:16] if name else ''


@dataclass(frozen=True)
class Row:
    game_id: str
    move_index: int
    round: int
    phase: str
    seat: int
    #: Group by this for train/test splits — see `player_key`.
    player: str
    faction: str
    engine_faction: str
    action: dict
    features: dict
    outcome: dict
    setup: dict


def _action(move) -> dict:
    """The decision, as its commands and their arguments. Annotations are not decisions."""
    clauses = []
    for clause in move.clauses:
        entry = {'command': clause.command, 'args': list(clause.args)}
        if clause.using:
            entry['using'] = [[area, amount] for area, amount in clause.using]
        clauses.append(entry)
    # A move is often several clauses ('build lab X. tech nav. up nav'); `command` names
    # the one that led, which is the choice, while the rest resolve it.
    return {'command': move.clauses[0].command, 'clauses': clauses, 'raw': move.raw}


def _features(record: GameRecord, turn, states, orders) -> dict:
    acting = states[turn.seat]
    order = orders.get(turn.round, ())
    # Opponents' board development, not just their score. With four players, who is close
    # to a federation or an academy drives a move as much as the scoreboard does, and the
    # rebuild pins all of it down exactly.
    opponents = [{'seat': seat, 'faction': state.faction,
                  'victory_points': state.victory_points,
                  'colonised': state.colonised,
                  'buildings': state.buildings(),
                  'research': dict(sorted(state.research.items())),
                  'federations': len(state.federations)}
                 for seat, state in sorted(states.items()) if seat != turn.seat]
    return {
        # Who moves when matters more with four players than with two, and it changes
        # every round: the first to pass goes first next round.
        'turn_order': list(order),
        'turn_position': order.index(turn.seat) if turn.seat in order else None,
        'victory_points': acting.victory_points,
        'vp_behind_leader': max(s.victory_points for s in states.values()) - acting.victory_points,
        'opponents': opponents,
        'buildings': acting.buildings(),
        'colonised': acting.colonised,
        'research': dict(sorted(acting.research.items())),
        'tech_tiles': list(acting.tech_tiles),
        'booster': acting.booster,
        'federations': list(acting.federations),
        'round_scoring': (record.round_scorings[turn.round - 1]
                          if turn.round != SETUP_ROUND else None),
        'final_scorings': list(record.final_scorings),
    }


def _outcome(record: GameRecord, turn, states) -> dict:
    seat = next(s for s in record.seats if s.seat == turn.seat)
    ordered = sorted(record.seats, key=lambda s: -s.victory_points)
    placement = 1 + sum(1 for s in record.seats if s.victory_points > seat.victory_points)
    return {
        'final_victory_points': seat.victory_points,
        'victory_points_still_to_come': seat.victory_points - states[turn.seat].victory_points,
        'placement': placement,
        'won': turn.seat in record.winners,
        'shared_win': len(record.winners) > 1 and turn.seat in record.winners,
        'margin': seat.victory_points - max(
            (s.victory_points for s in ordered if s.seat != seat.seat), default=0),
        'ranking': seat.ranking,
        'elo_initial': seat.elo_initial,
        'elo_delta': seat.elo_delta,
        'dropped': seat.dropped,
    }


def _setup(record: GameRecord) -> dict:
    options = record.options
    # The table's ratings ride along on every row: a strong seat's move in a mixed game
    # is still a strong player's move, but a consumer may want to weigh it differently
    # from one played against three equals.
    ratings = [r for r in table_ratings(record) if r is not None]
    return {
        'table_elo': table_ratings(record),
        'table_min_elo': min(ratings) if ratings else None,
        'nb_players': options.nb_players,
        'expansions': list(options.expansions),
        'faction_variant': options.faction_variant,
        'faction_variant_version': options.faction_variant_version,
        'layout': options.layout,
        'auction': options.auction,
        'advanced_rules': options.advanced_rules,
        'engine_version': options.engine_version,
        'factions': [s.faction for s in record.seats],
    }


def rows(record: GameRecord, final_board: dict, *, include_setup_round: bool = True,
         include_reactions: bool = False, min_elo: int | None = None):
    """Yield every usable decision in one game, or nothing if the rebuild did not verify.

    `min_elo` filters seat by seat, not game by game: a beginner at the table costs their
    own rows, not everyone else's.
    """
    verified = verify(record, final_board)
    if not all(field in verified for field in REQUIRED_FIELDS):
        return
    learning_from = (None if min_elo is None
                     else qualifying_seats(record, min_elo))
    setup = _setup(record)
    orders = turn_orders(record)
    for turn, states in trajectory(record):
        if turn.move.faction is None:
            continue  # 'init', and the seat-numbered setup lines that precede factions.
        if learning_from is not None and turn.seat not in learning_from:
            continue
        if not include_setup_round and turn.round == SETUP_ROUND:
            continue
        commands = set(turn.move.commands())
        if not include_reactions and commands <= REACTIONS:
            continue
        yield Row(
            game_id=record.game_id, move_index=turn.move_index, round=turn.round,
            phase=turn.phase, seat=turn.seat,
            player=player_key(record.seats[turn.seat].name),
            faction=turn.move.faction,
            engine_faction=ENGINE_FACTIONS[turn.move.faction],
            action=_action(turn.move),
            features=_features(record, turn, states, orders),
            outcome=_outcome(record, turn, states),
            setup=setup)


@dataclass(frozen=True)
class BuildReport:
    games: int
    skipped: int
    rows: int
    path: Path
    #: Selected games that would not rebuild, with the reason. Never silently dropped.
    unreadable: tuple[tuple[str, str], ...] = ()

    def describe(self) -> str:
        size = self.path.stat().st_size / 1024 ** 2 if self.path.exists() else 0
        return (f'{self.rows} decisions from {self.games} games '
                f'({self.skipped} produced no rows: unverifiable, or no seat cleared the '
                f'rating floor) -> {self.path} ({size:.1f} MB)')


def write(corpus, path: Path, game_ids=None, **options) -> BuildReport:
    """Write mirrored games out as JSONL, one decision per line.

    `game_ids` narrows the run to a subset — the setup filters use it, so that a single
    file never mixes player counts or expansions. The first line records which filters
    were applied, so a file found later can say what it is without being re-derived.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    games = skipped = written = 0
    unreadable: list[tuple[str, str]] = []
    # Each row repeats its game's setup, which is what keeps JSONL simple to consume and
    # also what makes it compress about tenfold. A '.gz' suffix writes it compressed; the
    # whole four-player corpus is several gigabytes otherwise.
    opener = ((lambda: gzip.open(path, 'wt')) if path.suffix == '.gz'
              else (lambda: path.open('w')))
    with opener() as stream:
        stream.write(json.dumps({
            'schema': SCHEMA_VERSION,
            'source': 'boardgamers.space',
            'written_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'filters': {'min_elo': options.get('min_elo'),
                        'include_setup_round': options.get('include_setup_round', True),
                        'include_reactions': options.get('include_reactions', False),
                        'games': len(game_ids) if game_ids is not None else None},
            'note': ('Log-derived. No legal-move list and no power bowls: neither is '
                     'recoverable from a move log. The rating floor is applied per seat, '
                     'so a row may come from a table that also held weaker players — see '
                     'each row\'s setup.table_elo.'),
        }, sort_keys=True) + '\n')
        for game_id in (corpus.ids() if game_ids is None else sorted(game_ids)):
            try:
                stored = corpus.raw(game_id)
                record = corpus.record(game_id)
            except Exception as error:   # a mirrored game that no longer rebuilds
                unreadable.append((game_id, str(error)))
                continue
            produced = 0
            for row in rows(record, stored['data'], **options):
                stream.write(json.dumps(asdict(row), sort_keys=True) + '\n')
                produced += 1
            if produced:
                games += 1
                written += produced
            else:
                skipped += 1
    return BuildReport(games, skipped, written, path, tuple(unreadable))
