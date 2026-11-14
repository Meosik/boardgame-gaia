"""Is the weak BC fit on the 114 shards an optimisation/capacity problem or an encoding problem?
Same shards, fixed split by game (= seed; Codex debate 2026-11-14: the first version validated on the last two
shards, which leaks one game across the boundary, and cut the learning curve from the front of the export):
validation = every fifth game of each quartet (manifest order), training = the other games; the learning curve
takes a random FRACTION of the training games inside each quartet (SUBSET_SEED). Variants:
  raw      the bc_train network on the stored features (width and lr from the command line)
  expand   candidate fields re-expanded: every categorical/integer value column becomes an embedding id
           (FeatureEncoder stores one ordinal scalar per field), the board columns (sum of 2**role) become
           three 0/1 planes (single-coordinate roles, federation hexes, satellites); state columns that are
           never non-zero are dropped in both variants.
  raw+o / expand+o   the same plus the outcome features of lab/scratch_bc114_outcome.py (state right after the
           candidate minus the state before, acting player's numeric fields; E147 (ㄱ)) added to the candidate input.
Usage: scratch_bc114_variants.py raw|expand|raw+o|expand+o WIDTH LR EPOCHS [STATE_LAYERS [FRACTION [SUBSET_SEED]]]"""
import glob
import json
import sys
import time

import numpy as np
import torch
from torch import nn

variant, width, lr, epochs = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
base, use_outcome = variant.split('+')[0], variant.endswith('+o')
state_layers = int(sys.argv[5]) if len(sys.argv) > 5 else 1
FIELDS = 34
paths = sorted(glob.glob('gaia-rl/runs/bc-114-shards/shard-*.npz'))
obs, cand, counts, chosen = [], [], [], []
for path in paths:
    shard = np.load(path)
    obs.append(shard['observation'])
    cand.append(shard['cand'])
    counts.append(np.diff(shard['cand_offsets']))
    chosen.append(shard['chosen'])
obs, cand = np.concatenate(obs), np.concatenate(cand)
counts, chosen = np.concatenate(counts).astype(np.int64), np.concatenate(chosen).astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])
# Game of every sample: the export walks the manifest in order (bc_dataset.iter_samples), one seed per game.
games = [json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')]
games = [g for g in games if g['replays']]
assert sum(g['decisions'] for g in games) == len(chosen), 'manifest and shards disagree'
game_of = np.repeat(np.arange(len(games)), [g['decisions'] for g in games])
quartet = [g['seed'].rsplit('-', 1)[0] for g in games]
fraction = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
subset = np.random.default_rng(int(sys.argv[7]) if len(sys.argv) > 7 else 0)
val_games, train_games = [], []
for name in sorted(set(quartet)):
    members = [i for i, q in enumerate(quartet) if q == name]
    held = members[4::5]
    rest = [i for i in members if i not in held]
    take = max(1, round(len(rest)*fraction))
    val_games += held
    train_games += sorted(subset.permutation(rest)[:take].tolist()) if fraction < 1 else rest
train_rows = np.flatnonzero(np.isin(game_of, train_games))
val_rows = np.flatnonzero(np.isin(game_of, val_games))
print('games: train', len(train_games), 'validation', len(val_games), 'per quartet',
      {name: (sum(quartet[i] == name for i in train_games), sum(quartet[i] == name for i in val_games))
       for name in sorted(set(quartet))}, flush=True)
keep = np.abs(obs[train_rows]).max(axis=0) > 0
obs = torch.from_numpy(obs[:, keep].astype(np.float32))
ids = np.zeros((len(cand), FIELDS), dtype=np.int64)
sizes = []
for f in range(FIELDS):                       # value column 2f+1, presence column 2f
    key = np.where(cand[:, 2*f] > 0, cand[:, 2*f+1].astype(np.float32), -1.0)
    values, inverse = np.unique(key, return_inverse=True)
    ids[:, f] = inverse
    sizes.append(len(values))
board = cand[:, FIELDS*2:].astype(np.int16)
outcome = None
if use_outcome:
    stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
    assert (stored['counts'] == counts).all(), 'outcome rows do not line up with the shards'
    outcome = stored['outcome'][:, np.abs(stored['outcome']).max(axis=0) > 0].astype(np.float32)/4
    print('outcome columns', outcome.shape[1], flush=True)
print(variant, 'width', width, 'lr', lr, 'state columns', int(keep.sum()), 'train', len(train_rows),
      'validation', len(val_rows), 'uniform loss %.3f' % float(np.log(counts[val_rows]).mean()),
      'chance %.3f' % float((1/counts[val_rows]).mean()), flush=True)


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        layers = [nn.Linear(obs.shape[1], width), nn.Tanh()]
        for _ in range(state_layers-1):
            layers += [nn.Linear(width, width), nn.Tanh()]
        self.state = nn.Sequential(*layers)
        if use_outcome:
            self.outcome = nn.Linear(outcome.shape[1], width)
        if base == 'raw':
            self.action = nn.Linear(cand.shape[1], width)
        else:
            self.embed = nn.ModuleList(nn.Embedding(size, width) for size in sizes)
            self.action = nn.Linear(3*board.shape[1], width)
        self.head = nn.Sequential(nn.Linear(width*2, width), nn.Tanh(), nn.Linear(width, 1))

    def forward(self, rows, cand_rows, owner):
        state = self.state(obs[rows])
        if base == 'raw':
            action = self.action(torch.from_numpy(cand[cand_rows].astype(np.float32)))
        else:
            cells = board[cand_rows]
            planes = np.concatenate([(cells % 32) > 0, (cells // 32) % 2 > 0, cells >= 64], axis=1)
            action = self.action(torch.from_numpy(planes.astype(np.float32)))
            field = torch.from_numpy(ids[cand_rows])
            for f, table in enumerate(self.embed):
                action = action+table(field[:, f])
        if use_outcome:
            action = action+self.outcome(torch.from_numpy(outcome[cand_rows]))
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
if fraction < 1:
    sys.exit()          # learning-curve runs: the summary line is enough
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
