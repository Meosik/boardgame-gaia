import json
import tempfile
import unittest
from pathlib import Path

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

    def test_iter_samples_builds_filter_precedes_engine_check(self):
        row = {'game': 'nowhere', 'replays': True, 'full_game': False, 'replay_engine_build_id': 'other'}
        old, new = dict(row, engine_build_id='aaa111'), dict(row, engine_build_id='bbb222')
        # no prefix matches: every game is skipped before the engine check, so nothing raises
        self.assertEqual(list(bc_dataset.iter_samples([old, new], builds=['ccc'])), [])
        # only the matching game reaches the engine check; builds=None keeps all games
        with self.assertRaisesRegex(RuntimeError, 'nowhere'):
            list(bc_dataset.iter_samples([old], builds=['aaa']))
        with self.assertRaises(RuntimeError):
            list(bc_dataset.iter_samples([old, new]))
        # games without engine_build_id never match a given prefix
        self.assertEqual(list(bc_dataset.iter_samples([row], builds=['aaa'])), [])


class LoadTests(unittest.TestCase):
    def test_load_resolves_relative_game_paths_against_manifest_parents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'root'
            game = root/'runs'/'lab-x'/'pair-000'/'game-0-A02'
            game.mkdir(parents=True)
            manifest = root/'runs'/'bc'/'manifest.jsonl'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('\n'.join(json.dumps({'game': g}) for g in
                                          ['runs/lab-x/pair-000/game-0-A02', '/abs/missing/game', 'runs/nope/g'])+'\n')
            games = bc_dataset._load(manifest)
            self.assertEqual(Path(games[0]['game']).resolve(), game.resolve())
            self.assertIsInstance(games[0]['game'], str)
            self.assertEqual(games[1]['game'], '/abs/missing/game')
            self.assertEqual(games[2]['game'], 'runs/nope/g')


if __name__ == '__main__':
    unittest.main()
