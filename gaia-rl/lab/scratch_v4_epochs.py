"""Epoch length with encoding 4 on the 93 games of 114 + 119, and the full-data checkpoints (HANDOFF E166 (ㄱ); lab
queue 122, run in the work tree). Cycle 121a trained the `all` arm for 9 epochs and its validation loss was lowest at
the last point, so 9 epochs are not too many and nothing longer was measured.
  1 load     the shards of 121a: gaia-rl/runs/bc-114-v4-shards-fc19 (cycle 120) and
             gaia-rl/runs/bc-119-v4-shards-fc19-c4096 (121a, export capacity 4096); no export here
  2 folds    the 5 game-level folds of 121a (game k of a quartet -> fold k mod 5)
  3 curve    per fold the `all` arm of 121a (every training game of the fold; the network and the optimizer step of
             tools/bc_train.py: width 256, lr 0.001, batch 256, torch seed 0, batch-order seed 0, shard by shard)
             trained for 18 epochs; after every epoch the validation loss and the hit of every validation decision.
             Epochs 1-9 are the same computation as 121a: the fold losses and accuracies at epoch 9 are compared
             with the figures of 121a.
  4 full     one training on all 93 games with the same settings, 18 epochs, the weights of every epoch saved as
             a checkpoint (inference.pt + metadata.json as tools/bc_train.py writes them) under
             gaia-rl/runs/bc-93-v4-w256-fc19/epoch-01 ... epoch-18 (written to <dir>.partial, renamed at the end)
  5 read     per epoch: fold-mean validation loss, per-game accuracy over the 93 validation games, and the paired
             per-game difference to epoch 9 (t interval). Checkpoint epoch = the epoch with the lowest fold-mean
             validation loss (the rule of bc_train.py); the epoch with the highest accuracy is reported beside it,
             with the paired difference between the two when they differ.
Writes gaia-rl/runs/bc-v4-epochs-93/metrics.json with the commit of this file (the full run refuses to start when the
file differs from its commit, or when the checkpoint directory exists).
Usage: scratch_v4_epochs.py          # 5 folds x 18 epochs + the full training, about 35-40 minutes
       scratch_v4_epochs.py smoke    # fold 0 and the full training at 2 epochs, checkpoints removed again"""
import json
import math
import os
import shutil
import subprocess
import sys
import time

import numpy as np

os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/tools']
import bc_train
import torch
from scipy.stats import t

SMOKE = sys.argv[1:] == ['smoke']
SCRIPT = 'gaia-rl/lab/scratch_v4_epochs.py'
SOURCES = [('114', 'gaia-rl/runs/bc-114-fc19/manifest.jsonl', 'gaia-rl/runs/bc-114-v4-shards-fc19'),
           ('119', 'gaia-rl/runs/bc-119-fc19/manifest.jsonl', 'gaia-rl/runs/bc-119-v4-shards-fc19-c4096')]
METRICS = 'gaia-rl/runs/bc-v4-epochs-93/metrics.json'
CHECKPOINTS = 'gaia-rl/runs/bc-v4-epochs-smoke' if SMOKE else 'gaia-rl/runs/bc-93-v4-w256-fc19'
EPOCHS, REFERENCE = (2, 1) if SMOKE else (18, 9)
BATCH, LR, WIDTH, FOLDS = 256, 0.001, 256, 5
FOLD_LIST = [0] if SMOKE else list(range(FOLDS))
REFERENCE_121A = {'loss': [2.0816, 2.094, 2.1144, 2.1069, 2.1488],          # the `all` arm of 121a at epoch 9
                  'accuracy': [0.4052, 0.4007, 0.3647, 0.3807, 0.3917]}
start = time.time()


def git(*arguments):
    return subprocess.run(['git', *arguments], capture_output=True, text=True, check=True).stdout.strip()


commit, dirty = git('log', '-1', '--format=%H', '--', SCRIPT), git('status', '--porcelain', '--', SCRIPT)
if not SMOKE:
    assert commit and not dirty, f'{SCRIPT} differs from its commit: {dirty!r}'
    assert not os.path.exists(CHECKPOINTS), f'{CHECKPOINTS} exists'
shutil.rmtree(CHECKPOINTS+'.partial', ignore_errors=True)

games, shards, decisions = [], [], 0
for source, manifest, directory in SOURCES:
    entries = [json.loads(line) for line in open(manifest)]
    assert all(entry['replays'] for entry in entries), manifest   # then the shard game id is the manifest line number
    for path in bc_train.shard_paths(directory):
        shard = bc_train.load_shard(path)
        shard['game'] = shard['game'].astype(np.int64)+len(games)
        shard['first'] = decisions
        decisions += len(shard['chosen'])
        shards.append(shard)
    games += [{'source': source, 'seed': entry['seed'], 'decisions': entry['decisions']} for entry in entries]
game_of = np.concatenate([shard['game'] for shard in shards])
present = np.bincount(game_of, minlength=len(games))
assert np.array_equal(present, [game['decisions'] for game in games]), 'shard decisions differ from the manifests'
SIZES = (shards[0]['observation'].shape[1], shards[0]['cand'].shape[1])
assert all((shard['observation'].shape[1], shard['cand'].shape[1]) == SIZES for shard in shards)
from gaia_rl.encoding import FeatureEncoderV4
from gaia_rl.versions import ENGINE_BUILD_ID, model_build_id, runtime_versions
assert SIZES == (FeatureEncoderV4().state_size, FeatureEncoderV4().candidate_size), SIZES

active = list(range(len(games)))
quartet = [game['seed'].split('@')[0].rsplit('-', 1)[0] for game in games]
fold_of = np.full(len(games), -1)
for name in sorted(set(quartet)):
    for k, i in enumerate(i for i in active if quartet[i] == name):
        fold_of[i] = k % FOLDS
source_of = np.array([game['source'] for game in games])
print('loaded: games', len(active), {name: quartet.count(name) for name in sorted(set(quartet))},
      '| decisions', decisions, '| script commit', commit[:12], '| seconds', round(time.time()-start), flush=True)


def rows_of(members):
    """Per shard: the sample rows of these games."""
    members = np.array(sorted(members))
    return [np.flatnonzero(np.isin(shard['game'], members)) for shard in shards]


def tensors_of(batch):
    return {key: torch.from_numpy(value) for key, value in batch.items()}


def evaluate(model, val_rows):
    """Validation loss per decision and (global decision index, hit) of every validation decision."""
    model.eval()
    loss, index, hit = 0.0, [], []
    with torch.no_grad():
        for shard, rows in zip(shards, val_rows):
            for number, batch in enumerate(bc_train.batches(shard, BATCH, None, rows) if len(rows) else ()):
                batch = tensors_of(batch)
                logits, _ = model(batch['observation'], batch['candidates'], batch['mask'])
                loss += float(torch.nn.functional.cross_entropy(logits, batch['chosen'], reduction='sum'))
                index.append(shard['first']+rows[number*BATCH:(number+1)*BATCH])
                hit.append((logits.argmax(dim=-1) == batch['chosen']).numpy())
    index, hit = np.concatenate(index), np.concatenate(hit)
    return loss/len(index), index, hit


def fit(train_rows, val_rows=None, after_epoch=None):
    """EPOCHS epochs of the training step of bc_train._run (the step of 121a's fit: fresh per-shard permutations
    every epoch). Returns the model and one point per epoch: steps, training loss, and with val_rows the validation
    loss, accuracy, decision index and hit. after_epoch(epoch, model, points) runs at the end of every epoch."""
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    model = bc_train.build_model(*SIZES, WIDTH, 4)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    steps, points = 0, []
    for epoch in range(1, EPOCHS+1):
        loss_sum = samples = 0
        for shard, rows in zip(shards, train_rows):
            for batch in (bc_train.batches(shard, BATCH, rng, rows) if len(rows) else ()):
                model.train()
                batch = tensors_of(batch)
                logits, _ = model(batch['observation'], batch['candidates'], batch['mask'])
                policy_loss = torch.nn.functional.cross_entropy(logits, batch['chosen'], reduction='sum')
                loss = policy_loss/len(batch['chosen'])
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                steps += 1
                loss_sum += float(policy_loss.detach())
                samples += len(batch['chosen'])
        point = {'epoch': epoch, 'steps': steps, 'train_loss': loss_sum/samples}
        assert math.isfinite(point['train_loss']), point
        if val_rows is not None:
            point['loss'], point['index'], point['hit'] = evaluate(model, val_rows)
            point['accuracy'] = float(point['hit'].mean())
        points.append(point)
        if after_epoch is not None:
            after_epoch(epoch, model, points)
    return model, points


# 3: the curve of the `all` arm, 5 folds
hits = np.zeros((EPOCHS, decisions), dtype=bool)
scored = np.zeros(decisions, dtype=bool)
fold_points = []
for fold in FOLD_LIST:
    val_games = [i for i in active if fold_of[i] == fold]
    train_games = [i for i in active if fold_of[i] != fold]
    assert not set(val_games) & set(train_games)
    train_rows, val_rows = rows_of(train_games), rows_of(val_games)
    val_decisions = int(sum(len(part) for part in val_rows))
    _, points = fit(train_rows, val_rows)
    for point in points:
        index, hit = point.pop('index'), point.pop('hit')
        assert len(index) == val_decisions and not scored[index].any()
        hits[point['epoch']-1][index] = hit
    scored[index] = True
    fold_points.append(points)
    print(json.dumps({'fold': fold, 'val_games': len(val_games), 'val_decisions': val_decisions,
                      'train_games': len(train_games), 'train_decisions': int(sum(len(part) for part in train_rows)),
                      'steps': points[-1]['steps'], 'loss': [round(point['loss'], 4) for point in points],
                      'accuracy': [round(point['accuracy'], 4) for point in points],
                      'seconds': round(time.time()-start)}), flush=True)

scored_games = [g for g in active if fold_of[g] in FOLD_LIST]
game_fold = np.array([fold_of[g] for g in scored_games])
accuracy_games = {epoch: np.array([hits[epoch-1][game_of == g].mean() for g in scored_games])
                  for epoch in range(1, EPOCHS+1)}


def paired(first, second):
    """Per-game accuracy of epoch `first` minus epoch `second`, paired on the validation games (t interval)."""
    diff = accuracy_games[first]-accuracy_games[second]
    mean, sd, n = float(diff.mean()), float(diff.std(ddof=1)), len(diff)
    half = float(t.ppf(0.975, n-1))*sd/math.sqrt(n)
    return {'first': first, 'second': second, 'mean': round(mean, 4), 'low': round(mean-half, 4),
            'high': round(mean+half, 4), 't': round(mean/(sd/math.sqrt(n)), 2) if sd else None, 'n': n,
            'better': int((diff > 0).sum()), 'equal': int((diff == 0).sum()), 'worse': int((diff < 0).sum()),
            'per_fold': [round(float(diff[game_fold == fold].mean()), 4) for fold in FOLD_LIST]}


def weighted(epoch, source=None):
    keep = scored if source is None else scored & (source_of[game_of] == source)
    return round(float(hits[epoch-1][keep].mean()), 4)


epochs = []
for epoch in range(1, EPOCHS+1):
    row = {'epoch': epoch,
           'loss_fold_mean': round(float(np.mean([points[epoch-1]['loss'] for points in fold_points])), 4),
           'train_loss_fold_mean': round(float(np.mean([points[epoch-1]['train_loss'] for points in fold_points])), 4),
           'fold_loss': [round(points[epoch-1]['loss'], 4) for points in fold_points],
           'fold_accuracy': [round(points[epoch-1]['accuracy'], 4) for points in fold_points],
           'per_game': round(float(accuracy_games[epoch].mean()), 4), 'decision_weighted': weighted(epoch),
           'decision_weighted_114_games': weighted(epoch, '114'), 'decision_weighted_119_games': weighted(epoch, '119'),
           'against_reference': paired(epoch, REFERENCE)}
    epochs.append(row)
    against = row['against_reference']
    print('epoch %2d: loss %.4f (train %.4f) | per-game accuracy %.4f | against epoch %d %+.4f [%+.4f, %+.4f] games %d/%d/%d'
          % (epoch, row['loss_fold_mean'], row['train_loss_fold_mean'], row['per_game'], REFERENCE, against['mean'],
             against['low'], against['high'], against['better'], against['equal'], against['worse']), flush=True)

lowest_loss = min(epochs, key=lambda row: row['loss_fold_mean'])['epoch']
highest_accuracy = max(epochs, key=lambda row: row['per_game'])['epoch']
selection = {'rule': 'the epoch with the lowest fold-mean validation loss', 'checkpoint_epoch': lowest_loss,
             'lowest_loss_epoch': lowest_loss, 'highest_accuracy_epoch': highest_accuracy,
             'lowest_loss_epoch_per_fold': [min(points, key=lambda point: point['loss'])['epoch'] for points in fold_points],
             'lowest_loss_is_the_last_epoch': lowest_loss == EPOCHS,
             'highest_accuracy_minus_lowest_loss': None if highest_accuracy == lowest_loss
             else paired(highest_accuracy, lowest_loss)}
print('selection', json.dumps(selection), flush=True)

check = None
if not SMOKE:      # epochs 1-9 repeat the `all` arm of 121a
    row = epochs[REFERENCE-1]
    difference = max(abs(a-b) for key, name in (('loss', 'fold_loss'), ('accuracy', 'fold_accuracy'))
                     for a, b in zip(row[name], REFERENCE_121A[key]))
    check = {'epoch': REFERENCE, 'fold_loss': row['fold_loss'], 'fold_accuracy': row['fold_accuracy'],
             'reference_121a': REFERENCE_121A, 'max_abs_difference_from_121a': round(difference, 4),
             'identical_to_121a': difference < 0.00005}
    print('check against 121a', json.dumps(check), flush=True)

# 4: the full training, a checkpoint per epoch
partial = CHECKPOINTS+'.partial'
encoder = FeatureEncoderV4()


def save(epoch, model, points):
    out = os.path.join(partial, 'epoch-%02d' % epoch)
    os.makedirs(out)
    state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    assert tuple(state) == bc_train.PARAMETERS[4], tuple(state)
    torch.save(state, os.path.join(out, 'inference.pt'))
    metadata = {'versions': runtime_versions(), 'model_build_id': model_build_id(), 'encoding_version': 4,
                'settings': {'capacity': encoder.candidate_capacity},
                'model': {'width': WIDTH, 'encoding': 4}, 'iteration': 0,
                'behaviour_cloning': {'shards': ' + '.join(directory for _, _, directory in SOURCES),
                                      'training_shards': len(shards), 'validation_shards': 0, 'validation_games': [],
                                      'games': len(games), 'decisions': decisions,
                                      'epochs': EPOCHS, 'saved_epoch': epoch, 'batch': BATCH, 'lr': LR, 'width': WIDTH,
                                      'seed': 0, 'value_weight': 0.0, 'script': SCRIPT, 'script_commit': commit,
                                      'history': [{'epoch': point['epoch'], 'steps': point['steps'],
                                                   'train': {'loss': point['train_loss']}} for point in points]}}
    with open(os.path.join(out, 'metadata.json'), 'w') as handle:   # the completion marker, as in bc_train
        json.dump(metadata, handle, indent=2)


every_row = rows_of(active)
model, full_points = fit(every_row, None, save)
# the saved weights of the last epoch, read back, score the same as the live model (on training games: no accuracy claim)
probe = rows_of([i for i in active if fold_of[i] == 0])
live_loss, _, live_hit = evaluate(model, probe)
again = bc_train.build_model(*SIZES, WIDTH, 4)
again.load_state_dict(torch.load(os.path.join(partial, 'epoch-%02d' % EPOCHS, 'inference.pt')))
read_loss, _, read_hit = evaluate(again, probe)
assert live_loss == read_loss and np.array_equal(live_hit, read_hit), (live_loss, read_loss)
full = {'directory': CHECKPOINTS, 'epochs': EPOCHS, 'games': len(games), 'decisions': decisions,
        'steps': full_points[-1]['steps'], 'train_loss': [round(point['train_loss'], 4) for point in full_points],
        'capacity_in_metadata': encoder.candidate_capacity, 'last_epoch_read_back_equal': True}
print('full', json.dumps(full), '| seconds', round(time.time()-start), flush=True)
if SMOKE:
    shutil.rmtree(partial)
    print('smoke ok: folds', FOLD_LIST, '| epochs', EPOCHS, '| steps', fold_points[0][-1]['steps'], full['steps'])
    sys.exit(0)

metrics = {'script': SCRIPT, 'script_commit': commit, 'engine_build_id': ENGINE_BUILD_ID,
           'games': len(games), 'decisions': decisions,
           'games_per_quartet': {name: quartet.count(name) for name in sorted(set(quartet))},
           'fold_val_games': [int((fold_of == fold).sum()) for fold in range(FOLDS)],
           'settings': {'width': WIDTH, 'epochs': EPOCHS, 'lr': LR, 'batch': BATCH, 'seed': 0},
           'epochs': epochs, 'selection': selection, 'check_121a': check, 'full': full,
           'conditions': {'versions': runtime_versions(), 'torch_threads': torch.get_num_threads()},
           'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
os.rename(partial, CHECKPOINTS)
print('checkpoints %s/epoch-01 ... epoch-%02d | checkpoint epoch by the rule: %d | seconds %d'
      % (CHECKPOINTS, EPOCHS, selection['checkpoint_epoch'], metrics['seconds']))
