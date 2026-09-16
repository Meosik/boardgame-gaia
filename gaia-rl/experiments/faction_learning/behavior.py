"""Same-faction, explicitly sourced BC; no deployment or PPO-state reset."""
import json
from pathlib import Path
import shutil

import numpy as np
import torch
from ray.rllib.core.columns import Columns

from gaia_rl.encoding import FeatureEncoder
from .models import digest, implementation_hashes, load_model, read_catalog, write_json
from .records import audited_samples


def batch(samples):
    capacity = max(len(s[1]) for s in samples)
    candidates = np.zeros((len(samples), capacity, samples[0][1].shape[1]), np.float32)
    mask = np.zeros((len(samples), capacity), bool)
    for i, (_, actions, _, _) in enumerate(samples):
        candidates[i, :len(actions)] = actions
        mask[i, :len(actions)] = True
    return {Columns.OBS: {'observation': torch.from_numpy(np.stack([s[0] for s in samples])),
        'candidates': torch.from_numpy(candidates), 'action_mask': torch.from_numpy(mask)}}, \
        torch.tensor([s[2] for s in samples])


def metrics(module, samples):
    if not samples:
        raise ValueError('No matching choices with more than one legal candidate')
    loss_sum, correct = 0.0, 0
    module.eval()
    with torch.no_grad():
        for offset in range(0, len(samples), 8):
            inputs, labels = batch(samples[offset:offset + 8])
            logits = module.forward_train(inputs)[Columns.ACTION_DIST_INPUTS]
            loss = torch.nn.functional.cross_entropy(logits, labels, reduction='sum')
            if not torch.isfinite(loss):
                raise ValueError('Non-finite imitation metric')
            loss_sum += float(loss)
            correct += int((logits.argmax(-1) == labels).sum())
    return {'cross_entropy': loss_sum / len(samples), 'accuracy': correct / len(samples),
            'samples': len(samples)}


def dataset(training_games, validation_games, faction, encoder, *, label_source='human'):
    if not training_games or not validation_games:
        raise ValueError('Separate training and validation games are required')
    seen = {key: set() for key in ('seed', 'recording_id', 'initial_sha256', 'trace_sha256')}
    samples, audits = {}, {}
    for split, paths in (('training', training_games), ('validation', validation_games)):
        samples[split], audits[split] = [], []
        for path in paths:
            rows, audit = audited_samples(path, faction, encoder, controller=label_source)
            if not rows:
                raise ValueError(f'No {faction} {label_source} labels in {path}')
            for key, values in seen.items():
                if audit[key] in values:
                    raise ValueError(f'Duplicate/leaked demonstration game: {key}')
                values.add(audit[key])
            samples[split].extend(rows)
            audits[split].append(audit)
    return samples, audits


def train(source, destination, faction, training_games, validation_games, *, epochs, seed=19,
          label_source='human'):
    if type(epochs) is not int or epochs <= 0:
        raise ValueError('An explicit positive epoch budget is required')
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    module, catalog = load_model(source, faction)
    source_digest = digest(source / 'catalog.json')
    samples, audits = dataset(training_games, validation_games, faction,
                             FeatureEncoder(catalog['capacity']), label_source=label_source)
    before = metrics(module, samples['validation'])
    optimizer = torch.optim.Adam(module.parameters(), lr=0.0003)
    rng = np.random.default_rng(seed)
    steps = 0
    for _ in range(epochs):
        module.train()
        order = rng.permutation(len(samples['training']))
        for offset in range(0, len(order), 8):
            inputs, labels = batch([samples['training'][i] for i in order[offset:offset + 8]])
            loss = torch.nn.functional.cross_entropy(
                module.forward_train(inputs)[Columns.ACTION_DIST_INPUTS], labels)
            if not torch.isfinite(loss):
                raise ValueError('Non-finite BC loss')
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in module.parameters()):
                raise ValueError('Non-finite BC weights')
            steps += 1
    report = {'faction': faction, 'label_source': label_source,
        'epochs': epochs, 'gradient_steps': steps, 'seed': seed,
        'before_validation': before, 'after_validation': metrics(module, samples['validation']),
        'training': metrics(module, samples['training']), 'datasets': audits, 'promotion': False,
        'scope': 'BC only; fresh isolated Adam, original PPO optimizer/checkpoint untouched',
        'limitations': ['Held-out imitation accuracy is not game strength or improved VP',
                        'Controller provenance is supplied by the recording caller',
                        'No automatic in-game update; separate game evaluation still required']}
    if read_catalog(source) != catalog or digest(source / 'catalog.json') != source_digest:
        raise ValueError('Source catalog changed during BC')
    destination.mkdir(parents=True, exist_ok=False)
    for other in catalog['models']:
        folder = destination / other
        folder.mkdir()
        if other == faction:
            torch.save(module.state_dict(), folder / 'inference.pt')
            torch.save(optimizer.state_dict(), folder / 'bc_optimizer.pt')
            catalog['models'][other] = {'status': 'bc_candidate',
                'sha256': digest(folder / 'inference.pt'), 'parent_sha256': catalog['models'][other]['sha256'],
                'optimizer_sha256': digest(folder / 'bc_optimizer.pt')}
        else:
            shutil.copyfile(source / other / 'inference.pt', folder / 'inference.pt')
            # Do not imply that copied inference weights include an older BC optimizer.
            catalog['models'][other].pop('optimizer_sha256', None)
    catalog.update(parent={'catalog': str(source.resolve()), 'sha256': source_digest},
                   implementation=implementation_hashes(), resume='inference/BC initialization only')
    write_json(destination / 'bc-report.json', report)
    write_json(destination / 'catalog.json', catalog)
    read_catalog(destination)
    return report
