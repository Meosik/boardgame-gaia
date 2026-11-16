"""Encoding 4 on the rebuilt work tree engine (HANDOFF E160/E161): the 114 games were re-indexed on the rebuilt engine
(gaia-rl/runs/bc-114-fc19/manifest.jsonl, 46/46 strict replays, same game order as the old manifest). This exports them
again, compares every row with the shards exported on the old build (cycle 118, gaia-rl/runs/bc-114-v4-shards), and
trains the 5 folds of cycle 118 again.
  1 export   bc_dataset.py export --encoding 4 of the new manifest -> gaia-rl/runs/bc-114-v4-shards-fc19
             (skipped when that directory already holds shards)
  2 equal    observation, cand, counts, chosen, game equal to the old shards, every row; any difference ends the run
  3 train    the 5 folds of cycle 118 (same val_games), width 256, 9 epochs, lr 0.001, batch 256, seed 0; every epoch's
             validation loss / accuracy and train loss compared with the 118 metrics
Writes gaia-rl/runs/bc-114-v4-rebuilt/metrics.json. Checkpoints: gaia-rl/runs/bc-114-v4-w256-fc19/fold-<k>.
Usage: scratch_v4_rebuilt.py          # export and 5 folds, about 15-20 minutes
       scratch_v4_rebuilt.py smoke    # first 300 decisions, 1 epoch, nothing kept"""
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

SMOKE = sys.argv[1:] == ['smoke']
MANIFEST = 'gaia-rl/runs/bc-114-fc19/manifest.jsonl'
OLD_SHARDS = 'gaia-rl/runs/bc-114-v4-shards'
OLD_METRICS = 'gaia-rl/runs/bc-114-v4-pipeline/metrics.json'
SHARDS = 'gaia-rl/runs/bc-114-v4-rebuilt-smoke' if SMOKE else 'gaia-rl/runs/bc-114-v4-shards-fc19'
ROOT = 'gaia-rl/runs/bc-114-v4-w256-fc19'
METRICS = 'gaia-rl/runs/bc-114-v4-rebuilt/metrics.json'
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
                    '--encoding', '4'] + (['--max', '300'] if SMOKE else []), check=True)
    print('exported | seconds', round(time.time()-start), flush=True)

keys = ('observation', 'cand', 'counts', 'chosen', 'game')
new, old = load(SHARDS, keys), load(OLD_SHARDS, keys)
decisions = len(new['chosen'])
rows = int(new['counts'].sum())
if not SMOKE:
    assert decisions == len(old['chosen']), 'decision counts differ'
    assert rows == int(old['counts'].sum()), 'candidate row counts differ'
assert np.array_equal(new['counts'], old['counts'][:decisions]), 'counts differ'
assert np.array_equal(new['chosen'], old['chosen'][:decisions]), 'chosen differ'
assert np.array_equal(new['game'], old['game'][:decisions]), 'game differ'
assert np.array_equal(new['observation'], old['observation'][:decisions]), 'observation differ'
assert np.array_equal(new['cand'], old['cand'][:rows]), 'cand differ'
equal = {'decisions': decisions, 'candidate_rows': rows, 'arrays': list(keys)}
print('equal:', json.dumps(equal), '| seconds', round(time.time()-start), flush=True)
del new, old

if SMOKE:
    bc_train.train(SHARDS, '/tmp/scratch-v4-rebuilt-smoke-%d' % os.getpid(), epochs=1, lr=0.001, width=256, val_every=0)
    print('smoke ok | seconds', round(time.time()-start))
    sys.exit(0)

reference = json.load(open(OLD_METRICS))['folds']
folds = []
for ref in reference:
    fold = ref['fold']
    history = bc_train.train(SHARDS, f'{ROOT}/fold-{fold}', epochs=9, batch=256, lr=0.001, width=256, seed=0,
                             val_games=ref['val_games'])
    saved = min(history, key=lambda row: row['validation']['loss'])
    difference = max(max(abs(row['validation'][key] - old_row[key]) for key in ('loss', 'accuracy'))
                     for row, old_row in zip(history, ref['validation']))
    difference = max(difference, max(abs(row['train']['loss'] - value) for row, value in zip(history, ref['train_loss'])))
    folds.append({'fold': fold, 'val_games': ref['val_games'], 'saved_epoch': saved['epoch'],
                  'saved_epoch_118': ref['saved_epoch'], 'validation': [row['validation'] for row in history],
                  'train_loss': [row['train']['loss'] for row in history], 'max_abs_difference_from_118': difference})
    print(json.dumps({'fold': fold, 'epoch 9': [round(history[-1]['validation'][key], 4) for key in ('loss', 'accuracy')],
                      'saved epoch': saved['epoch'], 'difference': difference,
                      'seconds': round(time.time()-start)}), flush=True)

last = [fold['validation'][-1] for fold in folds]
samples = sum(row['samples'] for row in last)
accuracy = round(sum(row['accuracy']*row['samples'] for row in last)/samples, 4)
identical = all(fold['max_abs_difference_from_118'] == 0 for fold in folds)
largest = max(fold['max_abs_difference_from_118'] for fold in folds)
from gaia_rl.versions import ENGINE_BUILD_ID
metrics = {'engine_build_id': ENGINE_BUILD_ID, 'equal': equal, 'folds': folds,
           'epoch_9': {'accuracy': accuracy, 'fold_mean_loss': round(float(np.mean([row['loss'] for row in last])), 4),
                       'samples': samples},
           'identical_to_118': identical, 'max_abs_difference_from_118': largest, 'checkpoints': ROOT,
           'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
print('5 folds, decision-weighted epoch 9 accuracy %.4f (118: 0.3638), identical to 118: %s, largest difference %s'
      % (accuracy, identical, largest))
