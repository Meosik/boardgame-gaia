"""E368: why terraforming power actions have many candidates - per decision, by id, remaining steps and QIC."""
import collections
import os
import sys

_r = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(_r, 'tools'), os.path.join(_r, 'python'), os.path.join(_r, 'experiments'), _r]
sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp
from economy.teacher import path_distance, RING
from four_factions.value import navigation

FREE = {2: 2, 6: 1}
worst = None
tot = collections.Counter()
for env, snap in t.play(rounds=3):
    st = snap['state']
    if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
        continue
    out = tp.prune_indices(snap)
    p = st['players'][snap['player']]
    starts = [s['hex'] for s in p['structures']]
    rows = []
    for i, c in enumerate(snap['candidates']):
        a = c['action']
        if i in out or a['type'] != 'PowerAction' or a.get('coord') is None:
            continue
        kind = st['board']['hexes'][a['coord']]['planet']['planet_type']
        steps = (tp._terraform_steps(st, p, kind) or 0) if kind in RING else 0
        qic = max(0, (path_distance(st, starts, a['coord']) - navigation(p) + 1) // 2)
        rows.append((a.get('id'), max(0, steps - FREE.get(a.get('id'), 0)), steps, qic, a['coord']))
    for r in rows:
        tot[(r[0], 'left%d' % r[1], 'qic%d' % r[3])] += 1
    if rows and (worst is None or len(rows) > len(worst[1])):
        worst = (st.get('round'), rows, p['faction'], p['research_tracks'].get('terraforming'), p['research_tracks'].get('navigation'))
print('3R total (id, steps left after free spades, qic):', sorted(tot.items(), key=lambda x: -x[1]))
r, rows, fac, tf, nav = worst
print('worst decision round', r, fac, 'tf', tf, 'nav', nav, 'n', len(rows), 'distinct hexes', len({x[4] for x in rows}))
print(' by (id, left, base steps, qic):', collections.Counter(x[:4] for x in rows).most_common())
