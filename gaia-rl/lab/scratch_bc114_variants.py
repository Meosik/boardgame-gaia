"""Is the weak BC fit on the 114 shards an optimisation/capacity problem or an encoding problem?
Same shards, same split (last 2 shards = validation), three variants:
  raw      the bc_train network on the stored features (width and lr from the command line)
  expand   candidate fields re-expanded: every categorical/integer value column becomes an embedding id
           (FeatureEncoder stores one ordinal scalar per field), the board columns (sum of 2**role) become
           three 0/1 planes (single-coordinate roles, federation hexes, satellites); state columns that are
           never non-zero are dropped in both variants.
Usage: scratch_bc114_variants.py raw|expand WIDTH LR EPOCHS [STATE_LAYERS]"""
import glob
import json
import sys
import time

import numpy as np
import torch
from torch import nn

variant, width, lr, epochs = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
state_layers = int(sys.argv[5]) if len(sys.argv) > 5 else 1
FIELDS = 34
paths = sorted(glob.glob('gaia-rl/runs/bc-114-shards/shard-*.npz'))
obs, cand, counts, chosen, split = [], [], [], [], 0
for n, path in enumerate(paths):
    shard = np.load(path)
    obs.append(shard['observation'])
    cand.append(shard['cand'])
    counts.append(np.diff(shard['cand_offsets']))
    chosen.append(shard['chosen'])
    if n == len(paths)-3:
        split = sum(len(c) for c in chosen)
obs, cand = np.concatenate(obs), np.concatenate(cand)
counts, chosen = np.concatenate(counts).astype(np.int64), np.concatenate(chosen).astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])
keep = np.abs(obs[:split]).max(axis=0) > 0
obs = torch.from_numpy(obs[:, keep].astype(np.float32))
ids = np.zeros((len(cand), FIELDS), dtype=np.int64)
sizes = []
for f in range(FIELDS):                       # value column 2f+1, presence column 2f
    key = np.where(cand[:, 2*f] > 0, cand[:, 2*f+1].astype(np.float32), -1.0)
    values, inverse = np.unique(key, return_inverse=True)
    ids[:, f] = inverse
    sizes.append(len(values))
board = cand[:, FIELDS*2:].astype(np.int16)
print(variant, 'width', width, 'lr', lr, 'state columns', int(keep.sum()), 'train', split, 'validation',
      len(chosen)-split, 'distinct values per field', sizes, flush=True)


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        layers = [nn.Linear(obs.shape[1], width), nn.Tanh()]
        for _ in range(state_layers-1):
            layers += [nn.Linear(width, width), nn.Tanh()]
        self.state = nn.Sequential(*layers)
        if variant == 'raw':
            self.action = nn.Linear(cand.shape[1], width)
        else:
            self.embed = nn.ModuleList(nn.Embedding(size, width) for size in sizes)
            self.action = nn.Linear(3*board.shape[1], width)
        self.head = nn.Sequential(nn.Linear(width*2, width), nn.Tanh(), nn.Linear(width, 1))

    def forward(self, rows, cand_rows, owner):
        state = self.state(obs[rows])
        if variant == 'raw':
            action = self.action(torch.from_numpy(cand[cand_rows].astype(np.float32)))
        else:
            cells = board[cand_rows]
            planes = np.concatenate([(cells % 32) > 0, (cells // 32) % 2 > 0, cells >= 64], axis=1)
            action = self.action(torch.from_numpy(planes.astype(np.float32)))
            field = torch.from_numpy(ids[cand_rows])
            for f, table in enumerate(self.embed):
                action = action+table(field[:, f])
        return self.head(torch.cat((state[owner], torch.tanh(action)), dim=-1)).squeeze(-1)


def run(model, sample_rows, optimizer=None, size=256):
    loss_sum = correct = 0
    for start in range(0, len(sample_rows), size):
        rows = sample_rows[start:start+size]
        k = counts[rows]
        cand_rows = np.concatenate([np.arange(offsets[r], offsets[r+1]) for r in rows])
        owner = torch.from_numpy(np.repeat(np.arange(len(rows)), k))
        with torch.set_grad_enabled(optimizer is not None):
            logits = model(rows, cand_rows, owner)
            # log-softmax per decision over its own candidates (ragged, no padding)
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
        correct += int((picked.detach() >= best).sum())
    return loss_sum/len(sample_rows), correct/len(sample_rows)


torch.manual_seed(0)
rng = np.random.default_rng(0)
model = Net()
optimizer = torch.optim.Adam(model.parameters(), lr=lr)
limit = int(sys.argv[6]) if len(sys.argv) > 6 else split      # learning curve: train on the first LIMIT samples
train_rows, val_rows = np.arange(min(limit, split)), np.arange(split, len(chosen))
print('training samples', len(train_rows), flush=True)
best = None
start = time.time()
for epoch in range(1, epochs+1):
    model.train()
    train = run(model, rng.permutation(train_rows), optimizer)
    model.eval()
    val = run(model, val_rows)
    if best is None or val[0] < best['val_loss']:
        best = {'epoch': epoch, 'train_loss': round(train[0], 3), 'train_acc': round(train[1], 3),
                'val_loss': round(val[0], 3), 'val_acc': round(val[1], 3)}
    if epoch % 5 == 0 or epoch == epochs:
        print(json.dumps({'epoch': epoch, 'train_loss': round(train[0], 3), 'train_acc': round(train[1], 3),
                          'val_loss': round(val[0], 3), 'val_acc': round(val[1], 3),
                          'seconds': round(time.time()-start)}), flush=True)
print('best by validation loss', json.dumps(best))

# Validation accuracy of the final model by the action type the teacher chose (field 1 = 'type').
from gaia_rl.vocabulary import CATEGORIES
model.eval()
table = {}
with torch.no_grad():
    for row in val_rows:
        cand_rows = np.arange(offsets[row], offsets[row+1])
        logits = model(np.array([row]), cand_rows, torch.zeros(len(cand_rows), dtype=torch.long))
        pick = cand_rows[chosen[row]]
        guess = cand_rows[int(logits.argmax())]
        names = []
        for c in (pick, guess):
            value = float(cand[c, 3]) if cand[c, 2] > 0 else 0.0
            names.append(CATEGORIES[round(value*len(CATEGORIES))-1] if value else 'none')
        entry = table.setdefault(names[0], [0, 0, 0, 0])
        entry[0] += 1
        entry[1] += pick == guess
        entry[2] += names[0] == names[1]
        entry[3] += len(cand_rows)
print('teacher type: decisions, exact, same type, mean candidates')
for name, (n, exact, same, k) in sorted(table.items(), key=lambda item: -item[1][0])[:16]:
    print(' ', name, n, '%.2f' % (exact/n), '%.2f' % (same/n), round(k/n))
print('  all', len(val_rows), '%.3f' % (sum(v[1] for v in table.values())/len(val_rows)),
      '%.3f' % (sum(v[2] for v in table.values())/len(val_rows)))
