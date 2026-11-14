"""Probe: what Environment.preview_state_json returns and what it costs per candidate (for outcome features)."""
import gzip
import json
import time

from gaia_rl import Environment

print(Environment.preview_state_json.__doc__)
print(Environment.fork.__doc__)
game = json.loads(open('gaia-rl/runs/bc-114/manifest.jsonl').readline())
rows = [json.loads(line) for line in gzip.open(game['game'] + '/decisions.jsonl.gz', 'rt')]
env = Environment(game['seed'], 2000)
spent = {'snapshot': 0.0, 'preview': 0.0, 'loads': 0.0}
previews = decisions = 0
for step, row in enumerate(rows[:120]):
    tick = time.perf_counter()
    snapshot = json.loads(env.snapshot_json())
    spent['snapshot'] += time.perf_counter()-tick
    for index in range(len(snapshot['candidates'])):
        tick = time.perf_counter()
        try:
            text = env.preview_state_json(snapshot['decision_id'], index)
        except TypeError as error:
            print('signature', error)
            raise
        mid = time.perf_counter()
        after = json.loads(text)
        spent['preview'] += mid-tick
        spent['loads'] += time.perf_counter()-mid
        previews += 1
    decisions += 1
    if step == 40:
        print('before keys', sorted(snapshot)[:12], '| after keys', sorted(after)[:12], 'chars', len(text))
        state = after.get('state', after)
        print('after state keys', sorted(state)[:20])
        player = state['players'][snapshot['player']]
        print('player keys', sorted(player))
        print('resources', player['resources'])
    env.step(row['decision_id'], row['index'])
print('decisions', decisions, 'previews', previews, {k: round(v, 2) for k, v in spent.items()},
      'ms per preview %.2f' % (1000*(spent['preview']+spent['loads'])/previews))
