"""One preregistered, source-frozen four-teacher game; no learning or publication."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl.versions import require_current_sources, runtime_versions
from four_factions import FACTIONS
from four_factions.games import audit, dump, play, progress
from four_factions.outcomes import summarize
from four_factions.provenance import hashes, verify
from four_factions.timed import TimedPreparationTeacher
from four_factions.value import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', default='quartet-pilot-20260913-27703')
    parser.add_argument('--bgg-openings', action='store_true',
                        help='Guide R1 using native-verified BGG Part 2 inventory goals')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('A new output directory is required; historical results stay intact')
    require_current_sources(ROOT)
    initial = json.loads(Environment(args.seed, 2000).snapshot_json())
    factions = [p['faction'] for p in initial['state']['players']]
    if set(factions) != set(FACTIONS):
        parser.error('Seed does not contain the approved quartet')
    # Reuse the existing source guard and receipts, not an unguarded pilot.
    spec = {'seed': args.seed, 'factions': factions}
    args.output.mkdir(parents=True)
    manifest = {'mode': 'competitive_teacher', 'teacher_variant': (
                    'preparation-paths-v4-bgg-r1' if args.bgg_openings else 'preparation-paths-v3-source-sequences'),
                'bgg_openings': args.bgg_openings,
                'versions': runtime_versions(), 'source_hashes': hashes(), 'factions': list(FACTIONS),
                'setups': {'training': [spec], 'validation': [], 'evaluation': []},
                'timing': {'target_mean_seconds': 60, 'maximum_seconds': 300,
                           'extension_policy': 'finish-current-comparison-only'},
                'training_performed': False, 'promotion': False,
                'forecast_opponents': 'purposeful faction-aware shallow continuations, not optimal opponents'}
    dump(args.output/'manifest.json', manifest)
    for name in manifest['source_hashes']:
        destination = args.output/'source-snapshot'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT/name).read_bytes())
    game = args.output/'training/0'  # Existing spectator layout only, not training data approval.
    try:
        verify(manifest)
        progress(args.output/'progress.json', {'stage': 'competition', 'path': str(game),
                 'all_four_teachers': True, 'training_started': False})
        result = play(spec, game, factory=lambda: TimedPreparationTeacher(
            args.seed, bgg_openings=args.bgg_openings), focal=None)
        receipt = audit(game)
        counts = Counter()
        timings = {f: [] for f in factions}
        with gzip.open(game/'decisions.jsonl.gz', 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                if row['policy'] is not True or not row.get('teacher_audit'):
                    raise ValueError('Every seat must have an audited teacher decision')
                s = row['snapshot']
                faction = s['state']['players'][s['player']]['faction']
                counts[faction] += 1
                timings[faction].append(row['seconds'])
        if set(counts) != set(FACTIONS):
            raise ValueError('Missing teacher faction')
        verify(manifest)
        timing = {f: {'decisions': len(t), 'mean_seconds': sum(t)/len(t),
                       'max_seconds': max(t), 'above_300_seconds': sum(x > 300 for x in t)}
                  for f, t in timings.items()}
        outcomes = summarize(game/'decisions.jsonl.gz', initial, json.loads((game/'terminal.json').read_text()))
        dump(args.output/'report.json', {'complete': True, 'all_four_teachers': True,
             'teacher_decisions': dict(counts), 'game': result, 'native_audit': receipt,
             'timing': timing, 'outcomes': outcomes, 'training_performed': False, 'promotion': False,
             'limitations': ['One map; not general strength evidence',
                            'Incomplete or unsearched forecasts remain unknown',
                            'Existing leaf estimates remain, no calibrated weight claim']})
        progress(args.output/'progress.json', {'stage': 'complete', 'all_four_teachers': True,
                 'native_complete': True})
    except BaseException as error:
        progress(args.output/'progress.json', {'stage': 'failed', 'error': repr(error),
                 'all_four_teachers': True})
        raise


if __name__ == '__main__':
    main()
