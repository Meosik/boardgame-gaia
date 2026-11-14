"""Does FeatureEncoderV4 reproduce the features measured in E148-E153 (`expand+o`)? For the chosen 114 games:
board columns equal the stored version 3 rows, field presence equal, field id <-> version 3 scalar one-to-one,
outcome columns equal runs/bc-114-outcome/outcome.npz (by name; the columns outcome.npz never saw must be 0).
Usage: scratch_v4_check.py GAME_INDEX [GAME_INDEX ...]"""
import glob
import gzip
import json
import sys
import time

import numpy as np

from gaia_rl import Environment
from gaia_rl.encoding import (FeatureEncoderV4, ACTION_FIELDS, OUTCOME_PLAYER, OUTCOME_OTHERS, OUTCOME_GLOBALS,
                              OUTCOME_SCALE)

start = time.time()
cand, counts = [], []
for path in sorted(glob.glob('gaia-rl/runs/bc-114-shards/shard-*.npz')):
    shard = np.load(path)
    cand.append(shard['cand'])
    counts.append(np.diff(shard['cand_offsets']))
cand, counts = np.concatenate(cand), np.concatenate(counts).astype(np.int64)
offsets = np.concatenate([[0], np.cumsum(counts)])
stored = np.load('gaia-rl/runs/bc-114-outcome/outcome.npz')
assert (stored['counts'] == counts).all()
names = [str(n) for n in stored['names']]
mine = list(OUTCOME_PLAYER)+['others.'+n for n in OUTCOME_OTHERS]+list(OUTCOME_GLOBALS)
seen = np.abs(stored['outcome']).max(axis=0) > 0
column_of = {name: mine.index(name) for name, used in zip(names, seen) if used}
unseen = [i for i, name in enumerate(mine) if name not in column_of]
print('loaded', len(counts), 'decisions', len(cand), 'rows | stored outcome columns', len(column_of),
      '| version 4 columns never seen in 114:', [mine[i] for i in unseen], flush=True)
games = [g for g in (json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')) if g['replays']]
first = np.concatenate([[0], np.cumsum([g['decisions'] for g in games])])
encoder = FeatureEncoderV4(2048)
fields = len(ACTION_FIELDS)
pairs = [set() for _ in range(fields)]
checked = rows = 0
for g in map(int, sys.argv[1:]):
    game, decision = games[g], int(first[g])
    env = Environment(game['seed'], 2000)
    for row in (json.loads(line) for line in gzip.open(game['game']+'/decisions.jsonl.gz', 'rt')):
        snapshot = json.loads(env.snapshot_json())
        if snapshot.get('player') is not None:
            n = len(snapshot['candidates'])
            assert n == counts[decision], (g, decision, n, counts[decision])
            previews = [json.loads(env.preview_state_json(snapshot['decision_id'], i)) for i in range(n)]
            new = encoder.encode(snapshot, snapshot['player'], previews)['candidates'][:n]
            old = cand[offsets[decision]:offsets[decision+1]]
            assert (new[:, encoder.board_offset:encoder.outcome_offset] == old[:, fields*2:]).all(), (g, decision)
            assert ((new[:, :fields] > 0) == (old[:, 0:fields*2:2] > 0)).all(), (g, decision)
            for f in range(fields):
                pairs[f].update(zip(new[:, f].tolist(), zip(old[:, 2*f].tolist(), old[:, 2*f+1].tolist())))
            out = new[:, encoder.outcome_offset:]*OUTCOME_SCALE
            want = stored['outcome'][offsets[decision]:offsets[decision+1]].astype(np.float32)
            for name, column in column_of.items():
                assert (out[:, column] == want[:, names.index(name)]).all(), (g, decision, name)
            assert not out[:, unseen].any(), (g, decision, [mine[i] for i in unseen if out[:, i].any()])
            decision += 1
            checked += 1
            rows += n
        env.step(row['decision_id'], row['index'])
    assert decision == first[g+1], (g, decision, first[g+1])
    print('game', g, game['seed'], 'ok', flush=True)
for f, found in enumerate(pairs):
    ids, scalars = {a for a, _ in found}, {b for _, b in found}
    assert len(ids) == len(found) == len(scalars), (ACTION_FIELDS[f], sorted(found))
print('decisions', checked, 'candidate rows', rows, '| board equal, presence equal, outcome equal |',
      'distinct ids per field', [len(found) for found in pairs], '| seconds', round(time.time()-start))
