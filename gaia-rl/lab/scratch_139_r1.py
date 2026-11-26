"""139 R1 mines per seat vs 138 setup (read-only). Board/home from 138 setup_state.json (same seed = same map)."""
import json, gzip, glob, collections
from pathlib import Path
import setup_report as sr
from strategy_teacher import distance
from faction_teachers.profiles import profiles

R9 = Path('/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-139-r1-placement-sim-20')
R8 = Path('/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-138-setup-placement-sim-20')
MINE = {'Build', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'EclipseAsteroidMine', 'SpaceGiantsBuildMine',
        'GleensBuildMine', 'TwilightRangeBuild', 'SpaceshipCreditTerraform', 'TinkeroidsUseTile', 'PowerAction',
        'IvitsPlaceSpaceStation', 'RebellionFreeTradingStation'}
s138 = {}
for p in R8.glob('**/setup_state.json'):
    seed = json.loads((p.parent/'result.json').read_text()).get('seed')
    s138[seed] = json.loads(p.read_text())
same = 0; tot_mines = collections.Counter(); hist = collections.Counter(); qic = 0; nmine = 0; steps = collections.Counter()
types = collections.Counter(); seats_same = 0; far = collections.Counter()
for res in sorted(R9.glob('pair-*/game-*/result.json')):
    r = json.loads(res.read_text()); st = s138.get(r['seed'])
    dec = [json.loads(l) for l in gzip.open(res.parent/'decisions.jsonl.gz', 'rt')]
    if st is None:
        print(res.parent.parent.name, 'no 138 state'); continue
    hexes = st['board']['hexes']
    place = collections.defaultdict(list); mines = collections.defaultdict(list)
    for d in dec:
        a = d['chosen']; act = a.get('action', {}); t = act.get('type'); seat = int(d['seat'])
        if t == 'PlaceStartingStructure':
            place[seat].append(act['coord'])
        elif t in MINE and act.get('coord'):
            mines[seat].append((t, act['coord']))
    g_same = True; line = []
    for seat, pl in enumerate(st['players']):
        own138 = sorted(s['hex'] for s in pl['structures'] if s.get('hex'))
        ok = sorted(place[seat]) == own138
        seats_same += ok; g_same &= ok
        prof = profiles().get(pl['faction']); home = prof.home if prof else None
        own = list(place[seat]); cells = []
        for t, c in mines[seat]:
            kind = (hexes.get(c, {}).get('planet') or {}).get('planet_type')
            dist = min((distance(c, o) for o in own), default=None)
            stp = sr._steps(home, kind)
            cells.append('%s%s/d%s%s' % (kind[:4] if kind else '?', '' if stp is None else stp, dist, '' if t == 'Build' else '[' + t[:10] + ']'))
            own.append(c); types[t] += 1
            if t in ('IvitsPlaceSpaceStation', 'RebellionFreeTradingStation'):
                continue
            nmine += 1; steps[kind if (kind in sr.SPECIAL or kind == 'Asteroid' or home is None) else stp] += 1
            if t not in ('RoundBoosterRangeBuild', 'TwilightRangeBuild'):
                far[min(dist or 0, 4)] += 1
        hist[sum(t not in ('IvitsPlaceSpaceStation', 'RebellionFreeTradingStation') for t, _ in mines[seat])] += 1
        line.append('%s %d%s:%s' % (pl['faction'][:6], len(mines[seat]), '' if ok else '*', ','.join(cells)))
    same += g_same
    print(res.parent.parent.name, ' | '.join(line))
print('games same setup as 138:', same, '/20; seats same:', seats_same, '/80')
print('R1 mines per seat hist:', dict(sorted(hist.items())), 'total', nmine, 'dist (non range-booster) 0..4+:', dict(sorted(far.items())))
print('steps:', dict(steps)); print('types:', dict(types))
