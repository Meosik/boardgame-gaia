"""Amount of data and epoch length with encoding 4 on the 141 games of 114 + 119 + 123, and the full-data checkpoints
(HANDOFF E182 (ㄱ); lab queue 124, run in the work tree). 121a: about 74 against 37 training games at equal steps
+2.32 pt [+1.68, +2.96]; 122: the validation loss of 93 games is lowest at epoch 9. 123 added 48 games on the same
engine build (fc19671c4278).
  1 export   bc_dataset.py export --encoding 4 --capacity 4096 of the 123 manifest (gaia-rl/runs/bc-123-fc19) ->
             gaia-rl/runs/bc-123-v4-shards-fc19-c4096 (one decision of 123 lists 2,417 candidates), written to
             <dir>.partial and renamed when the export ends. The shards of 114 (cycle 120) and 119 (121a) are reused.
  2 folds    5 game-level folds, game k of a quartet -> fold k mod 5 over 114, 119, 123 in this order (the games of
             114 and 119 keep the fold of 121a and 122)
  3 arms     per fold, the network and the optimizer step of tools/bc_train.py (width 256, lr 0.001, batch 256,
             torch seed 0, batch-order seed 0, shard by shard), validation on the held-out games of the fold:
             all              every training game of the fold (about 113), 18 epochs, a validation point per epoch
             twothirds-steps  two of every three training games of each quartet (about 75; the third, sixth, ...
                              game of a quartet is dropped, no random draw), stopped at the step count of the `all`
                              arm of the same fold at epoch 9, a validation point at every epoch of the `all` arm
  4 full     one training on all 141 games with the same settings, 18 epochs, the weights of every epoch saved as a
             checkpoint (inference.pt + metadata.json as tools/bc_train.py writes them) under
             gaia-rl/runs/bc-141-v4-w256-fc19/epoch-01 ... epoch-18 (written to <dir>.partial, renamed at the end)
  5 read     amount: per-game accuracy of `all` at epoch 9 minus `twothirds-steps` at the same step count, paired
             on the 141 validation games (t interval), per fold, quartet and source run. Epochs: per epoch the
             fold-mean validation loss, the per-game accuracy and the paired difference to epoch 9; checkpoint epoch
             = the epoch with the lowest fold-mean validation loss (the rule of bc_train.py and 122); the epoch with
             the highest accuracy is reported beside it, with the paired difference when they differ.
Writes gaia-rl/runs/bc-v4-amount-141/metrics.json with the commit of this file (the full run refuses to start when the
file differs from its commit, or when the checkpoint directory exists).
Usage: scratch_v4_amount_141.py          # export, 5 folds x 2 arms and the full training, about 1.5 hours
       scratch_v4_amount_141.py smoke    # 300 decisions of 123, fold 0 and the full training at 2 epochs, nothing kept"""
import glob
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
SCRIPT = 'gaia-rl/lab/scratch_v4_amount_141.py'
SOURCES = [('114', 'gaia-rl/runs/bc-114-fc19/manifest.jsonl', 'gaia-rl/runs/bc-114-v4-shards-fc19'),
           ('119', 'gaia-rl/runs/bc-119-fc19/manifest.jsonl', 'gaia-rl/runs/bc-119-v4-shards-fc19-c4096'),
           ('123', 'gaia-rl/runs/bc-123-fc19/manifest.jsonl',
            'gaia-rl/runs/bc-v4-amount-141-smoke-c4096' if SMOKE else 'gaia-rl/runs/bc-123-v4-shards-fc19-c4096')]
METRICS = 'gaia-rl/runs/bc-v4-amount-141/metrics.json'
CHECKPOINTS = 'gaia-rl/runs/bc-v4-amount-141-smoke' if SMOKE else 'gaia-rl/runs/bc-141-v4-w256-fc19'
EPOCHS, REFERENCE = (2, 1) if SMOKE else (18, 9)
BATCH, LR, WIDTH, FOLDS = 256, 0.001, 256, 5
CAPACITY = 4096   # export encoder capacity: one decision of 123 lists 2,417 candidates (2,324 federation routes)
FOLD_LIST = [0] if SMOKE else list(range(FOLDS))
start = time.time()


def git(*arguments):
    return subprocess.run(['git', *arguments], capture_output=True, text=True, check=True).stdout.strip()


commit, dirty = git('log', '-1', '--format=%H', '--', SCRIPT), git('status', '--porcelain', '--', SCRIPT)
if not SMOKE:
    assert commit and not dirty, f'{SCRIPT} differs from its commit: {dirty!r}'
    assert not os.path.exists(CHECKPOINTS), f'{CHECKPOINTS} exists'
shutil.rmtree(CHECKPOINTS+'.partial', ignore_errors=True)
if SMOKE:
    shutil.rmtree(SOURCES[-1][2], ignore_errors=True)

for _, manifest, directory in SOURCES:
    if not glob.glob(directory+'/shard-*.npz'):
        partial = directory+'.partial'      # a failed export must not leave a directory that looks complete
        shutil.rmtree(partial, ignore_errors=True)
        subprocess.run([sys.executable, 'gaia-rl/tools/bc_dataset.py', 'export', manifest, '--out', partial,
                        '--encoding', '4', '--capacity', str(CAPACITY)] + (['--max', '300'] if SMOKE else []),
                       check=True)
        os.rename(partial, directory)
        print('exported', directory, '| seconds', round(time.time()-start), flush=True)

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
if not SMOKE:
    assert np.array_equal(present, [game['decisions'] for game in games]), 'shard decisions differ from the manifests'
SIZES = (shards[0]['observation'].shape[1], shards[0]['cand'].shape[1])
assert all((shard['observation'].shape[1], shard['cand'].shape[1]) == SIZES for shard in shards)
from gaia_rl.encoding import FeatureEncoderV4
from gaia_rl.versions import ENGINE_BUILD_ID, model_build_id, runtime_versions
assert SIZES == (FeatureEncoderV4().state_size, FeatureEncoderV4().candidate_size), SIZES

active = [i for i in range(len(games)) if present[i]]      # every game, except in the smoke
quartet = [game['seed'].split('@')[0].rsplit('-', 1)[0] for game in games]
fold_of = np.full(len(games), -1)
for name in sorted(set(quartet)):
    for k, i in enumerate(i for i in range(len(games)) if quartet[i] == name):
        fold_of[i] = k % FOLDS
source_of = np.array([game['source'] for game in games])
print('loaded: games', len(active), {name: sum(quartet[i] == name for i in active) for name in sorted(set(quartet))},
      '| decisions', decisions, '| script commit', commit[:12], '| seconds', round(time.time()-start), flush=True)


def rows_of(members):
    """Per shard: the sample rows of these games."""
    members = np.array(sorted(members))
    return [np.flatnonzero(np.isin(shard['game'], members)) for shard in shards]


def two_thirds(train_games):
    """Two of every three training games of each quartet, in manifest order (the third, sixth, ... is dropped)."""
    keep = []
    for name in sorted(set(quartet)):
        keep += [i for k, i in enumerate(i for i in train_games if quartet[i] == name) if k % 3 != 2]
    return sorted(keep)


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


def fit(train_rows, val_rows=None, limit=None, mark=None, after_epoch=None):
    """The training step of bc_train._run over fresh per-shard permutations (the step of 121a and 122).
    Without `limit`: EPOCHS epochs, one point per epoch (steps, training loss, and with val_rows the validation loss,
    accuracy, decision index and hit); after_epoch(epoch, model, points) runs at the end of every epoch.
    With `limit`: until `limit` steps (it may end inside an epoch), a validation point every `mark` steps."""
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    model = bc_train.build_model(*SIZES, WIDTH, 4)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    steps, points, epoch = 0, [], 0
    while (steps < limit) if limit else (epoch < EPOCHS):
        epoch += 1
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
                if limit and (steps % mark == 0 or steps == limit):
                    point = {'steps': steps}
                    point['loss'], point['index'], point['hit'] = evaluate(model, val_rows)
                    point['accuracy'] = float(point['hit'].mean())
                    points.append(point)
                if limit and steps == limit:
                    break
            if limit and steps == limit:
                break
        if limit:
            continue
        point = {'epoch': epoch, 'steps': steps, 'train_loss': loss_sum/samples}
        assert math.isfinite(point['train_loss']), point
        if val_rows is not None:
            point['loss'], point['index'], point['hit'] = evaluate(model, val_rows)
            point['accuracy'] = float(point['hit'].mean())
        points.append(point)
        if after_epoch is not None:
            after_epoch(epoch, model, points)
    return model, points


# 3: the two arms, 5 folds
hits = np.zeros((EPOCHS, decisions), dtype=bool)       # the `all` arm, per epoch
hits_subset = np.zeros(decisions, dtype=bool)          # `twothirds-steps` at its last point
scored = np.zeros(decisions, dtype=bool)
fold_points, subset_folds = [], []
for fold in FOLD_LIST:
    val_games = [i for i in active if fold_of[i] == fold]
    train_games = [i for i in active if fold_of[i] != fold]
    subset_games = two_thirds(train_games)
    assert not set(val_games) & set(train_games) and set(subset_games) < set(train_games)
    train_rows, subset_rows, val_rows = rows_of(train_games), rows_of(subset_games), rows_of(val_games)
    val_decisions = int(sum(len(part) for part in val_rows))
    epoch_steps = sum(math.ceil(len(part)/BATCH) for part in train_rows)
    _, points = fit(train_rows, val_rows)
    assert [point['steps'] for point in points] == [epoch_steps*(k+1) for k in range(EPOCHS)]
    for point in points:
        index, hit = point.pop('index'), point.pop('hit')
        assert len(index) == val_decisions and not scored[index].any()
        hits[point['epoch']-1][index] = hit
    _, subset_points = fit(subset_rows, val_rows, limit=REFERENCE*epoch_steps, mark=epoch_steps)
    assert [point['steps'] for point in subset_points] == [epoch_steps*(k+1) for k in range(REFERENCE)]
    last = subset_points[-1]
    assert len(last['index']) == val_decisions and np.array_equal(np.sort(last['index']), np.sort(index))
    hits_subset[last['index']] = last['hit']
    scored[index] = True
    fold_points.append(points)
    subset_folds.append({'train_games': len(subset_games),
                         'train_decisions': int(sum(len(part) for part in subset_rows)), 'steps': last['steps'],
                         'loss': [round(point['loss'], 4) for point in subset_points],
                         'accuracy': [round(point['accuracy'], 4) for point in subset_points]})
    print(json.dumps({'fold': fold, 'val_games': len(val_games), 'val_decisions': val_decisions,
                      'train_games': len(train_games), 'train_decisions': int(sum(len(part) for part in train_rows)),
                      'steps_per_epoch': epoch_steps, 'loss': [round(point['loss'], 4) for point in points],
                      'accuracy': [round(point['accuracy'], 4) for point in points],
                      'twothirds-steps': subset_folds[-1], 'seconds': round(time.time()-start)}), flush=True)

scored_games = [g for g in active if fold_of[g] in FOLD_LIST]
game_fold = np.array([fold_of[g] for g in scored_games])
game_quartet = np.array([quartet[g] for g in scored_games])
game_source = np.array([games[g]['source'] for g in scored_games])
accuracy_games = {epoch: np.array([hits[epoch-1][game_of == g].mean() for g in scored_games])
                  for epoch in range(1, EPOCHS+1)}
accuracy_subset = np.array([hits_subset[game_of == g].mean() for g in scored_games])


def paired(first, second, groups=False):
    """Per-game accuracy `first` minus `second`, paired on the validation games (t interval)."""
    diff = first-second
    mean, sd, n = float(diff.mean()), float(diff.std(ddof=1)), len(diff)
    half = float(t.ppf(0.975, n-1))*sd/math.sqrt(n)
    out = {'mean': round(mean, 4), 'low': round(mean-half, 4), 'high': round(mean+half, 4),
           't': round(mean/(sd/math.sqrt(n)), 2) if sd else None, 'n': n,
           'better': int((diff > 0).sum()), 'equal': int((diff == 0).sum()), 'worse': int((diff < 0).sum()),
           'per_fold': [round(float(diff[game_fold == fold].mean()), 4) for fold in FOLD_LIST]}
    if groups:
        out['per_quartet'] = {name: [round(float(diff[game_quartet == name].mean()), 4),
                                     int((game_quartet == name).sum())] for name in sorted(set(game_quartet))}
        out['per_source'] = {name: [round(float(diff[game_source == name].mean()), 4),
                                    int((game_source == name).sum())] for name in sorted(set(game_source))}
    return out


def weighted(row, source=None):
    keep = scored if source is None else scored & (source_of[game_of] == source)
    return round(float(row[keep].mean()), 4) if keep.any() else None


amount = {'comparison': 'all at epoch %d minus twothirds-steps at the same step count' % REFERENCE,
          'all': {'per_game': round(float(accuracy_games[REFERENCE].mean()), 4),
                  'decision_weighted': weighted(hits[REFERENCE-1]),
                  'train_games': [int(sum(fold_of[i] != fold for i in active)) for fold in FOLD_LIST],
                  'fold_loss': [round(points[REFERENCE-1]['loss'], 4) for points in fold_points],
                  'fold_accuracy': [round(points[REFERENCE-1]['accuracy'], 4) for points in fold_points]},
          'twothirds-steps': {'per_game': round(float(accuracy_subset.mean()), 4),
                              'decision_weighted': weighted(hits_subset),
                              'train_games': [row['train_games'] for row in subset_folds],
                              'fold_loss': [row['loss'][-1] for row in subset_folds],
                              'fold_accuracy': [row['accuracy'][-1] for row in subset_folds],
                              'fold_loss_curve': [row['loss'] for row in subset_folds]},
          'difference': paired(accuracy_games[REFERENCE], accuracy_subset, groups=True)}
print('amount', json.dumps(amount), flush=True)

epochs = []
for epoch in range(1, EPOCHS+1):
    row = {'epoch': epoch,
           'loss_fold_mean': round(float(np.mean([points[epoch-1]['loss'] for points in fold_points])), 4),
           'train_loss_fold_mean': round(float(np.mean([points[epoch-1]['train_loss'] for points in fold_points])), 4),
           'fold_loss': [round(points[epoch-1]['loss'], 4) for points in fold_points],
           'fold_accuracy': [round(points[epoch-1]['accuracy'], 4) for points in fold_points],
           'per_game': round(float(accuracy_games[epoch].mean()), 4), 'decision_weighted': weighted(hits[epoch-1]),
           'decision_weighted_by_source': {name: weighted(hits[epoch-1], name) for name, _, _ in SOURCES},
           'against_reference': paired(accuracy_games[epoch], accuracy_games[REFERENCE])}
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
             else paired(accuracy_games[highest_accuracy], accuracy_games[lowest_loss])}
print('selection', json.dumps(selection), flush=True)

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
                                      'games': len(active), 'decisions': decisions,
                                      'epochs': EPOCHS, 'saved_epoch': epoch, 'batch': BATCH, 'lr': LR, 'width': WIDTH,
                                      'seed': 0, 'value_weight': 0.0, 'script': SCRIPT, 'script_commit': commit,
                                      'history': [{'epoch': point['epoch'], 'steps': point['steps'],
                                                   'train': {'loss': point['train_loss']}} for point in points]}}
    with open(os.path.join(out, 'metadata.json'), 'w') as handle:   # the completion marker, as in bc_train
        json.dump(metadata, handle, indent=2)


every_row = rows_of(active)
model, full_points = fit(every_row, None, after_epoch=save)
# the saved weights of the last epoch, read back, score the same as the live model (on training games: no accuracy claim)
probe = rows_of([i for i in active if fold_of[i] == 0])
live_loss, _, live_hit = evaluate(model, probe)
again = bc_train.build_model(*SIZES, WIDTH, 4)
again.load_state_dict(torch.load(os.path.join(partial, 'epoch-%02d' % EPOCHS, 'inference.pt')))
read_loss, _, read_hit = evaluate(again, probe)
assert live_loss == read_loss and np.array_equal(live_hit, read_hit), (live_loss, read_loss)
full = {'directory': CHECKPOINTS, 'epochs': EPOCHS, 'games': len(active), 'decisions': decisions,
        'steps': full_points[-1]['steps'], 'train_loss': [round(point['train_loss'], 4) for point in full_points],
        'capacity_in_metadata': encoder.candidate_capacity, 'last_epoch_read_back_equal': True}
print('full', json.dumps(full), '| seconds', round(time.time()-start), flush=True)
if SMOKE:
    shutil.rmtree(partial)
    shutil.rmtree(SOURCES[-1][2])
    print('smoke ok: folds', FOLD_LIST, '| epochs', EPOCHS, '| steps per epoch', fold_points[0][0]['steps'],
          '| twothirds-steps', subset_folds[0]['steps'], '| full', full['steps'])
    sys.exit(0)

metrics = {'script': SCRIPT, 'script_commit': commit, 'engine_build_id': ENGINE_BUILD_ID,
           'games': len(games), 'decisions': decisions,
           'games_per_quartet': {name: quartet.count(name) for name in sorted(set(quartet))},
           'games_per_source': {name: int((source_of == name).sum()) for name, _, _ in SOURCES},
           'fold_val_games': [int((fold_of == fold).sum()) for fold in range(FOLDS)],
           'settings': {'width': WIDTH, 'epochs': EPOCHS, 'reference_epoch': REFERENCE, 'lr': LR, 'batch': BATCH,
                        'seed': 0, 'export_capacity': CAPACITY},
           'amount': amount, 'epochs': epochs, 'selection': selection, 'full': full,
           'conditions': {'versions': runtime_versions(), 'torch_threads': torch.get_num_threads()},
           'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
os.rename(partial, CHECKPOINTS)
print('checkpoints %s/epoch-01 ... epoch-%02d | checkpoint epoch by the rule: %d | seconds %d'
      % (CHECKPOINTS, EPOCHS, selection['checkpoint_epoch'], metrics['seconds']))
