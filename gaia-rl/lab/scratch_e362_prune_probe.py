"""E362 probe (lab command, read-only): (1) run the pruning filter over 3 rounds of an easy game and
count candidates before/after by family; (2) draw a random map seed and pick the four base factions
that fit it best (planets within 3 hexes of a home-type hex at 0-1 terraforming steps, plus Gaia /
transdim planets for factions whose guide tracks include Gaia; Gleens count only 0-step and Gaia)."""
import collections
import json
import random
import sys

sys.argv = sys.argv[:1]
import test_teacher_patches as t
import teacher_patches as tp
from gaia_rl import Environment
from economy.teacher import RING

BASE = ['Terrans', 'Lantids', 'Xenos', 'Gleens', 'Taklons', 'Ambas', 'HadschHallas', 'Ivits',
        'Geodens', 'BalTaks', 'Itars', 'Nevlas', 'Firaks', 'Bescods']


def probe():
    totals = collections.Counter()
    decisions, rows = 0, []
    for env, snap in t.play(rounds=3):
        st = snap['state']
        if snap.get('player') is None or 'ActionPhase' not in str(st.get('phase')):
            continue
        decisions += 1
        out = tp.prune_indices(snap)
        n = len(snap['candidates'])
        totals['before'] += n
        totals['after'] += n-len(out)
        for i in out:
            a = snap['candidates'][i]['action']
            fam = 'fed' if a.get('type') == 'FormFederation' else ('tile' if 'tech_tile_choice' in a else 'mine')
            totals['cut_'+fam] += 1
        rows.append((n, n-len(out), st['round'], st['players'][snap['player']]['faction']))
    rows.sort(reverse=True)
    print('PROBE decisions', decisions, json.dumps(dict(totals)))
    print('PROBE largest (before, after, round, faction)', rows[:10])


def fit(state, faction):
    player = {'faction': faction}
    home = tp._home_type(player)
    hexes = state['board']['hexes']
    planets = {c: h['planet']['planet_type'] for c, h in hexes.items() if h.get('planet')}
    gaia_rider = faction in tp.GAIA_RIDERS
    best = 0.0
    for c, kind in planets.items():
        if kind != home:
            continue
        score = 0.0
        for d, other in planets.items():
            if d == c or tp._value.distance(c, d) > 3:
                continue
            if other in RING:
                steps = tp._terraform_steps(state, player, other)
                if steps == 0 or (steps == 1 and faction != 'Gleens'):
                    score += 1
            elif other in ('Gaia', 'Transdim') and (gaia_rider or faction == 'Gleens'):
                score += 1 if other == 'Gaia' else .5
        best = max(best, score)
    return best


def pick():
    seed = f'e362-{random.SystemRandom().randrange(10**6)}'
    state = json.loads(Environment(seed, 2000).snapshot_json())['state']
    scores = sorted(((fit(state, f), f) for f in BASE), reverse=True)
    chosen, homes = [], set()
    for s, f in scores:
        h = tp._home_type({'faction': f})
        if h in homes:
            continue
        chosen.append(f)
        homes.add(h)
        if len(chosen) == 4:
            break
    print('PICK seed', seed)
    print('PICK scores', [(f, s) for s, f in scores])
    print('PICK factions', ','.join(chosen))
    print('PICK seedarg', f'{seed}@factions={",".join(chosen)}')


def check_factory(rounds=1):
    """The prune factory's own choices (search on, easy budget) never pick a blocked candidate."""
    import budget_teacher
    budget_teacher.install(0)
    budget_teacher.set_horizon(2)
    env = Environment(t.SEED, 2000)
    teacher = tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier_prune(
        t.SEED, bgg_openings=True, shared_factions=True)
    teacher.bind(env)
    snap = json.loads(env.snapshot_json())
    checked = blocked_decisions = bad = 0
    while not env.is_terminal() and snap['state']['round'] <= rounds:
        out = tp.prune_indices(snap)
        decision_id, index = teacher.choose(snap)
        checked += 1
        blocked_decisions += bool(out)
        bad += index in out
        before = snap
        env.step(decision_id, index)
        snap = json.loads(env.snapshot_json())
        teacher.observe(before, index, snap)
    print('FACTORY decisions', checked, 'with_blocked', blocked_decisions, 'chose_blocked', bad)


if __name__ == '__main__':
    pick()
    probe()
    check_factory()
