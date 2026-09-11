"""Resume the same frozen action-purpose batch with bounded process parallelism."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import os
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from action_purpose.evaluate import run_game, dump, source_hash, historical_hashes
from action_purpose.costs import CorrectedContextTeacher
from action_purpose.teacher import PurposeTeacher
from gaia_rl.versions import require_current_sources, require_compatible_versions


def guard(manifest):
    require_current_sources(ROOT);require_compatible_versions(manifest['versions'])
    assert source_hash()==manifest['purpose_hash'] and historical_hashes()==manifest['historical_hashes']


def job(args):
    output, manifest, i, stage = args
    guard(manifest)
    spec = manifest['specs'][i]
    policy = CorrectedContextTeacher() if stage==0 else PurposeTeacher(stage)
    started = time.monotonic()
    result,replay = run_game(spec,policy,manifest['versions'])
    guard(manifest)
    with gzip.open(output/f'stage{stage}-{i}.json.gz','xt') as f:json.dump(replay,f,separators=(',',':'))
    dump(output/f'stage{stage}-{i}.json',result)
    return {'stage':stage,'game':i,'vp':result['vp'],'metrics':result['metrics'],'seconds':time.monotonic()-started}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path);parser.add_argument('--jobs',type=int,default=3)
    args=parser.parse_args()
    if not 1<=args.jobs<=4:parser.error('jobs must be 1..4')
    m=json.loads((args.output/'manifest.json').read_text());guard(m)
    if (args.output/'report.json').exists():parser.error('Batch already completed')
    tasks=[]
    for i in range(len(m['specs'])):
        for stage in m['stages']:
            path=args.output/f'stage{stage}-{i}.json'
            replay=args.output/f'stage{stage}-{i}.json.gz'
            if path.exists():
                r=json.loads(path.read_text());assert r['complete'] and replay.exists()
                continue
            assert not replay.exists(), 'Partial output requires explicit review'
            tasks.append((args.output,m,i,stage))
    dump(args.output/'resume.json',{'jobs':args.jobs,'remaining':[(i,s) for _,_,i,s in tasks],
         'reason':'Same preregistered games/seeds/policies; sequential process interrupted for bounded process parallelism. Completed results retained; incomplete game rerun from deterministic start.'})
    shutil.copyfile(__file__,args.output/'resume_action_purpose.py')
    started=time.monotonic();completed=[]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures=[pool.submit(job,t) for t in tasks]
        for f in as_completed(futures):
            r=f.result();completed.append(r);print(json.dumps(r),flush=True)
    guard(m)
    results={str(stage):[json.loads((args.output/f'stage{stage}-{i}.json').read_text()) for i in range(len(m['specs']))] for stage in m['stages']}
    summary={stage:{'mean_vp':statistics.mean(r['vp'] for r in rows),
       'by_faction':{f:statistics.mean(r['vp'] for r in rows if r['faction']==f) for f in ('Xenos','HadschHallas')},
       **{key:sum(r['metrics'][key] for r in rows) for key in ('burns','liquidation','passes_with_research','terraform_ore','ships')}} for stage,rows in results.items()}
    dump(args.output/'report.json',{'summary':summary,'all_complete':True,'promotion':False,'resume_seconds':time.monotonic()-started,'job_results':completed})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
