"""Opt-in fresh-model, single-update CUDA diagnostic; not a resumable trainer."""
import argparse
import json
import os
from pathlib import Path
import random
import socket
import subprocess
import time


def require_compute_node() -> None:
    job_id = os.environ.get('SLURM_JOB_ID')
    nodes = os.environ.get('SLURM_JOB_NODELIST')
    if not job_id or not nodes:
        raise RuntimeError('Run inside a Slurm GPU allocation, not on the login node')
    allocated = subprocess.check_output(
        ['scontrol', 'show', 'hostnames', nodes], text=True).splitlines()
    if socket.gethostname().split('.')[0] not in [n.split('.')[0] for n in allocated]:
        raise RuntimeError('This host is not an allocated compute node')


def prepare_output(output: Path) -> Path:
    output = output.resolve()
    if not any(output.is_relative_to(root) for root in (Path('/tmp'), Path('/local_datasets'))):
        raise ValueError('Output must be node-local under /tmp or /local_datasets')
    output.mkdir(parents=True, exist_ok=False)
    # Ray 2.58 defaults to ~/ray_results. Isolate HOME in this diagnostic process
    # before importing Ray, without changing the user's real home or shell.
    for name, directory in {'HOME': 'home', 'TMPDIR': 'tmp',
                            'XDG_CACHE_HOME': 'cache'}.items():
        path = output / directory
        path.mkdir()
        os.environ[name] = str(path)
    return output


def build_config():
    from ray.tune.registry import register_env
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.rllib.core.rl_module.rl_module import RLModuleSpec
    from ray.rllib.env.wrappers.pettingzoo_env import PettingZooEnv
    from gaia_rl.aec import GaiaAEC
    from gaia_rl.encoding import FeatureEncoder
    from gaia_rl.module import CandidateModule
    from gaia_rl.training import shared_policy

    register_env('gaia_offline', lambda config: PettingZooEnv(
        GaiaAEC(FeatureEncoder(config['capacity']))))
    # Match the CPU pilot's learning/game settings; only the learner GPU differs.
    return (PPOConfig()
        .environment('gaia_offline', env_config={'capacity': 2048}, disable_env_checking=True)
        .framework('torch')
        .env_runners(num_env_runners=0, rollout_fragment_length=16,
                     batch_mode='truncate_episodes')
        .learners(num_learners=0, num_gpus_per_learner=1, local_gpu_idx=0)
        .training(gamma=1.0, train_batch_size_per_learner=32,
                  minibatch_size=8, num_epochs=1, lr=0.0003, grad_clip=1.0)
        .multi_agent(policies={'shared'}, policy_mapping_fn=shared_policy)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=CandidateModule,
                                             model_config={'width': 64}))
        .debugging(seed=0, log_level='ERROR'))


def learner_state(algorithm):
    def inspect(learner):
        module = learner.module['shared']
        if not all(p.device.type == 'cuda' for p in module.parameters()):
            raise RuntimeError('PPO learner parameters are not all on CUDA')
        return {key: value.detach().cpu().clone() for key, value in module.state_dict().items()}

    results = list(algorithm.learner_group.foreach_learner(inspect))
    if len(results) != 1:
        raise RuntimeError('Expected exactly one local learner')
    if not results[0].ok:
        raise results[0].get()
    return results[0].get()


def run_smoke(output: Path) -> dict:
    import numpy as np
    import torch
    import ray
    from gaia_rl.versions import require_current_sources, require_compatible_versions, runtime_versions

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('Exactly one visible CUDA GPU required; no CPU fallback')
    require_current_sources(Path(__file__).resolve().parents[2])
    versions = runtime_versions()
    torch.set_num_threads(2)
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    algorithm = None
    started = time.monotonic()
    try:
        # Explicit local Ray prevents accidentally joining another user's cluster.
        ray.init(address='local', num_cpus=2, num_gpus=1, include_dashboard=False,
                 object_store_memory=128 * 1024**2, log_to_driver=False)
        algorithm = build_config().build_algo()
        before = learner_state(algorithm)
        result = algorithm.train()
        losses = {key: float(result['learners']['shared'][key])
                  for key in ('total_loss', 'policy_loss', 'vf_loss')}
        if not all(np.isfinite(value) for value in losses.values()):
            raise RuntimeError('Non-finite PPO loss')
        after = learner_state(algorithm)
        delta = torch.cat([(after[key] - before[key]).flatten() for key in before])
        if not torch.isfinite(delta).all() or not torch.any(delta != 0):
            raise RuntimeError('Non-finite or unchanged learner parameters')
        require_compatible_versions(versions)
        torch.save(after, output / 'diagnostic-weights.pt')
        report = {'status': 'complete', 'iterations': 1, 'fresh_model': True,
                  'resumable': False, 'learner_device': 'cuda:0',
                  'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
                  'cuda_runtime': torch.version.cuda, 'versions': versions,
                  'slurm_job_id': os.environ.get('SLURM_JOB_ID'),
                  'host': socket.gethostname(), 'losses': losses,
                  'parameter_delta_l2': torch.linalg.vector_norm(delta).item(),
                  'seconds': time.monotonic() - started}
    finally:
        try:
            if algorithm is not None:
                algorithm.stop()
        finally:
            ray.shutdown()
    # Written only after successful training, validation, weights save and shutdown.
    (output / 'complete.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require_compute_node()
    output = prepare_output(args.output)
    try:
        print(json.dumps(run_smoke(output), indent=2), flush=True)
    except Exception as error:
        (output / 'failure.json').write_text(json.dumps(
            {'status': 'failed', 'error': str(error)}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
