"""Bounded local RLlib PPO runs. No server integration and no implicit long training."""
import argparse
from functools import partial
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
from .encoding import FeatureEncoder, FeatureEncoderV4
from .module import CandidateModule
from .versions import (model_build_id, require_current_sources, require_compatible_versions,
                       require_loadable_checkpoint, runtime_versions)

ENCODERS = {3: FeatureEncoder, 4: FeatureEncoderV4}
# Settings saved before the encoding and the width were arguments: encoding 3 at width 64.
MODEL_DEFAULTS = {'encoding': 3, 'width': 64}
# Settings saved before the sampling processes and the minibatch size were arguments (restore_run compares with these).
SETTING_DEFAULTS = {**MODEL_DEFAULTS, 'env_runners': 0, 'minibatch_size': 8}


def shared_policy(agent_id, *args, **kwargs):
    return 'shared'


def model_settings(settings):
    return {key: settings.get(key, value) for key, value in MODEL_DEFAULTS.items()}


def episode_env(runner):
    """The GaiaAEC of an env runner (one environment per runner)."""
    return runner.env.unwrapped.envs[0].unwrapped.env


def make_env(config):
    """The environment of one env runner. In a remote sampling process (worker index > 0, also when RLlib restarts
    it): one torch thread and its own episode seed stream (seed, worker index), set explicitly so that no two
    runners of a run play the same episodes whatever seed RLlib hands to the first reset (restore_episode_rng
    wins over that seed). The driver's environment (worker index 0) is the pilot's, unchanged."""
    env = GaiaAEC(ENCODERS[config['encoding']](config['capacity']))
    if getattr(config, 'worker_index', 0):
        torch.set_num_threads(1)
        stream = np.random.default_rng([config['seed'], config.worker_index])
        env.restore_episode_rng(stream.bit_generator.state)
    return PettingZooEnv(env)


def _runner_rng(runner):
    """(worker index, the RNG states of this sampling process)."""
    return runner.worker_index, {'python': random.getstate(), 'numpy': np.random.get_state(),
                                 'torch': torch.get_rng_state(),
                                 'episode_rng': episode_env(runner).episode_rng_state()}


def _runner_threads(runner):
    return torch.get_num_threads()


def _restore_runner_rng(runner, states):
    state = states[runner.worker_index]
    random.setstate(state['python']); np.random.set_state(state['numpy']); torch.set_rng_state(state['torch'])
    episode_env(runner).restore_episode_rng(state['episode_rng'])
    return runner.worker_index


def remote_runners(algorithm, function):
    """Run FUNCTION on every remote env runner; refuse a missing or unhealthy one (results in worker order)."""
    wanted = algorithm.config.num_env_runners
    results = algorithm.env_runner_group.foreach_env_runner(function, local_env_runner=False)
    if len(results) != wanted:
        raise RuntimeError(f'{len(results)} of {wanted} env runners answered')
    return results


def build_algorithm(seed=0, capacity=2048, batch_size=32, encoding=3, width=64, env_runners=0, minibatch_size=8):
    """encoding 4: FeatureEncoderV4 observations (GaiaAEC previews every candidate) and the encoding 4 network.

    env_runners 0 = the pilot's single process (sampling in the driver, fragments of 16 decisions). N > 0 = N
    remote sampling processes, each with one environment, one torch thread and its own episode seed stream; an
    iteration's batch is split between them (rollout fragment 'auto')."""
    if encoding not in ENCODERS:
        raise ValueError(f'unknown encoding {encoding}')
    if env_runners < 0 or minibatch_size < 1:
        raise ValueError('env_runners must be >= 0 and minibatch_size positive')
    register_env('gaia_offline', make_env)
    config = (PPOConfig()
        # RLlib's generic checker samples padded actions without consulting masks.
        # AEC API, mask and native legality tests cover this contract instead.
        .environment('gaia_offline', env_config={'capacity':capacity,'encoding':encoding,'seed':seed},
                     disable_env_checking=True)
        .framework('torch')
        .env_runners(num_env_runners=env_runners, rollout_fragment_length=16 if env_runners == 0 else 'auto',
                     batch_mode='truncate_episodes')
        .learners(num_learners=0,num_gpus_per_learner=0)
        .training(gamma=1.0, train_batch_size_per_learner=batch_size,
                  minibatch_size=minibatch_size,num_epochs=1,lr=0.0003,grad_clip=1.0)
        .multi_agent(policies={'shared'},policy_mapping_fn=shared_policy)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=CandidateModule,
                                             model_config={'width':width,'encoding':encoding}))
        .debugging(seed=seed,log_level='ERROR'))
    return config.build_algo()


def parameter_vector(algorithm):
    return torch.cat([p.detach().cpu().flatten() for p in algorithm.get_module('shared').parameters()])


def require_initial_model(metadata, settings):
    """Refuse an initial checkpoint whose encoding or width is not this run's.

    The candidate capacity may differ: no weight depends on it (network.build), it only sizes the padded candidate
    list, so a BC checkpoint saved at 2048 starts a run at 4096."""
    model = metadata.get('model') or dict(MODEL_DEFAULTS)
    wanted = model_settings(settings)
    if metadata['encoding_version'] != wanted['encoding'] or model != wanted:
        raise ValueError('Initial checkpoint encoding/width differ from this run')


def initialize_from(algorithm, source, settings):
    """Start from saved policy weights (tools/bc_train.py or save_run): the weights only, no optimizer and no RNG.

    The checkpoint must be loadable (versions.require_loadable_checkpoint) and have this run's encoding and width
    (require_initial_model; its candidate capacity is recorded, not required). Returns what save_run records as
    `initialized_from`."""
    source = Path(source).resolve()
    metadata = json.loads((source/'metadata.json').read_text())
    require_loadable_checkpoint(metadata)
    require_initial_model(metadata, settings)
    weights = torch.load(source/'inference.pt', weights_only=True, map_location='cpu')
    algorithm.learner_group.set_weights({'shared': {key: value.cpu().numpy() for key, value in weights.items()}})
    algorithm.env_runner_group.sync_weights(from_worker_or_learner_group=algorithm.learner_group,
                                            inference_only=True)
    applied = algorithm.get_module('shared').state_dict()
    for key, value in weights.items():
        if not torch.equal(applied[key].cpu(), value):
            raise RuntimeError(f'Initial weights were not applied: {key}')
    return {'checkpoint': str(source), 'model_build_id': metadata.get('model_build_id'),
            'iteration': metadata.get('iteration'), 'behaviour_cloning': 'behaviour_cloning' in metadata,
            'capacity': metadata['settings']['capacity']}


def save_run(algorithm, destination, settings, iteration, initialized_from=None):
    destination = Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=False)
    algorithm.save_to_path(str(destination/'algorithm'))
    torch.save(algorithm.get_module('shared').state_dict(),destination/'inference.pt')
    # The driver's RNG (the learner's minibatch order; with env_runners 0 also the sampling) and the episode seed
    # stream of every sampling process. With remote runners the driver has no environment: `runners` holds each
    # remote process's own python/numpy/torch state and episode stream, keyed by worker index.
    remote = settings.get('env_runners', 0)
    torch.save({'python':random.getstate(),'numpy':np.random.get_state(),
                'torch':torch.get_rng_state(),
                'episode_rng':None if remote else episode_env(algorithm.env_runner).episode_rng_state(),
                'runners':dict(remote_runners(algorithm, _runner_rng)) if remote else {}},destination/'rng.pt')
    model = model_settings(settings)
    # versions = the full record of this run; model_build_id = what OfflinePolicy and initialize_from check.
    metadata = {'versions':runtime_versions(),'model_build_id':model_build_id(),
                'encoding_version':model['encoding'],'model':model,
                'settings':settings,'iteration':iteration,
                'resume_semantics':'optimizer/model restored; new episodes at resume boundary'}
    if initialized_from:
        metadata['initialized_from'] = initialized_from
    # Metadata is the completion marker: incomplete checkpoints have no marker.
    (destination/'metadata.json').write_text(json.dumps(metadata,indent=2))


def restore_run(algorithm, source, settings):
    source=Path(source).resolve()
    metadata=json.loads((source/'metadata.json').read_text())
    # Strict on purpose: a resumed run continues the optimizer and the RNG, so every package source must be the
    # saved one. Starting a new run from weights is initialize_from (model sources only).
    require_compatible_versions(metadata['versions'])
    if (metadata['encoding_version']!=model_settings(settings)['encoding']
            or {**SETTING_DEFAULTS,**metadata['settings']}!={**SETTING_DEFAULTS,**settings}):
        raise ValueError('Checkpoint encoding/training settings differ')
    algorithm.restore_from_path(str(source/'algorithm'))
    # This is a local, trusted checkpoint created by save_run, never an uploaded file.
    rng=torch.load(source/'rng.pt',weights_only=False,map_location='cpu')
    random.setstate(rng['python']);np.random.set_state(rng['numpy']);torch.set_rng_state(rng['torch'])
    remote=settings.get('env_runners',0)
    if remote:
        # Every saved sampling process gets its own state back; a different set of workers is not a resume.
        if sorted(rng.get('runners') or {})!=list(range(1,remote+1)):
            raise ValueError('Checkpoint has no RNG state for these env runners')
        restored=remote_runners(algorithm,partial(_restore_runner_rng,states=rng['runners']))
        if sorted(restored)!=sorted(rng['runners']):
            raise RuntimeError('Env runner RNG states were not all restored')
    else:
        episode_env(algorithm.env_runner).restore_episode_rng(rng['episode_rng'])
    return metadata['iteration']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=1)
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--capacity',type=int,default=2048)
    parser.add_argument('--batch-size',type=int,default=32)
    parser.add_argument('--resume',type=Path)
    parser.add_argument('--encoding',type=int,choices=sorted(ENCODERS),default=3,
                        help='4 = FeatureEncoderV4 (field ids | board | outcome of the previewed state)')
    parser.add_argument('--width',type=int,help='default 64 for encoding 3, 256 for encoding 4')
    parser.add_argument('--init',type=Path,
                        help='start from the weights of this checkpoint (bc_train or an earlier run); not with --resume')
    parser.add_argument('--env-runners',type=int,default=0,
                        help='remote sampling processes (0 = sample in the driver, the pilot setting)')
    parser.add_argument('--minibatch-size',type=int,default=8)
    parser.add_argument('--max-minutes',type=float,
                        help='stop at the first iteration boundary after this many minutes (at least one iteration)')
    args=parser.parse_args()
    if args.iterations<1:
        parser.error('iterations must be positive')
    if args.env_runners<0 or args.minibatch_size<1:
        parser.error('--env-runners must be >= 0 and --minibatch-size positive')
    if args.init and args.resume:
        parser.error('--init starts a new run, --resume continues one: give one of them')
    width=args.width or (256 if args.encoding==4 else 64)
    root=Path(__file__).resolve().parents[3]
    require_current_sources(root)
    if args.output.exists():
        parser.error('output must not already exist')
    torch.set_num_threads(2)
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    start_versions=runtime_versions()
    settings={'seed':args.seed,'capacity':args.capacity,'batch_size':args.batch_size,'device':'cpu',
              'encoding':args.encoding,'width':width,'env_runners':args.env_runners,
              'minibatch_size':args.minibatch_size}
    # Remote runners hand their fragments to the driver through the object store: room for a few batches of
    # padded observations (encoding 4 at capacity 4096 is 5.6 MiB a decision).
    spaces=ENCODERS[args.encoding](args.capacity).observation_space.spaces.values()
    decision_bytes=sum(int(np.prod(space.shape))*space.dtype.itemsize for space in spaces)
    store=(128*1024**2 if args.env_runners==0 else
           max(1024**3,3*args.batch_size*decision_bytes))
    ray.init(num_cpus=2+args.env_runners,include_dashboard=False,object_store_memory=store,
             log_to_driver=False)
    algorithm=None
    try:
        algorithm=build_algorithm(args.seed,args.capacity,args.batch_size,args.encoding,width,
                                  args.env_runners,args.minibatch_size)
        previous=restore_run(algorithm,args.resume,settings) if args.resume else 0
        # A resumed run keeps the record of where its first weights came from.
        origin=(initialize_from(algorithm,args.init,settings) if args.init else
                json.loads((args.resume.resolve()/'metadata.json').read_text()).get('initialized_from')
                if args.resume else None)
        before=parameter_vector(algorithm)
        start=time.monotonic();results=[];iteration_seconds=[]
        for i in range(args.iterations):
            began=time.monotonic()
            result=algorithm.train()
            iteration_seconds.append(time.monotonic()-began)
            learner=result['learners']['shared']
            for key in ('total_loss','policy_loss','vf_loss'):
                if key not in learner or not np.isfinite(learner[key]):
                    raise RuntimeError(f'PPO loss missing or non-finite: {key}')
            results.append(result)
            print(f'iteration {previous+i+1} completed',flush=True)
            if args.max_minutes is not None and time.monotonic()-start>=args.max_minutes*60:
                break
        done=len(results)
        after=parameter_vector(algorithm)
        if not torch.isfinite(after).all() or torch.equal(before,after):
            raise RuntimeError('PPO pilot failed: non-finite or unchanged parameters')
        require_compatible_versions(start_versions)
        save_run(algorithm,args.output,settings,previous+done,origin)
        report={'seconds':time.monotonic()-start,
                'iterations':done,'iteration_seconds':iteration_seconds,
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
