import os
import unittest
from unittest.mock import patch

from audit_engine_replay_compatibility import successor


class ReplayCompatibilityTests(unittest.TestCase):
    def test_missing_exported_event_log_is_restored_without_mutating_input(self):
        state = {'round': 1}
        with patch.dict(os.environ, {'GAIA_ENGINE_FIXES_2': 'original'}):
            with patch('audit_engine_replay_compatibility.evaluation_successor_json', return_value='{}') as native:
                self.assertEqual(successor(state, 0, {'type': 'Pass'}, '1'), {'state': {}})
                self.assertIn('"event_log": []', native.call_args.args[0])
            self.assertEqual(os.environ['GAIA_ENGINE_FIXES_2'], 'original')
        self.assertEqual(state, {'round': 1})

    def test_rule_error_is_reported_and_environment_restored(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch('audit_engine_replay_compatibility.evaluation_successor_json', side_effect=RuntimeError('not legal')):
                self.assertEqual(successor({}, 0, {}, '0'), {'error': 'not legal'})
            self.assertNotIn('GAIA_ENGINE_FIXES_2', os.environ)


if __name__ == '__main__':
    unittest.main()
