"""Literal Part 2 observations. No fitted weights, win rates, or forced selection."""
import csv
from dataclasses import dataclass, fields
from pathlib import Path
import re

BASE_FACTIONS = frozenset(('Terrans', 'Lantids', 'Xenos', 'Gleens', 'Taklons', 'Ambas',
    'HadschHallas', 'Ivits', 'Geodens', 'BalTaks', 'Firaks', 'Bescods', 'Nevlas', 'Itars'))
CSV_PATH = Path(__file__).resolve().parents[2] / 'research/strategy/bgg-openings-part2.csv'
TOKENS = {'M': 'mine', 'TS': 'trading_station', 'RL': 'research_lab',
          'PI': 'planetary_institute', 'AC': 'academy'}
LIMITS = {'mine': 8, 'trading_station': 4, 'research_lab': 3, 'planetary_institute': 1, 'academy': 2}


@dataclass(frozen=True)
class Buildings:
    mine: int = 0
    trading_station: int = 0
    research_lab: int = 0
    planetary_institute: int = 0
    academy: int = 0

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 <= value <= LIMITS[field.name]:
                raise ValueError(f'Invalid building count: {field.name}={value}')


def parse_buildings(label: str) -> Buildings:
    if not isinstance(label, str):
        raise ValueError('Opening notation must be text')
    result = {}
    for token in label.split('+'):
        match = re.fullmatch(r'([1-9][0-9]*)(M|TS|RL|PI|AC)', token)
        if match is None:
            raise ValueError(f'Invalid opening notation: {label}')
        number, symbol = match.groups()
        key = TOKENS[symbol]
        if key in result:
            raise ValueError(f'Duplicate building symbol: {label}')
        result[key] = int(number)
    return Buildings(**result)


@dataclass(frozen=True)
class Opening:
    faction: str
    label: str
    games: int
    average_score: int
    source_page: int
    source_row: int

    def __post_init__(self):
        if self.faction not in BASE_FACTIONS:
            raise ValueError(f'No BGG Part 2 table for {self.faction}')
        if (type(self.games) is not int or self.games < 5
                or type(self.average_score) is not int or self.average_score < 0
                or type(self.source_page) is not int or self.source_page not in range(2, 9)
                or type(self.source_row) is not int or self.source_row < 1):
            raise ValueError('Invalid source observation metadata')
        parse_buildings(self.label)

    @property
    def buildings(self) -> Buildings:
        return parse_buildings(self.label)


def load_catalog(path: Path = CSV_PATH) -> dict[str, tuple[Opening, ...]]:
    catalog: dict[str, list[Opening]] = {}
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['faction', 'source_page', 'source_row', 'opening', 'games', 'average_score']:
            raise ValueError('Unexpected opening CSV schema')
        for row in reader:
            opening = Opening(row['faction'], row['opening'], int(row['games']),
                int(row['average_score']), int(row['source_page']), int(row['source_row']))
            rows = catalog.setdefault(opening.faction, [])
            if (opening.source_row != len(rows) + 1
                    or any(r.buildings == opening.buildings for r in rows)
                    or rows and (opening.source_page != rows[0].source_page or opening.games > rows[-1].games)):
                raise ValueError(f'Duplicate or out-of-order source row: {opening}')
            rows.append(opening)
    if set(catalog) != BASE_FACTIONS:
        raise ValueError('Missing or unexpected source faction')
    # User-approved A-open candidates; preserve source order and provenance.
    allowed = {'Terrans': ('1AC+1M', '1RL+2M', '1RL+4M'), 'HadschHallas': ('1RL+4M', '1RL+1TS+2M'), 'Xenos': ('1RL+5M', '1RL+4M', '1RL+1TS+2M'), 'Taklons': ('1RL+5M', '1RL+4M')}
    return {f: tuple(row for row in rows
                     if f not in allowed or row.label in allowed[f])
            for f, rows in catalog.items()}
