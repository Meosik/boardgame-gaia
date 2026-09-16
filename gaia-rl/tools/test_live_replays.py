import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from gaia_rl._native import Environment
from gaia_rl.versions import runtime_versions
from evaluation_replays import frame, validate_replay
from live_replays import LiveReplayWriter


class LiveReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.writer = LiveReplayWriter(Path(self.temp.name)/'live', 'test')
        self.env = Environment('live-replay-native-test', 2000)
        s = json.loads(self.env.snapshot_json())
        self.record = {'schema_version': 1, 'metadata': {'seed': 'live-replay-native-test',
            'policy': 'test', 'faction': s['state']['players'][0]['faction'],
            'focus_player': 0, 'versions': runtime_versions(), 'steps': 0},
            'frames': [frame(s)], 'events': []}

    def test_real_prefix_revisions_are_immutable_and_not_completed_replays(self):
        original = copy.deepcopy(self.record)
        first = self.writer.write(self.record)
        first_bytes = (self.writer.directory/first['file']).read_bytes()
        s = json.loads(self.env.snapshot_json())
        self.env.step(s['decision_id'], 0)
        after = json.loads(self.env.snapshot_json())
        self.record['frames'].append(frame(after, s['player'], s['candidates'][0]['action'], s['candidates']))
        second = self.writer.write(self.record)
        self.assertEqual(first_bytes, (self.writer.directory/first['file']).read_bytes())
        self.assertEqual(first['steps'], 0)
        self.assertEqual(second['steps'], 1)
        self.assertNotEqual(first['file'], second['file'])
        live = json.loads(gzip.decompress((self.writer.directory/second['file']).read_bytes()))
        self.assertEqual(live['metadata']['steps'], 1)
        self.assertNotIn('scores', live['metadata'])
        with self.assertRaisesRegex(ValueError, 'completed'):
            validate_replay(live)
        self.assertEqual(self.record['frames'][0], original['frames'][0])

    def test_failure_preserves_last_real_state_without_final_scores(self):
        game = self.writer.write(self.record, 'failed')
        replay = json.loads(gzip.decompress((self.writer.directory/game['file']).read_bytes()))
        self.assertEqual(replay['metadata']['live_status'], 'failed')
        self.assertEqual(replay['frames'], self.record['frames'])
        self.assertNotIn('scores', replay['metadata'])

    def test_incomplete_cannot_claim_complete_or_modify_catalog(self):
        first = self.writer.write(self.record)
        with self.assertRaises(ValueError):
            self.writer.write(self.record, 'complete')
        catalog = json.loads((self.writer.directory/'index.json').read_text())
        self.assertEqual(catalog['games'], [first])

    def test_noncontiguous_prefix_and_reused_directory_rejected(self):
        self.record['frames'][0]['decision_id'] = 1
        with self.assertRaises(ValueError):
            self.writer.write(self.record)
        with self.assertRaises(FileExistsError):
            LiveReplayWriter(self.writer.directory, 'other')

    def test_cannot_change_identity_or_past_frames(self):
        first = self.writer.write(self.record)
        for change in ('identity', 'history'):
            broken = copy.deepcopy(self.record)
            if change == 'identity':
                broken['metadata']['seed'] = 'another-game'
            else:
                broken['frames'][0]['state']['players'][0]['vp'] += 1
            with self.assertRaisesRegex(ValueError, 'append-only'):
                self.writer.write(broken)
        self.assertEqual(json.loads((self.writer.directory/'index.json').read_text())['games'], [first])

    def test_failed_recording_cannot_silently_resume(self):
        self.writer.write(self.record, 'failed')
        with self.assertRaisesRegex(ValueError, 'cannot be resumed'):
            self.writer.write(self.record)


if __name__ == '__main__':
    unittest.main()
