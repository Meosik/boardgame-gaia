"""Candidate composition by action type over 3 rounds of the test game (same as the 140a probe)."""
import collections
import sys

sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp

kinds, after, n = collections.Counter(), collections.Counter(), 0
sub = collections.Counter()
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    n += 1
    out = tp.prune_indices(snap)
    for i, c in enumerate(snap['candidates']):
        a = c['action']
        k = a.get('type')
        kinds[k] += 1
        if i not in out:
            after[k] += 1
        if k == 'FreeAction':
            sub[str(a.get('action') or a.get('kind') or sorted(a))[:40]] += 1
print('decisions', n, 'total', sum(kinds.values()), 'after', sum(after.values()))
for k, v in kinds.most_common():
    print(k, v, after[k])
print('free', sub.most_common(8))
