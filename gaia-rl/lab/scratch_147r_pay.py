"""147r dump: which conversions E368 (_pay_kinds) would allow per target (read only)."""
import gzip, json, sys
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/baseline-teacher-20260917', 'gaia-rl/tools']
import teacher_patches as t

path = sys.argv[1]
d = json.load(gzip.open(path, 'rt'))
c = d['current']
s, p = c['state'], c['state']['players'][c['player']]
print('prune', sorted(t.prune_indices(c)))
for name, cost, big, built in t._pay_targets(s, p, c['candidates']):
    print(name, cost, sorted(t._pay_kinds(s, p, cost, big, built, c['candidates'])))
