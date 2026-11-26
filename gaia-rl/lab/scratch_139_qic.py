"""139: replay R1, QIC/nav use on each new mine + BalTaks R1 actions (read-only)."""
import json, gzip, collections
from pathlib import Path
from gaia_rl import Environment
import teacher_patches as tp
from strategy_teacher import distance

R9 = Path('/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-139-r1-placement-sim-20')
MINE = {'Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'EclipseAsteroidMine', 'SpaceGiantsBuildMine',
        'GleensBuildMine', 'TwilightRangeBuild', 'SpaceshipCreditTerraform', 'TinkeroidsUseTile', 'PowerAction'}
RANGE = ('RoundBoosterRangeBuild', 'TwilightRangeBuild')
out = collections.Counter(); shown = False; bal = []
for res in sorted(R9.glob('pair-*/game-*/result.json')):
    r = json.loads(res.read_text()); env = Environment(r['seed'], 2000)
    rows = [json.loads(l) for l in gzip.open(res.parent/'decisions.jsonl.gz', 'rt')]
    for row in rows:
        st = json.loads(env.snapshot_json())['state']
        a = row['chosen'].get('action', {}); t = a.get('type'); seat = int(row['seat'])
        p = st['players'][seat]
        if not shown:
            print('player keys:', sorted(p)); shown = True
        if p['faction'] == 'BalTaks' and row['chosen'].get('phase') == 'Game' and t != 'ChargePower':
            bal.append((res.parent.parent.name, t, json.dumps(a)[:90]))
        snap = json.loads(env.snapshot_json())
        idx = next((i for i, c in enumerate(snap['candidates']) if c == row['chosen'] or c.get('action') == row['chosen']), None)
        if idx is None:
            print('NOMATCH', res.parent.parent.name, row['step'], json.dumps(snap['candidates'][0])[:150]); out['replay fail game'] += 1; break
        try:
            env.step(snap['decision_id'], idx)
        except RuntimeError as e:
            print('FAIL', res.parent.parent.name, row['step'], t, e); out['replay fail game'] += 1; break
        if t in MINE and a.get('coord'):
            own = [s['hex'] for s in p['structures'] if s.get('hex')]
            d = min((distance(a['coord'], o) for o in own), default=0)
            q0 = p.get('qic', p.get('resources', {}).get('qic'))
            p1 = json.loads(env.snapshot_json())['state']['players'][seat]
            q1 = p1.get('qic', p1.get('resources', {}).get('qic'))
            reach = tp._reach(p)
            if t in RANGE:
                key = 'range-action'
            elif d <= reach:
                key = 'in reach (reach %d, distance %d)' % (reach, d)
            else:
                key = 'beyond reach %d: qic spent %s' % (reach, None if q0 is None else q0 - q1)
            out[key] += 1
for k, v in sorted(out.items()): print(v, k)
for b in bal: print(*b)
