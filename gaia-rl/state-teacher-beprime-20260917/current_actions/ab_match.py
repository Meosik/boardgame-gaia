"""Paired four-faction A/B matches; no training or automatic promotion."""
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics

from gaia_rl import Environment
from gaia_rl.versions import require_current_sources, runtime_versions
from current_actions.conservation import identity
from faction_teachers.clock import AdaptiveClock
from four_factions import FACTIONS
from four_factions.games import audit, dump, play, progress
from four_factions.provenance import hashes, verify
from four_factions.timed import TimedPreparationTeacher
from four_factions.value import ROOT


def validate_seeds(seeds):
    if (not seeds or any(not isinstance(s, str) or not s for s in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError('Nonempty distinct seed strings required')
    specs = []
    for seed in seeds:
        snapshot = json.loads(Environment(seed, 2000).snapshot_json())
        factions = [p['faction'] for p in snapshot['state']['players']]
        if len(factions) != 4 or set(factions) != set(FACTIONS):
            raise ValueError(f'{seed}: requires Xenos/HadschHallas/Terrans/Taklons, got {factions}')
        specs.append({'seed': seed, 'factions': factions,
                      'initial_snapshot_sha256': sha256(identity(snapshot).encode()).hexdigest()})
    return specs


def assignments(spec, pair):
    # Reverse game order between maps, not native seats/factions. Each faction
    # sees A and B in its identical native seat on each map.
    # Cycle all three two-versus-two partitions across maps instead of always
    # coupling the same factions' evaluation variants.
    team = (('Xenos', 'Terrans'), ('Xenos', 'Taklons'), ('Xenos', 'HadschHallas'))[pair % 3]
    complement = tuple(f for f in FACTIONS if f not in team)
    order = (complement, team) if pair % 2 == 0 else (team, complement)
    return [{'seed': spec['seed'], 'delta_factions': list(factions)} for factions in order]


def paired_scores(first, second):
    if (not first.get('complete') or not second.get('complete')
            or first['seed'] != second['seed']
            or first['factions'] != second['factions']
            or len(first['factions']) != 4 or set(first['factions']) != set(FACTIONS)):
        raise ValueError('Both complete games must share the exact seed and native faction seats')
    teams = [set(game.get('delta_factions', ())) for game in (first, second)]
    if any(len(team) != 2 for team in teams) or teams[0] & teams[1] or teams[0] | teams[1] != set(FACTIONS):
        raise ValueError('Complementary two-A/two-B assignments required')
    scores = [{int(k): v for k, v in game['scores'].items()} for game in (first, second)]
    if any(set(s) != set(range(4)) or any(not isinstance(v, (int, float)) or not math.isfinite(v)
                                        for v in s.values()) for s in scores):
        raise ValueError('Four finite native final scores required')
    by_faction = {}
    for faction in FACTIONS:
        seat = first['factions'].index(faction)
        a, b = (scores[1][seat], scores[0][seat]) if faction in teams[0] else (scores[0][seat], scores[1][seat])
        by_faction[faction] = {'A': a, 'B': b, 'B_minus_A': b-a}
    return {'seed': first['seed'], 'by_faction': by_faction,
            'mean_B_minus_A': statistics.mean(s['B_minus_A'] for s in by_faction.values())}


def summarize(pairs):
    if not pairs or len({p['seed'] for p in pairs}) != len(pairs):
        raise ValueError('Nonempty distinct completed pairs required')
    deltas = [p['mean_B_minus_A'] for p in pairs]
    return {'all_complete': True, 'pairs': len(pairs), 'games': 2*len(pairs),
            'mean_B_minus_A': statistics.mean(deltas),
            'paired_map_stdev': statistics.stdev(deltas) if len(deltas) > 1 else None,
            'by_faction': {f: {k: statistics.mean(p['by_faction'][f][k] for p in pairs)
                               for k in ('A', 'B', 'B_minus_A')} for f in FACTIONS},
            'training_performed': False, 'promotion': False,
            'limitations': ['Head-to-head crossover, not independent fixed-opponent trajectories',
                            'Shared quick fallback use is reported separately from B evaluation',
                            'Same clock limits, not equal completed search work',
                            'Existing leaf estimates are uncalibrated; no strength threshold assumed']}


def trace_statistics(path):
    """Audit actual execution modes so timeout fallback cannot masquerade as B."""
    modes = {f: Counter() for f in FACTIONS}
    seconds = {f: [] for f in FACTIONS}
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            receipt = row.get('teacher_audit')
            if row.get('policy') is not True or not receipt or 'ranking_mode' not in receipt:
                raise ValueError('Missing audited teacher execution mode')
            s = row['snapshot']
            faction = s['state']['players'][s['player']]['faction']
            modes[faction][receipt['ranking_mode']] += 1
            seconds[faction].append(row['seconds'])
    return {f: {'modes': dict(modes[f]), 'decisions': len(seconds[f]),
                'mean_seconds': statistics.mean(seconds[f]) if seconds[f] else None,
                'max_seconds': max(seconds[f], default=None)} for f in FACTIONS}


def make_manifest(specs):
    return {'experiment': 'current-action-table-vs-guide-state-delta-v2', 'versions': runtime_versions(),
            'source_hashes': hashes(), 'specs': specs,
            'schedule': [assignments(spec, i) for i, spec in enumerate(specs)],
            'A': 'Existing quartet policies, including CurrentActionTeacher stage1',
            'B': 'Native delta and rollout share B19-guided expansion value; conditional paid track plans',
            'factions': list(FACTIONS), 'bgg_openings': True,
            'clock': {'target_seconds': 10, 'long_seconds': 120, 'uses_per_seat': 6},
            'max_native_decisions': 2000, 'horizon_incomes': 2,
            'training_performed': False, 'promotion': False,
            'scope': 'B19 quartet expansion guidance; original resource prices/limits and A preserved; '
                     'not comparable to v1 without accounting for the changed B evaluator/plans'}


def run(specs, output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('A new output directory is required; historical results stay intact')
    manifest = make_manifest(specs)
    verify(manifest)
    output.mkdir(parents=True)
    dump(output/'manifest.json', manifest)
    for name in manifest['source_hashes']:
        destination = output/'source-snapshot'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT/name).read_bytes())
    pairs = []
    try:
        for pair, spec in enumerate(specs):
            completed = []
            for assignment in assignments(spec, pair):
                verify(manifest)
                delta = assignment['delta_factions']
                game = output/f'pair-{pair:03d}'/('B-'+'-'.join(delta))
                progress(output/'progress.json', {'state': 'running', 'completed_pairs': len(pairs),
                                                 'pair': pair, 'game': str(game)})

                def factory():
                    clock = AdaptiveClock()
                    return TimedPreparationTeacher(spec['seed'], target_seconds=clock.target_seconds,
                        maximum_seconds=clock.long_seconds, adaptive_clock=clock,
                        bgg_openings=True, delta_factions=delta)

                result = play(spec, game, factory=factory, focal=None)
                receipt = audit(game)
                if not receipt.get('native_complete'):
                    raise ValueError('Native replay audit did not complete')
                stats = trace_statistics(game/'decisions.jsonl.gz')
                dump(game/'ab-audit.json', {'delta_factions': delta, 'native': receipt, 'timing': stats})
                verify(manifest)
                completed.append({**result, 'delta_factions': delta})
            comparison = paired_scores(*completed)
            dump(output/f'pair-{pair:03d}'/'comparison.json', comparison)
            pairs.append(comparison)
        verify(manifest)
        report = summarize(pairs)
        dump(output/'report.json', report)
        progress(output/'progress.json', {'state': 'complete', 'completed_pairs': len(pairs)})
        return report
    except BaseException as error:
        progress(output/'progress.json', {'state': 'failed', 'completed_pairs': len(pairs), 'error': repr(error)})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', nargs='+', required=True, help='Each distinct quartet seed runs two games')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preflight-only', action='store_true', help='Validate setups and show schedule; no games or files')
    args = parser.parse_args()
    require_current_sources(ROOT)
    specs = validate_seeds(args.seeds)
    if args.output.exists():
        parser.error('A new output directory is required')
    if args.preflight_only:
        print(json.dumps({'specs': specs, 'schedule': [assignments(s, i) for i, s in enumerate(specs)],
                          'games': 2*len(specs), 'training_performed': False}, indent=2))
        return
    print(json.dumps(run(specs, args.output), indent=2))


if __name__ == '__main__':
    main()
