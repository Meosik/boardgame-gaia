"""Read-only recount for the 133 review: federation tokens held at the end vs FormFederation actions, per seat.

Replays each game with the lab engine build (the run's build; the work tree build diverges) and prints, per seat,
the FormFederation count, the rounds they were formed in, the final score and the federation tokens in the final
state (tokens from other routes show as a difference).

  scratch_133_review.py <run dir> [--keys]
"""
import gzip
import json
import os
import sys
from collections import Counter
from pathlib import Path

LAB = Path('/home/sohegi/projects/gaia-lab/gaia-rl')
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(LAB/'python')]
from gaia_rl import ENGINE_BUILD_ID, Environment  # noqa: E402

run = Path(sys.argv[1])
print('engine', ENGINE_BUILD_ID[:8])
rows_out = []
for game_dir in sorted(run.glob('pair-*/game-*')):
    result = json.loads((game_dir/'result.json').read_text())
    if not result.get('complete'):
        print('INCOMPLETE', game_dir)
        continue
    env = Environment(result['seed'], 2000)
    formed = [[] for _ in result['factions']]
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        for line in f:
            row = json.loads(line)
            action = (row.get('chosen') or {}).get('action') or {}
            if action.get('type') == 'FormFederation':
                formed[row['seat']].append(row['round'])
            env.step(row['decision_id'], row['index'])
    state = json.loads(env.snapshot_json())['state']
    players = state['players']
    if '--keys' in sys.argv:
        print(sorted(players[0].keys()))
        print({k: v for k, v in players[0].items() if 'fed' in k.lower()})
        break
    for seat, faction in enumerate(result['factions']):
        player = players[seat]
        held = len(player['federation_tokens'])+len(player['gray_federation_tokens'])
        rows_out.append((game_dir.parent.name, seat, faction, len(formed[seat]), formed[seat], held,
                         result['scores'][str(seat)]))
        if held != len(formed[seat]) and '--tracks' in sys.argv:
            print('extra token', game_dir.parent.name, seat, faction, 'tracks', player['research_tracks'],
                  'artifacts', player['artifacts'], 'alliance', player['alliance_tiles'],
                  'green', player['federation_tokens'], 'gray', player['gray_federation_tokens'])
for row in rows_out:
    print(*row)
if rows_out:
    print('formed', sorted(Counter(r[3] for r in rows_out).items()), 'held', sorted(Counter(str(r[5]) for r in rows_out).items()))
    print('held != formed:', [(r[0], r[1], r[2], r[3], r[5]) for r in rows_out if r[5] != r[3]])
    print('seats >= 120 VP:', sum(r[6] >= 120 for r in rows_out), '| >= 100:', sum(r[6] >= 100 for r in rows_out))
    for count in (1, 2, 3):
        scores = [r[6] for r in rows_out if r[3] == count]
        if scores:
            print('formed', count, 'seats', len(scores), 'mean VP %.1f' % (sum(scores)/len(scores)))
