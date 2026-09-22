"""Explicit next test entry point: integrated teacher vs unchanged economic control."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'gaia-rl/experiments'))
from economy.evaluate import digest, run_game, write
from economy.teacher import EconomyTeacher
from federation.evaluate import extra_metrics, summarize
from integrated.teacher import IntegratedTeacher
from integrated.features import income
from gaia_rl.versions import require_current_sources, require_compatible_versions


def source_hashes():
    return {name:digest(path.glob('*.py')) for name,path in {
        'original':ROOT/'gaia-rl/experiments', 'economy':ROOT/'gaia-rl/experiments/economy',
        'federation':ROOT/'gaia-rl/experiments/federation', 'integrated':Path(__file__).parent}.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    baseline=ROOT/'gaia-rl/runs/economy-teacher-v3'
    manifest=json.loads((baseline/'manifest.json').read_text())
    hashes=source_hashes()
    def guard():
        require_current_sources(ROOT);require_compatible_versions(manifest['versions'])
        if hashes != source_hashes() or hashes['original']!=manifest['original_experiment_hash'] or hashes['economy']!=manifest['economy_experiment_hash']:
            raise ValueError('Pinned experiment code changed')
    guard()
    if args.output.exists():parser.error('Output must be new')
    args.output.mkdir(parents=True)
    write(args.output/'manifest.json',{'versions':manifest['versions'],'source_hashes':hashes,
          'games':manifest['games'],'training_steps':0,'scope':'Xenos/HadschHallas; random opponents; observed maps',
          'policy':'IntegratedTeacher','promotion':False})
    results={'control':[],'integrated':[]};start=time.monotonic()
    try:
        for i in range(8):
            original=json.loads((baseline/f'game-{i}.json').read_text())
            for arm,policy in (('control',EconomyTeacher()),('integrated',IntegratedTeacher())):
                result,replay=run_game(original,policy,manifest['versions'],hashes['economy' if arm=='control' else 'integrated'])
                if replay:
                    result['extra']=extra_metrics(replay,original['seat'])
                    last=replay['frames'][-1]['state']
                    focal=next(p for p in last['players'] if p['player_id']==original['seat'])
                    result['advanced_tech_tiles']=focal['advanced_tech_tiles']
                    result['research_tracks']=focal['research_tracks']
                    result['permanent_knowledge_income']=income(focal,last)['knowledge']
                    replay['metadata'].update(policy=f'{arm}_teacher',source_hashes=hashes)
                    with gzip.open(args.output/f'{arm}-{i}.json.gz','wt') as f:json.dump(replay,f,separators=(',',':'))
                write(args.output/f'{arm}-{i}.json',result)
                results[arm].append(result)
                if arm=='control' and (not result['complete'] or result['steps']!=original['steps']
                      or {str(k):v for k,v in result['scores'].items()}!=original['scores']
                      or [c['action'] for c in result['choices']]!=[c['action'] for c in original['choices']]):
                    raise ValueError(f'Historical control mismatch: {i}')
                print(arm,i,result.get('vp',result.get('error')),flush=True)
        guard()
        write(args.output/'report.json',{**{a:summarize(r) for a,r in results.items()},
              'all_complete':all(r['complete'] for rows in results.values() for r in rows),
              'seconds':time.monotonic()-start,'promotion':False})
    except Exception:
        (args.output/'failure.log').write_text(traceback.format_exc());raise


if __name__=='__main__':main()
