"""Evaluate the current two-faction Paia candidate with real-time local replay prefixes."""
import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import time

from gaia_rl._native import Environment
from gaia_rl.versions import require_current_sources, runtime_versions
from action_purpose.evaluate import ROOT, dump
from current_actions.evaluate import source_hashes, audit_booster_builds
from current_actions.teacher import construction_cost
from conditional_plans.teacher import PaiaPlanTeacher, PaiaReplanTeacher
from conditional_plans.opening import OpeningPlanTeacher
from conditional_plans.economy_first import EconomyFirstTeacher
from evaluation_replays import frame, validate_replay
from replay_log import add_decision_log
from live_replays import LiveReplayWriter
from federation.teacher import power

PLANNING_MODES = {'goal-continuation': PaiaPlanTeacher, 'per-action': PaiaReplanTeacher,
                  'opening': OpeningPlanTeacher, 'economy-first': EconomyFirstTeacher}


def run_game(spec, policy, versions, writer, progress):
    env = Environment(spec['seed'], 2000)
    policy.bind(env)
    streams = [random.Random(f"{spec['seed']}:{spec['faction']}:opponent:{p}") for p in range(4)]
    snapshot = json.loads(env.snapshot_json())
    if snapshot['state']['players'][spec['seat']]['faction'] != spec['faction']:
        raise ValueError('Unexpected focal setup')
    record = {'schema_version': 1, 'metadata': {**spec, 'focus_player': spec['seat'],
              'policy': type(policy).__name__, 'stage': 1, 'versions': versions, 'steps': 0},
              'frames': [frame(snapshot)], 'events': []}
    choices = []
    writer.write(record)
    try:
        while not env.is_terminal():
            before = snapshot
            actor = before['player']
            start = time.monotonic()
            ranks = policy.rank(before) if actor == spec['seat'] else None
            if ranks is not None:
                if len(ranks) != len(before['candidates']) or not all(math.isfinite(v) for v, _ in ranks):
                    raise ValueError('Invalid teacher ranks')
                index = max(range(len(ranks)), key=lambda i: (ranks[i][0], -i))
            else:
                index = streams[actor].randrange(len(before['candidates']))
            action = before['candidates'][index]['action']
            env.step(before['decision_id'], index)
            snapshot = json.loads(env.snapshot_json())
            record['frames'].append(frame(snapshot, actor, action, before['candidates']))
            record['metadata']['steps'] = snapshot['steps']
            if ranks is not None:
                p, q = before['state']['players'][actor], snapshot['state']['players'][actor]
                cost = construction_cost(before['state'], p, action)
                row = {'step': snapshot['decision_id'], 'round': before['state']['round'],
                    'action': action, 'score': ranks[index][0], 'reason': ranks[index][1],
                    'cost': asdict(cost) if cost else None, 'resources_before': p['resources'],
                    'resources_after': q['resources'], 'seconds': time.monotonic()-start,
                    'top': [{'action': before['candidates'][i]['action'], 'score': ranks[i][0], 'reason': ranks[i][1]}
                            for i in sorted(range(len(ranks)), key=lambda i: (-ranks[i][0], i))[:3]]}
                if cost and action['type'] in ('Build', 'RoundBoosterRangeBuild', 'TwilightRangeBuild',
                                               'SpaceshipCreditTerraform', 'EclipseAsteroidMine'):
                    actual = {k: p['resources'][k]-q['resources'][k] for k in ('ore', 'credits', 'qic')}
                    expected = {k: getattr(cost, k) for k in actual}
                    if actual != expected:
                        raise ValueError(f'Build debit mismatch: {expected} != {actual}')
                    row['cost_verified'] = True
                choices.append(row)
            if not env.is_terminal():
                writer.write(record)
            progress(snapshot, action, time.monotonic()-start)
        scores = dict(env.final_scores())
        record['metadata']['scores'] = scores
        record = add_decision_log(record)
        validate_replay(record)
        kinds = Counter(c['action']['kind'] for c in choices if c['action']['type'] == 'FreeAction')
        focal = snapshot['state']['players'][spec['seat']]
        result = {'complete': True, **spec, 'vp': scores[spec['seat']], 'steps': snapshot['steps'],
                  'metrics': {'conversions': dict(kinds), 'liquidation': kinds['OreToCredit']+kinds['KnowledgeToCredit'],
                      'federations': sum(c['action']['type'] == 'FormFederation' for c in choices),
                      'unfederated_power': sum(power(focal, b['kind']) for b in focal['structures']
                                               if b['hex'] not in focal['federated_hexes']),
                      'advanced_tiles': len(focal['advanced_tech_tiles']),
                      'max_decision_seconds': max((c['seconds'] for c in choices), default=0)},
                  'final_tracks': snapshot['state']['players'][spec['seat']]['research_tracks'], 'choices': choices}
        audit_booster_builds(result, record)
        return result, record
    except BaseException:
        writer.write(record, 'failed')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--specs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--planning-mode', choices=PLANNING_MODES, default='goal-continuation')
    args = parser.parse_args()
    specs = json.loads(args.specs.read_text())
    if not specs or any(s['faction'] not in PaiaPlanTeacher.factions or s['seat'] not in range(4) for s in specs):
        parser.error('Xenos/HadschHallas specs required')
    require_current_sources(ROOT)
    versions = runtime_versions()
    hashes = source_hashes()
    live_path = ROOT/'gaia-rl/tools/live_replays.py'
    hashes[str(live_path.relative_to(ROOT))] = hashlib.sha256(live_path.read_bytes()).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    dump(args.output/'manifest.json', {'versions': versions, 'source_hashes': hashes, 'specs': specs,
         'stages': [1], 'purpose_stage': 1, 'teacher_variant': 'paia-two-faction-candidate',
         'training_steps': 0, 'promotion': False, 'horizon_incomes': 2,
         'planning_mode': args.planning_mode,
         **({'economy_focus': {'faction': 'HadschHallas', 'target': 4},
             'economy_five_timing_horizon': 'native game end'}
            if args.planning_mode == 'economy-first' else {})})
    for name in hashes:
        target = args.output/'source-snapshot'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    started = time.monotonic()
    results = []
    for game, spec in enumerate(specs):
        replay = None
        policy = PLANNING_MODES[args.planning_mode](1)
        policy.on_plan = lambda audit: print(f'plan root={audit["decision_id"]} round={audit["round"]} '
            f'selected={audit["selected"]} continued={audit.get("continued", False)}', flush=True)
        writer = LiveReplayWriter(args.output/f'live-{game}', str(args.output.resolve())+str(game))
        def progress(s, action, seconds):
            print(f'action={s["steps"]} round={s["state"]["round"]} type={action["type"]} seconds={seconds:.3f}', flush=True)
        try:
            result, replay = run_game(spec, policy, versions, writer, progress)
            require_current_sources(ROOT)
            for name, digest in hashes.items():
                if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
                    raise ValueError(f'Source changed during evaluation: {name}')
        except BaseException as error:
            if replay is not None:
                writer.write(replay, 'failed')
            dump(args.output/f'plans-{game}-failed.json', policy.plan_history)
            dump(args.output/'failure.json', {'all_complete': False, 'error': str(error),
                                              'error_type': type(error).__name__, 'game': game})
            raise
        dump(args.output/f'stage1-{game}.json', result)
        with gzip.open(args.output/f'stage1-{game}.json.gz', 'wt') as stream:
            json.dump(replay, stream)
        dump(args.output/f'plans-{game}.json', policy.plan_history)
        writer.write(replay, 'complete')
        results.append(result)
    dump(args.output/'report.json', {'all_complete': True, 'promotion': False,
         'seconds': time.monotonic()-started, 'summary': {'1': {'games': len(results),
         'mean_vp': sum(r['vp'] for r in results)/len(results)}}})


if __name__ == '__main__':
    main()
