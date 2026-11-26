"""E368 smoke: run prune_indices on real action-phase snapshots (first non-conversion candidate played)."""
import json
import random

from gaia_rl import Environment
import teacher_patches as tp

env = Environment('24')
rng = random.Random(1)
seen = total = blocked = 0
for step in range(400):
    snap = json.loads(env.snapshot_json())
    if snap.get('player') is None or not snap['candidates']:
        break
    if 'ActionPhase' in str(snap['state'].get('phase')):
        convs = tp._prune_convs(snap['state'], snap['state']['players'][snap['player']], snap['candidates'])
        n = sum(c['action'].get('type') == 'FreeAction' for c in snap['candidates'])
        seen += 1
        total += n
        blocked += len(convs)
        tp.prune_indices(snap)
    choices = [i for i, c in enumerate(snap['candidates']) if c['action'].get('type') != 'FreeAction']
    env.step(snap['decision_id'], rng.choice(choices or [0]))
print(f'decisions={seen} free_actions={total} conv_blocked={blocked} round={snap["state"]["round"]}')
