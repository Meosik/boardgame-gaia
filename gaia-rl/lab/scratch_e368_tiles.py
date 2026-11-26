"""E368: upgrade candidates with a tech tile choice - per decision: places, distinct tiles, track variants."""
import collections
import os
import sys

_r = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_r, 'tools'), os.path.join(_r, 'python'), os.path.join(_r, 'experiments'), _r]
sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp

rows = []
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    out = tp.prune_indices(snap)
    ups = [c['action'] for i, c in enumerate(snap['candidates'])
           if i not in out and c['action']['type'] == 'Upgrade' and c['action'].get('tech_tile_choice')]
    if not ups:
        continue
    places = {a.get('coord') for a in ups}
    tiles = collections.Counter(str(a['tech_tile_choice'].get('tile')) + '/' + str(a['tech_tile_choice'].get('kind')) for a in ups)
    rows.append((st.get('round'), st['players'][snap['player']]['faction'], len(ups), len(places), len(tiles), tiles.most_common(3)))
print('decisions', len(rows), 'cands', sum(r[2] for r in rows))
for r in rows:
    print(r)
