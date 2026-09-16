import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from watch_game import play


class WatchGameTests(unittest.TestCase):
    def test_completed_game_matches_existing_example(self):
        with tempfile.TemporaryDirectory() as directory:
            result = play('engine-kit-example', Path(directory))
            self.assertTrue(result['complete'])
            self.assertEqual(result['steps'], 123)
            self.assertEqual(result['scores'], [(0, 38), (1, 40), (2, 33), (3, 50)])
            catalog = json.loads((Path(directory) / 'ai-live/index.json').read_text())
            game = catalog['games'][0]
            self.assertEqual(game['status'], 'complete')
            replay = json.loads(gzip.decompress((Path(directory) / 'ai-live' / game['file']).read_bytes()))
            self.assertEqual(len(replay['frames']), 124)

    def test_bad_policy_marks_failure_instead_of_passing(self):
        with tempfile.TemporaryDirectory() as directory, patch('watch_game.choose', return_value=-1):
            with self.assertRaisesRegex(ValueError, 'invalid candidate'):
                play('engine-kit-example', Path(directory))
            game = json.loads((Path(directory) / 'ai-live/index.json').read_text())['games'][0]
            self.assertEqual(game['status'], 'failed')
            self.assertEqual(game['steps'], 0)

    def test_step_limit_keeps_nonterminal_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(Exception, 'step limit'):
                play('engine-kit-example', Path(directory), max_steps=1)
            game = json.loads((Path(directory) / 'ai-live/index.json').read_text())['games'][0]
            self.assertEqual(game['status'], 'failed')
            self.assertEqual(game['steps'], 1)


if __name__ == '__main__':
    unittest.main()
