"""Bounded local RLlib PPO runs. No server integration and no implicit long training."""
import argparse
import json
from pathlib import Path
import random
import resource
import time

import numpy as np
import torch
import ray
from ray.tune.registry import register_env
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.core.rl_module.rl_module import RLModuleSpec
from ray.rllib.env.wrappers.pettingzoo_env import PettingZooEnv

from .aec import GaiaAEC
from .encoding import FeatureEncoder, ENCODING_VERSION
from .module import CandidateModule
from .versions import require_current_sources, require_compatible_versions, runtime_versions


def shared_policy(agent_id, *args, **kwargs):
    return 'shared'


def build_algorithm(seed=0, capacity=2048, batch_size=32):
    register_env('gaia_offline', lambda config: PettingZooEnv(
        GaiaAEC(FeatureEncoder(config['capacity']))))
    config = (PPOConfig()
        # RLlib's generic checker samples padded actions without consulting masks.
        # AEC API, mask and native legality tests cover this contract instead.
        .environment('gaia_offline', env_config={'capacity':capacity},disable_env_checking=True)
        .framework('torch')
        .env_runners(num_env_runners=0, rollout_fragment_length=16,
                     batch_mode='truncate_episodes')
        .learners(num_learners=0,num_gpus_per_learner=0)
        .training(gamma=1.0, train_batch_size_per_learner=batch_size,
                  minibatch_size=8,num_epochs=1,lr=0.0003,grad_clip=1.0)
        .multi_agent(policies={'shared'},policy_mapping_fn=shared_policy)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=CandidateModule,
                                             model_config={'width':64}))
        .debugging(seed=seed,log_level='ERROR'))
    return config.build_algo()


def parameter_vector(algorithm):
    return torch.cat([p.detach().cpu().flatten() for p in algorithm.get_module('shared').parameters()])


def save_run(algorithm, destination, settings, iteration):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=False)
    algorithm.save_to_path(str(destination/'algorithm'))
    torch.save(algorithm.get_module('shared').state_dict(),destination/'inference.pt')
    torch.save({'python':random.getstate(),'numpy':np.random.get_state(),
                'torch':torch.get_rng_state(),
                'episode_rng':algorithm.env_runner.env.unwrapped.envs[0].unwrapped.env._seed_rng.bit_generator.state},destination/'rng.pt')
    metadata = {'versions':runtime_versions(),'encoding_version':ENCODING_VERSION,
                'settings':settings,'iteration':iteration,
                'resume_semantics':'optimizer/model restored; new episodes at resume boundary'}
    # Metadata is the completion marker: incomplete checkpoints have no marker.
    (destination/'metadata.json').write_text(json.dumps(metadata,indent=2))


def restore_run(algorithm, source, settings):
    source=Path(source).resolve()
    metadata=json.loads((source/'metadata.json').read_text())
    require_compatible_versions(metadata['versions'])
    if metadata['encoding_version']!=ENCODING_VERSION or metadata['settings']!=settings:
        raise ValueError('Checkpoint encoding/training settings differ')
    algorithm.restore_from_path(str(source/'algorithm'))
    # This is a local, trusted checkpoint created by save_run, never an uploaded file.
    rng=torch.load(source/'rng.pt',weights_only=False,map_location='cpu')
    random.setstate(rng['python']);np.random.set_state(rng['numpy']);torch.set_rng_state(rng['torch'])
    algorithm.env_runner.env.unwrapped.envs[0].unwrapped.env.restore_episode_rng(rng['episode_rng'])
    return metadata['iteration']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=1)
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--capacity',type=int,default=2048)
    parser.add_argument('--batch-size',type=int,default=32)
    parser.add_argument('--resume',type=Path)
    args=parser.parse_args()
    if args.iterations<1:
        parser.error('iterations must be positive')
    root=Path(__file__).resolve().parents[3]
    require_current_sources(root)
    if args.output.exists():
        parser.error('output must not already exist')
    torch.set_num_threads(2)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    start_versions=runtime_versions()
    settings={'seed':args.seed,'capacity':args.capacity,'batch_size':args.batch_size,'device':'cpu'}
    ray.init(num_cpus=2,include_dashboard=False,object_store_memory=128*1024**2,
             log_to_driver=False)
    algorithm=None
    try:
        algorithm=build_algorithm(args.seed,args.capacity,args.batch_size)
        previous=restore_run(algorithm,args.resume,settings) if args.resume else 0
        before=parameter_vector(algorithm)
        start=time.monotonic();results=[]
        for i in range(args.iterations):
            result=algorithm.train()
            learner=result['learners']['shared']
            for key in ('total_loss','policy_loss','vf_loss'):
                if key not in learner or not np.isfinite(learner[key]):
                    raise RuntimeError(f'PPO loss missing or non-finite: {key}')
            results.append(result)
            print(f'iteration {previous+i+1} completed',flush=True)
        after=parameter_vector(algorithm)
        if not torch.isfinite(after).all() or torch.equal(before,after):
            raise RuntimeError('PPO pilot failed: non-finite or unchanged parameters')
        require_compatible_versions(start_versions)
        save_run(algorithm,args.output,settings,previous+args.iterations)
        report={'seconds':time.monotonic()-start,
                'peak_driver_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                'parameter_delta_l2':torch.linalg.vector_norm(after-before).item(),
                'results':results}
        (args.output/'pilot.json').write_text(json.dumps(report,default=lambda x:x.tolist() if hasattr(x,'tolist') else str(x),indent=2))
        print(json.dumps({k:v for k,v in report.items() if k!='results'}),flush=True)
    finally:
        if algorithm is not None:
            algorithm.stop()
        ray.shutdown()


if __name__=='__main__':
    main()
