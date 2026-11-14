import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import policy_teacher


class FakeOfflinePolicy:
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint

    def choose(self, snapshot):
        return snapshot['decision_id'], 1


class PolicyTeacherTest(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType('gaia_rl.evaluation')
        fake.OfflinePolicy = FakeOfflinePolicy
        patcher = mock.patch.dict(sys.modules, {'gaia_rl.evaluation': fake})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_make_requires_checkpoint(self):
        with self.assertRaises(ValueError):
            policy_teacher.make('seed')

    def test_choose_passes_through_and_sets_audit(self):
        teacher = policy_teacher.make('seed', target_seconds=3, maximum_seconds=6,
                                      adaptive_clock=object(), checkpoint='runs/x')
        self.assertIsNone(teacher.last_audit)
        teacher.bind(object())
        result = teacher.choose({'decision_id': 7, 'player': 0, 'candidates': [{}, {}]})
        self.assertEqual(result, (7, 1))
        self.assertEqual(teacher.last_audit['decision_id'], 7)
        self.assertEqual(teacher.last_audit['selected'], 'policy')
        self.assertEqual(teacher.last_audit['plans'], [])
        self.assertIsNone(teacher.observe({}, 1, {}))

    def test_relative_checkpoint_resolves_against_gaia_rl(self):
        self.assertEqual(policy_teacher.make('s', checkpoint='runs/x').checkpoint, policy_teacher.ROOT/'runs/x')
        self.assertEqual(policy_teacher.ROOT.name, 'gaia-rl')
        self.assertEqual(policy_teacher.make('s', checkpoint='/tmp/ckpt').checkpoint, Path('/tmp/ckpt'))

    def test_spec_file_names_the_factory(self):
        spec = json.loads(Path(__file__).with_name('teacher-policy-bc-114.json').read_text())
        self.assertEqual(spec['factory'], 'policy_teacher:make')
        self.assertIn('checkpoint', spec['kwargs'])


if __name__ == '__main__':
    unittest.main()
