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

    def test_replay_compares_chosen_candidate_content(self):
        from gaia_rl import Environment
        seed = 'geo-quartet-1080194'
        env = Environment(seed, 2000)
        rows = []
        for _ in range(3):
            snapshot = json.loads(env.snapshot_json())
            rows.append({'decision_id': snapshot['decision_id'], 'index': 0, 'chosen': snapshot['candidates'][0]})
            env.step(rows[-1]['decision_id'], 0)
        self.assertTrue(bc_dataset._replays(seed, rows, {})[0])
        wrong = [dict(rows[0], chosen={'phase': 'Setup', 'action': {'type': 'PlaceStartingStructure', 'coord': '99,99'}})] + rows[1:]
        ok, why, _ = bc_dataset._replays(seed, wrong, {})
        self.assertFalse(ok)
        self.assertTrue(why.startswith('chosen differs at step 0'))

    def test_iter_samples_refuses_other_engine(self):
        row = {'game': 'nowhere', 'replays': True, 'full_game': False, 'replay_engine_build_id': 'other'}
        with self.assertRaises(RuntimeError):
            list(bc_dataset.iter_samples([row]))
        with self.assertRaises(RuntimeError):
            list(bc_dataset.iter_samples([{k: v for k, v in row.items() if k != 'replay_engine_build_id'}]))
        # with the override the engine check passes and it proceeds to the (missing) game
        with self.assertRaises(KeyError):
            list(bc_dataset.iter_samples([row], allow_engine_mismatch=True))


if __name__ == '__main__':
    unittest.main()
