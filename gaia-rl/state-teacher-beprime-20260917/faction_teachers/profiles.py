"""Native faction facts plus existing source coverage, not invented strategy weights."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import tomllib

from bgg_openings.catalog import Opening, load_catalog
from faction_learning import FACTIONS

ROOT = Path(__file__).resolve().parents[3]
GUIDES = {'Terrans': 'B04', 'Gleens': 'B05', 'Ambas': 'B06', 'Itars': 'B07',
          'Nevlas': 'B08', 'Firaks': 'B09', 'Taklons': 'B10', 'BalTaks': 'B11',
          'Ivits': 'B12', 'Bescods': 'B13', 'Geodens': 'B14', 'Xenos': 'B15',
          'Lantids': 'B16', 'HadschHallas': 'B17'}


@dataclass(frozen=True)
class Profile:
    faction: str
    home: str
    starting_structures: int
    openings: tuple[Opening, ...]
    sources: tuple[str, ...]
    coverage: str = 'source-openings-and-native-effects; not a validated expert'


@lru_cache(maxsize=1)
def profiles():
    native = tomllib.loads((ROOT/'gaia-engine/data/factions.toml').read_text())['factions']
    catalog = load_catalog()
    result = {row['id']: Profile(row['id'], row['home_planet'], len(row['starting_structures']),
                    catalog.get(row['id'], ()),
                    ('BGG-O2', GUIDES[row['id']]) if row['id'] in catalog else ('native-rules', 'LF04'),
                    'source-openings-and-native-effects; not a validated expert' if row['id'] in catalog
                    else 'native-baseline; no BGG opening or dedicated faction guide') for row in native}
    if set(result) != set(FACTIONS):
        raise ValueError('Native faction roster differs from the student roster')
    return result
