"""146 known-bad 35-37: federation choices. Read only.

  scratch_146_feds.py <game dir> <step> [<step> ...]
At each step: the seat's structures with power, gaiaformer/forming hexes, the chosen FormFederation
(buildings, power, satellites) and the legal FormFederation candidates grouped by
(satellites, buildings, power) with the cheapest ones listed.
"""
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python'), str(LAB/'baseline-teacher-20260917'), str(LAB/'tools')]

BASE = {'Mine': 1, 'TradingStation': 2, 'ResearchLab': 2, 'PlanetaryInstitute': 3, 'Academy': 3}


def kind(k):
    return k if isinstance(k, str) else next(iter(k))


def power(player, k):
    name = kind(k)
    active = set(player['tech_tiles']) - set(player['covered_tech_tiles'])
    return BASE.get(name, 0) + int(name in ('PlanetaryInstitute', 'Academy') and 6 in active)


def describe(player, action):
    own = {s['hex']: s['kind'] for s in player['structures']}
    hexes = action['hexes']
    pw = sum(power(player, own[h]) for h in hexes if h in own)
    other = [h for h in hexes if h not in own]
    return len([h for h in hexes if h in own]), pw, len(action.get('satellite_hexes') or []), other


def main():
    game = Path(sys.argv[1])
    steps = {int(s) for s in sys.argv[2:]}
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows:
        if row['step'] > max(steps):
            break
        if row['step'] in steps:
            snap = json.loads(env.snapshot_json())
            state, seat = snap['state'], snap['player']
            p = state['players'][seat]
            print(f"== step {row['step']} R{state['round']} seat {seat} {p['faction']} tech {p['tech_tiles']} "
                  f"res ore {p['resources']['ore']} cr {p['resources']['credits']} pw {p['resources']['power']}")
            print('  structures', [(s['hex'], kind(s['kind']), power(p, s['kind'])) for s in p['structures']],
                  'federated', p['federated_hexes'])
            forming = []

            def find(node, path):
                if isinstance(node, dict):
                    text = json.dumps({k: v for k, v in node.items() if not isinstance(v, (dict, list))})
                    if ('gaia' in text.lower() or 'former' in text.lower()) and ('hex' in node or 'coord' in node):
                        forming.append((path, text[:200]))
                    for k, v in node.items():
                        find(v, f'{path}.{k}')
                elif isinstance(node, list):
                    for j, v in enumerate(node):
                        find(v, f'{path}[{j}]')
            find(state['board'], 'board')
            for f in forming[:12]:
                print('  gaia?', f)
            chosen = snap['candidates'][row['index']]['action']
            print('  chosen', describe(p, chosen), json.dumps(chosen)[:300])
            feds = [c['action'] for c in snap['candidates'] if c['action'].get('type') == 'FormFederation']
            groups = Counter(describe(p, a)[:3] for a in feds)
            print('  legal feds', len(feds), '(buildings, power, satellites) -> count:',
                  sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][0]))[:15])
            best = sorted(feds, key=lambda a: (describe(p, a)[2], describe(p, a)[0]))[:4]
            for a in best:
                print('   cheap', describe(p, a), a['hexes'], 'sat', a.get('satellite_hexes'), 'token', a.get('token'))
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
