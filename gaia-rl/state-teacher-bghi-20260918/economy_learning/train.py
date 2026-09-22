"""Opt-in continued-weight pilot: matched PPO vs economy BC + PPO; no production edits."""
import argparse
from collections import Counter
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
import torch
from gaia_rl._native import Environment
from gaia_rl.encoding import FeatureEncoder, ENCODING_VERSION
from gaia_rl.versions import require_current_sources, require_compatible_versions
from economy.teacher import EconomyTeacher
from strategy_teacher import TARGETS
from strategy_pilot import (seed_all, make_module, clone_behavior, ppo_train,
                            ModulePolicy, evaluate, summarize)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hash(directory):
    return hashlib.sha256(b''.join(p.read_bytes() for p in sorted(directory.glob('*.py')))).hexdigest()


def dump(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)


def validate_splits(manifest):
    train, validation, evaluation = (manifest[k] for k in ('training', 'validation', 'evaluation'))
    if list(map(len, (train, validation, evaluation))) != [6, 2, 4]:
        raise ValueError('Expected original six/two/four pilot setup split')
    specs = train+validation+evaluation
    if len({s['seed'] for s in specs}) != len(specs):
        raise ValueError('Overlapping train/validation/evaluation seeds')
    for spec in specs:
        actual = json.loads(Environment(spec['seed']).snapshot_json())
        lineup = [p['faction'] for p in actual['state']['players']]
        if lineup != spec['factions'] or not all(t in lineup for t in TARGETS):
            raise ValueError('Saved faction lineup differs from native setup')
    for faction in TARGETS:
        if Counter(s['factions'].index(faction) for s in evaluation) != Counter(range(4)):
            raise ValueError('Evaluation seats are not balanced')
    return train, validation, evaluation


def collect(specs, encoder, output, policy=None):
    """Only the two target factions receive labels; native candidates stay unmodified."""
    policy = policy or EconomyTeacher()
    samples, games = [], []
    with gzip.open(output, 'wt') as log:
        for spec in specs:
            env = Environment(spec['seed'], 2000)
            rng = random.Random(spec['seed']+':opponent')
            histogram = Counter()
            while not env.is_terminal():
                s = json.loads(env.snapshot_json())
                player = s['state']['players'][s['player']]
                if player['faction'] in TARGETS:
                    decision, index = policy.choose(s)
                    reason = policy.score(s, s['candidates'][index]['action'])[1]
                    histogram[player['faction']+':'+s['candidates'][index]['action']['type']] += 1
                    if len(s['candidates']) > 1 and not reason.startswith('unmodeled'):
                        encoded = encoder.encode(s, s['player'])
                        samples.append((encoded['observation'], encoded['candidates'][:len(s['candidates'])].copy(), index, player['faction']))
                    log.write(json.dumps({'seed': spec['seed'], 'snapshot': s, 'index': index, 'reason': reason})+'\n')
                else:
                    decision, index = s['decision_id'], rng.randrange(len(s['candidates']))
                env.step(decision, index)
            terminal = json.loads(env.snapshot_json())
            games.append({**spec, 'scores': dict(env.final_scores()), 'steps': terminal['steps'], 'actions': dict(histogram)})
            print('demonstration', spec['seed'], games[-1]['scores'], flush=True)
    if not samples:
        raise ValueError('No eligible teacher labels')
    return samples, games


def load_initial(encoder, path):
    weights = torch.load(path, weights_only=True, map_location='cpu')
    if not weights or not all(torch.isfinite(v).all() for v in weights.values()):
        raise ValueError('Invalid initial weights')
    model = make_module(encoder)
    model.load_state_dict(weights, strict=True)
    initial = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    for key, value in weights.items():
        torch.testing.assert_close(initial[key], value, rtol=0, atol=0)
    return model, initial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    old_dir = ROOT/'gaia-rl/runs/strategy-pilot-v2'
    old = json.loads((old_dir/'manifest.json').read_text())
    economic = json.loads((ROOT/'gaia-rl/runs/economy-teacher-v3/manifest.json').read_text())
    versions = old['versions']
    require_current_sources(ROOT)
    require_compatible_versions(versions)
    hashes = {'original': source_hash(ROOT/'gaia-rl/experiments'),
              'teacher': source_hash(ROOT/'gaia-rl/experiments/economy'),
              'learning': source_hash(Path(__file__).parent)}
    if hashes['original'] != old['experiment_hash'] or hashes['teacher'] != economic['economy_experiment_hash']:
        raise ValueError('Pinned original/teacher implementation changed')
    if ENCODING_VERSION != old['encoding_version']:
        raise ValueError('Encoder version changed')
    train, validation, evaluation = validate_splits(old)
    args.seed = 19
    args.capacity = 2048
    args.bc_epochs = 4
    args.ppo_iterations = 4
    args.batch_size = 256
    weights_path = old_dir/'baseline/inference.pt'
    weight_hash = file_hash(weights_path)
    torch.set_num_threads(2)
    seed_all(args.seed)
    encoder = FeatureEncoder(args.capacity)
    model, initial = load_initial(encoder, weights_path)
    args.output.mkdir(parents=True)
    start = time.monotonic()
    dump(args.output/'manifest.json', {'versions': versions, 'encoding_version': ENCODING_VERSION,
        'source_hashes': hashes, 'starting_weights': str(weights_path), 'starting_weights_sha256': weight_hash,
        'settings': {k: v for k, v in vars(args).items() if k != 'output'},
        'training': train, 'validation': validation, 'evaluation': evaluation,
        'warning': 'Continued inference weights, fresh optimizers. Same PPO budget; extra BC compute. Previously inspected maps, random opponents.'})
    try:
        samples, demos = collect(train, encoder, args.output/'demonstrations.jsonl.gz')
        valid_samples, valid_games = collect(validation, encoder, args.output/'validation.jsonl.gz')
        dump(args.output/'demonstration_report.json', {'training': demos, 'validation': valid_games,
            'training_samples': len(samples), 'validation_samples': len(valid_samples),
            'samples_by_faction': dict(Counter(s[3] for s in samples))})
        seed_all(args.seed)
        bc = clone_behavior(model, samples, valid_samples, args.bc_epochs, args.seed)
        bc_weights = copy.deepcopy(model.state_dict())
        if not all(torch.isfinite(v).all() for v in bc_weights.values()):
            raise ValueError('Nonfinite BC weights')
        dump(args.output/'imitation.json', bc)
        (args.output/'bc_only').mkdir()
        torch.save(bc_weights, args.output/'bc_only/inference.pt')
        import ray
        ray.init(num_cpus=2, include_dashboard=False, object_store_memory=128*1024**2, log_to_driver=False)
        try:
            control, _ = ppo_train(initial, train, args, args.output/'continued_ppo')
            student, _ = ppo_train(bc_weights, train, args, args.output/'economy_bc_ppo')
        finally:
            ray.shutdown()
        result = {}
        for label, weights in (('continued_ppo', control), ('bc_only', bc_weights), ('economy_bc_ppo', student)):
            policy = ModulePolicy(encoder, weights)
            games = evaluate(policy, evaluation, label)
            dump(args.output/f'{label}_evaluation.json', games)
            result[label] = summarize(games)
        require_current_sources(ROOT)
        require_compatible_versions(versions)
        actual = {'original': source_hash(ROOT/'gaia-rl/experiments'),
                  'teacher': source_hash(ROOT/'gaia-rl/experiments/economy'),
                  'learning': source_hash(Path(__file__).parent)}
        if actual != hashes or file_hash(weights_path) != weight_hash:
            raise ValueError('Source or initial weights changed during training')
        dump(args.output/'report.json', {'summary': result, 'imitation': bc, 'seconds': time.monotonic()-start,
            'all_games_complete': all(r['completed'] == r['attempted'] for arm in result.values() for r in arm.values()),
            'limitations': ['Inference weights continued, optimizer reset', 'Additional BC compute not matched',
                'Teacher scoped to Xenos/HadschHallas; PPO shared across factions',
                'Small reused-map random-opponent sample; no generalization claim',
                'Pinned engine retains raw-Gaia and TF Mars cost discrepancies',
                'Academy, conversion-chain, power-acceptance and federation-lookahead proposals not implemented']})
        print(json.dumps(result, indent=2), flush=True)
    except Exception:
        (args.output/'failure.log').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
