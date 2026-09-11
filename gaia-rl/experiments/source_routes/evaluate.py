"""Same corrected engine, frozen control vs source-route candidate; no training."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
from economy.evaluate import run_game, write, digest
from federation.evaluate import extra_metrics, summarize
from integrated.evaluate import source_hashes
from research_context.evaluate import diagnostics
from research_context.teacher import ContextResearchTeacher
from source_routes.teacher import SourceRouteTeacher
from gaia_rl.versions import require_current_sources, require_compatible_versions, runtime_versions
from gaia_rl._native import SOURCE_MANIFEST


def hashes():
    return source_hashes() | {name: digest((ROOT/'gaia-rl/experiments'/name).glob('*.py'))
                             for name in ('research_context', 'source_routes')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    previous = json.loads((ROOT/'gaia-rl/runs/research-context-v1/manifest.json').read_text())
    frozen = hashes()
    versions = runtime_versions()
    specs = json.loads((ROOT/'gaia-rl/experiments/research_context/fresh_specs.json').read_text())

    def guard():
        require_current_sources(ROOT)
        require_compatible_versions(versions)
        assert hashes() == frozen, 'Sources changed during run'
        assert all(frozen[k] == value for k, value in previous['source_hashes'].items()), 'Historical teacher source changed'

    guard()
    args.output.mkdir(parents=True)
    write(args.output/'manifest.json', {'versions': versions, 'source_hashes': frozen, 'games': specs,
          'previous_versions': previous['versions'], 'training_steps': 0, 'promotion': False,
          'comparison': 'Both policies rerun under corrected Eclipse engine; no historical score-equivalence claim',
          'warning': 'Four pairs on two observed maps; random opponents; no retuning on outcomes'})
    (args.output/'native-source-manifest.txt').write_text(SOURCE_MANIFEST)
    for name in frozen:
        source = ROOT/'gaia-rl/experiments' if name == 'original' else ROOT/'gaia-rl/experiments'/name
        dst = args.output/'source-snapshot'/name
        dst.mkdir(parents=True)
        for p in source.glob('*.py'):
            shutil.copyfile(p, dst/p.name)
        assert digest(dst.glob('*.py')) == frozen[name]
    for line in SOURCE_MANIFEST.splitlines():
        _, name = line.split('  ', 1)
        dst = args.output/'native-source'/name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, dst)
    results = {'control': [], 'candidate': []}
    started = time.monotonic()
    for i, spec in enumerate(specs):
        for arm, policy in (('control', ContextResearchTeacher()), ('candidate', SourceRouteTeacher())):
            result, replay = run_game(spec, policy, versions, frozen['research_context' if arm == 'control' else 'source_routes'])
            if replay:
                result['extra'] = extra_metrics(replay, spec['seat'])
                result['research'] = diagnostics(replay, spec['seat'])
                replay['metadata'].update(policy=f'{arm}_source_routes_teacher', source_hashes=frozen)
                with gzip.open(args.output/f'{arm}-{i}.json.gz', 'wt') as f:
                    json.dump(replay, f, separators=(',', ':'))
            write(args.output/f'{arm}-{i}.json', result)
            results[arm].append(result)
            print(arm, i, spec['faction'], result.get('vp', result.get('error')),
                  result.get('research', {}).get('final_tracks'), flush=True)
            guard()
    pairs = [{'seed': spec['seed'], 'faction': spec['faction'],
              'control': a.get('vp'), 'candidate': b.get('vp'),
              'delta': b['vp']-a['vp'] if a['complete'] and b['complete'] else None}
             for spec, a, b in zip(specs, results['control'], results['candidate'])]
    write(args.output/'report.json', {**{arm: summarize(rows) for arm, rows in results.items()},
          'pairs': pairs, 'seconds': time.monotonic()-started,
          'all_complete': all(r['complete'] for rows in results.values() for r in rows), 'promotion': False})


if __name__ == '__main__':
    main()
