import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from coaching.session import Conflict, Session
from coaching.branch import branch_session

SEED = 'quartet-pilot-20260913-27703'


class Teacher:
    def __init__(self, prefix, memory):
        self.prefix, self.memory = list(prefix), memory

    def bind(self, env):
        self.env = env
        return self

    def choose(self, snapshot):
        self.memory['_plans'] = {str(snapshot['player']): {'proposed': True}}
        self.last_audit = {'scores': [[i/10, 'test score'] for i in range(len(snapshot['candidates']))],
                           'selected': 'test', 'ranking_mode': 'test'}
        return snapshot['decision_id'], 0

    def observe(self, before, index, after):
        if before['steps'] != len(self.prefix) or after['steps'] != len(self.prefix)+1:
            raise ValueError('bad prefix')
        self.prefix.append(index)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'game'
        self.config = {'seed': SEED}
        self.session = Session(self.path, self.config, Environment, Teacher)

    def tearDown(self):
        if self.session.worker:
            self.session.worker.join(10)
        self.tmp.cleanup()

    def ready(self, session=None):
        session = session or self.session
        session.start_recommendation()
        session.worker.join(10)
        self.assertEqual(session.status, 'ready', session.error)

    def test_no_move_until_approval_all_four_seats_and_resume(self):
        seats = set()
        for _ in range(8):
            before = self.session.current
            self.ready()
            seats.add(before['player'])
            self.assertEqual(self.session.current, before)
            self.assertEqual(json.loads(self.session.env.snapshot_json()), before)
            # Plain polling, even repeated, never executes a suggestion.
            for _ in range(3):
                self.assertEqual(self.session.public()['snapshot'], before)
            self.session.approve(before['decision_id'], 0)
            self.assertEqual(self.session.status, 'waiting')
        self.assertEqual(seats, {0, 1, 2, 3})
        resumed = Session(self.path, self.config, Environment, Teacher)
        self.assertEqual(resumed.current, self.session.current)
        self.assertEqual(resumed.history, self.session.history)
        self.assertTrue(all(r['controller'] == 'ai_accepted_by_human' for r in resumed.history))

    def test_override_requires_reason_and_plan_and_records_actual_state(self):
        before = self.session.current
        self.ready()
        for reason, plan in [('', ''), ('reason', ''), (' ', 'plan')]:
            with self.assertRaises(ValueError):
                self.session.approve(before['decision_id'], 1, reason, plan)
        self.assertEqual(self.session.current, before)
        expected = json.loads(self.session.env.fork(before['decision_id'], 1).snapshot_json())
        self.session.approve(before['decision_id'], 1, '충전 이웃보다 확장', '먼 행성을 시작점으로')
        row = self.session.export()['decisions'][0]
        self.assertEqual(row['controller'], 'human_override')
        self.assertEqual(row['before'], before)
        self.assertEqual(row['after'], expected)
        self.assertNotIn(str(before['player']), row['memory_after'].get('_plans', {}))
        self.assertEqual(row['recommendation']['index'], 0)
        self.assertEqual(row['plan'], '먼 행성을 시작점으로')
        resumed = Session(self.path, self.config, Environment, Teacher)
        self.assertEqual(resumed.current, expected)

    def test_stale_duplicate_illegal_and_unready_requests_do_not_move(self):
        decision = self.session.current['decision_id']
        with self.assertRaises(Conflict):
            self.session.approve(decision, 0)
        self.ready()
        for index in (-1, True, 999999, None):
            with self.assertRaises(ValueError):
                self.session.approve(decision, index)
        with self.assertRaises(Conflict):
            self.session.approve(decision+1, 0)
        self.session.approve(decision, 0)
        after = self.session.current
        with self.assertRaises(Conflict):
            self.session.approve(decision, 0)
        self.assertEqual(self.session.current, after)
        self.assertEqual(len(self.session.history), 1)

    def test_next_teacher_configuration_uses_next_decision_prefix(self):
        self.ready()
        with patch.object(self.session, 'teacher_factory', wraps=Teacher) as factory:
            self.session.approve(self.session.current['decision_id'], 0)
        self.assertEqual(factory.call_args.args[0], [0])
        self.assertEqual(self.session.teacher.prefix, [0])

    def test_technology_requires_explicit_confirmation_even_for_recommendation(self):
        self.ready()
        before = self.session.current
        with patch('coaching.session.technology_choice', return_value=True):
            for confirmation in (False, None, 1, 'true'):
                with self.assertRaisesRegex(ValueError, '기술'):
                    self.session.approve(before['decision_id'], 0, technology_confirmed=confirmation)
                self.assertEqual(self.session.current, before)
            self.session.approve(before['decision_id'], 0, technology_confirmed=True)
        self.assertTrue(self.session.history[-1]['technology_confirmed'])

    def test_branch_preserves_original_and_replays_exact_prefix_with_distinct_id(self):
        for _ in range(3):
            self.ready()
            self.session.approve(self.session.current['decision_id'], 0)
        original = {str(p): p.read_bytes() for p in self.path.rglob('*.json')}
        branch = branch_session(self.path, Path(self.tmp.name)/'branch/game', 1, Environment, Teacher)
        self.assertEqual(branch.current, self.session.history[1]['before'])
        self.assertEqual(len(branch.history), 1)
        self.assertEqual(branch.status, 'ready')
        self.assertNotEqual(branch.public()['session_id'], self.session.public()['session_id'])
        self.assertTrue(all(Path(p).read_bytes() == data for p, data in original.items()))
        self.assertEqual(Session(branch.path, self.config, Environment, Teacher).current, branch.current)
        with self.assertRaises(FileExistsError):
            branch_session(self.path, branch.path, 1, Environment, Teacher)

    def test_suggestion_survives_restart_without_new_inference(self):
        self.ready()
        resumed = Session(self.path, self.config, Environment, Teacher)
        self.assertEqual(resumed.status, 'ready')
        self.assertEqual(resumed.recommendation, self.session.recommendation)
        self.assertEqual(resumed.current['steps'], 0)

    def test_durable_write_failure_does_not_execute_or_consume_approval(self):
        self.ready()
        before = self.session.current
        with patch('coaching.session.write_new', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.session.approve(before['decision_id'], 0)
        self.assertEqual(self.session.status, 'ready')
        self.assertEqual(self.session.current, before)
        self.assertEqual(json.loads(self.session.env.snapshot_json()), before)
        self.assertEqual(self.session.history, [])
        self.session.approve(before['decision_id'], 0)
        self.assertEqual(len(self.session.history), 1)

    def test_inference_failure_preserves_position_and_can_retry(self):
        before = self.session.current
        with patch.object(Teacher, 'choose', side_effect=RuntimeError('failed')):
            self.session.start_recommendation()
            self.session.worker.join(10)
        self.assertEqual(self.session.status, 'error')
        self.assertEqual(self.session.current, before)
        self.assertFalse(list((self.path/'decisions').glob('*.json')))
        self.ready()

    def test_tampered_history_and_config_rejected(self):
        self.ready()
        self.session.approve(self.session.current['decision_id'], 0)
        row_path = self.path/'decisions/000000.json'
        row = json.loads(row_path.read_text())
        row['after']['steps'] = 777
        row_path.write_text(json.dumps(row))
        with self.assertRaises(ValueError):
            Session(self.path, self.config, Environment, Teacher)
        with self.assertRaises(ValueError):
            Session(self.path, {**self.config, 'different_policy': True}, Environment, Teacher)

    def test_recovery_rejects_changed_recommendation_provenance(self):
        self.ready()
        self.session.approve(self.session.current['decision_id'], 0)
        path = self.path/'decisions/000000.json'
        row = json.loads(path.read_text())
        row['recommendation']['index'] = 1
        row['controller'] = 'human_override'
        row['reason'], row['plan'] = 'invented', 'invented'
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError, 'recommendation differs'):
            Session(self.path, self.config, Environment, Teacher)

    def test_recovery_rejects_a_pending_recommendation_with_missing_scores(self):
        self.ready()
        path = self.path/'suggestions/000000.json'
        value = json.loads(path.read_text())
        value['audit']['scores'] = []
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'genuine candidate scores'):
            Session(self.path, self.config, Environment, Teacher)


if __name__ == '__main__':
    unittest.main()
