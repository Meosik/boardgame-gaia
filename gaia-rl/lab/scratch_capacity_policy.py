"""Does the trained v4 checkpoint work with a larger run-time candidate capacity (HANDOFF E165, Codex debate)?
Replays game 20 of 119 (quartet-b-98306) up to the 2,257-candidate decision at step 217 and scores decisions with
the same weights under an encoder of capacity 2048 and of capacity 4096. Nothing is written."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/tools']
import bc_dataset
from gaia_rl import Environment
from gaia_rl.encoding import EncodingError, FeatureEncoderV4
from gaia_rl.evaluation import OfflinePolicy
from ray.rllib.core.columns import Columns

game = list(bc_dataset._load('gaia-rl/runs/bc-119-fc19/manifest.jsonl'))[20]
policy = OfflinePolicy('gaia-rl/runs/bc-114-v4-w256-fc19/fold-0')
encoders = {2048: policy.encoder, 4096: FeatureEncoderV4(4096)}
assert policy.encoder.candidate_capacity == 2048


def logits(encoder, snapshot, previews):
    observation = encoder.encode(snapshot, snapshot['player'], previews)
    with torch.no_grad():
        batch = {Columns.OBS: {key: torch.as_tensor(value).unsqueeze(0) for key, value in observation.items()}}
        return policy.module.forward_inference(batch)[Columns.ACTION_DIST_INPUTS][0].numpy()


env = Environment(game['seed'], 2000)
compared = largest = 0
for step, row in enumerate(bc_dataset._rows(Path(game['game']))):
    snapshot = json.loads(env.snapshot_json())
    n = len(snapshot['candidates'])
    if snapshot.get('player') is not None and (step % 20 == 0 or step >= 210):
        previews = [json.loads(env.preview_state_json(snapshot['decision_id'], i)) for i in range(n)]
        wide = logits(encoders[4096], snapshot, previews)
        try:
            narrow = logits(encoders[2048], snapshot, previews)
        except EncodingError as error:
            print(json.dumps({'step': step, 'candidates': n, 'capacity 2048': str(error),
                              'capacity 4096': {'logits': len(wide), 'finite on legal': bool(np.isfinite(wide[:n]).all()),
                                                'argmax': int(wide.argmax()), 'teacher chose': row['index']}}))
        else:
            difference = float(np.abs(wide[:n]-narrow[:n]).max())
            largest = max(largest, difference)
            compared += 1
            assert int(wide.argmax()) == int(narrow.argmax()) < n
    if step == 217:
        break
    env.step(row['decision_id'], row['index'])
print('decisions compared', compared, '| largest logit difference on legal candidates', largest)
