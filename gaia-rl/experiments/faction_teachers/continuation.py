"""Exact native prefix continuation with explicitly mixed teacher provenance."""
from copy import deepcopy
import json
from pathlib import Path

from gaia_rl import Environment
from gaia_rl.versions import require_compatible_versions
from faction_learning.models import digest
from faction_learning.records import state_hash
from four_factions.timed import atomic_json


def load_continuation(path, seed):
    path = Path(path)
    saved = json.loads(path.read_text())
    source = Path(saved['source'])
    if (saved.get('schema') != 1 or saved['seed'] != seed or
            saved['header_sha256'] != digest(source/'recording.json') or
            saved['trace_sha256'] != digest(source/'decisions.jsonl') or
            state_hash(saved['snapshot']) != saved['snapshot_sha256']):
        raise ValueError('Continuation checkpoint/seed/recording checksum mismatch')
    header = json.loads((source/'recording.json').read_text())
    require_compatible_versions(header['versions'])
    if (header['seed'] != seed or header.get('teacher_seats') != [0, 1, 2, 3] or
            header['max_steps'] != 2000 or header['human_seats'] or
            any(saved['source_manifest'][key] != header['teacher_spec'][key]
                for key in ('versions', 'source_hashes'))):
        raise ValueError('Continuation source is not the recorded four-teacher game')
    data = (source/'decisions.jsonl').read_bytes()
    if data and not data.endswith(b'\n'):
        raise ValueError('Partial decision row at continuation boundary')
    rows = [json.loads(line) for line in data.splitlines()]
    audits = [json.loads(line) for line in (source/'teacher-audit.jsonl').read_text().splitlines()]
    if ([row['index'] for row in rows] != saved['prefix'] or len(rows) != len(audits) or
            any(row['decision_id'] != audit['decision_id'] or row['index'] != audit['index']
                for row, audit in zip(rows, audits))):
        raise ValueError('Continuation prefix/audit mismatch')
    env = Environment(seed, header['max_steps'])
    if json.loads(env.snapshot_json()) != header['initial']:
        raise ValueError('Continuation initial native state mismatch')
    for row in rows:
        before = json.loads(env.snapshot_json())
        actor, index = before['player'], row['index']
        if (env.is_terminal() or type(index) is not int or not 0 <= index < len(before['candidates']) or
                row['decision_id'] != before['decision_id'] or row['controller'] != 'teacher' or
                row['player'] != actor or row['faction'] != before['state']['players'][actor]['faction'] or
                state_hash(before) != row['before_sha256'] or
                before['candidates'][index] != row['action']):
            raise ValueError('Continuation recorded action/before-state mismatch')
        env.step(row['decision_id'], index)
        if state_hash(json.loads(env.snapshot_json())) != row['after_sha256']:
            raise ValueError('Continuation recorded after-state mismatch')
    if env.is_terminal() or json.loads(env.snapshot_json()) != saved['snapshot']:
        raise ValueError('Continuation must match an unfinished native position')
    provenance = {'source': str(source.resolve()), 'recording_id': header['recording_id'],
        'header_sha256': saved['header_sha256'], 'trace_sha256': saved['trace_sha256'],
        'checkpoint_sha256': digest(path), 'imported_steps': len(rows),
        'resume_state_sha256': saved['snapshot_sha256'],
        'original_teacher_spec': header['teacher_spec'],
        'note': 'Imported prefix used the original teacher; new timing applies only after this boundary'}
    return {'saved': saved, 'rows': rows, 'audits': audits, 'provenance': provenance}


def restore_continuation(continuation, env, recorder, policy, audit):
    for row, old_audit in zip(continuation['rows'], continuation['audits']):
        env.step(row['decision_id'], row['index'])
        recorded = recorder.step(row['decision_id'], row['index'], controller='teacher')
        if recorded != json.loads(env.snapshot_json()) or state_hash(recorded) != row['after_sha256']:
            raise ValueError('Continuation diverged while copying verified prefix')
        audit.write(json.dumps({**old_audit, 'imported_from_original_teacher': True}, allow_nan=False)+'\n')
    audit.flush()
    saved = continuation['saved']
    before = json.loads(env.snapshot_json())
    if before != saved['snapshot']:
        raise ValueError('Restored native position differs from checkpoint')
    policy.prefix = list(saved['prefix'])
    policy.memory = deepcopy(saved['memory'])
    if 'times' in saved:
        policy.times = deepcopy(saved['times'])
    return before


def save_checkpoint(recorder, policy, manifest):
    current = recorder.current
    atomic_json(recorder.path/'policy-checkpoint.json', {
        'schema': 1, 'seed': recorder.header['seed'], 'source': str(recorder.path.resolve()),
        'prefix': policy.prefix, 'memory': policy.memory, 'times': policy.times,
        'snapshot': current, 'snapshot_sha256': state_hash(current),
        'header_sha256': digest(recorder.path/'recording.json'),
        'trace_sha256': digest(recorder.path/'decisions.jsonl'), 'source_manifest': manifest})
    atomic_json(recorder.path/'progress.json', {
        'steps': current['steps'], 'round': current['state']['round'], 'phase': current['state']['phase'],
        'player': current['player'], 'complete': False,
        'adaptive_clock': policy.adaptive_clock.state() if policy.adaptive_clock is not None else None})
