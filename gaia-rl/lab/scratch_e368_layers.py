"""E368: candidates compared per decision, flat (after pruning) vs layered (kind -> place, 3 reps per kind)."""
import collections
import sys

sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp

REPS = 3
rows = []
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    out = tp.prune_indices(snap)
    by = collections.Counter(c['action'].get('type') for i, c in enumerate(snap['candidates']) if i not in out)
    flat = sum(by.values())
    layer1 = sum(min(REPS, v) for v in by.values())
    rows.append((len(snap['candidates']), flat, len(by), layer1, max(by.values()), flat / len(by)))
n = len(rows)
print('decisions', n)
for name, j in (('raw', 0), ('flat_pruned', 1), ('kinds', 2), ('layer1', 3), ('largest_kind', 4), ('mean_kind', 5)):
    vals = sorted(r[j] for r in rows)
    print(name, 'sum', round(sum(vals)), 'mean', round(sum(vals) / n, 1), 'max', round(vals[-1], 1))
worst = sum(r[3] + r[4] for r in rows)
avg = sum(r[3] + r[5] for r in rows)
print('layered worst(layer1+largest) sum', round(worst), 'mean', round(worst / n, 1))
print('layered avg(layer1+mean kind) sum', round(avg), 'mean', round(avg / n, 1))
kinds = collections.Counter()
for env, snap in []:
    pass
