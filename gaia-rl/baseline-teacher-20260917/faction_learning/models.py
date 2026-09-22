"""Immutable inference catalogs, not a replacement for full PPO checkpoints."""
from hashlib import sha256
import json
from pathlib import Path

from . import FACTIONS

ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def implementation_hashes():
    return {p.name: digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}


def make_module(capacity=4096):
    from gymnasium import spaces
    from gaia_rl.encoding import FeatureEncoder
    from gaia_rl.module import CandidateModule
    encoder = FeatureEncoder(capacity)
    return CandidateModule(observation_space=encoder.observation_space,
        action_space=spaces.Discrete(capacity), model_config={'width': 64})


def validate_weights(weights, capacity):
    import torch
    module = make_module(capacity)
    expected = module.state_dict()
    if not isinstance(weights, dict) or weights.keys() != expected.keys():
        raise ValueError('Unexpected model tensor names')
    for name, tensor in weights.items():
        if (not isinstance(tensor, torch.Tensor) or tensor.shape != expected[name].shape
                or tensor.dtype != expected[name].dtype or not torch.isfinite(tensor).all()):
            raise ValueError(f'Invalid model tensor: {name}')
    module.load_state_dict(weights, strict=True)
    return module


def read_catalog(source):
    from gaia_rl.encoding import ENCODING_VERSION
    from gaia_rl.versions import require_compatible_versions, require_current_sources
    source = Path(source)
    data = json.loads((source / 'catalog.json').read_text())
    require_current_sources(ROOT)
    require_compatible_versions(data['versions'])
    if (data.get('schema') != 1 or data.get('encoding_version') != ENCODING_VERSION
            or data.get('capacity') != 4096 or set(data['models']) != set(FACTIONS)
            or data.get('promotion') is not False):
        raise ValueError('Unsupported faction catalog')
    for faction, entry in data['models'].items():
        if entry['status'] not in ('untrained', 'ppo_import', 'bc_candidate', 'ppo_candidate'):
            raise ValueError('Unknown training status')
        path = source / faction / 'inference.pt'
        if path.is_symlink() or path.parent.is_symlink() or digest(path) != entry['sha256']:
            raise ValueError(f'Model checksum differs: {faction}')
    return data


def load_model(source, faction):
    import torch
    if faction not in FACTIONS:
        raise ValueError(f'Unknown faction: {faction}')
    data = read_catalog(source)
    weights = torch.load(Path(source) / faction / 'inference.pt',
                         map_location='cpu', weights_only=True)
    return validate_weights(weights, data['capacity']), data


def initialize(destination, *, source=None, seed=19):
    """Copy explicitly selected trained policies; independently initialize the rest.

    Source PPO optimizer/RNG files are kept at their original location. The new
    catalog deliberately does not claim that inference weights can resume PPO.
    """
    import torch
    from gaia_rl.encoding import ENCODING_VERSION
    from gaia_rl.versions import (require_compatible_versions, require_current_sources,
                                 runtime_versions)
    require_current_sources(ROOT)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    imported, provenance = {}, None
    if source is not None:
        source = Path(source).resolve()
        metadata = json.loads((source / 'metadata.json').read_text())
        require_compatible_versions(metadata['versions'])
        if metadata['encoding_version'] != ENCODING_VERSION:
            raise ValueError('Incompatible encoding')
        imported = torch.load(source / 'inference.pt', map_location='cpu', weights_only=True)
        if (not imported or set(imported) != set(metadata['factions'])
                or not set(imported) <= set(FACTIONS)):
            raise ValueError('Checkpoint faction identities differ')
        for weights in imported.values():
            validate_weights(weights, 4096)
        provenance = {'checkpoint': str(source), 'metadata_sha256': digest(source / 'metadata.json'),
                      'inference_sha256': digest(source / 'inference.pt'),
                      'optimizer': 'original full PPO checkpoint preserved, not reset or copied'}
    destination.mkdir(parents=True, exist_ok=False)
    entries = {}
    # Do not alter the caller's RNG or share parameter storage across factions.
    with torch.random.fork_rng(devices=[]):
        for index, faction in enumerate(FACTIONS):
            torch.manual_seed(seed + index)
            weights = imported[faction] if faction in imported else make_module().state_dict()
            folder = destination / faction
            folder.mkdir()
            torch.save(weights, folder / 'inference.pt')
            entries[faction] = {'sha256': digest(folder / 'inference.pt'),
                'status': 'ppo_import' if faction in imported else 'untrained',
                'initialization_seed': None if faction in imported else seed + index}
    write_json(destination / 'catalog.json', {'schema': 1, 'versions': runtime_versions(),
        'encoding_version': ENCODING_VERSION, 'capacity': 4096, 'models': entries,
        'source': provenance, 'implementation': implementation_hashes(), 'promotion': False,
        'resume': 'inference/BC initialization only; use source checkpoint for exact PPO resume'})
    return read_catalog(destination)
