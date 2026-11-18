"""Amount of data with encoding 4 on the 93 games of 114 + 119 (HANDOFF E162 (ㄱ), E163; lab queue 121, run in the
work tree). Both collections were indexed on the rebuilt engine fc19671c4278 (46 + 47 strict replays, 28,098
decisions); cycle 120 showed the 114 export on that engine equal to the old one, row for row.
  1 export   bc_dataset.py export --encoding 4 of the 119 manifest -> gaia-rl/runs/bc-119-v4-shards-fc19
             (skipped when the directory already holds shards; the 114 shards are those of cycle 120)
  2 folds    5 game-level folds over the 93 games, stratified by quartet: game k of a quartet (114 games first,
             then 119, manifest order) -> fold k mod 5, so the 114 games keep their folds of 117 / 118 / 120
  3 arms     the network and the optimizer step of tools/bc_train.py (width 256, lr 0.001, batch 256, torch seed 0,
             batch-order seed 0, shard by shard), validation on the fold's held-out games:
               all            every training game of the fold (about 74), 9 epochs
               half-steps     every other training game inside each quartet (about 37), stopped at the step count of
                              `all` in the same fold, in the middle of an epoch
               quarter-steps  every fourth training game inside each quartet (about 19), same step count
               half, quarter  the same subsets at 9 epochs of their own (fewer steps: beside only)
             quarter is a subset of half; no random draw. Every arm takes 9 validation points: after each of its own
             epochs, or for the -steps arms after every epoch length of `all`.
  4 compare  per-game accuracy at the last point, paired on the 93 validation games (t interval):
             all - half-steps, half-steps - quarter-steps, all - quarter-steps; beside all - half, all - quarter
Writes gaia-rl/runs/bc-v4-amount-93/metrics.json with the commit of this file (the full run refuses to start when the
file differs from its commit).
Usage: scratch_v4_amount.py          # export and 5 folds x 5 arms, about 60 minutes (smoke: 0.15-0.2 s per step)
       scratch_v4_amount.py smoke    # 300 decisions of 119, fold 0, 1 epoch, nothing kept"""
import glob
import json
import math
import os
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
SCRIPT = 'gaia-rl/lab/scratch_v4_amount.py'
SOURCES = [('114', 'gaia-rl/runs/bc-114-fc19/manifest.jsonl', 'gaia-rl/runs/bc-114-v4-shards-fc19'),
           ('119', 'gaia-rl/runs/bc-119-fc19/manifest.jsonl',
            'gaia-rl/runs/bc-v4-amount-smoke' if SMOKE else 'gaia-rl/runs/bc-119-v4-shards-fc19')]
METRICS = 'gaia-rl/runs/bc-v4-amount-93/metrics.json'
EPOCHS = 1 if SMOKE else 9
BATCH, LR, WIDTH, FOLDS = 256, 0.001, 256, 5
ARMS = {   # name: (training games, stop)
    'all': ('all', 'epochs'),
    'half-steps': ('half', 'steps'),
    'quarter-steps': ('quarter', 'steps'),
    'half': ('half', 'epochs'),
    'quarter': ('quarter', 'epochs'),
}
PAIRS = [   # (label, first arm, second arm): the difference is first - second
    ('1 data amount at the same step count: all - half', 'all', 'half-steps'),
    ('2 data amount at the same step count: half - quarter', 'half-steps', 'quarter-steps'),
    ('3 data amount at the same step count: all - quarter', 'all', 'quarter-steps'),
    ('beside (same epochs, fewer steps): all - half', 'all', 'half'),
    ('beside (same epochs, fewer steps): all - quarter', 'all', 'quarter'),
]
start = time.time()


def git(*arguments):
    return subprocess.run(['git', *arguments], capture_output=True, text=True, check=True).stdout.strip()


commit, dirty = git('log', '-1', '--format=%H', '--', SCRIPT), git('status', '--porcelain', '--', SCRIPT)
if not SMOKE:
    assert commit and not dirty, f'{SCRIPT} differs from its commit: {dirty!r}'

for _, manifest, directory in SOURCES:
    if not glob.glob(directory+'/shard-*.npz'):
        subprocess.run([sys.executable, 'gaia-rl/tools/bc_dataset.py', 'export', manifest, '--out', directory,
                        '--encoding', '4'] + (['--max', '300'] if SMOKE else []), check=True)
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
assert SIZES == (FeatureEncoderV4().state_size, FeatureEncoderV4().candidate_size), SIZES

active = [i for i in range(len(games)) if present[i]]      # every game, except in the smoke
quartet = [game['seed'].split('@')[0].rsplit('-', 1)[0] for game in games]
fold_of = np.full(len(games), -1)
for name in sorted(set(quartet)):
    for k, i in enumerate(i for i in active if quartet[i] == name):
        fold_of[i] = k % FOLDS
print('loaded: games', len(active), {name: sum(quartet[i] == name for i in active) for name in sorted(set(quartet))},
      '| decisions', decisions, '| script commit', commit[:12], '| seconds', round(time.time()-start), flush=True)


def rows_of(members):
    """Per shard: the sample rows of these games."""
    members = np.array(sorted(members))
    return [np.flatnonzero(np.isin(shard['game'], members)) for shard in shards]


def thin(train_games, step):
    keep = []
    for name in sorted(set(quartet)):
        keep += [i for i in train_games if quartet[i] == name][::step]
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


def fit(train_rows, val_rows, limit, mark):
    """The training step of bc_train._run over fresh per-shard permutations until `limit` steps (it may end inside
    an epoch); a validation point every `mark` steps. Returns steps, [(steps, loss, accuracy)], index, hit."""
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    model = bc_train.build_model(*SIZES, WIDTH, 4)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    steps, curve, index, hit = 0, [], None, None
    while steps < limit:
        for shard, rows in zip(shards, train_rows):
            for batch in (bc_train.batches(shard, BATCH, rng, rows) if len(rows) else ()):
                model.train()
                batch = tensors_of(batch)
                logits, _ = model(batch['observation'], batch['candidates'], batch['mask'])
                loss = torch.nn.functional.cross_entropy(logits, batch['chosen'], reduction='sum')/len(batch['chosen'])
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                steps += 1
                if steps % mark == 0 or steps == limit:
                    val_loss, index, hit = evaluate(model, val_rows)
                    curve.append((steps, val_loss, float(hit.mean())))
                if steps == limit:
                    break
            if steps == limit:
                break
    return steps, curve, index, hit


hits = {arm: np.zeros(decisions, dtype=bool) for arm in ARMS}
fold_rows = {arm: {'loss': [], 'accuracy': [], 'steps': [], 'train_games': [], 'train_decisions': []} for arm in ARMS}
curves = {arm: [] for arm in ARMS}   # per fold: the validation loss at each of the EPOCHS points
for fold in range(1 if SMOKE else FOLDS):
    val_games = [i for i in active if fold_of[i] == fold]
    train_games = [i for i in active if fold_of[i] != fold]
    members = {'all': train_games, 'half': thin(train_games, 2), 'quarter': thin(train_games, 4)}
    assert set(members['quarter']) <= set(members['half']) <= set(members['all']) and not set(val_games) & set(train_games)
    rows = {name: rows_of(chosen) for name, chosen in members.items()}
    val_rows = rows_of(val_games)
    epoch_steps = {name: sum(math.ceil(len(part)/BATCH) for part in parts) for name, parts in rows.items()}
    line = {'fold': fold, 'val_games': len(val_games), 'val_decisions': int(sum(len(part) for part in val_rows))}
    for arm, (data, stop) in ARMS.items():
        mark = epoch_steps['all'] if stop == 'steps' else epoch_steps[data]
        steps, curve, index, hit = fit(rows[data], val_rows, EPOCHS*mark, mark)
        assert len(curve) == EPOCHS and curve[-1][0] == steps, (arm, steps, curve)
        if stop == 'steps':
            assert steps == EPOCHS*epoch_steps['all'], (arm, steps)
        assert len(index) == line['val_decisions']
        hits[arm][index] = hit
        row = fold_rows[arm]
        train_decisions = int(sum(len(part) for part in rows[data]))
        for key, value in (('loss', curve[-1][1]), ('accuracy', curve[-1][2]), ('steps', steps),
                           ('train_games', len(members[data])), ('train_decisions', train_decisions)):
            row[key].append(value)
        curves[arm].append([point[1] for point in curve])
        line[arm] = {'loss': round(curve[-1][1], 4), 'accuracy': round(curve[-1][2], 4), 'steps': steps,
                     'train_games': len(members[data]), 'train_decisions': train_decisions}
    line['seconds'] = round(time.time()-start)
    print(json.dumps(line), flush=True)
if SMOKE:
    print('smoke ok: arms', list(ARMS), '| step counts', {arm: fold_rows[arm]['steps'] for arm in ARMS},
          '| train games', {arm: fold_rows[arm]['train_games'] for arm in ARMS})
    sys.exit(0)

per_game = {arm: np.array([hits[arm][game_of == g].mean() for g in range(len(games))]) for arm in ARMS}
source_of = np.array([game['source'] for game in games])


def compare(first, second):
    diff = per_game[first]-per_game[second]
    mean, sd, n = float(diff.mean()), float(diff.std(ddof=1)), len(diff)
    half = float(t.ppf(0.975, n-1))*sd/math.sqrt(n)
    reading = 'not confirmed (interval includes 0)' if mean-half <= 0 <= mean+half else (
        'first arm better' if mean > 0 else 'first arm worse')
    groups = {name: [i for i, q in enumerate(quartet) if q == name] for name in sorted(set(quartet))}
    groups.update({'games of '+name: list(np.flatnonzero(source_of == name)) for name in ('114', '119')})
    return {'first': first, 'second': second, 'mean': round(mean, 4), 'low': round(mean-half, 4),
            'high': round(mean+half, 4), 't': round(mean/(sd/math.sqrt(n)), 2), 'n': n,
            'better': int((diff > 0).sum()), 'equal': int((diff == 0).sum()), 'worse': int((diff < 0).sum()),
            'per_fold': [round(float(diff[fold_of == fold].mean()), 4) for fold in range(FOLDS)],
            'groups': {name: {'mean': round(float(diff[group].mean()), 4), 'better': int((diff[group] > 0).sum()),
                              'games': len(group)} for name, group in groups.items()},
            'reading': reading}


arms = {}
for arm in ARMS:
    row, mean_curve = fold_rows[arm], np.mean(curves[arm], axis=0)
    arms[arm] = {'per_game': round(float(per_game[arm].mean()), 4),
                 'decision_weighted': round(float(hits[arm].mean()), 4),
                 'decision_weighted_114_games': round(float(hits[arm][source_of[game_of] == '114'].mean()), 4),
                 'decision_weighted_119_games': round(float(hits[arm][source_of[game_of] == '119'].mean()), 4),
                 'fold_loss': [round(value, 4) for value in row['loss']],
                 'fold_accuracy': [round(value, 4) for value in row['accuracy']],
                 'steps': row['steps'], 'train_games': row['train_games'], 'train_decisions': row['train_decisions'],
                 'loss_curve_fold_mean': [round(float(value), 4) for value in mean_curve],
                 'lowest_point': int(np.argmin(mean_curve))+1}
    print(arm, json.dumps(arms[arm]), flush=True)
comparisons = {label: compare(first, second) for label, first, second in PAIRS}
for label, row in comparisons.items():
    print('%s: %+.4f [%+.4f, %+.4f] t %.2f, games %d/%d/%d of %d - %s' % (
        label, row['mean'], row['low'], row['high'], row['t'], row['better'], row['equal'], row['worse'], row['n'],
        row['reading']), flush=True)

from gaia_rl.versions import ENGINE_BUILD_ID, runtime_versions
metrics = {'script': SCRIPT, 'script_commit': commit, 'engine_build_id': ENGINE_BUILD_ID,
           'games': len(games), 'decisions': decisions,
           'games_per_quartet': {name: quartet.count(name) for name in sorted(set(quartet))},
           'fold_val_games': [int((fold_of == fold).sum()) for fold in range(FOLDS)],
           'settings': {'width': WIDTH, 'epochs': EPOCHS, 'lr': LR, 'batch': BATCH, 'seed': 0},
           'reference_118': {'decision_weighted_114_games_trained_on_114_only': 0.3638},
           'arms': arms, 'comparisons': comparisons,
           'conditions': {'versions': runtime_versions(), 'torch_threads': torch.get_num_threads()},
           'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
print('all: decision-weighted %.4f on 93 games, %.4f on the 114 games (118, trained on 114 only: 0.3638) | seconds %d'
      % (arms['all']['decision_weighted'], arms['all']['decision_weighted_114_games'], metrics['seconds']))
