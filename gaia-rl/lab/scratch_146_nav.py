"""146 known-bad 34: navigation 2 late for Firaks/Itars. Read only.

  scratch_146_nav.py <game dir> <seat> [<last round>]
For each decision of the seat up to <last round>: navigation level, QIC, knowledge; for every
Build/RoundBoosterTerraformBuild the distance to the nearest own structure (range need) and QIC paid;
and at each decision the number of legal Build candidates vs Build targets beyond range+0 QIC.
"""
import gzip
import json
import os
import sys
from pathlib import Path

LAB = Path.home()/'projects/gaia-lab/gaia-rl'
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python')]

RANGE = [1, 1, 2, 2, 3, 4]


def qr(c):
    q, r = c.split(',')
    return int(q), int(r)


def dist(a, b):
    (q1, r1), (q2, r2) = qr(a), qr(b)
    return (abs(q1-q2)+abs(r1-r2)+abs(q1+r1-q2-r2))//2


def main():
    game, seat = Path(sys.argv[1]), int(sys.argv[2])
    last = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    result = json.loads((game/'result.json').read_text())
    from gaia_rl import Environment
    env = Environment(result['seed'], 2000)
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows:
        snap = json.loads(env.snapshot_json())
        state = snap['state']
        if state['round'] > last:
            break
        if snap['player'] == seat and state['round'] >= 1:
            p = state['players'][seat]
            res = p['resources']
            nav = p['research_tracks']['navigation']
            action = snap['candidates'][row['index']]['action']
            own = [s['hex'] for s in p['structures']]
            builds = [c['action']['coord'] for c in snap['candidates'] if c['action'].get('type') == 'Build']
            far = [b for b in builds if min(dist(b, o) for o in own) > RANGE[nav]]
            line = (f"{row['step']} R{state['round']} nav {nav} q {res['qic']} k {res['knowledge']} ore {res['ore']} "
                    f"cr {res['credits']} builds {len(builds)} (need qic {len(far)}) {json.dumps(action)[:90]}")
            if action.get('type') in ('Build', 'RoundBoosterTerraformBuild') and 'coord' in action:
                d = min(dist(action['coord'], o) for o in own)
                line += f"  dist {d} range {RANGE[nav]}"
            print(line)
        env.step(row['decision_id'], row['index'])


if __name__ == '__main__':
    main()
