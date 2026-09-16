"""Durable approval boundary around native decisions, separate from BC records."""
from copy import deepcopy
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import tempfile
import threading


def clone(value):
    return deepcopy(value)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def snapshot(env):
    return json.loads(env.snapshot_json())


def write_new(path, value):
    """Publish once, durably. A failed write never advances the live environment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(name, path)  # No overwrite, even for duplicate requests/processes.
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(name)


class Conflict(ValueError):
    pass


def technology_choice(candidate):
    action = candidate['action']
    if (action['type'] in ('RebellionGainTechTile', 'ItarsGaiaTechTile')
            or action.get('bonus_tech_tile') is not None):
        return True
    choice = action.get('tech_tile_choice', action.get('choice'))
    return isinstance(choice, dict) and choice.get('kind') in (
        'Standard', 'Advanced', 'LostFleetAdvanced')


class Session:
    def __init__(self, path, config, environment_factory, teacher_factory):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.teacher_factory = teacher_factory
        self.path.mkdir(parents=True, exist_ok=True)
        self.env = environment_factory(config['seed'], 2000)
        initial = snapshot(self.env)
        manifest = {'schema': 1, 'config': config, 'initial': initial,
                    'training_performed': False, 'automatic_weight_updates': False,
                    'labels': 'AI accepted by human or human override; not certified expert demonstrations'}
        manifest_path = self.path/'session.json'
        if manifest_path.exists():
            if json.loads(manifest_path.read_text()) != manifest:
                raise ValueError('Session source/config/native initial state differs')
        else:
            write_new(manifest_path, manifest)
        self.manifest = manifest
        self.runtime_clock = None
        self.teacher = teacher_factory((), {}).bind(self.env)
        self.history = []
        for path in sorted((self.path/'decisions').glob('*.json')):
            row = json.loads(path.read_text())
            before = snapshot(self.env)
            if (path.name != f'{len(self.history):06d}.json' or row['before'] != before
                    or row['decision_id'] != before['decision_id']):
                raise ValueError('Discontinuous or divergent coaching history')
            suggestion_path = self.path/'suggestions'/f'{len(self.history):06d}.json'
            suggestion = json.loads(suggestion_path.read_text())
            self._validate_recommendation(suggestion, before)
            if row['recommendation'] != suggestion:
                raise ValueError('Recorded recommendation differs from its original receipt')
            self._validate_choice(row['index'], before)
            if row['action'] != before['candidates'][row['index']]:
                raise ValueError('Recorded native action differs')
            self._validate_feedback(row['index'], row['recommendation'], row['reason'], row['plan'])
            expected_controller = ('human_override' if row['index'] != row['recommendation']['index']
                                   else 'ai_accepted_by_human')
            if row['controller'] != expected_controller:
                raise ValueError('Coaching controller provenance differs')
            self.env.step(before['decision_id'], row['index'])
            if row['after'] != snapshot(self.env):
                raise ValueError('Recorded native transition differs')
            self.history.append(row)
        memory = self.history[-1]['memory_after'] if self.history else {}
        self.teacher = teacher_factory([r['index'] for r in self.history], clone(memory)).bind(self.env)
        self.current = snapshot(self.env)
        self.status = 'complete' if self.env.is_terminal() else 'waiting'
        self.recommendation = None
        self.error = None
        self.worker = None
        self._load_suggestion()

    @staticmethod
    def _validate_choice(index, before):
        if type(index) is not int or not 0 <= index < len(before['candidates']):
            raise ValueError('합법 행동 목록에서 선택해 주세요.')

    @staticmethod
    def _validate_feedback(index, suggestion, reason, plan):
        for value in (reason, plan):
            if not isinstance(value, str) or len(value) > 8000:
                raise ValueError('이유와 계획은 각각 8,000자 이하의 글이어야 합니다.')
        if index != suggestion['index'] and (not reason.strip() or not plan.strip()):
            raise ValueError('AI와 다른 수를 선택한 이유와 다음 계획을 모두 적어 주세요.')

    @classmethod
    def _validate_recommendation(cls, value, before):
        cls._validate_choice(value['index'], before)
        if (value['decision_id'] != before['decision_id']
                or value['before_sha256'] != digest(before)):
            raise ValueError('Recommendation is for a different native state')
        scores = value['audit'].get('scores')
        if (not isinstance(scores, list) or len(scores) != len(before['candidates'])
                or any(not isinstance(s, (list, tuple)) or len(s) != 2
                       or not isinstance(s[0], (int, float)) or not math.isfinite(s[0])
                       or not isinstance(s[1], str) for s in scores)):
            raise ValueError('Teacher did not provide genuine candidate scores')

    def _suggestion_path(self):
        return self.path/'suggestions'/f'{self.current["steps"]:06d}.json'

    def _load_suggestion(self):
        path = self._suggestion_path()
        if self.status == 'complete' or not path.exists():
            return
        value = json.loads(path.read_text())
        if (value['before_sha256'] != digest(self.current)
                or value['memory_before'] != self.teacher.memory):
            raise ValueError('Saved recommendation differs from the pending decision')
        self._validate_recommendation(value, self.current)
        self.recommendation = value
        self.teacher.memory = clone(value['memory_after_search'])
        self.status = 'ready'

    def start_recommendation(self):
        with self.lock:
            if self.status not in ('waiting', 'error'):
                return
            self.status, self.error = 'thinking', None
            self.worker = threading.Thread(target=self._recommend, daemon=True)
            self.worker.start()

    def _recommend(self):
        # Only this thread uses the teacher/native env until status becomes ready.
        before, memory_before = clone(self.current), clone(self.teacher.memory)
        try:
            decision, index = self.teacher.choose(before)
            if decision != before['decision_id'] or snapshot(self.env) != before:
                raise ValueError('Teacher changed the parent decision')
            self._validate_choice(index, before)
            audit = clone(self.teacher.last_audit)
            value = {'decision_id': decision, 'index': index, 'before_sha256': digest(before),
                     'audit': audit, 'memory_before': memory_before,
                     'memory_after_search': clone(self.teacher.memory)}
            self._validate_recommendation(value, before)
            write_new(self._suggestion_path(), value)
            with self.lock:
                self.recommendation, self.status = value, 'ready'
        except Exception as error:
            with self.lock:
                self.teacher = self.teacher_factory([r['index'] for r in self.history],
                                                   memory_before).bind(self.env)
                self.error, self.status = str(error), 'error'

    def public(self):
        with self.lock:
            recommendation = None
            if self.recommendation:
                r = self.recommendation
                from current_actions.conservation import blocked
                recommendation = {'index': r['index'], 'audit': r['audit'],
                    'scores': [{'value': score[0], 'reason': score[1], 'excluded': blocked(score)}
                               for score in r['audit']['scores']]}
            return clone({'schema': 1, 'session_id': digest(str(self.path.resolve())), 'status': self.status,
                          'snapshot': self.current, 'recommendation': recommendation,
                          'error': self.error, 'config': {**self.manifest['config'],
                              **({'clock': self.runtime_clock['clock']} if self.runtime_clock else {})},
                          'runtime_clock': self.runtime_clock,
                          'recorded': len(self.history),
                          'corrections': sum(r['controller'] == 'human_override' for r in self.history),
                          'last_feedback': ({k: self.history[-1][k] for k in
                              ('controller', 'reason', 'plan', 'player', 'decision_id')}
                                            if self.history else None)})

    def approve(self, decision_id, index, reason='', plan='', technology_confirmed=False):
        with self.lock:
            if (type(decision_id) is not int or decision_id != self.current['decision_id']
                    or self.status != 'ready'):
                raise Conflict('이미 처리됐거나 아직 추천이 준비되지 않은 결정입니다. 최신 화면을 확인해 주세요.')
            before, rec = self.current, self.recommendation
            self._validate_choice(index, before)
            if technology_choice(before['candidates'][index]) and technology_confirmed is not True:
                raise ValueError('받을 기술과 연결 연구 트랙을 직접 확인하고 선택해 주세요.')
            self._validate_feedback(index, rec, reason, plan)
            override = index != rec['index']
            branch = self.env.fork(decision_id, index)
            after = snapshot(branch)
            memory = clone(rec['memory_before'] if override else rec['memory_after_search'])
            # A proposed plan was not accepted. Preserve other seats and clock expenditure,
            # but do not force the correcting human back onto the rejected actor's plan.
            if override:
                actor = str(before['player'])
                memory.pop(actor, None)
                memory.get('_plans', {}).pop(actor, None)
                if '_clock' in rec['memory_after_search']:
                    memory['_clock'] = clone(rec['memory_after_search']['_clock'])
            teacher = self.teacher_factory([r['index'] for r in self.history], memory)
            teacher.observe(before, index, after)
            row = {'schema': 1, 'decision_id': decision_id, 'player': before['player'],
                   'faction': before['state']['players'][before['player']]['faction'],
                   'index': index, 'action': before['candidates'][index],
                   'controller': 'human_override' if override else 'ai_accepted_by_human',
                   'reason': reason.strip(), 'plan': plan.strip(), 'recommendation': rec,
                   'technology_confirmed': technology_confirmed is True,
                   'before': before, 'after': after, 'memory_after': clone(teacher.memory)}
            write_new(self.path/'decisions'/f'{before["steps"]:06d}.json', row)
            self.env, self.current = branch, after
            self.history.append(row)
            # Configure the next recommendation at its own decision boundary,
            # not at the just-approved decision's clock-policy boundary.
            self.teacher = self.teacher_factory([r['index'] for r in self.history],
                                                clone(teacher.memory)).bind(branch)
            self.recommendation, self.error = None, None
            self.status = 'complete' if branch.is_terminal() else 'waiting'
            return self.public()

    def export(self):
        with self.lock:
            return clone({'manifest': self.manifest, 'decisions': self.history,
                          'runtime_clock': self.runtime_clock,
                          'current': self.current, 'complete': self.status == 'complete',
                          'training_performed': False})
