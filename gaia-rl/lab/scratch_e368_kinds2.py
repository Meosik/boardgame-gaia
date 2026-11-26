"""E368 (ㄴ): which kind is largest after pruning, and its size per decision (same 3R test game)."""
import collections
import sys

sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp

tot, mx, largest, sample = collections.Counter(), collections.Counter(), collections.Counter(), {}
n = 0
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    n += 1
    out = tp.prune_indices(snap)
    by = collections.Counter()
    for i, c in enumerate(snap['candidates']):
        if i in out:
            continue
        k = c['action'].get('type')
        by[k] += 1
        sample.setdefault(k, str(c['action'])[:160])
    for k, v in by.items():
        tot[k] += v
        mx[k] = max(mx[k], v)
    largest[by.most_common(1)[0][0]] += 1
print('decisions', n)
for k, v in tot.most_common():
    print(k, 'sum', v, 'max', mx[k], 'largest_in', largest[k])
for k, s in sample.items():
    print('eg', s)
