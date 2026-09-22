"""Identical native/source guards for competition and training, without Torch."""
import hashlib

from gaia_rl._native import SOURCE_MANIFEST
from gaia_rl.versions import require_current_sources, require_compatible_versions
from current_actions.evaluate import source_hashes
from four_factions.value import ROOT, INCOME_PATH


def hashes():
    result = source_hashes()
    files = [ROOT / line.split('  ', 1)[1] for line in SOURCE_MANIFEST.splitlines()]
    files += list((ROOT/'gaia-rl/python/gaia_rl').rglob('*.py'))
    files += [INCOME_PATH, ROOT/'gaia-engine/examples/income_projection_data.rs',
              ROOT/'gaia-rl/examples/faction_lineups.rs',
              ROOT/'gaia-rl/research/strategy/bgg-openings-part2.csv']
    for path in files:
        result[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def verify(manifest):
    require_current_sources(ROOT)
    require_compatible_versions(manifest['versions'])
    if hashes() != manifest['source_hashes']:
        raise ValueError('Pinned experiment/income sources changed; no silent continuation')
