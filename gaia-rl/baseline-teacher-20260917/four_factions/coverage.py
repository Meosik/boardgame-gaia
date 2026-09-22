"""Diagnostic steering to native rare phases, NOT demonstrations or score evidence."""
import json
import random

import numpy as np
from gaia_rl._native import Environment
from gaia_rl.encoding import FeatureEncoder
from current_actions.conservation import blocked
from four_factions.teacher import NativeFactionTeacher
from strategy_teacher import distance


def probe(spec, faction):
    env = Environment(spec['seed'], 2000)
    policy = NativeFactionTeacher().bind(env)
    encoder = FeatureEncoder()
    seat = spec['factions'].index(faction)
    rng = random.Random(spec['seed']+':rare-phase-coverage')
    actions, checks, roots = [], [], []
    target = 'TerransGaiaConversion' if faction == 'Terrans' else 'TaklonsChargePower'
    formed = False
    while not env.is_terminal():
        snapshot = json.loads(env.snapshot_json())
        actor = snapshot['player']
        if actor == seat:
            original = env.snapshot_json()
            scores = policy.rank(snapshot)
            assert env.snapshot_json() == original
            encoded = encoder.encode(snapshot, actor)
            assert np.isfinite(encoded['observation']).all() and np.isfinite(encoded['candidates']).all()
            index = max((i for i, score in enumerate(scores) if not blocked(score)),
                        key=lambda i: (scores[i][0], -i))
            if any(c['action']['type'] == target for c in snapshot['candidates']):
                checks.append(target)
                roots.append({'decision': len(actions), 'snapshot': snapshot, 'scores': scores})
                return {'faction': faction, 'seed': spec['seed'], 'checks': checks, 'actions': actions, 'roots': roots,
                        'diagnostic_only': True, 'complete_game': False}
            # Deliberately force native-legal PI/project opportunities solely to
            # exercise ability decisions. Never include this trace in BC data.
            player = snapshot['state']['players'][seat]
            pi = any(s['kind'] == 'PlanetaryInstitute' for s in player['structures'])
            station = any(s['kind'] == 'TradingStation' for s in player['structures'])
            action_phase = isinstance(snapshot['state']['phase'], dict) and 'ActionPhase' in snapshot['state']['phase']
            preferred = [i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'Upgrade'
                         and c['action'].get('to') == 'PlanetaryInstitute' and not blocked(scores[i])]
            if not pi and not station:
                preferred += [i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'Upgrade'
                              and c['action'].get('to') == 'TradingStation' and not blocked(scores[i])]
            if faction == 'Terrans' and pi and not formed:
                preferred += [i for i, c in enumerate(snapshot['candidates'])
                              if c['action']['type'] == 'GaiaFormation' and not blocked(scores[i])]
            if faction == 'Taklons' and pi:
                preferred += [i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'FreeAction'
                              and c['action']['kind'] == 'PowerToCredit' and not blocked(scores[i])]
            if action_phase and (not pi or faction == 'Terrans' and formed):
                # Wait for actual income instead of spending PI funding on a lab.
                preferred += [i for i, c in enumerate(snapshot['candidates']) if c['action']['type'] == 'Pass']
            if preferred:
                index = preferred[0]
        else:
            index = rng.randrange(len(snapshot['candidates']))
            if faction == 'Taklons':
                neighbors = [i for i, c in enumerate(snapshot['candidates'])
                             if c['action']['type'] in ('Build', 'Upgrade')
                             and any(distance(c['action']['coord'], s['hex']) <= 2
                                     for s in snapshot['state']['players'][seat]['structures'])]
                if neighbors:
                    index = neighbors[0]
        action = snapshot['candidates'][index]['action']
        if actor == seat and action['type'] == 'GaiaFormation':
            formed = True
        actions.append(action)
        env.step(snapshot['decision_id'], index)
    raise RuntimeError(f'Native diagnostic game ended without {target}; do not claim rare-phase coverage')
