"""Which decisions of the 114 / 119 games list more candidates than the encoder capacity (2048)? Replays the indexed
games without encoding (queue 121 failed in the 119 export with `Candidate capacity exceeded`)."""
import collections
import json
import os
import sys
from pathlib import Path

os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/tools']
import bc_dataset
from gaia_rl import Environment

CAPACITY = 2048
for name in sys.argv[1:]:
    manifest = f'gaia-rl/runs/bc-{name}-fc19/manifest.jsonl'
    decisions = over = largest = 0
    sizes = []
    for number, game in enumerate(bc_dataset._load(manifest)):
        env = Environment(game['seed'], 2000)
        for step, row in enumerate(bc_dataset._rows(Path(game['game']))):
            snapshot = json.loads(env.snapshot_json())
            seat = snapshot.get('player')
            if seat is not None:
                n = len(snapshot['candidates'])
                sizes.append(n)
                if n > CAPACITY:
                    over += 1
                    first = snapshot['candidates'][0]
                    kinds = collections.Counter(
                        str((c.get('action') or {}).get('type')) if isinstance(c, dict) else type(c).__name__
                        for c in snapshot['candidates'])
                    chosen = snapshot['candidates'][row['index']]
                    print(json.dumps({'manifest': name, 'game': number, 'seed': game['seed'], 'step': step,
                                      'decision': decisions, 'round': snapshot['state'].get('round'), 'seat': seat,
                                      'faction': game['factions'][seat], 'candidates': n,
                                      'kinds': kinds.most_common(4), 'chosen': str(chosen)[:160],
                                      'first': str(first)[:160]}, ensure_ascii=False), flush=True)
                decisions += 1
            env.step(row['decision_id'], row['index'])
    sizes.sort()
    print(name, 'games', number+1, 'decisions', decisions, 'over capacity', over, 'largest', sizes[-1],
          'over 1024:', sum(n > 1024 for n in sizes), 'p99', sizes[int(len(sizes)*0.99)], flush=True)
