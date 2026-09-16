"""Adapt completed, version-pinned evaluations to the existing replay schema.

Kept outside gaia_rl: recording must not invalidate trained policy fingerprints.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import random
import tempfile

from publish_replays import read_catalog, write_catalog
from replay_log import add_decision_log

ROOT = Path(__file__).resolve().parents[2]


def validate_replay(replay):
    if replay.get('schema_version') != 1:
        raise ValueError('Unsupported replay schema')
    metadata, frames, events = replay['metadata'], replay['frames'], replay['events']
    steps, seat = metadata['steps'], metadata['focus_player']
    if not isinstance(steps, int) or steps < 1 or seat not in range(4) or len(frames) != steps + 1:
        raise ValueError('Incomplete replay frames')
    end = 0
    for i, frame in enumerate(frames):
        if (frame['decision_id'] != i or not isinstance(frame['event_end'], int)
                or not end <= frame['event_end'] <= len(events)
                or not 0 <= frame['legal_federation_count'] <= frame['legal_action_count']
                or len(frame['state']['players']) != 4
                or not isinstance(frame['state']['board']['hexes'], dict)):
            raise ValueError('Invalid replay frame or log boundary')
        if i == 0:
            if frame['player'] is not None or frame['action'] is not None:
                raise ValueError('Invalid initial replay frame')
        elif frame['player'] not in range(4) or not isinstance(frame['action'].get('type'), str):
            raise ValueError('Invalid replay action')
        end = frame['event_end']
    terminal = frames[-1]['state']['phase']
    if end != len(events) or not isinstance(terminal, dict) or 'Ended' not in terminal:
        raise ValueError('Replay is not a completed game')
    scores = {str(k): v for k, v in terminal['Ended']['final_scores']}
    if set(scores) != {'0', '1', '2', '3'} or scores != {str(k): v for k, v in metadata['scores'].items()}:
        raise ValueError('Replay final scores differ from metadata')
    if metadata['faction'] != frames[0]['state']['players'][seat]['faction']:
        raise ValueError('Replay focal faction mismatch')


def validate_batch(source):
    games = read_catalog(source/'index.json')
    if not games:
        raise ValueError('Empty replay batch')
    for game in games:
        path = source/game['file']
        if path.is_symlink():
            raise ValueError('Refusing symlink replay')
        with gzip.open(path, 'rt') as stream:
            replay = json.load(stream)
        validate_replay(replay)
        meta = replay['metadata']
        if (game['steps'] != meta['steps'] or game['seed'] != meta['seed']
                or game['faction'] != meta['faction'] or game['policy'] != meta['policy']
                or game['vp'] != meta['scores'][str(meta['focus_player'])]):
            raise ValueError('Catalog differs from replay')
    return games


def frame(snapshot, actor=None, action=None, candidates=()):
    state = copy.deepcopy(snapshot['state'])
    state.pop('event_log', None)
    return {'decision_id': snapshot['decision_id'], 'player': actor, 'action': action,
            'legal_action_count': len(candidates),
            'legal_federation_count': sum(c['action']['type'] == 'FormFederation' for c in candidates),
            'event_end': 0, 'state': state}


def reproduce_ppo(report):
    from gaia_rl._native import Environment
    from gaia_rl.evaluation import OfflinePolicy
    from gaia_rl.versions import require_current_sources, require_compatible_versions
    import torch

    require_current_sources(ROOT)
    require_compatible_versions(report['versions'])
    rows = report['games']
    seeds = {row['seed'] for row in rows}
    if (not rows or len(rows) != 4 * len(seeds)
            or any(sorted(row['seat'] for row in rows if row['seed'] == seed) != list(range(4)) for seed in seeds)):
        raise ValueError('Evaluation must contain all four seats per seed')
    torch.set_num_threads(2)
    policy = OfflinePolicy(report['checkpoint'])
    opponent = None if report['opponent'] == 'uniform-random' else OfflinePolicy(report['opponent'])
    for row in rows:
        # Exactly the RNG and argmax inference of gaia_rl.evaluation, not training sampling.
        env = Environment(row['seed'])
        rng = random.Random(f"{row['seed']}-seat-{row['seat']}")
        snapshot = json.loads(env.snapshot_json())
        frames = [frame(snapshot)]
        while not env.is_terminal():
            actor = snapshot['player']
            current = policy if actor == row['seat'] else opponent
            decision, index = (current.choose(snapshot) if current else
                               (snapshot['decision_id'], rng.randrange(len(snapshot['candidates']))))
            action = snapshot['candidates'][index]['action']
            before = snapshot
            env.step(decision, index)
            snapshot = json.loads(env.snapshot_json())
            frames.append(frame(snapshot, actor, action, before['candidates']))
        scores = {str(k): v for k, v in env.final_scores()}
        if scores != row['scores'] or snapshot['steps'] != row['steps']:
            raise ValueError('Evaluation reproduction mismatch; nothing published')
        replay = {'schema_version': 1, 'metadata': {
            'seed': row['seed'], 'focus_player': row['seat'],
            'faction': frames[0]['state']['players'][row['seat']]['faction'],
            'policy': 'PPO 대전 평가', 'opponent': report['opponent'],
            'versions': report['versions'], 'scores': scores, 'steps': row['steps'],
            'reproduced_original': True}, 'frames': frames, 'events': []}
        yield add_decision_log(replay)
    require_current_sources(ROOT)
    require_compatible_versions(report['versions'])


def recorded_purpose(run, report):
    if report.get('all_complete') is not True:
        raise ValueError('Teacher comparison is incomplete')
    manifest = json.loads((run/'manifest.json').read_text())
    for i, spec in enumerate(manifest['specs']):
        for stage in manifest['stages']:
            row = json.loads((run/f'stage{stage}-{i}.json').read_text())
            if row.get('complete') is not True:
                raise ValueError('Teacher game is incomplete')
            with gzip.open(run/f'stage{stage}-{i}.json.gz', 'rt') as stream:
                replay = json.load(stream)
            meta = replay['metadata']
            if (meta['versions'] != manifest['versions'] or meta['steps'] != row['steps']
                    or meta['seed'] != spec['seed'] or meta['focus_player'] != spec['seat']
                    or meta['faction'] != spec['faction'] or meta['stage'] != stage
                    or meta['scores'][str(spec['seat'])] != row['vp']):
                raise ValueError('Teacher replay differs from evaluation')
            yield replay


def export_evaluation(run):
    run = run.resolve()
    report_bytes = (run/'report.json').read_bytes()
    digest = hashlib.sha256(report_bytes).hexdigest()
    destination = run/'browser-replays'
    if destination.exists():
        validate_batch(destination)
        provenance = json.loads((destination/'export.json').read_text())
        if provenance['report_sha256'] != digest:
            raise ValueError('Evaluation changed after replay export')
        return destination
    report = json.loads(report_bytes)
    records = reproduce_ppo(report) if 'games' in report else recorded_purpose(run, report)
    staging = Path(tempfile.mkdtemp(prefix='replay-export-', dir=run))
    prefix = 'eval-' + hashlib.sha256((run.name + digest).encode()).hexdigest()[:16]
    catalog = []
    for i, replay in enumerate(records):
        validate_replay(replay)
        meta = replay['metadata']
        meta['evaluation_report_sha256'] = digest
        name = f'{prefix}-{i}'
        filename = name + '.json.gz'
        # Fixed gzip timestamp makes independent retries byte-identical.
        payload = json.dumps(replay, separators=(',', ':'), ensure_ascii=False).encode()
        (staging/filename).write_bytes(gzip.compress(payload, mtime=0))
        catalog.append({'id': name, 'file': filename, 'policy': meta['policy'],
                        'faction': meta['faction'], 'seed': meta['seed'],
                        'vp': meta['scores'][str(meta['focus_player'])], 'steps': meta['steps']})
        print(f'Replay verified: {name}, {catalog[-1]["vp"]} VP', flush=True)
    write_catalog(staging/'index.json', catalog)
    (staging/'export.json').write_text(json.dumps({'report_sha256': digest}, indent=2))
    validate_batch(staging)
    staging.rename(destination)
    return destination
