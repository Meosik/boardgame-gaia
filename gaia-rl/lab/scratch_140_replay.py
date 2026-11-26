"""140-prune-one-game review (read-only): replay the logged choices from the seed, check each digest,
recompute prune_indices and tag every blocked candidate by rule; count chosen-blocked, candidates per round,
federations per seat at the end."""
import collections
import gzip
import json
import sys

import teacher_ab as ab
import teacher_patches as tp
from gaia_rl import Environment
from economy.teacher import BUILD_TYPES, RING

RUN = sys.argv[1]
rows = [json.loads(l) for l in gzip.open(RUN+'/decisions.jsonl.gz', 'rt')]
seed = json.load(open(RUN+'/result.json'))['seed']
env = Environment(seed, ab.MAX_DECISIONS)
snap = json.loads(env.snapshot_json())


def mine_rule(state, player, a):
    from economy.teacher import path_distance
    from four_factions.value import navigation
    coord = a['coord']
    kind = state['board']['hexes'][coord]['planet']['planet_type']
    starts = [s['hex'] for s in player['structures']]
    qic = max(0, (path_distance(state, starts, coord)-navigation(player)+1)//2) if starts else 0
    if kind == 'Gaia':
        return 'P4'
    if qic >= 2:
        return 'P2'
    steps = tp._terraform_steps(state, player, kind) or 0
    return 'P5' if player['faction'] == 'Gleens' and steps >= 1 else 'P1'


def fed_rule(state, player, a):
    if state['round'] < 6 and len(a.get('satellite_hexes') or []) >= 4:
        return 'F5'
    power = {str(s['hex']): tp._structure_power(s) for s in player['structures']}
    built = [power.get(str(h), 0) for h in a.get('hexes') or [] if power.get(str(h), 0)]
    return 'F2' if built and sum(built)-min(built) >= tp._fed_minimum(player) else 'F1'


bad_digest = chose_blocked = with_blocked = 0
kinds = collections.Counter()
by_round = collections.defaultdict(lambda: [0, 0, 0])
logged_mismatch = 0
consumed = 0
for r in rows:
    if ab.digest(snap) != r['digest']:
        print('DIGEST MISMATCH at step', r['step'], 'round', r['round'])
        bad_digest += 1
        break
    if (snap['decision_id'] != r['decision_id'] or len(snap['candidates']) != r['candidates']
            or snap['candidates'][r['index']] != r['chosen']):
        print('DIVERGE at step', r['step'], 'round', r['round'], 'ncand', len(snap['candidates']), r['candidates'],
              'logged', json.dumps(r['chosen'])[:200], 'kinds_here', sorted(collections.Counter(c['action'].get('type') for c in snap['candidates']).items()))
        break
    state, cands = snap['state'], snap['candidates']
    out = tp.prune_indices(snap)
    if len(out) != (r['prune_blocked'] or 0):
        logged_mismatch += 1
    player = state['players'][snap['player']] if snap.get('player') is not None else None
    for i in out:
        a = cands[i]['action']
        if a.get('type') == 'FormFederation':
            tag = fed_rule(state, player, a)
        elif isinstance(a.get('tech_tile_choice'), dict):
            tag = 'tile'
        else:
            tag = mine_rule(state, player, a)
        kinds[(state['round'], tag)] += 1
    with_blocked += bool(out)
    chose_blocked += r['index'] in out
    b = by_round[state['round']]
    b[0] += 1
    b[1] += len(cands)
    b[2] += len(out)
    env.step(r['decision_id'], r['index'])
    snap = json.loads(env.snapshot_json())
    consumed += 1
verified = bad_digest == 0 and consumed == len(rows) and env.is_terminal()
pre = '' if verified else 'UNVERIFIED '
print('REPLAY verified', verified, 'consumed', consumed, 'of', len(rows))
print('REPLAY rows', len(rows), 'digest_mismatch', bad_digest, 'terminal', env.is_terminal(),
      'logged_count_mismatch', logged_mismatch)
print(pre + 'REPLAY with_blocked', with_blocked, 'chose_blocked', chose_blocked)
print(pre + 'REPLAY kinds', sorted(kinds.items()))
print('REPLAY by_round (decisions, candidates, blocked)', dict(sorted(by_round.items())))
for seat, p in enumerate(snap['state']['players']):
    print('SEAT', seat, p['faction'], 'feds', len(p.get('federations') or []), 'vp', p.get('vp'))
