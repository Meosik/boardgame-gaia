"""Opt-in matched PPO pilot with/without source-informed behavior cloning.

No existing training defaults, game rules or rewards are modified. Output must be new.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import time
from collections import Counter

import numpy as np
import torch
from gymnasium import spaces
from ray.rllib.core.columns import Columns

from gaia_rl._native import Environment
from gaia_rl.aec import GaiaAEC
from gaia_rl.encoding import FeatureEncoder, ENCODING_VERSION
from gaia_rl.module import CandidateModule
from gaia_rl.versions import require_current_sources, runtime_versions, require_compatible_versions
from strategy_teacher import StrategyTeacher, TARGETS

ROOT = Path(__file__).resolve().parents[2]


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, default=lambda x: x.tolist() if hasattr(x,'tolist') else str(x))


def discover(prefix, count, seat_balanced=False):
    """Select only by faction lineup/seat, never by map quality or game result."""
    found=[]; buckets=Counter()
    for attempt in range(20000):
        seed=f'{prefix}-{attempt}'
        s=json.loads(Environment(seed).snapshot_json())
        lineup=[p['faction'] for p in s['state']['players']]
        if not all(t in lineup for t in TARGETS): continue
        if seat_balanced:
            # Balance both targets independently; maps are NOT rotations of one board.
            if lineup.index(TARGETS[1]) != (lineup.index(TARGETS[0])+1)%4: continue
            if buckets[(TARGETS[0],lineup.index(TARGETS[0]))]>=count: continue
        found.append({'seed':seed,'factions':lineup})
        for t in TARGETS: buckets[(t,lineup.index(t))]+=1
        if (not seat_balanced and len(found)==count) or (seat_balanced and len(found)==4*count):
            return found
    raise RuntimeError('Faction/seat seed search exhausted; do not change acceptance criteria')


def collect(specs, encoder, output):
    teacher=StrategyTeacher(); samples=[]; games=[]
    with gzip.open(output,'wt') as log:
        for spec in specs:
            env=Environment(spec['seed'],2000); rng=random.Random(spec['seed']+':opponent')
            histogram=Counter(); max_candidates=0
            while not env.is_terminal():
                s=json.loads(env.snapshot_json()); p=s['state']['players'][s['player']]
                max_candidates=max(max_candidates,len(s['candidates']))
                if p['faction'] in TARGETS:
                    decision,index=teacher.choose(s); reason=teacher.score(s,s['candidates'][index]['action'])[1]
                    histogram[p['faction']+':'+s['candidates'][index]['action']['type']]+=1
                    if len(s['candidates']) > 1 and not reason.startswith('unmodeled'):
                        obs=encoder.encode(s,s['player']); n=len(s['candidates'])
                        samples.append((obs['observation'],obs['candidates'][:n].copy(),index,p['faction']))
                    log.write(json.dumps({'seed':spec['seed'],'snapshot':s,'index':index,'reason':reason})+'\n')
                else: decision,index=s['decision_id'],rng.randrange(len(s['candidates']))
                env.step(decision,index)
            games.append({**spec,'scores':dict(env.final_scores()),'steps':s['steps']+1,
                          'actions':dict(histogram),'max_candidates':max_candidates})
            print('demonstration',spec['seed'],games[-1]['scores'],flush=True)
    return samples,games


def make_module(encoder):
    return CandidateModule(observation_space=encoder.observation_space,
                           action_space=spaces.Discrete(encoder.candidate_capacity),model_config={'width':64})


def batch(samples):
    capacity=max(len(s[1]) for s in samples)
    candidates=np.zeros((len(samples),capacity,samples[0][1].shape[1]),np.float32)
    mask=np.zeros((len(samples),capacity),bool)
    for i,(_,actions,_,_) in enumerate(samples):
        candidates[i,:len(actions)]=actions;mask[i,:len(actions)]=True
    return {Columns.OBS:{'observation':torch.from_numpy(np.stack([s[0] for s in samples])),
                         'candidates':torch.from_numpy(candidates),'action_mask':torch.from_numpy(mask)}}, torch.tensor([s[2] for s in samples])


def imitation_metrics(module,samples):
    losses=[]; correct=0
    with torch.no_grad():
        for offset in range(0,len(samples),8):
            b,y=batch(samples[offset:offset+8]); logits=module.forward_train(b)[Columns.ACTION_DIST_INPUTS]
            losses.extend(torch.nn.functional.cross_entropy(logits,y,reduction='none').tolist())
            correct+=int((logits.argmax(-1)==y).sum())
    if not losses: raise ValueError('Empty demonstration set')
    return {'cross_entropy':float(np.mean(losses)),'accuracy':correct/len(samples),'samples':len(samples)}


def clone_behavior(module,samples,validation,epochs,seed):
    optimizer=torch.optim.Adam(module.parameters(),lr=0.0003)
    before=imitation_metrics(module,validation);rng=np.random.default_rng(seed)
    for epoch in range(epochs):
        order=rng.permutation(len(samples))
        for offset in range(0,len(order),8):
            b,y=batch([samples[i] for i in order[offset:offset+8]])
            loss=torch.nn.functional.cross_entropy(module.forward_train(b)[Columns.ACTION_DIST_INPUTS],y)
            if not torch.isfinite(loss): raise RuntimeError('Non-finite imitation loss')
            optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(module.parameters(),1.0);optimizer.step()
        print('imitation epoch',epoch+1,flush=True)
    return {'before_validation':before,'after_validation':imitation_metrics(module,validation),
            'training':imitation_metrics(module,samples),'epochs':epochs,'gradient_steps':epochs*((len(samples)+7)//8)}


class SeedPoolAEC(GaiaAEC):
    """Experiment-only setup pool; ordinary GaiaAEC and production setup stay untouched."""
    def __init__(self, capacity, seeds):
        super().__init__(FeatureEncoder(capacity),max_steps=2000)
        self.seeds=tuple(seeds);self.pool_rng=np.random.default_rng()

    def reset(self,seed=None,options=None):
        # Retain the base AEC reward/dead-step initialization, then replace only setup.
        super().reset(seed=seed,options=options)
        if seed is not None: self.pool_rng=np.random.default_rng(seed)
        chosen=self.seeds[int(self.pool_rng.integers(len(self.seeds)))]
        self._native=Environment(chosen,self.max_steps);self._read_snapshot()
        self.agent_selection=f"player_{self._snapshot['player']}";self._update_infos()


def ppo_train(weights,specs,args,destination):
    import ray
    from ray.tune.registry import register_env
    from ray.rllib.algorithms.ppo import PPOConfig
    from ray.rllib.core.rl_module.rl_module import RLModuleSpec
    from ray.rllib.env.wrappers.pettingzoo_env import PettingZooEnv
    from gaia_rl.training import shared_policy
    seed_all(args.seed)
    register_env('gaia_strategy_pilot',lambda c: PettingZooEnv(SeedPoolAEC(c['capacity'],c['seeds'])))
    config=(PPOConfig().environment('gaia_strategy_pilot',env_config={'capacity':args.capacity,'seeds':[s['seed'] for s in specs]},disable_env_checking=True)
        .framework('torch').env_runners(num_env_runners=0,rollout_fragment_length=16,batch_mode='truncate_episodes')
        .learners(num_learners=0,num_gpus_per_learner=0)
        .training(gamma=1.0,train_batch_size_per_learner=args.batch_size,minibatch_size=8,num_epochs=1,lr=0.0003,grad_clip=1.0)
        .multi_agent(policies={'shared'},policy_mapping_fn=shared_policy)
        .rl_module(rl_module_spec=RLModuleSpec(module_class=CandidateModule,model_config={'width':64}))
        .debugging(seed=args.seed,log_level='ERROR'))
    algo=config.build_algo()
    try:
        algo.learner_group.set_weights({'shared':{k:v.cpu().numpy() for k,v in weights.items()}})
        algo.env_runner_group.sync_weights(from_worker_or_learner_group=algo.learner_group,inference_only=True)
        for k,v in weights.items():
            torch.testing.assert_close(algo.get_module('shared').state_dict()[k].cpu(),v.cpu(),rtol=0,atol=0)
        reports=[]
        for iteration in range(args.ppo_iterations):
            result=algo.train(); losses=result['learners']['shared']
            if not all(np.isfinite(losses[k]) for k in ('total_loss','policy_loss','vf_loss')):
                raise RuntimeError('Non-finite PPO loss')
            reports.append({'iteration':iteration+1,'losses':losses,'env_runners':result['env_runners']})
            print(destination.name,'PPO iteration',iteration+1,flush=True)
        trained={k:v.detach().cpu().clone() for k,v in algo.get_module('shared').state_dict().items()}
        if not all(torch.isfinite(v).all() for v in trained.values()): raise RuntimeError('Non-finite weights')
        destination.mkdir()
        # Inference-only pilot artifacts, intentionally not presented as resumable save_run checkpoints.
        torch.save(trained,destination/'inference.pt')
        dump(destination/'training.json',reports)
        return trained,reports
    finally: algo.stop()


class ModulePolicy:
    def __init__(self,encoder,weights):
        self.encoder=encoder;self.module=make_module(encoder);self.module.load_state_dict(weights);self.module.eval()

    def choose(self,s):
        obs=self.encoder.encode(s,s['player'])
        with torch.no_grad():
            b={Columns.OBS:{k:torch.as_tensor(v).unsqueeze(0) for k,v in obs.items()}}
            logits=self.module.forward_inference(b)[Columns.ACTION_DIST_INPUTS][0]
            index=int(logits.argmax())
        if not 0<=index<len(s['candidates']): raise RuntimeError('Masked action chosen')
        return s['decision_id'],index


def evaluate(policy,specs,label):
    games=[]
    for spec in specs:
        for faction in TARGETS:
            seat=spec['factions'].index(faction);env=Environment(spec['seed'],2000)
            # Independent per-seat streams avoid coupling random opponents to focal action counts.
            rngs=[random.Random(f"{spec['seed']}:{faction}:opponent:{p}") for p in range(4)]
            actions=Counter();rounds={}
            try:
                while not env.is_terminal():
                    s=json.loads(env.snapshot_json());player=s['player']
                    if player==seat:
                        decision,index=policy.choose(s)
                        actions[s['candidates'][index]['action']['type']]+=1
                        if s['state']['round'] not in rounds:
                            p=s['state']['players'][seat]
                            rounds[s['state']['round']]={k:copy.deepcopy(p[k]) for k in ('resources','research_tracks','structures','explored_ships','federation_tokens','advanced_tech_tiles')}
                    else: decision,index=s['decision_id'],rngs[player].randrange(len(s['candidates']))
                    env.step(decision,index)
                scores=dict(env.final_scores());best=max(scores.values())
                row={'seed':spec['seed'],'faction':faction,'seat':seat,'complete':True,'vp':scores[seat],
                     'win_share':1/sum(v==best for v in scores.values()) if scores[seat]==best else 0,
                     'scores':scores,'steps':s['steps']+1,'actions':dict(actions),'round_starts':rounds}
            except Exception as error:
                # Failed games stay in the report and invalidate strength comparisons.
                row={'seed':spec['seed'],'faction':faction,'seat':seat,'complete':False,
                     'error':repr(error),'snapshot':json.loads(env.snapshot_json()),'actions':dict(actions)}
            games.append(row);print(label,faction,spec['seed'],row.get('vp',row.get('error')),flush=True)
    return games


def summarize(games):
    result={}
    for faction in TARGETS:
        rows=[g for g in games if g['faction']==faction];done=[g for g in rows if g['complete']]
        result[faction]={'completed':len(done),'attempted':len(rows),
                         'mean_vp_completed_only':float(np.mean([g['vp'] for g in done])) if done else None,
                         'mean_win_share_completed_only':float(np.mean([g['win_share'] for g in done])) if done else None}
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seed',default=19,type=int)
    parser.add_argument('--seed-manifest',type=Path,help='Reuse a trusted local manifest after a failed pilot; verify lineups and versions')
    parser.add_argument('--capacity',default=2048,type=int)
    parser.add_argument('--demo-games',default=6,type=int)
    parser.add_argument('--validation-games',default=2,type=int)
    parser.add_argument('--eval-per-seat',default=1,type=int)
    parser.add_argument('--bc-epochs',default=4,type=int)
    parser.add_argument('--ppo-iterations',default=4,type=int)
    parser.add_argument('--batch-size',default=256,type=int)
    args=parser.parse_args()
    if args.output.exists() or min(args.capacity,args.demo_games,args.validation_games,args.eval_per_seat,args.bc_epochs,args.ppo_iterations,args.batch_size)<1:
        parser.error('new output path and positive budgets required')
    require_current_sources(ROOT);versions=runtime_versions();args.output.mkdir(parents=True)
    torch.set_num_threads(2);seed_all(args.seed);start=time.monotonic()
    script_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()
    if args.seed_manifest:
        prior=json.loads(args.seed_manifest.read_text());require_compatible_versions(prior['versions'])
        train,validation,evaluation=(prior[k] for k in ('training','validation','evaluation'))
        if [len(train),len(validation),len(evaluation)] != [args.demo_games,args.validation_games,4*args.eval_per_seat]:
            raise ValueError('Reused seed pool sizes differ from requested budgets')
        all_specs=train+validation+evaluation
        if len({s['seed'] for s in all_specs})!=len(all_specs): raise ValueError('Overlapping seed splits')
        for spec in all_specs:
            actual=json.loads(Environment(spec['seed']).snapshot_json())
            if [p['faction'] for p in actual['state']['players']]!=spec['factions'] or not all(t in spec['factions'] for t in TARGETS):
                raise ValueError('Seed manifest lineup differs')
        for faction in TARGETS:
            if Counter(spec['factions'].index(faction) for spec in evaluation)!=Counter({i:args.eval_per_seat for i in range(4)}):
                raise ValueError('Unbalanced evaluation seats')
    else:
        train=discover(f'strategy-{args.seed}-train',args.demo_games)
        validation=discover(f'strategy-{args.seed}-validation',args.validation_games)
        evaluation=discover(f'strategy-{args.seed}-heldout',args.eval_per_seat,True)
    manifest={'versions':versions,'encoding_version':ENCODING_VERSION,'experiment_hash':script_hash,
              'settings':vars(args),'training':train,'validation':validation,'evaluation':evaluation,
              'warning':'Seat-balanced distinct maps, not same-map rotations. Extra BC compute reported separately. Small random-opponent pilot, not strength evidence.'}
    dump(args.output/'manifest.json',manifest)
    encoder=FeatureEncoder(args.capacity)
    samples,demogames=collect(train,encoder,args.output/'demonstrations.jsonl.gz')
    val_samples,val_games=collect(validation,encoder,args.output/'validation.jsonl.gz')
    dump(args.output/'demonstration_report.json',{'training':demogames,'validation':val_games,
         'samples_by_faction':dict(Counter(s[3] for s in samples))})
    seed_all(args.seed);student=make_module(encoder);initial=copy.deepcopy(student.state_dict())
    bc=clone_behavior(student,samples,val_samples,args.bc_epochs,args.seed)
    bc_weights=copy.deepcopy(student.state_dict());dump(args.output/'imitation.json',bc)
    # Both PPO arms start with fresh optimizers and use identical initialization before BC,
    # PPO seeds, setup pools and sample budgets. BC is the only extra training treatment.
    import ray
    ray.init(num_cpus=2,include_dashboard=False,object_store_memory=128*1024**2,log_to_driver=False)
    try:
        baseline,_=ppo_train(initial,train,args,args.output/'baseline')
        pretrained,_=ppo_train(bc_weights,train,args,args.output/'imitation_plus_ppo')
    finally: ray.shutdown()
    results={}
    for label,policy in [('baseline',ModulePolicy(encoder,baseline)),
                         ('imitation_plus_ppo',ModulePolicy(encoder,pretrained)),('teacher',StrategyTeacher())]:
        games=evaluate(policy,evaluation,label);dump(args.output/f'{label}_evaluation.json',games)
        results[label]=summarize(games)
    require_current_sources(ROOT);require_compatible_versions(versions)
    report={'versions':versions,'experiment_hash':script_hash,'summary':results,'imitation':bc,
            'seconds':time.monotonic()-start,'all_games_complete':all(v['completed']==v['attempted'] for summary in results.values() for v in summary.values()),
            'limitations':['Not a long training run or human-strength benchmark','Against uniform random legal-action opponents only',
                           'BC treatment has additional supervised compute; equal PPO budget, not equal total compute',
                           'Other factions receive PPO updates but have no teacher labels','Partial heuristic coverage; no full counterfactual cost/advanced-tech evaluator',
                           'Inference-only artifacts; no optimizer-resume or server integration']}
    dump(args.output/'report.json',report);print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
