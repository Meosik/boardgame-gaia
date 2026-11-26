"""In-memory pattern summary of 138 setup states (no files written under the run dir)."""
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
import setup_report as sr

run = Path(sys.argv[1])
games = [sr.game_report(p) for p in sorted(run.glob('**/setup_state.json'))]
print('games', len(games))
by_fac = defaultdict(list)
pair_d, adds, opp, steps, qic, near, dist_vs_add = [], [], [], Counter(), 0, 0, defaultdict(list)
top_kind = Counter()
nsites = 0
for g in games:
    for s in g['seats']:
        pw = s['pairwise_distance']
        a = s['added_planets']
        og = [v for v in s['min_distance_to_opponent'].values() if v is not None]
        by_fac[s['faction']].append((pw, a['second_adds'] if a else None, min(og) if og else None, s['reach'],
                                     len(s['free_planets_in_reach'][s['structures'][0]]) if s['structures'] else None))
        pair_d += pw
        if a:
            adds.append(a['second_adds'])
            if pw:
                dist_vs_add[pw[0]].append(a['second_adds'])
        if og:
            opp.append(min(og))
        for t in s['top_sites']:
            nsites += 1
            steps['spec:'+t['planet'] if t['steps'] is None else t['steps']] += 1
            qic += t['qic']
            near += t['near_opponent']
print('own pairwise distance', sorted(Counter(pair_d).items()))
print('2nd adds dist', sorted(Counter(adds).items()), 'overlap(0-1)', sum(x <= 1 for x in adds), '/', len(adds))
print('min opp distance', sorted(Counter(opp).items()))
print('top sites', nsites, 'steps', sorted(steps.items(), key=str), 'qic', qic, 'near', near)
print('dist -> 2nd adds mean', {d: (round(mean(v), 1), len(v)) for d, v in sorted(dist_vs_add.items())})
print('faction: n | own dist mean | 2nd adds mean | min opp mean | reach | free in reach of 1st')
for f, rows in sorted(by_fac.items()):
    d = [x for r in rows for x in r[0]]
    ad = [r[1] for r in rows if r[1] is not None]
    op = [r[2] for r in rows if r[2] is not None]
    fr = [r[4] for r in rows if r[4] is not None]
    print(f, len(rows), round(mean(d), 1) if d else '-', round(mean(ad), 1) if ad else '-',
          round(mean(op), 1) if op else '-', sorted({r[3] for r in rows}), round(mean(fr), 1) if fr else '-')
