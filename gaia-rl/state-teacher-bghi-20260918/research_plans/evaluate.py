"""Same-map Hadsch comparison: current stage1 versus two-income native plans."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import time

from action_purpose.evaluate import ROOT, dump, run_game
from current_actions.evaluate import audit_booster_builds, source_hashes
from current_actions.teacher import CurrentActionTeacher
from research_plans.teacher import ResearchPlanTeacher
from gaia_rl._native import SOURCE_MANIFEST
from gaia_rl.versions import require_current_sources, runtime_versions, require_compatible_versions


def teacher_for_variant(variant, candidate_factory=ResearchPlanTeacher):
    if variant not in (0, 1):
        raise ValueError('Variants: 0=current stage1; 1=two-income plan candidate')
    return CurrentActionTeacher(1) if variant == 0 else candidate_factory(1)


def sources_for_comparison(fixture_dirs=()):
    sources = source_hashes()
    for directory in (Path(__file__).parent/'fixtures', *fixture_dirs):
        for path in directory.glob('*.json'):
            sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return sources


def main(*, faction='HadschHallas', candidate_factory=ResearchPlanTeacher,
         teacher_variant='hadsch-native-research-plans', fixture_dirs=(), description=None):
    parser = argparse.ArgumentParser(description=description or __doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--specs', type=Path, required=True)
    parser.add_argument('--stages', default='0,1', help='Comparison variants, NOT purpose ablation stages')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('New output directory required')
    variants = [int(n) for n in args.stages.split(',')]
    if not variants or len(set(variants)) != len(variants) or any(v not in (0, 1) for v in variants):
        parser.error('Unique comparison variants 0,1 required')
    specs = json.loads(args.specs.read_text())
    if not specs or any(s['faction'] != faction or s['seat'] not in range(4) for s in specs):
        parser.error(f'Nonempty {faction}-only specs required')
    versions, sources = runtime_versions(), sources_for_comparison(fixture_dirs)

    def guard():
        require_current_sources(ROOT)
        require_compatible_versions(versions)
        if sources_for_comparison(fixture_dirs) != sources:
            raise ValueError('Teacher/runner sources changed mid-comparison')

    guard()
    args.output.mkdir(parents=True)
    dump(args.output/'manifest.json', {'versions': versions, 'source_hashes': sources,
        'specs': specs, 'stages': variants, 'purpose_stage': 1, 'horizon_incomes': 2,
        'teacher_variant': teacher_variant, 'training_steps': 0, 'promotion': False,
        'warning': 'Variants0/1 share current stage1. Forecast continuation uses CurrentContextTeacher; '
                   'forecast and real opponents are random, not strong-player predictions.'})
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
    results = {str(v): [] for v in variants}
    start = time.monotonic()
    for i, spec in enumerate(specs):
        for variant in variants:
            policy = teacher_for_variant(variant, candidate_factory)
            if isinstance(policy, candidate_factory):
                policy.on_plan = lambda audit: print(
                    f'plan decision={audit["decision_id"]} round={audit["round"]} '
                    f'selected={audit["selected"]} complete='
                    f'{sum(p["complete"] for p in audit["plans"])}/{len(audit["plans"])}', flush=True)
            try:
                guard()
                result, replay = run_game(spec, policy, versions)
                audit_booster_builds(result, replay)
                # Existing export contract calls this field stage. Preserve the actual
                # purpose stage separately so the comparison cannot masquerade as an ablation.
                replay['metadata'].update(stage=variant, purpose_stage=1, comparison_variant=variant)
                if isinstance(policy, candidate_factory):
                    dump(args.output/f'plans-{i}.json', policy.plan_history)
                    result['metrics'].update(
                        planned_decisions=len(policy.plan_history),
                        plan_changes=sum(p['selected'] != 'current-choice' for p in policy.plan_history),
                        action_changes=sum(p['selected_first'] != next(r['first'] for r in p['plans']
                                           if r['goal'] == 'current-choice') for p in policy.plan_history),
                        incomplete_forecasts=sum(not r['complete'] for p in policy.plan_history for r in p['plans']))
                    if any('funding_searches' in r for p in policy.plan_history for r in p['plans']):
                        result['metrics'].update(
                            funding_search_limit_hits=sum(search['node_limit_reached']
                                for p in policy.plan_history for r in p['plans']
                                for search in r.get('funding_searches', [])),
                            incomplete_funding_alternatives=sum(not alternative['complete']
                                for p in policy.plan_history for r in p['plans']
                                for alternative in r.get('funding_alternatives', [])))
                guard()
                with (args.output/f'stage{variant}-{i}.json.gz').open('xb') as stream:
                    stream.write(gzip.compress(json.dumps(replay, separators=(',', ':')).encode(), mtime=0))
            except Exception as error:
                if isinstance(policy, candidate_factory):
                    dump(args.output/f'failed-plans-{i}.json', policy.plan_history)
                dump(args.output/f'stage{variant}-{i}.json', {'complete': False, **spec, 'error': repr(error)})
                raise
            dump(args.output/f'stage{variant}-{i}.json', result)
            results[str(variant)].append(result)
            print(variant, i, result['vp'], result['metrics'], flush=True)
    guard()
    summary = {v: {'mean_vp': statistics.mean(r['vp'] for r in rows),
                   'by_faction': {faction: statistics.mean(r['vp'] for r in rows)}}
               for v, rows in results.items()}
    dump(args.output/'report.json', {'all_complete': True, 'promotion': False,
        'summary': summary, 'seconds': time.monotonic()-start})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
