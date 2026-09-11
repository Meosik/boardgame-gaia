import json
import unittest

from gaia_rl import ENGINE_BUILD_ID, Environment
from gaia_rl._native import StepLimitError


class NativeTests(unittest.TestCase):
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
