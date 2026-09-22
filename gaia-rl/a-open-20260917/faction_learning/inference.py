"""Pinned, native-seat inference API. Server/global player IDs must not enter it."""
from pathlib import Path

import torch
from ray.rllib.core.columns import Columns

from gaia_rl.encoding import FeatureEncoder
from .models import digest, load_model


class PinnedPolicy:
    def __init__(self, source, faction):
        self.source = Path(source)
        self.faction = faction
        self.module, self.catalog = load_model(source, faction)
        if self.catalog['models'][faction]['status'] == 'untrained':
            raise ValueError('Untrained initialization is not a trained opponent')
        self.module.eval()
        self.encoder = FeatureEncoder(self.catalog['capacity'])
        self.catalog_sha256 = digest(self.source / 'catalog.json')
        self.model_sha256 = self.catalog['models'][faction]['sha256']

    def choose(self, snapshot):
        players = snapshot['state']['players']
        actor = snapshot['player']
        if ([p['player_id'] for p in players] != list(range(4))
                or type(actor) is not int or actor not in range(4)):
            raise ValueError('Only canonical native seats 0..3 are supported')
        if players[actor]['faction'] != self.faction:
            raise ValueError('Cross-faction inference request')
        if not snapshot['candidates']:
            raise ValueError('No native candidates; no fallback pass is permitted')
        obs = self.encoder.encode(snapshot, actor)
        inputs = {Columns.OBS: {k: torch.from_numpy(v).unsqueeze(0) for k, v in obs.items()}}
        with torch.no_grad():
            logits = self.module.forward_inference(inputs)[Columns.ACTION_DIST_INPUTS][0]
            if not torch.isfinite(logits[:len(snapshot['candidates'])]).all():
                raise ValueError('Non-finite inference logits')
            index = int(logits.argmax())
        if index >= len(snapshot['candidates']):
            raise ValueError('Model selected a padded action')
        return {'decision_id': snapshot['decision_id'], 'index': index,
            'action': snapshot['candidates'][index], 'faction': self.faction,
            'model_sha256': self.model_sha256, 'catalog_sha256': self.catalog_sha256}
