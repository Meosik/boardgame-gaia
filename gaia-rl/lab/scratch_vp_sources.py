"""Where the teacher's points come from (HANDOFF E170; user 2026-11-18 "150점은 나와야"): the 93 complete 6-round
self-play games of 114 + 119 replayed from seed + decision log; every VP change is booked to the acting seat's action
type, the end-of-game part is split into research tracks (4 VP per level 3/4/5, rulebook) and the rest (final goals +
leftover resources). Then, inside each (quartet, faction) cell, seats above the cell's median final score against the
others. A reading aid for candidates, not an effect estimate.
Usage: scratch_vp_sources.py probe   # one game: action types, VP by type, player keys
       scratch_vp_sources.py         # all games -> gaia-rl/runs/vp-sources-93/seats.json + tables"""
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = ['gaia-rl/python', 'gaia-rl/tools']
from gaia_rl import Environment

RUNS = Path('/home/sohegi/projects/gaia-lab/gaia-rl/runs')
SOURCES = ['lab-114-all-tier-selfplay-18f-full', 'lab-119-all-tier-selfplay-18f-full-more']
TRACKS = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')
PROBE = sys.argv[1:] == ['probe']
OUT = Path('gaia-rl/runs/vp-sources-93/seats.json')


def replay(game_dir, result):
    """Per seat: VP booked by the action type that changed it, and the end state."""
    env = Environment(result['seed'], 2000)
    booked = [Counter() for _ in range(4)]
    counts = [Counter() for _ in range(4)]
    snapshot = json.loads(env.snapshot_json())
    start = [player['vp'] for player in snapshot['state']['players']]
    rounds = [Counter() for _ in range(4)]
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as handle:
        for line in handle:
            row = json.loads(line)
            assert snapshot['decision_id'] == row['decision_id'], (game_dir, row['decision_id'])
            actor, kind = snapshot['player'], snapshot['candidates'][row['index']]['action']['type']
            before = [player['vp'] for player in snapshot['state']['players']]
            round_number = snapshot['state'].get('round')
            env.step(row['decision_id'], row['index'])
            snapshot = json.loads(env.snapshot_json())
            counts[actor][kind] += 1
            for seat, player in enumerate(snapshot['state']['players']):
                change = player['vp']-before[seat]
                if change:
                    booked[seat][kind if seat == actor else 'other seat: '+kind] += change
                    rounds[seat][round_number] += change
    assert env.is_terminal(), game_dir
    final = dict(env.final_scores())
    seats = []
    for seat, player in enumerate(snapshot['state']['players']):
        levels = [player['research_tracks'][track] for track in TRACKS]
        track_vp = sum(4*max(level-2, 0) for level in levels)
        end = final[seat]-player['vp']
        assert sum(booked[seat].values())+start[seat] == player['vp'], (game_dir, seat)
        seats.append({'faction': player['faction'], 'final': final[seat], 'start': start[seat],
                      'booked': dict(booked[seat]), 'end_tracks': track_vp, 'end_rest': end-track_vp,
                      'by_round': {str(key): value for key, value in rounds[seat].items()},
                      'actions': dict(counts[seat]),
                      'federations': len(player.get('federation_tokens', []))+len(player.get('gray_federation_tokens', [])),
                      'green_left': len(player.get('federation_tokens', [])),
                      'advanced': len(player.get('advanced_tech_tiles', [])),
                      'level5': sum(level >= 5 for level in levels), 'levels': levels})
    return seats, snapshot


rows = []
for source in SOURCES:
    for game_dir in sorted((RUNS/source).glob('pair-*/game-*')):
        result_file = game_dir/'result.json'
        if not result_file.exists():
            continue
        result = json.loads(result_file.read_text())
        if not result.get('complete'):
            continue
        seats, snapshot = replay(game_dir, result)
        seed, _, order = result['seed'].partition('@order=')
        order = [int(seat) for seat in order.split(',')] if order else list(range(4))
        for seat, row in enumerate(seats):
            assert row['final'] == result['scores'][str(seat)], (game_dir, seat)
            row.update(source=source[4:7], seed=seed, quartet=seed.rsplit('-', 1)[0], seat=seat,
                       turn=order.index(seat), rank=sorted((-other['final'] for other in seats)).index(-row['final'])+1)
            rows.append(row)
        if PROBE:
            player = snapshot['state']['players'][0]
            print('player keys', sorted(player))
            print('state keys', sorted(snapshot['state']))
            for row in seats:
                print(row['faction'], row['final'], 'start', row['start'], 'booked', row['booked'],
                      'tracks', row['end_tracks'], 'rest', row['end_rest'], 'by round', row['by_round'])
            sys.exit(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(rows))
print('games', len(rows)//4, 'seats', len(rows), '->', OUT)
print('action types with VP', sorted({kind for row in rows for kind in row['booked']}))
