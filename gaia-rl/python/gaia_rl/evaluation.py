"""Held-out complete games, rotating the candidate through all four seats."""
import argparse
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from gymnasium import spaces
from ray.rllib.core.columns import Columns

from ._native import Environment
from .encoding import FeatureEncoder, ENCODING_VERSION
from .module import CandidateModule
from .versions import require_current_sources, require_compatible_versions, runtime_versions


class OfflinePolicy:
    """Inference-only boundary for future integration; never mutates game state."""
    def __init__(self, checkpoint):
        checkpoint=Path(checkpoint)
        metadata=json.loads((checkpoint/'metadata.json').read_text())
        require_compatible_versions(metadata['versions'])
        if metadata['encoding_version']!=ENCODING_VERSION:
            raise ValueError('Incompatible observation encoding')
        self.encoder=FeatureEncoder(metadata['settings']['capacity'])
        self.module=CandidateModule(observation_space=self.encoder.observation_space,
            action_space=spaces.Discrete(self.encoder.candidate_capacity),model_config={'width':64})
        self.module.load_state_dict(torch.load(checkpoint/'inference.pt',weights_only=True,map_location='cpu'))
        self.module.eval()

    def choose(self,snapshot):
        if snapshot['player'] is None or not snapshot['candidates']:
            raise ValueError('No live decision to choose')
        observation=self.encoder.encode(snapshot,snapshot['player'])
        with torch.no_grad():
            batch={Columns.OBS:{key:torch.as_tensor(value).unsqueeze(0) for key,value in observation.items()}}
            logits=self.module.forward_inference(batch)[Columns.ACTION_DIST_INPUTS][0]
            if not torch.isfinite(logits).all():
                raise ValueError('Non-finite policy logits')
            index=int(logits.argmax())
        if not 0<=index<len(snapshot['candidates']):
            raise ValueError('Policy selected a masked action')
        return snapshot['decision_id'],index


def evaluate(policy, opponent, seed_count, prefix):
    games=[];start=time.monotonic()
    for seed in range(seed_count):
        for seat in range(4):
            env=Environment(f'{prefix}-{seed}')
            rng=random.Random(f'{prefix}-{seed}-seat-{seat}')
            while not env.is_terminal():
                snapshot=json.loads(env.snapshot_json())
                player=snapshot['player']
                current=policy if player==seat else opponent
                decision,index=(current.choose(snapshot) if current else
                                (snapshot['decision_id'],rng.randrange(len(snapshot['candidates']))))
                env.step(decision,index)
            scores=dict(env.final_scores());best=max(scores.values())
            winners=sum(score==best for score in scores.values())
            games.append({'seed':f'{prefix}-{seed}','seat':seat,'scores':scores,
                          'vp':scores[seat], 'win_share':1/winners if scores[seat]==best else 0,
                          'steps':json.loads(env.snapshot_json())['steps']})
            print(f'evaluated seed {seed}, seat {seat}: {scores}',flush=True)
    # Bootstrap whole seed groups: rotations of the same map are not independent games.
    groups=np.array([np.mean([g['win_share'] for g in games if g['seed']==f'{prefix}-{seed}'])
                     for seed in range(seed_count)])
    interval=None
    if seed_count>=2:
        rng=np.random.default_rng(0)
        means=np.mean(rng.choice(groups,size=(2000,seed_count),replace=True),axis=1)
        interval=np.quantile(means,[0.025,0.975]).tolist()
    return {'versions':runtime_versions(),'games':games,'seconds':time.monotonic()-start,
            'mean_vp':float(np.mean([g['vp'] for g in games])),
            'mean_win_share':float(groups.mean()),'seed_bootstrap_95_interval':interval,
            'warning':'Small pilot evaluation is not evidence of playing strength.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path,required=True)
    parser.add_argument('--opponent',type=Path,help='Omit for a uniform random legal-action opponent')
    parser.add_argument('--seeds',type=int,default=2)
    parser.add_argument('--seed-prefix',default='rl-heldout-v1')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.seeds<1 or args.output.exists():
        parser.error('seeds must be positive and output must not already exist')
    require_current_sources(Path(__file__).resolve().parents[3])
    torch.set_num_threads(2)
    policy=OfflinePolicy(args.checkpoint)
    opponent=OfflinePolicy(args.opponent) if args.opponent else None
    report=evaluate(policy,opponent,args.seeds,args.seed_prefix)
    report['checkpoint']=str(args.checkpoint)
    report['opponent']=str(args.opponent) if args.opponent else 'uniform-random'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report,output,indent=2)


if __name__=='__main__':
    main()
