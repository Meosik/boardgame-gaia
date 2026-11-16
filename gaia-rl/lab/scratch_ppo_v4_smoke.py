"""Smoke of encoding 4 PPO from a BC checkpoint (HANDOFF E153 step 3b): build_algorithm(encoding 4), initialize_from,
one training iteration, save_run, OfflinePolicy on the saved run.

Skips training.main's require_current_sources on purpose: the work tree's compiled engine is older than its source
(gaia-engine/src/rules/ai_federation.rs, 966e9ea), so `python -m gaia_rl.training` refuses to start until the user
rebuilds. This is a throwaway check of the Python path, not a run of record.

Usage: scratch_ppo_v4_smoke.py <initial checkpoint> <new output directory>
"""
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import ray
import torch

from gaia_rl import Environment
from gaia_rl.evaluation import OfflinePolicy
from gaia_rl.training import build_algorithm, initialize_from, parameter_vector, save_run

init, out = Path(sys.argv[1]), Path(sys.argv[2])
torch.set_num_threads(2)
random.seed(0); np.random.seed(0); torch.manual_seed(0)
settings = {'seed': 0, 'capacity': 2048, 'batch_size': 32, 'device': 'cpu', 'encoding': 4, 'width': 256}
ray.init(num_cpus=2, include_dashboard=False, object_store_memory=128*1024**2, log_to_driver=False)
algorithm = None
try:
    start = time.monotonic()
    algorithm = build_algorithm(0, 2048, 32, 4, 256)
    origin = initialize_from(algorithm, init, settings)
    before = parameter_vector(algorithm)
    result = algorithm.train()
    learner = result['learners']['shared']
    after = parameter_vector(algorithm)
    assert torch.isfinite(after).all() and not torch.equal(before, after)
    save_run(algorithm, out, settings, 1, origin)
    print(json.dumps({'seconds': round(time.monotonic()-start, 1),
                      'losses': {key: float(learner[key]) for key in ('total_loss', 'policy_loss', 'vf_loss')},
                      'delta_l2': torch.linalg.vector_norm(after-before).item(), 'initialized_from': origin}))
finally:
    if algorithm is not None:
        algorithm.stop()
    ray.shutdown()
metadata = json.loads((out/'metadata.json').read_text())
policy = OfflinePolicy(out)
env = Environment('quartet-a-72715')
snapshot = json.loads(env.snapshot_json())
print({key: metadata[key] for key in ('encoding_version', 'model', 'iteration')}, policy.encoding,
      policy.choose(snapshot, env))
