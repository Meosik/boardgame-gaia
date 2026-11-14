"""115d review: federations formed per seat (from the recorded `chosen`), and where a flag-off replay on the
work tree engine first leaves the recorded line (indirect evidence that the lab ran with the flag on)."""
import glob
import gzip
import json
from collections import Counter

from gaia_rl import Environment
from gaia_rl.versions import ENGINE_BUILD_ID

RUN = '/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-115d-fed-on-crash-seeds-full'
print('engine', ENGINE_BUILD_ID[:12])
for game in sorted(glob.glob(RUN + '/pair-*/game-*')):
    result = json.load(open(game + '/result.json'))
    rows = [json.loads(line) for line in gzip.open(game + '/decisions.jsonl.gz', 'rt')]
    feds = Counter()
    for row in rows:
        action = (row.get('chosen') or {}).get('action') or {}
        if action.get('type') == 'FormFederation':
            feds[result['factions'][row['seat']]] += 1
    print(game.split('/')[-2], result['seed'], 'scores', result.get('scores'), 'federations', dict(feds))
    env = Environment(result['seed'], 2000)
    fed_decisions = 0
    for step, row in enumerate(rows):
        snapshot = json.loads(env.snapshot_json())
        candidates = snapshot['candidates']
        off = sum(c['action'].get('type') == 'FormFederation' for c in candidates)
        fed_decisions += bool(off)
        same = row['index'] < len(candidates) and candidates[row['index']] == row['chosen']
        if not same:
            alt = [i for i, c in enumerate(candidates) if c == row['chosen']]
            print('  first off-replay mismatch at step', step, 'seat', row['seat'], 'recorded index', row['index'],
                  'flag-off list', len(candidates), 'flag-off federation candidates', off,
                  'chosen type', row['chosen'].get('action', {}).get('type'), 'chosen found at off index', alt[:3],
                  '| earlier decisions with federation candidates:', fed_decisions - bool(off))
            break
        env.step(row['decision_id'], row['index'])
    else:
        print('  flag-off replay matches the whole game', len(rows))
