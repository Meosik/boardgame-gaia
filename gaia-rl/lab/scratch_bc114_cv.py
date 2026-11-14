"""Paired test of the outcome features on the 114 BC samples (HANDOFF E148 (ㄴ) ①, Codex debate 2026-11-14):
`expand` vs `expand+o` (lab/scratch_bc114_variants.py) on a 5-fold cross-validation by game, stratified by quartet
(game k of a quartet, manifest order, goes to fold k mod 5), so each of the 46 games is validated exactly once.
Both arms: width 64, lr 0.001, the same torch seed and batch order, a fixed EPOCHS (no epoch picked on the
validation fold). Report: per-game top-1 accuracy of both arms, the per-game difference (mean, t interval over
games, games where +o is better), and the decision-weighted totals.
Usage: scratch_bc114_cv.py [EPOCHS=9]"""
import glob
import json
import math
import sys
import time

import numpy as np
import torch
from torch import nn

EPOCHS = int(sys.argv[1]) if len(sys.argv) > 1 else 9
WIDTH, LR, FIELDS = 64, 0.001, 34
obs_all, cand, counts, chosen = [], [], [], []
for path in sorted(glob.glob('gaia-rl/runs/bc-114-shards/shard-*.npz')):
    shard = np.load(path)
    obs_all.append(shard['observation'])
    cand.append(shard['cand'])
    counts.append(np.diff(shard['cand_offsets']))
    chosen.append(shard['chosen'])
obs_all, cand = np.concatenate(obs_all), np.concatenate(cand)
counts, chosen = np.concatenate(counts).astype(np.int64), np.concatenate(chosen).astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])
games = [g for g in (json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')) if g['replays']]
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
stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
assert (stored['counts'] == counts).all()
outcome = stored['outcome'][:, np.abs(stored['outcome']).max(axis=0) > 0].astype(np.float32)/4
del cand


class Net(nn.Module):
    def __init__(self, obs, use_outcome):
        super().__init__()
        self.obs, self.use_outcome = obs, use_outcome
        self.state = nn.Sequential(nn.Linear(obs.shape[1], WIDTH), nn.Tanh())
        self.embed = nn.ModuleList(nn.Embedding(size, WIDTH) for size in sizes)
        self.action = nn.Linear(3*board.shape[1], WIDTH)
        self.head = nn.Sequential(nn.Linear(WIDTH*2, WIDTH), nn.Tanh(), nn.Linear(WIDTH, 1))
        if use_outcome:                      # created last: the shared layers start from the same weights in both arms
            self.outcome = nn.Linear(outcome.shape[1], WIDTH)

    def forward(self, rows, cand_rows, owner):
        cells = board[cand_rows]
        planes = np.concatenate([(cells % 32) > 0, (cells // 32) % 2 > 0, cells >= 64], axis=1)
        action = self.action(torch.from_numpy(planes.astype(np.float32)))
        field = torch.from_numpy(ids[cand_rows])
        for f, table in enumerate(self.embed):
            action = action+table(field[:, f])
        if self.use_outcome:
            action = action+self.outcome(torch.from_numpy(outcome[cand_rows]))
        return self.head(torch.cat((self.state(self.obs[rows])[owner], torch.tanh(action)), dim=-1)).squeeze(-1)


def run(model, sample_rows, optimizer=None, size=256):
    correct = np.zeros(len(sample_rows), dtype=bool)
    loss_sum = 0.0
    for start in range(0, len(sample_rows), size):
        rows = sample_rows[start:start+size]
        k = counts[rows]
        cand_rows = np.concatenate([np.arange(offsets[r], offsets[r+1]) for r in rows])
        owner = torch.from_numpy(np.repeat(np.arange(len(rows)), k))
        with torch.set_grad_enabled(optimizer is not None):
            logits = model(rows, cand_rows, owner)
            peak = torch.full((len(rows),), -1e30).scatter_reduce(0, owner, logits.detach(), 'amax')
            total = torch.zeros(len(rows)).index_add(0, owner, torch.exp(logits-peak[owner]))
            first = np.concatenate([[0], np.cumsum(k)[:-1]])
            picked = logits[torch.from_numpy(first+chosen[rows])]
            loss = (torch.log(total)+peak-picked).sum()
        if optimizer is not None:
            optimizer.zero_grad()
            (loss/len(rows)).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        loss_sum += float(loss.detach())
        best = torch.zeros(len(rows)).scatter_reduce(0, owner, logits.detach(), 'amax', include_self=False)
        correct[start:start+size] = (picked.detach() >= best).numpy()
    return loss_sum/len(sample_rows), correct


start = time.time()
hit = {False: np.zeros(len(chosen), dtype=bool), True: np.zeros(len(chosen), dtype=bool)}
for fold in range(5):
    val_rows = np.flatnonzero(fold_of[game_of] == fold)
    train_rows = np.flatnonzero(fold_of[game_of] != fold)
    keep = np.abs(obs_all[train_rows]).max(axis=0) > 0
    obs = torch.from_numpy(obs_all[:, keep].astype(np.float32))
    line = {'fold': fold, 'val_games': int((fold_of == fold).sum()), 'val_decisions': len(val_rows)}
    for use_outcome in (False, True):
        torch.manual_seed(0)
        rng = np.random.default_rng(0)
        model = Net(obs, use_outcome)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)
        for _ in range(EPOCHS):
            model.train()
            run(model, rng.permutation(train_rows), optimizer)
        model.eval()
        loss, correct = run(model, val_rows)
        hit[use_outcome][val_rows] = correct
        line['expand+o' if use_outcome else 'expand'] = {'loss': round(loss, 3), 'acc': round(float(correct.mean()), 3)}
    line['seconds'] = round(time.time()-start)
    print(json.dumps(line), flush=True)

per_game = np.array([[hit[arm][game_of == g].mean() for arm in (False, True)] for g in range(len(games))])
diff = per_game[:, 1]-per_game[:, 0]
mean, sd, n = diff.mean(), diff.std(ddof=1), len(diff)
from scipy.stats import t
half = t.ppf(0.975, n-1)*sd/math.sqrt(n)
print('epochs', EPOCHS, '| decisions', len(chosen), '| decision-weighted accuracy expand %.3f expand+o %.3f' % (
    hit[False].mean(), hit[True].mean()))
print('per game (n=%d): expand %.3f, expand+o %.3f, difference %+.3f [%+.3f, %+.3f], games +o better %d, equal %d, '
      'worse %d' % (n, per_game[:, 0].mean(), per_game[:, 1].mean(), mean, mean-half, mean+half,
                    int((diff > 0).sum()), int((diff == 0).sum()), int((diff < 0).sum())))
for name in sorted(set(quartet)):
    members = [i for i, q in enumerate(quartet) if q == name]
    print('  %s games %d difference %+.3f, better %d/%d' % (name, len(members), diff[members].mean(),
                                                          int((diff[members] > 0).sum()), len(members)))
print('  largest gains', np.round(np.sort(diff)[-3:], 3).tolist(), 'largest losses', np.round(np.sort(diff)[:3], 3).tolist())
