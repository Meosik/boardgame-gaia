"""Paired test of structure-kind / planet-type / satellite outcome features on the 114 BC samples (HANDOFF E149 (ㄴ) ②,
run from the lab queue in the work tree): `expand+o` vs `expand+o2` on the 5 game-level folds of
lab/scratch_bc114_cv.py (quartet-stratified, game k of a quartet -> fold k mod 5), both arms width 64, lr 0.001,
the same torch seed and batch order, fixed 9 epochs (no epoch picked on the validation fold).
o  = the 53 outcome columns of E148 (gaia-rl/runs/bc-114-outcome/outcome.npz, lab/scratch_bc114_outcome.py).
o2 = o + for every candidate, state right after it (Environment.preview_state_json) minus the state before:
     the acting player's structure count per kind (`players[].structures[].kind`), the number of planets the acting
     player owns per planet type (`board.hexes[].planet`), and the number of hexes with the acting player's satellite.
Stage 1 writes gaia-rl/runs/bc-114-outcome/o2.npz (reused when present), stage 2 prints one line per fold and the
per-game summary and writes gaia-rl/runs/bc-114-o2/metrics.json.
Usage: scratch_bc114_o2.py          # both stages, about 9 minutes
       scratch_bc114_o2.py smoke    # 2 games extracted, 1 epoch, fold 0, nothing written"""
import glob
import gzip
import json
import math
import os
import sys
import time
from collections import Counter

import numpy as np
import torch
from scipy.stats import t
from torch import nn

from gaia_rl import Environment

SMOKE = sys.argv[1:] == ['smoke']
EPOCHS = 1 if SMOKE else 9
WIDTH, LR, FIELDS = 64, 0.001, 34
EXTRA = 40            # o2 columns; grows by first appearance, fatal when exceeded
STORE = 'gaia-rl/runs/bc-114-outcome/o2.npz'
METRICS = 'gaia-rl/runs/bc-114-o2/metrics.json'
E149 = {'expand+o per game': 0.346, 'expand+o decision-weighted': 0.347}

games = [g for g in (json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')) if g['replays']]
stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
counts = stored['counts'].astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])


def tally(state, actor):
    out = Counter()
    for item in next(p for p in state['players'] if p['player_id'] == actor)['structures']:
        kind = item['kind']
        out['structure.'+(kind if isinstance(kind, str) else next(iter(kind)))] += 1
    for cell in state['board']['hexes'].values():
        planet = cell.get('planet')
        if planet and planet.get('owner') == actor:
            out['planet.'+planet['planet_type']] += 1
        if actor in cell.get('satellites', ()):
            out['satellites'] += 1
    return out


def extract(limit):
    columns, blocks = {}, []
    for game in games[:limit]:
        env = Environment(game['seed'], 2000)
        for row in (json.loads(line) for line in gzip.open(game['game']+'/decisions.jsonl.gz', 'rt')):
            snapshot = json.loads(env.snapshot_json())
            actor = snapshot.get('player')
            if actor is not None:
                if len(snapshot['candidates']) != counts[len(blocks)]:
                    raise RuntimeError('candidate count differs from outcome.npz at decision %d of %s: %d vs %d' % (
                        len(blocks), game['seed'], len(snapshot['candidates']), counts[len(blocks)]))
                before = tally(snapshot['state'], actor)
                block = np.zeros((len(snapshot['candidates']), EXTRA), dtype=np.float32)
                for index in range(len(block)):
                    after = tally(json.loads(env.preview_state_json(snapshot['decision_id'], index)), actor)
                    for key in after.keys() | before.keys():
                        delta = after[key]-before[key]
                        if delta:
                            column = columns.setdefault(key, len(columns))
                            if column >= EXTRA:
                                raise RuntimeError(f'more than {EXTRA} o2 columns: {key}')
                            block[index, column] = delta
                blocks.append(block)
            env.step(row['decision_id'], row['index'])
    return np.concatenate(blocks), sorted(columns, key=columns.get), len(blocks)


start = time.time()
if not SMOKE and os.path.exists(STORE) and np.array_equal(np.load(STORE)['counts'], counts):
    names = [str(n) for n in np.load(STORE)['names']]
    extra = np.load(STORE)['extra'].astype(np.float32)
    print('o2 columns read from', STORE, flush=True)
else:
    part, names, decisions = extract(2 if SMOKE else len(games))
    extra = np.zeros((offsets[-1], EXTRA), dtype=np.float32)
    extra[:len(part)] = np.clip(part, -30, 30)
    if not SMOKE:
        assert decisions == len(counts) and len(part) == offsets[-1], (decisions, len(counts), len(part))
        np.savez_compressed(STORE, extra=extra.astype(np.float16), counts=counts, names=np.array(names))
extract_seconds = round(time.time()-start)
used = np.abs(extra).max(axis=0) > 0
changed = float((np.abs(extra).max(axis=1) > 0).mean())
print('o2 columns', len(names), '| seconds', extract_seconds, '| candidate rows with an o2 change %.3f' % changed)
print('o2 columns:', ' '.join(names), flush=True)

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
ARMS = {'expand+o': base, 'expand+o2': np.concatenate([base, extra[:, used]/4], axis=1)}


class Net(nn.Module):
    def __init__(self, obs, features):
        super().__init__()
        self.obs, self.features = obs, features
        self.state = nn.Sequential(nn.Linear(obs.shape[1], WIDTH), nn.Tanh())
        self.embed = nn.ModuleList(nn.Embedding(size, WIDTH) for size in sizes)
        self.action = nn.Linear(3*board.shape[1], WIDTH)
        self.head = nn.Sequential(nn.Linear(WIDTH*2, WIDTH), nn.Tanh(), nn.Linear(WIDTH, 1))
        self.outcome = nn.Linear(features.shape[1], WIDTH)   # created last: the shared layers start equal in both arms

    def forward(self, rows, cand_rows, owner):
        cells = board[cand_rows]
        planes = np.concatenate([(cells % 32) > 0, (cells // 32) % 2 > 0, cells >= 64], axis=1)
        action = self.action(torch.from_numpy(planes.astype(np.float32)))
        field = torch.from_numpy(ids[cand_rows])
        for f, table in enumerate(self.embed):
            action = action+table(field[:, f])
        action = action+self.outcome(torch.from_numpy(self.features[cand_rows]))
        return self.head(torch.cat((self.state(self.obs[rows])[owner], torch.tanh(action)), dim=-1)).squeeze(-1)


def run(model, sample_rows, optimizer=None, size=256):
    correct = np.zeros(len(sample_rows), dtype=bool)
    loss_sum = 0.0
    for begin in range(0, len(sample_rows), size):
        rows = sample_rows[begin:begin+size]
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
        correct[begin:begin+size] = (picked.detach() >= best).numpy()
    return loss_sum/len(sample_rows), correct


hit = {arm: np.zeros(len(chosen), dtype=bool) for arm in ARMS}
folds = []
for fold in range(1 if SMOKE else 5):
    val_rows = np.flatnonzero(fold_of[game_of] == fold)
    train_rows = np.flatnonzero(fold_of[game_of] != fold)
    keep = np.abs(obs_all[train_rows]).max(axis=0) > 0
    obs = torch.from_numpy(obs_all[:, keep].astype(np.float32))
    line = {'fold': fold, 'val_games': int((fold_of == fold).sum()), 'val_decisions': len(val_rows)}
    for arm, features in ARMS.items():
        torch.manual_seed(0)
        rng = np.random.default_rng(0)
        model = Net(obs, features)
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)
        for _ in range(EPOCHS):
            model.train()
            run(model, rng.permutation(train_rows), optimizer)
        model.eval()
        loss, correct = run(model, val_rows)
        hit[arm][val_rows] = correct
        line[arm] = {'loss': round(loss, 3), 'acc': round(float(correct.mean()), 3)}
    line['seconds'] = round(time.time()-start)
    folds.append(line)
    print(json.dumps(line), flush=True)
if SMOKE:
    print('smoke ok: arms', {arm: features.shape[1] for arm, features in ARMS.items()})
    sys.exit(0)

per_game = np.array([[hit[arm][game_of == g].mean() for arm in ARMS] for g in range(len(games))])
diff = per_game[:, 1]-per_game[:, 0]
mean, sd, n = float(diff.mean()), float(diff.std(ddof=1)), len(diff)
half = float(t.ppf(0.975, n-1))*sd/math.sqrt(n)
reading = 'effect not confirmed (interval includes 0)' if mean-half <= 0 <= mean+half else (
    'o2 better' if mean > 0 else 'o2 worse')
metrics = {
    'epochs': EPOCHS, 'games': n, 'decisions': len(chosen), 'o_columns': int(base.shape[1]),
    'o2_extra_columns': [name for name, keep_it in zip(names, used) if keep_it],
    'candidate_rows_with_o2_change': round(changed, 3), 'extract_seconds': extract_seconds, 'folds': folds,
    'decision_weighted': {arm: round(float(hit[arm].mean()), 4) for arm in ARMS},
    'per_game': {arm: round(float(per_game[:, i].mean()), 4) for i, arm in enumerate(ARMS)},
    'difference': {'mean': round(mean, 4), 'low': round(mean-half, 4), 'high': round(mean+half, 4),
                   'better': int((diff > 0).sum()), 'equal': int((diff == 0).sum()), 'worse': int((diff < 0).sum())},
    'quartets': {name: {'games': len(members), 'difference': round(float(diff[members].mean()), 4),
                        'better': int((diff[members] > 0).sum())}
                 for name in sorted(set(quartet)) for members in [[i for i, q in enumerate(quartet) if q == name]]},
    'largest_gains': np.round(np.sort(diff)[-3:], 3).tolist(), 'largest_losses': np.round(np.sort(diff)[:3], 3).tolist(),
    'e149_expected': E149, 'reading': reading, 'seconds': round(time.time()-start),
}
os.makedirs(os.path.dirname(METRICS), exist_ok=True)
with open(METRICS, 'w') as handle:
    json.dump(metrics, handle, indent=1)
print('epochs', EPOCHS, '| decisions', len(chosen), '| decision-weighted accuracy expand+o %.3f expand+o2 %.3f' % (
    hit['expand+o'].mean(), hit['expand+o2'].mean()))
print('per game (n=%d): expand+o %.3f (E149: %.3f), expand+o2 %.3f, difference %+.3f [%+.3f, %+.3f], games o2 better %d, '
      'equal %d, worse %d' % (n, per_game[:, 0].mean(), E149['expand+o per game'], per_game[:, 1].mean(), mean,
                              mean-half, mean+half, int((diff > 0).sum()), int((diff == 0).sum()), int((diff < 0).sum())))
for name, row in metrics['quartets'].items():
    print('  %s games %d difference %+.3f, better %d/%d' % (name, row['games'], row['difference'], row['better'],
                                                          row['games']))
print('  largest gains', metrics['largest_gains'], 'largest losses', metrics['largest_losses'])
print('reading:', reading)
