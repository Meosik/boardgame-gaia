"""Outcome features for the 114 BC samples (HANDOFF E147 (ㄱ) test, not an encoder): for every candidate of every
decision, what the state looks like right after it (Environment.preview_state_json, no search, no opponent move)
minus the state before - the acting player's numeric fields (resources, power bowls, tracks, VP, flags, list
lengths: tiles, tokens, federated hexes, structures), the other players' summed VP / bowl / resource change, and
whether the same player moves again, the round, the phase and the used power actions changed.
Rows follow the bc_dataset export order (manifest order, one row per candidate), so they line up with the
concatenated `cand` rows of gaia-rl/runs/bc-114-shards. Output: gaia-rl/runs/bc-114-outcome/outcome.npz."""
import gzip
import json
import os
import time

import numpy as np

from gaia_rl import Environment

WIDTH = 96            # actor columns; grows by first appearance, fatal when exceeded
OTHERS = ('vp', 'bowl1', 'bowl2', 'bowl3', 'goods')
GLOBALS = ('same_player', 'round', 'phase_changed', 'power_actions')


def flat(node, path, out):
    if isinstance(node, (bool, int, float)):
        out[path] = float(node)
    elif isinstance(node, list):
        out[path+'#'] = float(len(node))
    elif isinstance(node, dict):
        for key, child in node.items():
            flat(child, f'{path}.{key}' if path else key, out)
    return out


def others(state, actor):
    total = [0.0]*len(OTHERS)
    for player in state['players']:
        if player['player_id'] != actor:
            res = player['resources']
            total[0] += player['vp']
            total[1] += res['power']['bowl1']
            total[2] += res['power']['bowl2']
            total[3] += res['power']['bowl3']
            total[4] += res['ore']+res['credits']+res['knowledge']+res['qic']
    return total


columns = {}
rows_out, counts = [], []
start = time.time()
games = [json.loads(line) for line in open('gaia-rl/runs/bc-114/manifest.jsonl')]
for game in games:
    if not game['replays']:
        continue
    env = Environment(game['seed'], 2000)
    for row in (json.loads(line) for line in gzip.open(game['game']+'/decisions.jsonl.gz', 'rt')):
        snapshot = json.loads(env.snapshot_json())
        actor = snapshot.get('player')
        if actor is not None:
            state = snapshot['state']
            me = next(p for p in state['players'] if p['player_id'] == actor)
            before, before_others = flat(me, '', {}), others(state, actor)
            block = np.zeros((len(snapshot['candidates']), WIDTH+len(OTHERS)+len(GLOBALS)), dtype=np.float32)
            for index in range(len(snapshot['candidates'])):
                after = json.loads(env.preview_state_json(snapshot['decision_id'], index))
                mine = flat(next(p for p in after['players'] if p['player_id'] == actor), '', {})
                for key in mine.keys() | before.keys():
                    delta = mine.get(key, 0.0)-before.get(key, 0.0)
                    if delta:
                        column = columns.setdefault(key, len(columns))
                        if column >= WIDTH:
                            raise RuntimeError(f'more than {WIDTH} actor columns: {key}')
                        block[index, column] = delta
                block[index, WIDTH:WIDTH+len(OTHERS)] = np.subtract(others(after, actor), before_others)
                block[index, WIDTH+len(OTHERS):] = (after.get('current_player') == actor,
                                                    after['round']-state['round'],
                                                    after['phase'] != state['phase'],
                                                    len(after['used_power_actions'])-len(state['used_power_actions']))
            rows_out.append(block)
            counts.append(len(block))
        env.step(row['decision_id'], row['index'])
outcome = np.clip(np.concatenate(rows_out), -30, 30).astype(np.float16)
names = sorted(columns, key=columns.get)+['']*(WIDTH-len(columns))+['others.'+n for n in OTHERS]+list(GLOBALS)
os.makedirs('gaia-rl/runs/bc-114-outcome', exist_ok=True)
np.savez_compressed('gaia-rl/runs/bc-114-outcome/outcome.npz', outcome=outcome, counts=np.array(counts),
                    names=np.array(names))
used = np.abs(outcome).max(axis=0) > 0
print('decisions', len(counts), 'candidate rows', len(outcome), 'actor columns', len(columns), 'columns ever non-zero',
      int(used.sum()), 'seconds', round(time.time()-start))
print('rows with no change at all: %.3f' % float((np.abs(outcome[:, :WIDTH+len(OTHERS)]).max(axis=1) == 0).mean()))
print('actor columns:', ' '.join(sorted(columns, key=columns.get)))
