import json
import unittest

import bc_dataset


class ReplayTests(unittest.TestCase):
    def test_replay_requires_recorded_steps_and_scores(self):
        from gaia_rl import Environment
        seed = 'geo-quartet-1080194'
        env = Environment(seed, 2000)
        rows = []
        for _ in range(3):
            rows.append({'decision_id': json.loads(env.snapshot_json())['decision_id'], 'index': 0})
            env.step(rows[-1]['decision_id'], 0)
        snapshot = json.loads(env.snapshot_json())
        scores = {str(s): p['vp'] for s, p in enumerate(snapshot['state']['players'])}
        result = {'steps': snapshot['steps'], 'scores': scores}
        self.assertTrue(bc_dataset._replays(seed, rows, result)[0])
        ok, why, _ = bc_dataset._replays(seed, rows, {**result, 'steps': result['steps'] + 1})
        self.assertFalse(ok)
        self.assertTrue(why.startswith('steps differ'))
        ok, why, _ = bc_dataset._replays(seed, rows, {**result, 'scores': {**scores, '0': scores['0'] + 1}})
        self.assertFalse(ok)
        self.assertTrue(why.startswith('scores differ'))
        self.assertTrue(bc_dataset._replays(seed, rows, {})[0])


if __name__ == '__main__':
    unittest.main()
