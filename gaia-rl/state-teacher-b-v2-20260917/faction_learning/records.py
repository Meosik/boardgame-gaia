"""Complete native-replayed records with explicitly declared controller provenance.

This local API is not an authentication boundary: the game server must supply the
controller identity. Native replay proves actions, not that a human is an expert.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

from .models import ROOT, digest, write_json


def snapshot(env):
    return json.loads(env.snapshot_json())


def state_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def controllers(human_seats, teacher_seats, teacher_spec):
    humans, teachers = list(human_seats), list(teacher_seats)
    for seats in (humans, teachers):
        if (len(set(seats)) != len(seats)
                or any(type(s) is not int or s not in range(4) for s in seats)):
            raise ValueError('Declare distinct controller seats from 0 to 3')
    if not (humans or teachers) or set(humans) & set(teachers):
        raise ValueError('Declare non-overlapping human or teacher seats')
    if teachers:
        if (not isinstance(teacher_spec, dict) or not teacher_spec.get('name')
                or not isinstance(teacher_spec.get('source_hashes'), dict)
                or not teacher_spec['source_hashes']
                or any(not isinstance(value, str) or len(value) != 64
                       or any(c not in '0123456789abcdef' for c in value)
                       for value in teacher_spec['source_hashes'].values())):
            raise ValueError('Teacher seats require a named policy and source hashes')
    return {s: 'human' if s in humans else 'teacher' if s in teachers else 'ai' for s in range(4)}


class NativeRecorder:
    """Own one fresh native episode. Incomplete/forked records cannot enter BC."""
    def __init__(self, destination, seed, human_seats=(), *, max_steps=2000,
                 teacher_seats=(), teacher_spec=None):
        from gaia_rl._native import Environment
        from gaia_rl.versions import require_current_sources, runtime_versions
        require_current_sources(ROOT)
        seats = list(human_seats)
        teachers = list(teacher_seats)
        self._controllers = controllers(seats, teachers, teacher_spec)
        self.path = Path(destination)
        self._env = Environment(seed, max_steps)
        self._failed = False
        self._closed = False
        self.path.mkdir(parents=True, exist_ok=False)
        self.header = {'schema': 1, 'recording_id': str(uuid4()), 'seed': seed,
            'max_steps': max_steps, 'versions': runtime_versions(), 'human_seats': sorted(seats),
            'initial': snapshot(self._env), 'provenance': 'caller-declared controllers',
            'undo': 'unsupported; a changed history requires a separate verified record'}
        if teachers:
            self.header.update(teacher_seats=sorted(teachers),
                               teacher_spec=json.loads(json.dumps(teacher_spec, allow_nan=False)))
        write_json(self.path / 'recording.json', self.header)
        self._stream = (self.path / 'decisions.jsonl').open('x')

    @property
    def current(self):
        return snapshot(self._env)

    def step(self, decision_id, index, *, controller):
        if self._closed or self._failed:
            raise RuntimeError('Recording is closed or failed')
        before = self.current
        actor = before['player']
        expected = self._controllers[actor]
        if controller != expected:
            raise ValueError('Controller does not own the native acting seat')
        if type(index) is not int or type(decision_id) is not int:
            raise ValueError('Integer decision ID and index required')
        self._env.step(decision_id, index)
        row = {'decision_id': decision_id, 'index': index, 'player': actor,
            'faction': before['state']['players'][actor]['faction'], 'controller': controller,
            'before_sha256': state_hash(before), 'action': before['candidates'][index],
            'after_sha256': state_hash(self.current)}
        try:
            self._stream.write(json.dumps(row, allow_nan=False) + '\n')
            self._stream.flush()
            os.fsync(self._stream.fileno())
        except BaseException:
            self._failed = True
            raise
        return self.current

    def finish(self):
        if self._failed or self._closed or not self._env.is_terminal():
            raise ValueError('Only a successfully recorded terminal game can finish')
        self.close()
        write_json(self.path / 'complete.json', {'trace_sha256': digest(self.path / 'decisions.jsonl'),
            'header_sha256': digest(self.path / 'recording.json'), 'terminal': self.current,
            'scores': self._env.final_scores()})

    def close(self):
        self._stream.close()
        self._closed = True


def audited_samples(source, faction, encoder, *, controller='human'):
    """Replay every decision; label only the explicitly selected role and faction.

    Replay and source receipts do not authenticate the caller or certify skill.
    """
    if controller not in ('human', 'teacher'):
        raise ValueError('Imitation labels must be explicitly human or teacher')
    from gaia_rl._native import Environment
    from gaia_rl.versions import require_compatible_versions, require_current_sources
    require_current_sources(ROOT)
    source = Path(source)
    header = json.loads((source / 'recording.json').read_text())
    complete = json.loads((source / 'complete.json').read_text())
    require_compatible_versions(header['versions'])
    if (header.get('schema') != 1 or header.get('provenance') != 'caller-declared controllers'
            or digest(source / 'recording.json') != complete['header_sha256']
            or digest(source / 'decisions.jsonl') != complete['trace_sha256']):
        raise ValueError('Recording manifest/checksum differs')
    seats = header['human_seats']
    owners = controllers(seats, header.get('teacher_seats', ()), header.get('teacher_spec'))
    env = Environment(header['seed'], header['max_steps'])
    if snapshot(env) != header['initial']:
        raise ValueError('Initial native state differs')
    samples, counts = [], {'human': 0, 'ai': 0}
    if header.get('teacher_seats'):
        counts['teacher'] = 0
    with (source / 'decisions.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            before = snapshot(env)
            actor, index = before['player'], row['index']
            if (env.is_terminal() or type(index) is not int or index < 0
                    or index >= len(before['candidates'])
                    or type(row['decision_id']) is not int
                    or row['decision_id'] != before['decision_id']):
                raise ValueError('Invalid/stale recorded decision')
            actual_faction = before['state']['players'][actor]['faction']
            actual_controller = owners[actor]
            if (row['player'] != actor or row['faction'] != actual_faction
                    or row['controller'] != actual_controller or row['before_sha256'] != state_hash(before)
                    or row['action'] != before['candidates'][index]):
                raise ValueError('Recorded action/controller/native state differs')
            counts[actual_controller] += 1
            if actual_controller == controller and actual_faction == faction and len(before['candidates']) > 1:
                obs = encoder.encode(before, actor)
                samples.append((obs['observation'], obs['candidates'][:len(before['candidates'])].copy(),
                                index, actual_faction))
            env.step(row['decision_id'], index)
            if row['after_sha256'] != state_hash(snapshot(env)):
                raise ValueError('Recorded native transition differs')
    if not env.is_terminal() or snapshot(env) != complete['terminal']:
        raise ValueError('Incomplete or divergent native game')
    if json.loads(json.dumps(env.final_scores())) != complete['scores']:
        raise ValueError('Native final scores differ')
    return samples, {'path': str(source.resolve()), 'seed': header['seed'],
        'recording_id': header['recording_id'], 'initial_sha256': state_hash(header['initial']),
        'trace_sha256': complete['trace_sha256'], 'counts': counts, 'samples': len(samples),
        'native_replayed': True, 'label_source': controller, 'teacher_spec': header.get('teacher_spec'),
        'human_identity': 'caller-declared, not authenticated by offline audit'}
