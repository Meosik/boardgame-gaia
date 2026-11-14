"""Network width and data amount on the 114 BC samples (HANDOFF E151 (ㄴ), run from the lab queue in the work tree).
Same 5 game-level folds, loaders, network and training step as lab/scratch_bc114_o2.py (quartet-stratified, game k of
a quartet -> fold k mod 5; lr 0.001, batch 256, the same torch seed and batch-order seed in every arm, no epoch picked
on the validation fold). Seven arms, input `expand+o` (53 outcome columns) unless marked o2:
  w64-all          width 64, all training games of the fold, 9 epochs   (= the A arm of 116 / E149: reproducibility check)
  w64-half         width 64, half the training games, 9 epochs          (fewer optimizer steps: reported beside)
  w64-half-steps   width 64, half the training games, stopped at exactly the step count of w64-all in the same fold,
                   9 * ceil(N_all / 256), in the middle of an epoch      (Codex debate 2/2: update count matched)
  w256-all, w256-half, w256-half-steps   the same three at width 256
  w256-all-o2      width 256, all games, 9 epochs, input `expand+o2` (gaia-rl/runs/bc-114-outcome/o2.npz of 116)
Half the training games = inside each quartet, every other training game of the fold in manifest order (no random
draw). The dropped all-zero state columns are those of the fold's full training set in every arm, so arms of one
width start from the same weights. Every arm takes 9 validation points: after each of its own epochs, or for the
-steps arms every ceil(N_all / 256) steps (the points of the all-games arm).
Writes gaia-rl/runs/bc-114-size/metrics.json.
Usage: scratch_bc114_size.py          # about 25-35 minutes
       scratch_bc114_size.py smoke    # fold 0, 1 epoch, nothing written"""
import glob
import json
import math
import os
import sys
import time

import numpy as np
import torch
from scipy.stats import t
from torch import nn

SMOKE = sys.argv[1:] == ['smoke']
EPOCHS = 1 if SMOKE else 9
LR, FIELDS, BATCH = 0.001, 34, 256
VERSION = 2          # o2.npz extraction version written by scratch_bc114_o2.py
STORE = 'gaia-rl/runs/bc-114-outcome/o2.npz'
METRICS = 'gaia-rl/runs/bc-114-size/metrics.json'
EXPECTED = {'w64-all per game': 0.3466, 'w64-all decision-weighted': 0.3472}   # 116 A arm (E149: 0.346 / 0.347)
ARMS = {   # name: (input, width, training games, stop)
    'w64-all': ('o', 64, 'all', 'epochs'),
    'w64-half': ('o', 64, 'half', 'epochs'),
    'w64-half-steps': ('o', 64, 'half', 'steps'),
    'w256-all': ('o', 256, 'all', 'epochs'),
    'w256-half': ('o', 256, 'half', 'epochs'),
    'w256-half-steps': ('o', 256, 'half', 'steps'),
    'w256-all-o2': ('o2', 256, 'all', 'epochs'),
}
PAIRS = [   # (label, first arm, second arm): the difference is first - second
    ('width: 256 - 64, all games, 9 epochs', 'w256-all', 'w64-all'),
    ('data amount at the same step count, width 64: all - half', 'w64-all', 'w64-half-steps'),
    ('data amount at the same step count, width 256: all - half', 'w256-all', 'w256-half-steps'),
    ('o2 at width 256: o2 - o', 'w256-all-o2', 'w256-all'),
    ('beside (same epochs, fewer steps), width 64: all - half', 'w64-all', 'w64-half'),
    ('beside (same epochs, fewer steps), width 256: all - half', 'w256-all', 'w256-half'),
]

start = time.time()
games = [g for g in (json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')) if g['replays']]
stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
counts = stored['counts'].astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])
cache = np.load(STORE)
if not (np.array_equal(cache['counts'], counts) and 'version' in cache.files and int(cache['version']) == VERSION):
    raise RuntimeError(f'{STORE} does not match outcome.npz or extraction version {VERSION}: run scratch_bc114_o2.py')
extra = cache['extra'].astype(np.float32)
used = np.abs(extra).max(axis=0) > 0

obs_all, cand, chosen = [], [], []
shard_counts = []
for path in sorted(glob.glob('gaia-rl/runs/bc-114-shards/shard-*.npz')):
    shard = np.load(path)
    obs_all.append(shard['observation'])
    cand.append(shard['cand'])
    shard_counts.append(np.diff(shard['cand_offsets']))
    chosen.append(shard['chosen'])
obs_all, cand = np.concatenate(obs_all), np.concatenate(cand)
chosen = np.concatenate(chosen).astype(np.int64)
assert np.array_equal(np.concatenate(shard_counts), counts)
assert sum(g['decisions'] for g in games) == len(chosen)
game_of = np.repeat(np.arange(len(games)), [g['decisions'] for g in games])
quartet = [g['seed'].rsplit('-', 1)[0] for g in games]
fold_of = np.zeros(len(games), dtype=int)
for name in set(quartet):
    for k, i in enumerate(i for i, q in enumerate(quartet) if q == name):
        fold_of[i] = k % 5
ids = np.zeros((len(cand), FIELDS), dtype=np.int64)
sizes = []
for f in range(FIELDS):
    key = np.where(cand[:, 2*f] > 0, cand[:, 2*f+1].astype(np.float32), -1.0)
    values, inverse = np.unique(key, return_inverse=True)
    ids[:, f] = inverse
    sizes.append(len(values))
board = cand[:, FIELDS*2:].astype(np.int16)
del cand
base = stored['outcome'][:, np.abs(stored['outcome']).max(axis=0) > 0].astype(np.float32)/4
FEATURES = {'o': base, 'o2': np.concatenate([base, extra[:, used]/4], axis=1)}
print('loaded: games', len(games), '| decisions', len(chosen), '| o columns', base.shape[1], '| o2 columns',
      FEATURES['o2'].shape[1], '| seconds', round(time.time()-start), flush=True)


class Net(nn.Module):
    def __init__(self, obs, features, width):
        super().__init__()
        self.obs, self.features = obs, features
        self.state = nn.Sequential(nn.Linear(obs.shape[1], width), nn.Tanh())
        self.embed = nn.ModuleList(nn.Embedding(size, width) for size in sizes)
        self.action = nn.Linear(3*board.shape[1], width)
        self.head = nn.Sequential(nn.Linear(width*2, width), nn.Tanh(), nn.Linear(width, 1))
        self.outcome = nn.Linear(features.shape[1], width)   # created last, as in scratch_bc114_o2.py

    def forward(self, rows, cand_rows, owner):
        cells = board[cand_rows]
        planes = np.concatenate([(cells % 32) > 0, (cells // 32) % 2 > 0, cells >= 64], axis=1)
        action = self.action(torch.from_numpy(planes.astype(np.float32)))
        field = torch.from_numpy(ids[cand_rows])
        for f, table in enumerate(self.embed):
            action = action+table(field[:, f])
        action = action+self.outcome(torch.from_numpy(self.features[cand_rows]))
        return self.head(torch.cat((self.state(self.obs[rows])[owner], torch.tanh(action)), dim=-1)).squeeze(-1)


def batch_loss(model, rows, train):
    k = counts[rows]
    cand_rows = np.concatenate([np.arange(offsets[r], offsets[r+1]) for r in rows])
    owner = torch.from_numpy(np.repeat(np.arange(len(rows)), k))
    with torch.set_grad_enabled(train):
        logits = model(rows, cand_rows, owner)
        peak = torch.full((len(rows),), -1e30).scatter_reduce(0, owner, logits.detach(), 'amax')
        total = torch.zeros(len(rows)).index_add(0, owner, torch.exp(logits-peak[owner]))
        first = np.concatenate([[0], np.cumsum(k)[:-1]])
        picked = logits[torch.from_numpy(first+chosen[rows])]
        loss = (torch.log(total)+peak-picked).sum()
    best = torch.zeros(len(rows)).scatter_reduce(0, owner, logits.detach(), 'amax', include_self=False)
    return loss, (picked.detach() >= best).numpy()


def evaluate(model, rows):
    model.eval()
    loss_sum, correct = 0.0, np.zeros(len(rows), dtype=bool)
    for begin in range(0, len(rows), BATCH):
        loss, ok = batch_loss(model, rows[begin:begin+BATCH], False)
        loss_sum += float(loss)
        correct[begin:begin+BATCH] = ok
    return loss_sum/len(rows), correct


def fit(model, train_rows, val_rows, limit, mark):
    """Optimizer steps over fresh permutations of train_rows until `limit` steps (it may end inside an epoch);
    a validation point every `mark` steps and at the end. Returns steps, [(steps, loss, accuracy)], last hits."""
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    rng = np.random.default_rng(0)
    steps, curve, correct = 0, [], None
    while steps < limit:
        order = rng.permutation(train_rows)
        for begin in range(0, len(order), BATCH):
            rows = order[begin:begin+BATCH]
            model.train()
            loss, _ = batch_loss(model, rows, True)
            optimizer.zero_grad()
            (loss/len(rows)).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            steps += 1
            if steps % mark == 0 or steps == limit:
                val_loss, correct = evaluate(model, val_rows)
                curve.append((steps, val_loss, float(correct.mean())))
            if steps == limit:
                break
    return steps, curve, correct


def half_of(train_games):
    keep = []
    for name in sorted(set(quartet)):
        keep += [i for i in train_games if quartet[i] == name][::2]
    return sorted(keep)


hit = {arm: np.zeros(len(chosen), dtype=bool) for arm in ARMS}
fold_rows = {arm: {'loss': [], 'acc': [], 'steps': [], 'train_games': [], 'train_decisions': []} for arm in ARMS}
curves = {arm: [] for arm in ARMS}   # per fold: [loss at each of the EPOCHS validation points]
for fold in range(1 if SMOKE else 5):
    val_rows = np.flatnonzero(fold_of[game_of] == fold)
    train_games = [i for i in range(len(games)) if fold_of[i] != fold]
    members = {'all': train_games, 'half': half_of(train_games)}
    rows_of = {name: np.flatnonzero(np.isin(game_of, chosen_games)) for name, chosen_games in members.items()}
    assert np.array_equal(rows_of['all'], np.flatnonzero(fold_of[game_of] != fold))
    keep = np.abs(obs_all[rows_of['all']]).max(axis=0) > 0
    obs = torch.from_numpy(obs_all[:, keep].astype(np.float32))
    epoch_steps = {name: math.ceil(len(rows)/BATCH) for name, rows in rows_of.items()}
    line = {'fold': fold, 'val_games': int((fold_of == fold).sum()), 'val_decisions': len(val_rows)}
    for arm, (feature, width, data, stop) in ARMS.items():
        torch.manual_seed(0)
        model = Net(obs, FEATURES[feature], width)
        mark = epoch_steps['all'] if stop == 'steps' else epoch_steps[data]
        steps, curve, correct = fit(model, rows_of[data], val_rows, EPOCHS*mark, mark)
        assert len(curve) == EPOCHS and curve[-1][0] == steps, (arm, steps, curve)
        if stop == 'steps':
            assert steps == EPOCHS*epoch_steps['all'], (arm, steps)
        hit[arm][val_rows] = correct
        row = fold_rows[arm]
        row['loss'].append(curve[-1][1])
        row['acc'].append(curve[-1][2])
        row['steps'].append(steps)
        row['train_games'].append(len(members[data]))
        row['train_decisions'].append(len(rows_of[data]))
        curves[arm].append([point[1] for point in curve])
        line[arm] = {'loss': round(curve[-1][1], 3), 'acc': round(curve[-1][2], 3), 'steps': steps,
                     'train_games': len(members[data]), 'train_decisions': len(rows_of[data])}
    line['seconds'] = round(time.time()-start)
    print(json.dumps(line), flush=True)
if SMOKE:
    print('smoke ok: arms', list(ARMS), '| step counts', {arm: fold_rows[arm]['steps'] for arm in ARMS})
    sys.exit(0)

per_game = {arm: np.array([hit[arm][game_of == g].mean() for g in range(len(games))]) for arm in ARMS}


def text(values, digits=3):
    return ' '.join(('%.*f' % (digits, v)) if isinstance(v, float) else str(v) for v in values)


def compare(first, second):
    diff = per_game[first]-per_game[second]
    mean, sd, n = float(diff.mean()), float(diff.std(ddof=1)), len(diff)
    half = float(t.ppf(0.975, n-1))*sd/math.sqrt(n)
    reading = 'not confirmed (interval includes 0)' if mean-half <= 0 <= mean+half else (
        'first arm better' if mean > 0 else 'first arm worse')
    parts = []
    for name in sorted(set(quartet)):
        group = [i for i, q in enumerate(quartet) if q == name]
        parts.append('%s %+.3f %d/%d' % (name, diff[group].mean(), int((diff[group] > 0).sum()), len(group)))
    return {'first': first, 'second': second, 'mean': round(mean, 4), 'low': round(mean-half, 4),
            'high': round(mean+half, 4), 'better': int((diff > 0).sum()), 'equal': int((diff == 0).sum()),
            'worse': int((diff < 0).sum()), 'quartets': ', '.join(parts), 'reading': reading}


arms = {}
for arm, (feature, width, data, stop) in ARMS.items():
    row = fold_rows[arm]
    curve = np.mean(np.array(curves[arm]), axis=0)
    arms[arm] = {
        'input': feature, 'width': width, 'games': data, 'stop': stop,
        'per_game': round(float(per_game[arm].mean()), 4), 'decision_weighted': round(float(hit[arm].mean()), 4),
        'fold_loss': text(row['loss']), 'fold_acc': text(row['acc']), 'fold_steps': text(row['steps']),
        'fold_train_games': text(row['train_games']), 'fold_train_decisions': text(row['train_decisions']),
        'curve_loss_fold_mean': text(curve.tolist()), 'lowest_loss_point': int(np.argmin(curve))+1,
    }
comparisons = {label: compare(first, second) for label, first, second in PAIRS}
check = abs(arms['w64-all']['per_game']-EXPECTED['w64-all per game']) < 0.0006
metrics = {'epochs': EPOCHS, 'games': len(games), 'decisions': len(chosen), 'arms': arms, 'comparisons': comparisons,
           'expected': EXPECTED, 'w64_all_reproduces_116': bool(check), 'seconds': round(time.time()-start)}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
print('per arm (n=%d games): per-game accuracy | decision-weighted | fold-mean validation loss at the 9 points '
      '(lowest point)' % len(games))
for arm, row in arms.items():
    print('  %-16s %.4f | %.4f | %s (%d)' % (arm, row['per_game'], row['decision_weighted'],
                                           row['curve_loss_fold_mean'], row['lowest_loss_point']))
print('w64-all per game %.4f, expected %.4f (116 A arm): %s' % (
    arms['w64-all']['per_game'], EXPECTED['w64-all per game'], 'reproduced' if check else 'NOT reproduced'))
for label, row in comparisons.items():
    print('%s: %+.4f [%+.4f, %+.4f], games better %d, equal %d, worse %d -> %s' % (
        label, row['mean'], row['low'], row['high'], row['better'], row['equal'], row['worse'], row['reading']))
    print('  quartets:', row['quartets'])
