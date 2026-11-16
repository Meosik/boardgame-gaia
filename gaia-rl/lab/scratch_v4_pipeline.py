"""Encoding 4 through the real tools on the 114 games (HANDOFF E153 (ㄱ) step 2): export, equality with the measured
features, and the 5-fold training of cycle 117's `w256-all` arm with tools/bc_train.py.
  1 export   bc_dataset.py export --encoding 4 of gaia-rl/runs/bc-114/manifest.jsonl -> gaia-rl/runs/bc-114-v4-shards
             (skipped when that directory already holds shards; a partial export fails step 2)
  2 equal    against the stored version 3 shards (runs/bc-114-shards) and runs/bc-114-outcome/outcome.npz, every row:
             same decisions, candidate counts, chosen index and state vector; board columns equal; field present /
             absent equal; field id <-> version 3 scalar one-to-one per field; outcome columns equal by name, columns
             outcome.npz never saw are 0; the game column = the manifest line of the game. Any difference ends the run.
  3 train    the folds of lab/scratch_bc114_size.py (quartet-stratified, game k of a quartet -> fold k mod 5), each
             with bc_train.train(width 256, 9 epochs, lr 0.001, batch 256, seed 0, the fold's games held out).
Reported: per fold the validation loss / accuracy at every epoch and the saved (lowest validation loss) epoch; over the
5 folds the decision-weighted accuracy at epoch 9 and at the saved epochs, beside cycle 117 `w256-all` (0.3651 at epoch
9, fold losses 2.268 2.191 2.328 2.350 2.238) and `w64-all` (0.3469). Not the same network bit for bit: bc_train reads
the whole state vector and the whole field vocabulary, shuffles inside each shard, and draws other initial weights.
Writes gaia-rl/runs/bc-114-v4-pipeline/metrics.json. Checkpoints: gaia-rl/runs/bc-114-v4-w256-<time>/fold-<k>.
Usage: scratch_v4_pipeline.py          # export about 30 min, training about 5 x 5 min
       scratch_v4_pipeline.py smoke    # shards in runs/bc-114-v4-smoke (first rows only), 1 epoch, nothing written"""
import glob
import json
import os
import subprocess
import sys
import time

import numpy as np

os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/tools']
import bc_train
from gaia_rl.encoding import ACTION_FIELDS, OUTCOME_GLOBALS, OUTCOME_OTHERS, OUTCOME_PLAYER, OUTCOME_SCALE

SMOKE = sys.argv[1:] == ['smoke']
MANIFEST = 'gaia-rl/runs/bc-114/manifest.jsonl'
SHARDS = 'gaia-rl/runs/bc-114-v4-smoke' if SMOKE else 'gaia-rl/runs/bc-114-v4-shards'
METRICS = 'gaia-rl/runs/bc-114-v4-pipeline/metrics.json'
REFERENCE = {'w256-all decision-weighted, epoch 9': 0.3651, 'w64-all decision-weighted, epoch 9': 0.3469,
             'w256-all fold loss, epoch 9': [2.268, 2.191, 2.328, 2.350, 2.238],
             'w256-all fold-mean loss, lowest point (epoch 5)': 2.188}
FIELDS = len(ACTION_FIELDS)
start = time.time()


def load(directory, keys):
    parts = {key: [] for key in keys}
    for path in sorted(glob.glob(directory+'/shard-*.npz')):
        with np.load(path) as shard:
            for key in keys:
                parts[key].append(np.diff(shard['cand_offsets']) if key == 'counts' else shard[key])
    return {key: np.concatenate(values) for key, values in parts.items()}


if not glob.glob(SHARDS+'/shard-*.npz'):
    subprocess.run([sys.executable, 'gaia-rl/tools/bc_dataset.py', 'export', MANIFEST, '--out', SHARDS,
                    '--encoding', '4'], check=True)
    print('exported | seconds', round(time.time()-start), flush=True)

lines = [json.loads(line) for line in open(MANIFEST) if line.strip()]
games = [(number, game) for number, game in enumerate(lines) if game['replays']]
new = load(SHARDS, ('observation', 'cand', 'counts', 'chosen', 'game'))
old = load('gaia-rl/runs/bc-114-shards', ('observation', 'cand', 'counts', 'chosen'))
stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
decisions = len(new['chosen'])
assert SMOKE or decisions == len(old['chosen']) == sum(game['decisions'] for _, game in games), 'decision counts differ'
rows = int(new['counts'].sum())
assert np.array_equal(new['counts'], old['counts'][:decisions]) and np.array_equal(stored['counts'][:decisions], new['counts'])
assert np.array_equal(new['chosen'], old['chosen'][:decisions])
assert np.array_equal(new['observation'], old['observation'][:decisions]), 'state vectors differ'
assert np.array_equal(new['game'], np.repeat([number for number, _ in games],
                                             [game['decisions'] for _, game in games])[:decisions]), 'game column'
cand, before = new['cand'], old['cand'][:rows]
assert cand.shape[1] == FIELDS+256+len(OUTCOME_PLAYER)+len(OUTCOME_OTHERS)+len(OUTCOME_GLOBALS)
assert np.array_equal(cand[:, FIELDS:FIELDS+256], before[:, FIELDS*2:]), 'board columns differ'
assert np.array_equal(cand[:, :FIELDS] > 0, before[:, 0:FIELDS*2:2] > 0), 'field presence differs'
distinct = []
for f in range(FIELDS):
    present = cand[:, f] > 0
    pairs = np.unique(np.stack([cand[present, f], before[present, 2*f+1]], axis=1).astype(np.float32), axis=0)
    assert len(pairs) == len(np.unique(pairs[:, 0])) == len(np.unique(pairs[:, 1])), ACTION_FIELDS[f]
    distinct.append(len(pairs))
names = [str(name) for name in stored['names']]
mine = list(OUTCOME_PLAYER)+['others.'+name for name in OUTCOME_OTHERS]+list(OUTCOME_GLOBALS)
seen = np.abs(stored['outcome']).max(axis=0) > 0
matched = 0
for column, name in enumerate(mine):
    values = cand[:, FIELDS+256+column].astype(np.float32)*OUTCOME_SCALE
    if name in names and seen[names.index(name)]:
        assert np.array_equal(values, stored['outcome'][:rows, names.index(name)].astype(np.float32)), name
        matched += 1
    else:
        assert not values.any(), name
assert matched == int(seen.sum()), (matched, int(seen.sum()))
equal = {'decisions': decisions, 'candidate_rows': rows, 'outcome_columns_equal': matched,
         'outcome_columns_zero': len(mine)-matched, 'distinct_ids_per_field': distinct}
print('equal:', json.dumps(equal), '| seconds', round(time.time()-start), flush=True)
del new, old, cand, before, stored

if SMOKE:
    history = bc_train.train(SHARDS, '/tmp/scratch-v4-pipeline-smoke-%d' % os.getpid(), epochs=1, lr=0.001, width=256,
                             val_every=0)
    print('smoke ok | seconds', round(time.time()-start))
    sys.exit(0)

quartet = [game['seed'].rsplit('-', 1)[0] for _, game in games]
fold_of = {}
for name in set(quartet):
    for k, i in enumerate(i for i, q in enumerate(quartet) if q == name):
        fold_of[games[i][0]] = k % 5
root = 'gaia-rl/runs/bc-114-v4-w256-'+time.strftime('%Y%m%d-%H%M%S')
folds = []
for fold in range(5):
    held = sorted(number for number, value in fold_of.items() if value == fold)
    history = bc_train.train(SHARDS, f'{root}/fold-{fold}', epochs=9, batch=256, lr=0.001, width=256, seed=0,
                             val_games=held)
    saved = min(history, key=lambda row: row['validation']['loss'])
    folds.append({'fold': fold, 'val_games': held, 'saved_epoch': saved['epoch'],
                  'validation': [row['validation'] for row in history],
                  'train_loss': [row['train']['loss'] for row in history]})
    print(json.dumps({'fold': fold, 'val_games': len(held), 'samples': history[-1]['validation']['samples'],
                      'epoch 9': [round(history[-1]['validation'][key], 4) for key in ('loss', 'accuracy')],
                      'saved epoch': saved['epoch'],
                      'saved': [round(saved['validation'][key], 4) for key in ('loss', 'accuracy')],
                      'seconds': round(time.time()-start)}), flush=True)


def weighted(pick):
    chosen = [pick(fold) for fold in folds]
    samples = sum(row['samples'] for row in chosen)
    return {'accuracy': round(sum(row['accuracy']*row['samples'] for row in chosen)/samples, 4),
            'fold_mean_loss': round(float(np.mean([row['loss'] for row in chosen])), 4), 'samples': samples}


curve = np.mean([[row['loss'] for row in fold['validation']] for fold in folds], axis=0)
metrics = {'equal': equal, 'folds': folds, 'epoch_9': weighted(lambda fold: fold['validation'][-1]),
           'saved_epoch': weighted(lambda fold: fold['validation'][fold['saved_epoch']-1]),
           'fold_mean_loss_by_epoch': [round(float(value), 4) for value in curve],
           'lowest_fold_mean_loss_epoch': int(np.argmin(curve))+1, 'reference_117': REFERENCE,
           'checkpoints': root, 'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
print('5 folds, decision-weighted: epoch 9 accuracy %.4f, fold-mean loss %.4f | saved epochs %s accuracy %.4f, loss %.4f'
      % (metrics['epoch_9']['accuracy'], metrics['epoch_9']['fold_mean_loss'],
         [fold['saved_epoch'] for fold in folds], metrics['saved_epoch']['accuracy'],
         metrics['saved_epoch']['fold_mean_loss']))
print('fold-mean validation loss by epoch:', metrics['fold_mean_loss_by_epoch'],
      '(lowest at epoch %d)' % metrics['lowest_fold_mean_loss_epoch'])
print('cycle 117 reference:', json.dumps(REFERENCE))
