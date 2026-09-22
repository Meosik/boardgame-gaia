"""Small isolated quartet BC/PPO comparison; explicit run, new outputs, no promotion."""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time
import traceback

import torch

from gaia_rl.encoding import FeatureEncoder, ENCODING_VERSION
from gaia_rl.versions import require_current_sources, runtime_versions
from four_factions import FACTIONS
from four_factions.games import audit, dump, play, progress
from four_factions.setup import validate
from four_factions.provenance import hashes, verify
from four_factions.teacher import QuartetTeacher
from four_factions.value import ROOT
from strategy_pilot import seed_all, make_module, clone_behavior, ppo_train, ModulePolicy


def samples_from(paths, encoder):
    samples = []
    for path in paths:
        receipt = json.loads((path/'native-audit.json').read_text())
        if not receipt['native_complete']:
            raise ValueError('Demonstration lacks native completion audit')
        if hashlib.sha256((path/'decisions.jsonl.gz').read_bytes()).hexdigest() != receipt['trace_sha256']:
            raise ValueError('Demonstration changed after its native audit')
        with gzip.open(path/'decisions.jsonl.gz', 'rt') as trace:
            for line in trace:
                row = json.loads(line)
                snapshot = row['snapshot']
                if not row['policy'] or len(snapshot['candidates']) <= 1 or row['reason'].startswith('unmodeled'):
                    continue
                faction = snapshot['state']['players'][snapshot['player']]['faction']
                if faction not in FACTIONS:
                    raise ValueError('Outside-quartet demonstration')
                obs = encoder.encode(snapshot, snapshot['player'])
                samples.append((obs['observation'], obs['candidates'][:len(snapshot['candidates'])].copy(),
                                row['index'], faction))
    if set(s[3] for s in samples) != set(FACTIONS):
        raise ValueError('Missing eligible demonstration labels for a faction')
    return samples


def summary(games):
    result = {}
    for faction in FACTIONS:
        rows = [row for game in games if game.get('complete') for row in game['rows'] if row['faction'] == faction]
        attempted = sum(game.get('focal') == faction for game in games)
        result[faction] = {'attempted': attempted, 'completed': len(rows),
            'mean_vp_completed_only': sum(row['vp'] for row in rows)/len(rows) if rows else None,
            'mean_win_share_completed_only': sum(row['win_share'] for row in rows)/len(rows) if rows else None}
    return result


def evaluate(factory, specs, output, manifest):
    games = []
    for index, spec in enumerate(specs):
        for faction in FACTIONS:
            verify(manifest)
            destination = output/f'{index}-{faction}'
            try:
                result = play(spec, destination, factory=factory, focal=faction)
                audit(destination)
            except Exception as error:
                result = {'complete': False, **spec, 'focal': faction, 'error': repr(error)}
            games.append(result)
            # Individual failures remain saved; never report only successful seeds.
    return games


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setups', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('A new output directory is required')
    pools = json.loads(args.setups.read_text())
    validate(pools)
    require_current_sources(ROOT)
    # Same previously approved small CPU budget, not a long-strength-training run.
    args.seed, args.capacity = 19, 2048
    args.bc_epochs, args.ppo_iterations, args.batch_size = 4, 4, 256
    torch.set_num_threads(2)
    seed_all(args.seed)
    versions = runtime_versions()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {'versions': versions, 'encoding_version': ENCODING_VERSION,
        'source_hashes': hashes(), 'factions': FACTIONS, 'setups': pools,
        'settings': {'seed': args.seed, 'capacity': args.capacity, 'bc_epochs': args.bc_epochs,
                     'ppo_iterations': args.ppo_iterations, 'batch_size': args.batch_size, 'torch_threads': 2},
        'initialization': 'fresh matched weights, fresh PPO optimizers; no old checkpoint overwritten',
        'promotion': False, 'reward': 'unchanged native terminal relative VP /100, gamma1',
        'evaluation': 'one focal policy vs three uniform random opponents; separate maps balanced by seat'}
    dump(args.output/'manifest.json', manifest)
    for name in manifest['source_hashes']:
        destination = args.output/'source-snapshot'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((ROOT/name).read_bytes())
    started = time.monotonic()
    stage = 'demonstrations'
    try:
        paths = {}
        for split in ('training', 'validation'):
            paths[split] = []
            for index, spec in enumerate(pools[split]):
                verify(manifest)
                destination = args.output/split/str(index)
                progress(args.output/'progress.json', {'stage': stage, 'split': split, 'game': index,
                         'path': str(destination), 'training_started': False})
                play(spec, destination)
                audit(destination)
                paths[split].append(destination)
        verify(manifest)
        encoder = FeatureEncoder(args.capacity)
        samples = samples_from(paths['training'], encoder)
        validation = samples_from(paths['validation'], encoder)
        dump(args.output/'dataset.json', {'training': dict(Counter(s[3] for s in samples)),
            'validation': dict(Counter(s[3] for s in validation)), 'all_demonstrations_native_audited': True})
        seed_all(args.seed)
        model = make_module(encoder)
        initial = copy.deepcopy(model.state_dict())
        torch.save(initial, args.output/'initial.pt')
        stage = 'behavior_cloning'
        progress(args.output/'progress.json', {'stage': stage, 'training_started': True})
        bc = clone_behavior(model, samples, validation, args.bc_epochs, args.seed)
        bc_weights = copy.deepcopy(model.state_dict())
        if not all(torch.isfinite(v).all() for v in bc_weights.values()):
            raise ValueError('Nonfinite BC weights')
        dump(args.output/'imitation.json', bc)
        (args.output/'bc_only').mkdir()
        torch.save(bc_weights, args.output/'bc_only/inference.pt')
        del samples, validation, model
        verify(manifest)
        import ray
        stage = 'ppo'
        progress(args.output/'progress.json', {'stage': stage, 'training_started': True})
        ray.init(num_cpus=2, include_dashboard=False, object_store_memory=128*1024**2, log_to_driver=False)
        try:
            control, _ = ppo_train(initial, pools['training'], args, args.output/'baseline_ppo')
            verify(manifest)
            student, _ = ppo_train(bc_weights, pools['training'], args, args.output/'bc_ppo')
        finally:
            ray.shutdown()
        for weights, before in ((control, initial), (student, bc_weights)):
            if not any(not torch.equal(weights[k], before[k]) for k in before):
                raise ValueError('No training parameter updates')
        stage = 'held_out_evaluation'
        results = {}
        arms = [('bc_only', lambda: ModulePolicy(encoder, bc_weights)),
                ('baseline_ppo', lambda: ModulePolicy(encoder, control)),
                ('bc_ppo', lambda: ModulePolicy(encoder, student)), ('teacher', QuartetTeacher)]
        for label, factory in arms:
            progress(args.output/'progress.json', {'stage': stage, 'arm': label, 'training_started': True})
            games = evaluate(factory, pools['evaluation'], args.output/'evaluation'/label, manifest)
            dump(args.output/f'{label}_evaluation.json', games)
            results[label] = summary(games)
        verify(manifest)
        complete = all(r['attempted'] == r['completed'] == 4 for arm in results.values() for r in arm.values())
        report = {'all_games_complete': complete, 'summary': results, 'promotion': False,
            'seconds': time.monotonic()-started, 'peak_driver_rss_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'limitations': ['Very small PPO budget; no strength or human-level claim',
                'Additional BC compute is not matched total compute', 'Inference-only weights, not resumable training checkpoints',
                'Random opponents; different maps balanced by seat, not rotations of the same map',
                'Teacher conservation is not a PPO legality mask; student violations are reported',
                'Different teacher search depth by faction; Terrans/Taklons are native local soft heuristics']}
        dump(args.output/'report.json', report)
        progress(args.output/'progress.json', {'stage': 'complete' if complete else 'failed_evaluations',
                                             'all_games_complete': complete, 'promotion': False})
        if not complete:
            raise RuntimeError('One or more held-out games failed; see retained per-game reports')
    except BaseException:
        (args.output/'failure.log').write_text(traceback.format_exc())
        progress(args.output/'progress.json', {'stage': 'failed', 'failed_stage': stage, 'promotion': False})
        raise


if __name__ == '__main__':
    main()
