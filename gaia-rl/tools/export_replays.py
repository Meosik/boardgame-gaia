"""Reproduce trusted local AI pilot evaluations as versioned read-only replay files."""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys

import torch
from replay_log import add_decision_log

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'gaia-rl/experiments'))
from strategy_pilot import ModulePolicy
from strategy_teacher import StrategyTeacher
from gaia_rl._native import Environment
from gaia_rl.encoding import FeatureEncoder
from gaia_rl.versions import require_current_sources,require_compatible_versions


def export_game(run,label,row,manifest):
    policy=(StrategyTeacher() if label=='teacher' else ModulePolicy(
        FeatureEncoder(manifest['settings']['capacity']),
        torch.load(run/label/'inference.pt',weights_only=True,map_location='cpu')))
    seed=row['seed'];faction=row['faction'];seat=row['seat']
    rngs=[random.Random(f'{seed}:{faction}:opponent:{p}') for p in range(4)]
    env=Environment(seed,2000);s=json.loads(env.snapshot_json());frames=[];actions=Counter()
    events=copy.deepcopy(s['state']['event_log'])
    def frame(snapshot,actor=None,action=None,candidates=None):
        state=copy.deepcopy(snapshot['state']);state.pop('event_log',None)
        legal=[c['action'] for c in candidates or [] if c['action']['type']=='FormFederation']
        return {'decision_id':snapshot['decision_id'],'player':actor,'action':action,
                'legal_action_count':len(candidates or []),'legal_federation_count':len(legal),
                'federation_example':legal[0] if legal else None,
                'event_end':len(snapshot['state']['event_log']),'state':state}
    frames.append(frame(s))
    while not env.is_terminal():
        actor=s['player']
        decision,index=policy.choose(s) if actor==seat else (s['decision_id'],rngs[actor].randrange(len(s['candidates'])))
        action=s['candidates'][index]['action']
        if actor==seat:actions[action['type']]+=1
        before=s;env.step(decision,index);s=json.loads(env.snapshot_json())
        current=s['state']['event_log']
        if current[:len(events)]!=events:raise ValueError('Event log is not append-only; cannot map indices faithfully')
        events=current;frames.append(frame(s,actor,action,before['candidates']))
    if ({str(p):v for p,v in env.final_scores()}!=row['scores'] or s['steps']!=row['steps'] or dict(actions)!=row['actions']):
        raise ValueError(f'Reproduction mismatch: {label}/{seed}/{faction}')
    return add_decision_log({'schema_version':1,'metadata':{'seed':seed,'policy':label,'faction':faction,
            'focus_player':seat,'versions':manifest['versions'],'experiment_hash':manifest.get('experiment_hash'),
            'source_hashes':manifest.get('source_hashes'),
            'scores':row['scores'],'steps':s['steps'],'reproduced_original':True},'events':events,'frames':frames})


def check_sources(manifest):
    require_current_sources(ROOT)
    require_compatible_versions(manifest['versions'])
    directories = {'original': ROOT/'gaia-rl/experiments',
                   'teacher': ROOT/'gaia-rl/experiments/economy',
                   'learning': ROOT/'gaia-rl/experiments/economy_learning'}
    expected = manifest.get('source_hashes') or {'original': manifest['experiment_hash']}
    for name, saved in expected.items():
        digest = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(directories[name].glob('*.py')))).hexdigest()
        if digest != saved:
            raise ValueError(f'Experiment implementation differs from saved evaluation: {name}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads((args.run/'manifest.json').read_text());check_sources(manifest)
    learning = 'source_hashes' in manifest
    labels = ('continued_ppo','bc_only','economy_bc_ppo') if learning else ('baseline','imitation_plus_ppo','teacher')
    prefix = f'{args.run.name}-' if learning else ''
    if args.output.exists():parser.error('output must be new')
    args.output.mkdir(parents=True);catalog=[]
    for label in labels:
        rows=json.loads((args.run/f'{label}_evaluation.json').read_text())
        for i,row in enumerate(rows):
            if not row['complete']:raise ValueError('Cannot export an incomplete evaluation as complete')
            replay=export_game(args.run,label,row,manifest)
            name=f'{prefix}{label}-{i}.json.gz';path=args.output/name
            with gzip.open(path,'wt',encoding='utf-8') as f:json.dump(replay,f,separators=(',',':'))
            catalog.append({'id':f'{prefix}{label}-{i}','file':name,'policy':label,'faction':row['faction'],
                            'seed':row['seed'],'vp':row['vp'],'steps':row['steps']})
            print(name,'verified',row['vp'],'VP',path.stat().st_size,'bytes',flush=True)
    check_sources(manifest)
    # Completion marker; a failed partial export cannot be selected in the UI.
    with (args.output/'index.json').open('x') as f:json.dump({'schema_version':1,'games':catalog},f,indent=2)


if __name__=='__main__':
    torch.set_num_threads(2)
    main()
