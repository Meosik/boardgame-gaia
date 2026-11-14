"""Why does BC on the 114 shards stay near chance? Data checks: candidate counts, uniform loss, chosen-index
distribution, feature scale, and whether the chosen candidate's feature row is unique in its decision."""
import glob
import math
import sys
from collections import Counter

import numpy as np

paths = sorted(glob.glob((sys.argv[1] if len(sys.argv) > 1 else 'gaia-rl/runs/bc-114-shards') + '/shard-*.npz'))
counts, chosen, uniform, forced = [], [], 0.0, 0
dup_chosen = dup_any = 0
dup_share = []
obs_abs, cand_abs = [], []
obs_nonzero = cand_nonzero = None
obs_max = cand_max = None
total = 0
for path in paths:
    shard = np.load(path)
    offsets = shard['cand_offsets']
    obs = shard['observation'].astype(np.float32)
    cand = shard['cand'].astype(np.float32)
    obs_max = np.abs(obs).max(axis=0) if obs_max is None else np.maximum(obs_max, np.abs(obs).max(axis=0))
    cand_max = np.abs(cand).max(axis=0) if cand_max is None else np.maximum(cand_max, np.abs(cand).max(axis=0))
    obs_abs.append(np.abs(obs).sum(axis=1))
    for i, pick in enumerate(shard['chosen']):
        rows = cand[offsets[i]:offsets[i+1]]
        k = len(rows)
        counts.append(k)
        chosen.append(int(pick))
        uniform += math.log(k)
        forced += k == 1
        same = (rows == rows[pick]).all(axis=1).sum()
        dup_chosen += same > 1
        dup_share.append(1/same)
        dup_any += len(np.unique(rows, axis=0)) < k
        total += 1
counts = np.array(counts)
chosen = np.array(chosen)
print('samples', total, 'shards', len(paths))
print('candidates per decision: median', int(np.median(counts)), 'mean %.1f' % counts.mean(), 'p90',
      int(np.percentile(counts, 90)), 'max', counts.max(), '| forced (1 candidate)', int(forced))
print('uniform cross-entropy (mean ln K) %.3f' % (uniform/total), '| chance accuracy %.3f' % (1/counts).mean())
print('chosen index: == 0 %.3f' % (chosen == 0).mean(), '| == last %.3f' % (chosen == counts-1).mean(),
      '| top indexes', Counter(chosen.tolist()).most_common(6))
print('relative position chosen/(K-1), deciles of non-forced:',
      np.round(np.percentile((chosen/np.maximum(counts-1, 1))[counts > 1], [10, 30, 50, 70, 90]), 2).tolist())
print('chosen candidate row not unique in its decision: %.3f' % (dup_chosen/total),
      '| decisions with any duplicate rows %.3f' % (dup_any/total),
      '| accuracy ceiling if ties are split evenly %.3f' % float(np.mean(dup_share)))
print('observation: columns', len(obs_max), 'never non-zero', int((obs_max == 0).sum()), 'max abs %.1f' % obs_max.max(),
      'columns with max abs > 1:', int((obs_max > 1).sum()), '> 10:', int((obs_max > 10).sum()),
      '| mean L1 per row %.1f' % float(np.concatenate(obs_abs).mean()))
print('candidate features: columns', len(cand_max), 'never non-zero', int((cand_max == 0).sum()),
      'max abs %.1f' % cand_max.max(), 'columns with max abs > 1:', int((cand_max > 1).sum()), '> 10:',
      int((cand_max > 10).sum()))
