"""ab_replays: a teacher_ab-style game directory becomes a valid, score-checked replay."""
import gzip
import json
from pathlib import Path
import random
import tempfile
import unittest

import ab_replays


def fake_game(root, seed='geo-quartet-9840'):
    """A finished game in teacher_ab's layout, played by uniformly random choices."""
    from gaia_rl import Environment
    env = Environment(seed, 2000)
    rng = random.Random(1)
    snapshot = json.loads(env.snapshot_json())
    factions = None
    game = root/'lab-test'/'pair-000'/'game-0-A02'
    game.mkdir(parents=True)
    with gzip.open(game/'decisions.jsonl.gz', 'wt') as out:
        while not env.is_terminal():
            index = rng.randrange(len(snapshot['candidates']))
            out.write(json.dumps({'decision_id': snapshot['decision_id'], 'index': index, 'arm': 'A', 'seconds': 0})+'\n')
            env.step(snapshot['decision_id'], index)
            snapshot = json.loads(env.snapshot_json())
            factions = factions or [p['faction'] for p in snapshot['state']['players']]
    factions = [p['faction'] for p in snapshot['state']['players']]
    (game/'result.json').write_text(json.dumps({'seed': seed, 'factions': factions, 'a_seats': [0, 2],
        'complete': True, 'scores': {str(k): v for k, v in env.final_scores()}}))
    return game


class AbReplayTests(unittest.TestCase):
    def test_export_reproduces_scores_and_writes_a_catalog(self):
        root = Path(tempfile.mkdtemp())
        game = fake_game(root)
        replay = ab_replays.replay_game(game, 'B', 'test')
        self.assertIn(replay['metadata']['focus_player'], (1, 3))
        self.assertIn('B팔 (A 좌석 0,2)', replay['metadata']['policy'])
        out = root/'out'

        class Args:
            games, output, focus, label = [str(game)], str(out), 'best', None
        ab_replays.cmd_export(Args)
        catalog = json.loads((out/'index.json').read_text())['games']
        self.assertEqual(len(catalog), 1)
        self.assertTrue((out/catalog[0]['file']).exists())

    def test_a_changed_trace_is_refused(self):
        root = Path(tempfile.mkdtemp())
        game = fake_game(root)
        result = json.loads((game/'result.json').read_text())
        result['scores']['0'] += 1
        (game/'result.json').write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            ab_replays.replay_game(game, 'best', 'test')


if __name__ == '__main__':
    unittest.main()
