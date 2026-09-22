"""Parse boardgamers.space Gaia Project move notation. Unknown tokens raise, never pass through.

A recorded move is one line of `moveHistory`: a subject, then clauses separated by
`.`, plus parenthesised annotations the site's engine adds for the reader. The
annotations restate state the clauses already caused, so they are captured but never
treated as commands.

    terrans build lab 3A1. tech nav. up nav (0 ⇒ 1).
    xenos charge 2pw (1/5/0/0 ⇒ 0/5/1/0)

Every vocabulary below was read off a downloaded corpus rather than guessed. Refusing
unknown tokens is deliberate: the site's engine keeps being released, and a silently
skipped clause would quietly bias every count built on top of it.
"""
from dataclasses import dataclass, field
import re

FACTIONS = frozenset((
    'terrans', 'lantids', 'xenos', 'gleens', 'taklons', 'ambas', 'hadsch-hallas', 'ivits',
    'geodens', 'baltaks', 'firaks', 'bescods', 'nevlas', 'itars',
    # Lost Fleet additions.
    'darkanians', 'tinkeroids', 'moweyds', 'spacegiants',
))

# The engine's `FactionId` spelling, so counts can be joined against native replays.
ENGINE_FACTIONS = {
    'terrans': 'Terrans', 'lantids': 'Lantids', 'xenos': 'Xenos', 'gleens': 'Gleens',
    'taklons': 'Taklons', 'ambas': 'Ambas', 'hadsch-hallas': 'HadschHallas', 'ivits': 'Ivits',
    'geodens': 'Geodens', 'baltaks': 'BalTaks', 'firaks': 'Firaks', 'bescods': 'Bescods',
    'nevlas': 'Nevlas', 'itars': 'Itars', 'darkanians': 'Darkanians',
    'tinkeroids': 'Tinkeroids', 'moweyds': 'Moweyds', 'spacegiants': 'SpaceGiants',
}

TRACKS = frozenset(('terra', 'nav', 'int', 'gaia', 'eco', 'sci'))
STRUCTURES = frozenset(('m', 'ts', 'lab', 'PI', 'ac1', 'ac2', 'gf', 'sp'))
BOARD_ACTIONS = frozenset(
    [f'power{i}' for i in range(1, 8)] + [f'qic{i}' for i in range(1, 4)])
BOOSTERS = frozenset(f'booster{i}' for i in range(1, 11))
FEDERATION_TILES = frozenset(f'fed{i}' for i in range(1, 7))
TECH_TILES = (frozenset(f'free{i}' for i in range(1, 4)) | TRACKS
              | frozenset(f'adv-{t}' for t in TRACKS | {'ext'}))
# The expansion's four physical spaceship boards (engine `SpaceshipId`).
SPACESHIPS = frozenset(('twilight', 'rebellion', 'tfmars', 'eclipse'))
# Lost Fleet federation tokens are named per spaceship reward ('ship-fed-credit',
# 'ship-fed-orequic', 'ship-fed-tech'). Only one Lost Fleet game appeared in the
# sample the vocabulary above was read from, so the suffix set is matched by shape
# rather than enumerated — enumerating three of eight would reject valid records.
SHIP_FEDERATION = re.compile(r'ship-fed-[a-z]+')

# Clause commands, mapped to how many space-separated arguments each may carry.
PLAIN_COMMANDS = {
    'build': 2, 'up': 1, 'action': 1, 'special': 1, 'tech': 1, 'cover': 1,
    'burn': 1, 'brainstone': 1, 'booster': 1, 'fedtile': 1, 'lostPlanet': 1,
    'swap-PI': 1, 'explore': 1, 'gaiaFormTransdim': 1, 'income': 1,
    'charge': 1, 'decline': (0, 1), 'spaceshipAction': 2,
}
# '3A1'/'7C' on the map sectors, 'IS5' on a Lost Fleet interstellar space.
KNOWN_COMMANDS = frozenset(PLAIN_COMMANDS) | {
    'spend', 'pass', 'federation', 'special', 'rotate', 'faction', 'bid'}
# '3A1'/'7C' on a map sector; 'IS5' and 'DS12_0' on Lost Fleet interstellar and
# deep-space hexes, which the base game's sector lettering cannot name.
COORD_PATTERN = r'(?:[0-9]+[A-C][0-9]*|IS[0-9]+|DS[0-9]+_[0-9]+)'
COORD = re.compile(COORD_PATTERN)
ANNOTATION = re.compile(r'\(([^)]*)\)')
BOWL_ANNOTATION = re.compile(
    r'^(?P<before>[0-9]+(?:,B)?(?:/[0-9]+(?:,B)?){3}) ⇒ (?P<after>[0-9]+(?:,B)?(?:/[0-9]+(?:,B)?){3})$')
LEVEL_ANNOTATION = re.compile(r'^(?P<before>[0-9]+) ⇒ (?P<after>[0-9]+)$')
FROM_ANNOTATION = re.compile(rf'^from (?P<coord>{COORD_PATTERN})$')


class NotationError(ValueError):
    """A recorded line this parser will not guess at."""


@dataclass(frozen=True)
class Clause:
    command: str
    args: tuple[str, ...] = ()
    #: Power bowls drained to pay for this clause, as ('area1', 4) pairs.
    using: tuple[tuple[str, int], ...] = ()

    def arg(self, index: int = 0) -> str:
        return self.args[index]


@dataclass(frozen=True)
class Move:
    """One `moveHistory` line.

    `index` is the 0-based offset into `moveHistory`, which is also what `advancedLog`
    move numbers mean. They are not 1-based: `moveHistory[0]` is the `init` line and
    carries no log entry, so an off-by-one here silently attributes every resource
    change to the wrong move and the wrong player.
    """
    index: int
    subject: str
    clauses: tuple[Clause, ...]
    annotations: tuple[str, ...] = field(default=())
    raw: str = ''

    @property
    def faction(self) -> str | None:
        return self.subject if self.subject in FACTIONS else None

    @property
    def is_setup(self) -> bool:
        return self.faction is None

    def commands(self) -> tuple[str, ...]:
        return tuple(clause.command for clause in self.clauses)

    def first(self, command: str) -> Clause | None:
        for clause in self.clauses:
            if clause.command == command:
                return clause
        return None


def _split_using(tokens: list[str], context: str) -> tuple[list[str], tuple[tuple[str, int], ...]]:
    """Peel a trailing 'using area1: 4, area2: 2' payment off a clause's arguments.

    Gaia-forming and satellite placement both spend power the player chooses bowl by
    bowl, and the site records that choice inline rather than as its own clause.
    A Taklons brainstone pays like a token and is named as its own 'bowl'.
    """
    if 'using' not in tokens:
        return tokens, ()
    split = tokens.index('using')
    head, payment = tokens[:split], ' '.join(tokens[split + 1:])
    areas = []
    for part in payment.split(','):
        match = re.fullmatch(r'\s*(area[1-3]|brainstone):\s*([0-9]+)\s*', part)
        if match is None:
            raise NotationError(f'{context}: unreadable power payment {payment!r}')
        areas.append((match.group(1), int(match.group(2))))
    if not areas:
        raise NotationError(f'{context}: empty power payment')
    return head, tuple(areas)


def _coord(token: str, context: str) -> str:
    if not COORD.fullmatch(token):
        raise NotationError(f'{context}: {token!r} is not a map coordinate')
    return token


def _amount(token: str, context: str) -> str:
    """Resource amounts stay textual ('4pw', '1q', '2pw,1t'): they are multi-typed bundles."""
    if not re.fullmatch(r'-?[0-9]*[a-zA-Z+\-]+[0-9]*(?:,-?[0-9]*[a-zA-Z+\-]+[0-9]*)*', token):
        raise NotationError(f'{context}: {token!r} is not a resource amount')
    return token


def _check_clause(clause: Clause) -> Clause:
    command, args = clause.command, clause.args
    if command == 'build':
        if args[0] not in STRUCTURES:
            raise NotationError(f'Unknown structure {args[0]!r}')
        _coord(args[1], 'build')
    elif command in ('up', 'cover') and args[0] not in TRACKS | TECH_TILES:
        raise NotationError(f'{command}: unknown track or tile {args[0]!r}')
    elif command == 'tech' and args[0] not in TECH_TILES:
        raise NotationError(f'tech: unknown tile {args[0]!r}')
    elif command == 'action' and args[0] not in BOARD_ACTIONS:
        raise NotationError(f'action: unknown board action {args[0]!r}')
    elif command == 'booster' and args[0] not in BOOSTERS:
        raise NotationError(f'booster: unknown booster {args[0]!r}')
    elif command == 'fedtile':
        if args[0] not in FEDERATION_TILES and not SHIP_FEDERATION.fullmatch(args[0]):
            raise NotationError(f'fedtile: unknown federation tile {args[0]!r}')
    elif command in ('lostPlanet', 'swap-PI', 'gaiaFormTransdim'):
        _coord(args[0], command)
    elif command == 'burn':
        if not args[0].isdigit():
            raise NotationError(f'burn: {args[0]!r} is not a power count')
    elif command == 'brainstone':
        # 'discard' spends the brainstone instead of moving it between bowls.
        if args[0] not in ('area1', 'area2', 'area3', 'gaia', 'discard'):
            raise NotationError(f'brainstone: unknown destination {args[0]!r}')
    elif command in ('explore', 'spaceshipAction') and args[0] not in SPACESHIPS:
        raise NotationError(f'{command}: unknown spaceship {args[0]!r}')
    elif command in ('charge', 'income'):
        _amount(args[0], command)
    elif command == 'decline' and args:
        # Either the declined power ('2pw') or the declined offer ('up', 'tech').
        if args[0] not in ('up', 'tech'):
            _amount(args[0], command)
    return clause


def _parse_clause(text: str) -> tuple[Clause, ...]:
    tokens = text.split()
    command = tokens[0]
    rest, using = _split_using(tokens[1:], command)
    args = tuple(rest)
    if command == 'spend':
        # 'spend 3pw for 1o', possibly chained: 'spend 1o for 1t. spend ...'
        if len(args) != 3 or args[1] != 'for':
            raise NotationError(f'spend: unreadable cost/gain in {text!r}')
        return (_check_clause(Clause('spend', (_amount(args[0], 'spend'),
                                               _amount(args[2], 'spend')))),)
    if command == 'pass':
        # 'pass', 'pass returning boosterN', 'pass boosterN returning boosterM'.
        taken = returned = None
        rest = list(args)
        if rest and rest[0] in BOOSTERS:
            taken = rest.pop(0)
        if rest and rest[0] == 'returning':
            if len(rest) < 2 or rest[1] not in BOOSTERS:
                raise NotationError(f'pass: unreadable booster exchange in {text!r}')
            returned = rest[1]
            del rest[:2]
        # Two fixed slots, so 'took nothing' stays distinguishable from 'returned nothing'.
        passed = Clause('pass', (taken or '', returned or ''))
        if not rest:
            return (passed,)
        # Some recorded games run the next clause straight on without the '.' separator
        # ('pass booster4 spend 1pw for 1c'). Split rather than drop the trailing clause.
        if rest[0] not in KNOWN_COMMANDS:
            raise NotationError(f'pass: unreadable booster exchange in {text!r}')
        return (passed,) + _parse_clause(' '.join(rest))
    if command == 'federation':
        # '<coord>,<coord>,... fed3 [using area1: 2]'
        if len(args) < 2:
            raise NotationError(f'federation: missing hexes or tile in {text!r}')
        hexes = tuple(_coord(h, 'federation') for h in args[0].split(','))
        if args[1] not in FEDERATION_TILES and not SHIP_FEDERATION.fullmatch(args[1]):
            raise NotationError(f'federation: unknown tile {args[1]!r}')
        return (Clause('federation', (','.join(hexes), args[1]), using),)
    if command == 'special':
        return (Clause('special', (' '.join(args),)),) if args else (Clause('special'),)
    if command == 'rotate':
        if len(args) % 2:
            raise NotationError(f'rotate: unpaired sector/rotation in {text!r}')
        return (Clause('rotate', args),)
    if command == 'faction':
        if len(args) != 1 or args[0] not in FACTIONS:
            raise NotationError(f'faction: unreadable faction in {text!r}')
        return (Clause('faction', (args[0],)),)
    if command == 'bid':
        if len(args) != 2 or args[0] not in FACTIONS or not args[1].lstrip('-').isdigit():
            raise NotationError(f'bid: unreadable bid in {text!r}')
        return (Clause('bid', (args[0], args[1])),)
    if command not in PLAIN_COMMANDS:
        raise NotationError(f'Unknown command {command!r} in {text!r}')
    arity = PLAIN_COMMANDS[command]
    allowed = arity if isinstance(arity, tuple) else (arity,)
    if len(args) not in allowed:
        raise NotationError(f'{command}: expected {allowed} arguments, got {len(args)} in {text!r}')
    return (_check_clause(Clause(command, args, using)),)


def parse_move(line: str, index: int) -> Move:
    if not isinstance(line, str) or not line.strip():
        raise NotationError(f'Move {index} is empty')
    annotations = tuple(match.group(1) for match in ANNOTATION.finditer(line))
    for annotation in annotations:
        if not (BOWL_ANNOTATION.match(annotation) or LEVEL_ANNOTATION.match(annotation)
                or FROM_ANNOTATION.match(annotation)):
            raise NotationError(f'Move {index}: unreadable annotation ({annotation})')
    stripped = ANNOTATION.sub('', line).strip()
    subject, _, rest = stripped.partition(' ')
    if subject == 'init':
        # 'init <nbPlayers> <gameId>' opens every record and commands nothing.
        parts = rest.split()
        if len(parts) != 2 or not parts[0].isdigit():
            raise NotationError(f'Move {index}: unreadable init line {line!r}')
        return Move(index, 'init', (Clause('init', (parts[0], parts[1])),), annotations, line)
    if subject not in FACTIONS and not re.fullmatch(r'p[1-8]', subject):
        raise NotationError(f'Move {index}: unknown subject {subject!r}')
    clauses = tuple(clause
                    for part in rest.split('.') if part.strip()
                    for clause in _parse_clause(part.strip()))
    if not clauses:
        raise NotationError(f'Move {index}: no clauses in {line!r}')
    return Move(index, subject, clauses, annotations, line)


def parse_history(move_history) -> tuple[Move, ...]:
    if not isinstance(move_history, list) or not move_history:
        raise NotationError('moveHistory is missing or empty')
    return tuple(parse_move(line, index) for index, line in enumerate(move_history))
