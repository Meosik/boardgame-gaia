"""Fresh-map paired experiment: pinned integrated teacher vs contextual research."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'gaia-rl/experiments'))
from economy.evaluate import run_game,write,digest
from federation.evaluate import extra_metrics,summarize
from integrated.evaluate import source_hashes
from integrated.teacher import IntegratedTeacher
from research_context.teacher import ContextResearchTeacher
from gaia_rl.versions import require_current_sources,require_compatible_versions


def diagnostics(replay,seat):
    rounds={};advanced=[];counts={};last=replay['frames'][-1]['state']
    for old,new in zip(replay['frames'],replay['frames'][1:]):
        before=next(p for p in old['state']['players'] if p['player_id']==seat)
        after=next(p for p in new['state']['players'] if p['player_id']==seat)
        rnd=old['state']['round']
        if rnd:
            rounds[rnd]=after['research_tracks']
            for track,value in after['research_tracks'].items():
                counts[track]=counts.get(track,0)+max(0,value-before['research_tracks'][track])
        for tile in set(after['advanced_tech_tiles'])-set(before['advanced_tech_tiles']):
            advanced.append({'round':rnd,'tile':tile})
    focal=next(p for p in last['players'] if p['player_id']==seat)
    return {'final_tracks':focal['research_tracks'],'tracks_by_round':rounds,'advances':counts,
            'advanced_acquired':advanced}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--specs',required=True,type=Path)
    args=parser.parse_args()
    baseline=json.loads((ROOT/'gaia-rl/runs/integrated-teacher-v1/manifest.json').read_text())
    specs=json.loads(args.specs.read_text())
    hashes=source_hashes()|{'research_context':digest(Path(__file__).parent.glob('*.py'))}
    def guard():
        require_current_sources(ROOT);require_compatible_versions(baseline['versions'])
        assert baseline['source_hashes']==source_hashes(),'Pinned integrated source changed'
        assert hashes==source_hashes()|{'research_context':digest(Path(__file__).parent.glob('*.py'))}
    guard()
    if args.output.exists():parser.error('Output must be new')
    args.output.mkdir(parents=True)
    write(args.output/'manifest.json',{'versions':baseline['versions'],'source_hashes':hashes,'games':specs,
          'policy':'ContextResearchTeacher','training_steps':0,'promotion':False,
          'selection':'First two fresh namespace seeds with both focal factions; setup metadata only, no policy outcomes inspected',
          'warning':'Four pairs/two maps/random opponents; exploratory, no retuning during comparison'})
    for name in hashes:
        source=ROOT/'gaia-rl/experiments' if name=='original' else ROOT/'gaia-rl/experiments'/name
        dst=args.output/'source-snapshot'/name;dst.mkdir(parents=True)
        for p in source.glob('*.py'):shutil.copyfile(p,dst/p.name)
        assert digest(dst.glob('*.py'))==hashes[name]
    results={'control':[],'contextual':[]};start=time.monotonic()
    for i,spec in enumerate(specs):
        for arm,teacher in (('control',IntegratedTeacher()),('contextual',ContextResearchTeacher())):
            result,replay=run_game(spec,teacher,baseline['versions'],hashes['integrated' if arm=='control' else 'research_context'])
            if replay:
                result['extra']=extra_metrics(replay,spec['seat'])
                result['research']=diagnostics(replay,spec['seat'])
                replay['metadata'].update(policy=f'{arm}_research_teacher',source_hashes=hashes)
                with gzip.open(args.output/f'{arm}-{i}.json.gz','wt') as f:json.dump(replay,f,separators=(',',':'))
            write(args.output/f'{arm}-{i}.json',result);results[arm].append(result)
            print(arm,i,spec['faction'],result.get('vp',result.get('error')),result.get('research',{}).get('final_tracks'),flush=True)
            guard()
    write(args.output/'report.json',{**{arm:summarize(rows) for arm,rows in results.items()},
          'seconds':time.monotonic()-start,'all_complete':all(r['complete'] for rows in results.values() for r in rows),
          'promotion':False})


if __name__=='__main__':main()
