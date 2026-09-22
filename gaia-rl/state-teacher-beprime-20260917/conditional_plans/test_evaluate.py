"""Failure plumbing tests; mocked termination is not native completion evidence."""
import json
import unittest
from unittest.mock import MagicMock, patch

from gaia_rl._native import Environment
from conditional_plans.evaluate import PLANNING_MODES, run_game


class EvaluationFailureTests(unittest.TestCase):
    def test_modes_have_distinct_recorded_identities_and_same_faction_scope(self):
        continuation = PLANNING_MODES['goal-continuation'](1)
        control = PLANNING_MODES['per-action'](1)
        self.assertNotEqual(type(continuation).__name__, type(control).__name__)
        self.assertEqual(continuation.factions, control.factions)
        self.assertTrue(continuation.continue_goals)
        self.assertFalse(control.continue_goals)

    def setUp(self):
        snapshot = json.loads(Environment('live-failure-test', 2000).snapshot_json())
        actor = snapshot['player']
        self.spec = {'seed': 'live-failure-test', 'seat': actor,
                     'faction': snapshot['state']['players'][actor]['faction']}
        self.env = MagicMock()
        self.env.snapshot_json.return_value = json.dumps(snapshot)
        self.writer = MagicMock()

    def test_interrupted_decision_marks_last_record_failed(self):
        self.env.is_terminal.return_value = False
        policy = MagicMock()
        policy.rank.side_effect = KeyboardInterrupt()
        with patch('conditional_plans.evaluate.Environment', return_value=self.env):
            with self.assertRaises(KeyboardInterrupt):
                run_game(self.spec, policy, {}, self.writer, MagicMock())
        self.assertEqual(self.writer.write.call_args.args[1], 'failed')
        self.assertEqual(len(self.writer.write.call_args.args[0]['frames']), 1)

    def test_final_audit_failure_does_not_leave_live_status_running(self):
        self.env.is_terminal.return_value = True
        self.env.final_scores.return_value = [(p, 0) for p in range(4)]
        with patch('conditional_plans.evaluate.Environment', return_value=self.env), \
                patch('conditional_plans.evaluate.validate_replay', side_effect=ValueError('audit rejected')):
            with self.assertRaisesRegex(ValueError, 'audit rejected'):
                run_game(self.spec, MagicMock(), {}, self.writer, MagicMock())
        self.assertEqual(self.writer.write.call_args.args[1], 'failed')


if __name__ == '__main__':
    unittest.main()
