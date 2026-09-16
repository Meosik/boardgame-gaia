import json
import unittest

from gaia_rl import ENGINE_BUILD_ID, Environment
from gaia_rl._native import StepLimitError


class NativeTests(unittest.TestCase):
    def test_paid_state_preview_and_candidate_diagnostics_are_exposed(self):
        env = Environment('python-state-preview', max_steps=1)
        before = json.loads(env.snapshot_json())
        self.assertEqual(before['candidate_generation'], {
            'federation_limit_hits': 0, 'federation_limit_reasons': []})
        state = json.loads(env.preview_state_json(before['decision_id'], 0))
        branch = env.fork(before['decision_id'], 0)
        self.assertEqual(state, json.loads(branch.snapshot_json())['state'])
        self.assertEqual(json.loads(env.snapshot_json()), before)
        with self.assertRaises(StepLimitError):
            branch.preview_state_json(json.loads(branch.snapshot_json())['decision_id'], 0)

    def test_fingerprint_and_typed_nonterminal_limit(self):
        env = Environment("python-native-limit", max_steps=1)
        snapshot = json.loads(env.snapshot_json())
        self.assertEqual(snapshot["engine_build_id"], ENGINE_BUILD_ID)
        env.step(snapshot["decision_id"], 0)
        before = env.snapshot_json()
        snapshot = json.loads(before)
        with self.assertRaises(StepLimitError):
            env.step(snapshot["decision_id"], 0)
        self.assertEqual(env.snapshot_json(), before)
        self.assertFalse(env.is_terminal())
        self.assertIsNone(env.final_scores())
        self.assertEqual(env.rewards(), [0.0] * 4)


if __name__ == "__main__":
    unittest.main()
