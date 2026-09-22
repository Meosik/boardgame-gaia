"""Current teacher stages with booster12 debit audits; frozen runners stay intact."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import time

from action_purpose.evaluate import ROOT, dump, run_game as previous_game
from current_actions.teacher import (BOOSTER_BUILD, CurrentActionTeacher,
                                    CurrentContextTeacher, construction_cost)
from gaia_rl._native import SOURCE_MANIFEST
from gaia_rl.versions import require_compatible_versions, require_current_sources, runtime_versions


def teacher_for_stage(stage):
    return CurrentContextTeacher() if stage == 0 else CurrentActionTeacher(stage)


def audit_booster_builds(result, replay):
    uses = 0
    actor = result['seat']
    for row in result['choices']:
        if row['action']['type'] != BOOSTER_BUILD:
            continue
        before = replay['frames'][row['step']-1]['state']
        after = replay['frames'][row['step']]['state']
        player = before['players'][actor]
        cost = construction_cost(before, player, row['action'])
        expected = {k: getattr(cost, k) for k in ('ore', 'credits', 'qic')}
        actual = {k: player['resources'][k]-after['players'][actor]['resources'][k] for k in expected}
        if actual != expected:
            raise ValueError(f'Booster12 cost mismatch: {expected} != {actual}')
        row.update(cost=asdict(cost), cost_verified=True)
        uses += 1
    builds = [c['cost'] for c in result['choices'] if c['cost'] and c['cost']['terraform_steps']]
    result['metrics'].update(
        booster12_uses=uses,
        verified_build_costs=sum(c.get('cost_verified', False) for c in result['choices']),
        terraform_ore=sum(c['terraform_ore'] for c in builds),
        three_ore_builds=sum(c['terraform_ore'] == 3*c['terraform_steps'] for c in builds))


def source_hashes():
    files = sorted((ROOT/'gaia-rl/experiments').rglob('*.py'))
    files += [ROOT/'gaia-rl/tools'/name for name in
              ('simulate.py', 'replay_log.py', 'replay_income.py', 'evaluation_replays.py')]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--specs', type=Path, default=ROOT/'gaia-rl/experiments/research_context/fresh_specs.json')
    parser.add_argument('--stages', default='0,1,2,3,4')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('New output directory required')
    stages = [int(n) for n in args.stages.split(',')]
    if not stages or len(stages) != len(set(stages)) or any(n not in range(5) for n in stages):
        parser.error('Unique stages 0..4 required')
    specs = json.loads(args.specs.read_text())
    if not specs or any(s['faction'] not in ('Xenos', 'HadschHallas') or s['seat'] not in range(4) for s in specs):
        parser.error('Nonempty Xenos/HadschHallas specs required')
    versions, sources = runtime_versions(), source_hashes()

    def guard():
        require_current_sources(ROOT)
        require_compatible_versions(versions)
        if source_hashes() != sources:
            raise ValueError('Teacher/runner sources changed mid-run')

    guard()
    args.output.mkdir(parents=True)
    dump(args.output/'manifest.json', {
        'versions': versions, 'source_hashes': sources, 'specs': specs, 'stages': stages,
        'teacher_variant': 'current-actions-booster12', 'training_steps': 0, 'promotion': False,
        'warning': 'All stages include booster12; stages1..4 include purposeful batches. '
                   'Not comparable to historical stages without rerunning; random opponents.'})
    (args.output/'native-source-manifest.txt').write_text(SOURCE_MANIFEST)
    for name in sources:
        dest = args.output/'source-snapshot'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
    for line in SOURCE_MANIFEST.splitlines():
        _, name = line.split('  ', 1)
        dest = args.output/'native-source'/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dest)
    results = {str(stage): [] for stage in stages}
    start = time.monotonic()
    for i, spec in enumerate(specs):
        for stage in stages:
            try:
                guard()
                result, replay = previous_game(spec, teacher_for_stage(stage), versions)
                audit_booster_builds(result, replay)
                guard()
                payload = json.dumps(replay, separators=(',', ':')).encode()
                with (args.output/f'stage{stage}-{i}.json.gz').open('xb') as stream:
                    stream.write(gzip.compress(payload, mtime=0))
            except Exception as error:
                dump(args.output/f'stage{stage}-{i}.json', {'complete': False, **spec, 'error': repr(error)})
                raise
            dump(args.output/f'stage{stage}-{i}.json', result)
            results[str(stage)].append(result)
            print(stage, i, spec['faction'], result['vp'], result['metrics'], flush=True)
    summary = {stage: {
        'mean_vp': statistics.mean(r['vp'] for r in rows),
        'by_faction': {f: statistics.mean(r['vp'] for r in rows if r['faction'] == f)
                       for f in sorted({r['faction'] for r in rows})},
        'booster12_uses': sum(r['metrics']['booster12_uses'] for r in rows)}
        for stage, rows in results.items()}
    guard()
    dump(args.output/'report.json', {'summary': summary, 'seconds': time.monotonic()-start,
                                   'all_complete': True, 'promotion': False})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
