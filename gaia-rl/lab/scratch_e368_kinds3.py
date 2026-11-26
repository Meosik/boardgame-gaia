"""E368 (ㄴ): break down PowerAction, Upgrade and FreeAction candidates after pruning (same 3R test game)."""
import collections
import sys

sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp

pa, up, fr = collections.Counter(), collections.Counter(), collections.Counter()
pa_max, up_places = 0, 0
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    out = tp.prune_indices(snap)
    keep = [c['action'] for i, c in enumerate(snap['candidates']) if i not in out]
    for a in keep:
        if a['type'] == 'PowerAction':
            pa[(a.get('id'), a.get('coord') is not None)] += 1
        elif a['type'] == 'Upgrade':
            up[(str(a.get('to'))[:20], a.get('tech_tile_choice') is not None)] += 1
        elif a['type'] == 'FreeAction':
            fr[a.get('kind')] += 1
    places = {a.get('coord') for a in keep if a['type'] == 'Upgrade'}
    up_places += len(places)
print('PowerAction (id, has coord)', sorted(pa.items(), key=lambda x: -x[1]))
print('Upgrade (to, has tile)', sorted(up.items(), key=lambda x: -x[1]), 'distinct upgrade places sum', up_places)
print('FreeAction', fr.most_common())
