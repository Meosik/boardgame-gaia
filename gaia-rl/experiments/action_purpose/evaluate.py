"""Fixed cumulative ablations on corrected native rules; no learning or promotion."""
import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
sys.path.insert(0, str(ROOT/'gaia-rl/tools'))
from action_purpose.costs import CorrectedContextTeacher, construction_cost
from action_purpose.teacher import PurposeTeacher
from gaia_rl._native import Environment, SOURCE_MANIFEST
from gaia_rl.versions import runtime_versions, require_current_sources, require_compatible_versions
from replay_log import add_decision_log
from source_routes.evaluate import hashes as historical_hashes


def dump(path, value):
    with path.open('x') as f:json.dump(value, f, indent=2)


def source_hash():
    return hashlib.sha256(b''.join(p.read_bytes() for p in sorted(Path(__file__).parent.glob('*.py')))).hexdigest()


def run_game(spec, policy, versions):
    env = Environment(spec['seed'], 2000)
    if isinstance(policy, PurposeTeacher):policy.bind(env)
    rngs = [random.Random(f"{spec['seed']}:{spec['faction']}:opponent:{p}") for p in range(4)]
    frames, choices = [], []
    def frame(s, actor=None, action=None, candidates=()):
        state = s['state'].copy();state.pop('event_log', None)
        return {'decision_id': s['decision_id'], 'player': actor, 'action': action,
                'legal_action_count': len(candidates), 'legal_federation_count': sum(c['action']['type']=='FormFederation' for c in candidates),
                'event_end': 0, 'state': state}
    s = json.loads(env.snapshot_json())
    assert s['state']['players'][spec['seat']]['faction'] == spec['faction'], 'Unexpected focal setup'
    frames.append(frame(s))
    while not env.is_terminal():
        actor = s['player'];ranked = None
        if actor == spec['seat']:
            ranked = policy.rank(s)
            assert len(ranked)==len(s['candidates']) and all(math.isfinite(v) for v,_ in ranked)
            index = max(range(len(ranked)), key=lambda i:(ranked[i][0], -i))
        else:
            index = rngs[actor].randrange(len(s['candidates']))
        action = s['candidates'][index]['action']
        before = s
        env.step(s['decision_id'], index)
        s = json.loads(env.snapshot_json())
        frames.append(frame(s, actor, action, before['candidates']))
        if ranked:
            p, after = before['state']['players'][actor], s['state']['players'][actor]
            cost = construction_cost(before['state'], p, action)
            row = {'step': s['decision_id'], 'round': before['state']['round'], 'action': action,
                   'score': ranked[index][0], 'reason': ranked[index][1], 'cost': asdict(cost) if cost else None,
                   'resources_before': p['resources'], 'resources_after': after['resources'],
                   'preview_count': getattr(policy, 'preview_count', 0),
                   'top': [{'action': before['candidates'][j]['action'], 'score': ranked[j][0], 'reason': ranked[j][1]}
                           for j in sorted(range(len(ranked)), key=lambda j: (-ranked[j][0], j))[:3]]}
            if cost and action['type'] in ('Build','RoundBoosterRangeBuild','TwilightRangeBuild','SpaceshipCreditTerraform','EclipseAsteroidMine'):
                actual = {k: p['resources'][k]-after['resources'][k] for k in ('ore','credits','qic')}
                expected = {k: getattr(cost,k) for k in actual}
                if actual != expected:raise ValueError(f'Corrected cost mismatch: {action}: {expected} != {actual}')
                row['cost_verified'] = True
            if action['type']=='Pass':
                row['unused_legal_research'] = any(c['action']['type']=='ResearchAdvance' for c in before['candidates'])
            choices.append(row)
    scores = dict(env.final_scores())
    replay = add_decision_log({'schema_version': 1, 'metadata': {**spec, 'focus_player': spec['seat'],
        'policy': type(policy).__name__, 'stage': getattr(policy,'stage',0), 'versions': versions,
        'steps': s['steps'], 'scores': scores}, 'frames': frames, 'events': []})
    kinds = Counter(c['action'].get('kind') for c in choices if c['action']['type']=='FreeAction')
    builds = [c for c in choices if c['cost'] and c['cost']['terraform_steps']]
    metrics = {'conversions': dict(kinds), 'burns': kinds['BurnPower'],
               'liquidation': kinds['OreToCredit']+kinds['KnowledgeToCredit'],
               'three_ore_builds': sum(c['cost']['terraform_ore']==3*c['cost']['terraform_steps'] for c in builds),
               'terraform_ore': sum(c['cost']['terraform_ore'] for c in builds),
               'passes_with_research': sum(c.get('unused_legal_research',False) for c in choices),
               'ships': len(s['state']['players'][spec['seat']]['explored_ships']),
               'verified_build_costs': sum(c.get('cost_verified',False) for c in choices)}
    return {'complete': True, **spec, 'vp': scores[spec['seat']], 'steps': s['steps'], 'metrics': metrics,
            'final_tracks': s['state']['players'][spec['seat']]['research_tracks'], 'choices': choices}, replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--specs', type=Path, default=ROOT/'gaia-rl/experiments/research_context/fresh_specs.json')
    parser.add_argument('--stages', default='0,1,2,3,4')
    args = parser.parse_args()
    if args.output.exists():parser.error('New output directory required')
    stages = [int(n) for n in args.stages.split(',')]
    if len(stages)!=len(set(stages)) or any(n not in range(5) for n in stages):parser.error('Unique stages 0..4 required')
    specs = json.loads(args.specs.read_text())
    versions, frozen, own = runtime_versions(), historical_hashes(), source_hash()
    previous = json.loads((ROOT/'gaia-rl/runs/source-routes-v1/manifest.json').read_text())
    assert frozen == previous['source_hashes'], 'Historical strategies changed'
    def guard():
        require_current_sources(ROOT);require_compatible_versions(versions)
        assert historical_hashes()==frozen and source_hash()==own, 'Sources changed mid-run'
    guard();args.output.mkdir(parents=True)
    dump(args.output/'manifest.json', {'versions': versions, 'historical_hashes': frozen, 'purpose_hash': own,
         'specs': specs, 'stages': stages, 'training_steps': 0, 'promotion': False,
         'warning': 'Corrected Gaia/TFMars; both arms rerun; cumulative ablations; reused maps/random opponents; no tuning on results'})
    (args.output/'native-source-manifest.txt').write_text(SOURCE_MANIFEST)
    for p in Path(__file__).parent.glob('*.py'):
        dst=args.output/'source-snapshot'/p.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(p,dst)
    for line in SOURCE_MANIFEST.splitlines():
        _, name = line.split('  ',1);dst=args.output/'native-source'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    results = {str(stage): [] for stage in stages};start=time.monotonic()
    for i,spec in enumerate(specs):
        for stage in stages:
            try:
                policy = CorrectedContextTeacher() if stage==0 else PurposeTeacher(stage)
                result,replay = run_game(spec,policy,versions)
                with gzip.open(args.output/f'stage{stage}-{i}.json.gz','wt') as f:json.dump(replay,f,separators=(',',':'))
            except Exception as error:
                result = {'complete':False, **spec, 'error':repr(error)}
                dump(args.output/f'stage{stage}-{i}.json',result)
                raise
            dump(args.output/f'stage{stage}-{i}.json',result);results[str(stage)].append(result)
            print(stage,i,spec['faction'],result['vp'],result['metrics'],flush=True);guard()
    summary = {stage:{'mean_vp':statistics.mean(r['vp'] for r in rows),
                      'by_faction':{f:statistics.mean(r['vp'] for r in rows if r['faction']==f) for f in ('Xenos','HadschHallas')},
                      'burns':sum(r['metrics']['burns'] for r in rows),'liquidation':sum(r['metrics']['liquidation'] for r in rows),
                      'passes_with_research':sum(r['metrics']['passes_with_research'] for r in rows),
                      'terraform_ore':sum(r['metrics']['terraform_ore'] for r in rows),
                      'ships':sum(r['metrics']['ships'] for r in rows)} for stage,rows in results.items()}
    dump(args.output/'report.json', {'summary':summary,'seconds':time.monotonic()-start,'all_complete':True,'promotion':False})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
