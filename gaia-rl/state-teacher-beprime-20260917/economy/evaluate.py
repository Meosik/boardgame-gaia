"""Eight matched teacher-only games. No learning or historical artifact overwrites."""
import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'gaia-rl/experiments'))
sys.path.insert(0, str(ROOT/'gaia-rl/tools'))
from economy.teacher import EconomyTeacher, construction_cost, neighbors, origins, steps_for, path_distance
from strategy_teacher import TARGETS
from gaia_rl._native import Environment
from gaia_rl.versions import require_current_sources, require_compatible_versions
from replay_log import add_decision_log


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)


def digest(paths):
    return hashlib.sha256(b''.join(p.read_bytes() for p in sorted(paths))).hexdigest()


def tokens(player):
    return sum(player['resources']['power'][key] for key in ('bowl1', 'bowl2', 'bowl3'))


def inspect_decision(before, after, actor, action):
    player = before['players'][actor]
    cost = construction_cost(before, player, action)
    t = action['type']
    row = {'round': before['round'], 'action': action, 'cost': asdict(cost) if cost else None}
    if cost and action.get('coord'):
        row['opponent_neighbor'] = bool(neighbors(before, player, action['coord']))
        # Tech acquisition may grant resources. Verify only unambiguous construction debits.
        if t != 'TwilightFreeResearchLab' and (t != 'Upgrade' or action['to'] == 'TradingStation'):
            observed = {k: player['resources'][k]-after['players'][actor]['resources'][k]
                        for k in ('ore', 'credits', 'qic')}
            expected = {k: getattr(cost, k) for k in observed}
            if t == 'SpaceshipCreditTerraform' and player['resources']['credits'] < cost.credits:
                # Existing validator checks activation and mine separately, then saturates.
                # Keep the nominal ranking cost; expose the underpayment rather than hiding it.
                row['engine_cost_anomaly'] = {'expected_credits': cost.credits,
                    'paid_credits': observed['credits'], 'reason': 'TFMars activation and mine not validated together'}
                expected['credits'] = player['resources']['credits']
            if observed != expected:
                raise ValueError(f'Construction estimate differs from actual debit: {action}: {expected} != {observed}')
            row['cost_verified'] = True
    if t == 'FormFederation':
        row.update(satellites=len(action['satellite_hexes']), power_before=tokens(player),
                   power_after= tokens(after['players'][actor]))
    if t == 'PlaceStartingStructure':
        row['opponent_neighbor'] = bool(neighbors(before, player, action['coord']))
        counts = Counter()
        for coord, cell in before['board']['hexes'].items():
            planet = cell['planet']
            if not planet or planet['owner'] is not None or coord == action['coord']:
                continue
            distance = path_distance(before, [action['coord']], coord)
            steps = steps_for(player, planet)
            if 1 <= distance <= 3 and steps in (0, 1) and planet['planet_type'] in ('Terra','Oxide','Volcanic','Desert','Swamp','Titanium','Ice'):
                counts[f'{steps}_step_at_distance_{distance}'] += 1
        row['nearby_planets'] = dict(counts)
    return row


def metrics(choices):
    costs = [c for c in choices if c['cost']]
    ts = [c for c in costs if c['action']['type'] == 'Upgrade' and c['action']['to'] == 'TradingStation']
    terraform = [c for c in costs if c['cost']['terraform_steps']]
    federations = [c for c in choices if c['action']['type'] == 'FormFederation']
    placements = [c for c in choices if c['action']['type'] == 'PlaceStartingStructure']
    return {'paid_trading_stations': len(ts), 'six_credit_trading_stations': sum(c['cost']['credits'] == 6 for c in ts),
            'paid_terraform_builds': len(terraform), 'three_ore_step_builds': sum(c['cost']['terraform_ore'] == 3*c['cost']['terraform_steps'] for c in terraform),
            'construction_actions': len(costs), 'construction_with_neighbor': sum(c['opponent_neighbor'] for c in costs),
            'cost_debits_verified': sum(c.get('cost_verified', False) for c in costs),
            'engine_cost_anomalies': sum('engine_cost_anomaly' in c for c in costs),
            'starting_mines': len(placements), 'starting_mines_with_neighbor': sum(c['opponent_neighbor'] for c in placements),
            'federations': len(federations), 'satellites': sum(c['satellites'] for c in federations),
            'federation_details': [{k: c[k] for k in ('step','round','satellites','power_before','power_after')} for c in federations]}


def historical_rows(saved, manifest):
    rows = []
    for index, original in enumerate(saved):
        path = ROOT/f'gaia-frontend/public/ai-replays/teacher-{index}.json.gz'
        replay = json.load(gzip.open(path))
        meta = replay['metadata']
        if any(meta[key] != value for key, value in {'seed': original['seed'], 'faction': original['faction'],
                'focus_player': original['seat'], 'scores': original['scores'], 'steps': original['steps'],
                'versions': manifest['versions'], 'experiment_hash': manifest['experiment_hash'], 'reproduced_original': True}.items()):
            raise ValueError('Historical replay does not match evaluation')
        choices = []
        for before, after in zip(replay['frames'], replay['frames'][1:]):
            if after['player'] == original['seat']:
                row = inspect_decision(before['state'], after['state'], after['player'], after['action'])
                choices.append({'step': after['decision_id'], **row})
        rows.append({k: original[k] for k in ('seed','faction','seat','complete','vp','steps')} | {'metrics': metrics(choices), 'choices': choices})
    return rows


def run_game(original, teacher, versions, experiment_hash):
    seed, faction, seat = (original[k] for k in ('seed','faction','seat'))
    env = Environment(seed, 2000)
    rngs = [random.Random(f'{seed}:{faction}:opponent:{p}') for p in range(4)]
    s = json.loads(env.snapshot_json())
    frames = []
    choices = []
    def frame(snapshot, actor=None, action=None, candidates=()):
        state = snapshot['state'].copy()
        state.pop('event_log', None)
        return {'decision_id': snapshot['decision_id'], 'player': actor, 'action': action,
                'legal_action_count': len(candidates), 'legal_federation_count': sum(c['action']['type']=='FormFederation' for c in candidates),
                'event_end': 0, 'state': state}
    frames.append(frame(s))
    try:
        while not env.is_terminal():
            actor = s['player']
            decision, index = teacher.choose(s) if actor == seat else (s['decision_id'], rngs[actor].randrange(len(s['candidates'])))
            action = s['candidates'][index]['action']
            reason = teacher.score(s, action)[1] if actor == seat else None
            before = s
            env.step(decision, index)
            s = json.loads(env.snapshot_json())
            frames.append(frame(s, actor, action, before['candidates']))
            if actor == seat:
                inspected = inspect_decision(before['state'], s['state'], actor, action)
                choices.append({'step': s['decision_id'], 'reason': reason, **inspected})
        scores = dict(env.final_scores())
        result = {'seed': seed, 'faction': faction, 'seat': seat, 'complete': True,
                  'vp': scores[seat], 'scores': scores, 'steps': s['steps'], 'metrics': metrics(choices), 'choices': choices}
        replay = add_decision_log({'schema_version': 1, 'metadata': {'seed': seed, 'policy': 'economy_teacher',
                'faction': faction, 'focus_player': seat, 'versions': versions, 'experiment_hash': experiment_hash,
                'steps': s['steps'], 'scores': scores}, 'frames': frames, 'events': []})
        return result, replay
    except Exception as error:
        return {'seed': seed, 'faction': faction, 'seat': seat, 'complete': False,
                'error': repr(error), 'snapshot': json.loads(env.snapshot_json()), 'choices': choices}, None


def summary(rows):
    result = {}
    keys = ('paid_trading_stations', 'six_credit_trading_stations', 'paid_terraform_builds',
            'three_ore_step_builds', 'construction_actions', 'construction_with_neighbor',
            'starting_mines', 'starting_mines_with_neighbor', 'federations', 'satellites', 'cost_debits_verified', 'engine_cost_anomalies')
    for faction in TARGETS:
        group = [r for r in rows if r['faction'] == faction]
        complete = [r for r in group if r['complete']]
        result[faction] = {'attempted': len(group), 'completed': len(complete),
            'mean_vp_complete_only': sum(r['vp'] for r in complete)/len(complete) if complete else None,
            'totals_complete_only': {k: sum(r['metrics'][k] for r in complete) for k in keys},
            'federation_power_after': [f['power_after'] for r in complete for f in r['metrics']['federation_details']]}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'gaia-rl/runs/strategy-pilot-v2')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require_current_sources(ROOT)
    manifest = json.loads((args.source/'manifest.json').read_text())
    require_compatible_versions(manifest['versions'])
    if digest((ROOT/'gaia-rl/experiments').glob('*.py')) != manifest['experiment_hash']:
        raise ValueError('Original pilot code changed')
    source_hash = digest(Path(__file__).parent.glob('*.py'))
    if args.output.exists():
        parser.error('Output must be new')
    args.output.mkdir(parents=True)
    started = time.monotonic()
    saved = json.loads((args.source/'teacher_evaluation.json').read_text())
    if len(saved) != 8 or not all(row['complete'] for row in saved):
        raise ValueError('Expected the complete eight-game teacher pilot')
    write(args.output/'manifest.json', {'versions': manifest['versions'], 'original_experiment_hash': manifest['experiment_hash'],
        'economy_experiment_hash': source_hash, 'source': str(args.source), 'policy': 'economy_teacher',
        'training_steps': 0, 'max_steps_per_game': 2000, 'games': [{k: r[k] for k in ('seed','faction','seat')} for r in saved]})
    baseline = historical_rows(saved, manifest)
    write(args.output/'original_teacher.json', baseline)
    revised = []
    for index, original in enumerate(saved):
        result, replay = run_game(original, EconomyTeacher(), manifest['versions'], source_hash)
        revised.append(result)
        write(args.output/f'game-{index}.json', result)
        if replay:
            with gzip.open(args.output/f'replay-{index}.json.gz', 'wt') as f:
                json.dump(replay, f, separators=(',', ':'))
        print(index, original['faction'], original['seed'], result.get('vp', result.get('error')), flush=True)
    require_current_sources(ROOT)
    require_compatible_versions(manifest['versions'])
    if digest(Path(__file__).parent.glob('*.py')) != source_hash:
        raise ValueError('Economic experiment source changed during evaluation')
    write(args.output/'report.json', {'original': summary(baseline), 'revised': summary(revised),
        'all_complete': all(r['complete'] for r in revised), 'elapsed_seconds': time.monotonic()-started,
        'warning': 'Already-observed four maps, two factions, random opponents; no training or independent generalization claim. No retuning on these results.'})


if __name__ == '__main__':
    main()
