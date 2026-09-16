import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from gaia_rl._native import Environment
from gaia_rl.versions import runtime_versions
from watch_ai_game import GameObserver, GrowingTrace


class GrowingTraceTests(unittest.TestCase):
    def test_partial_gzip_and_partial_json_wait_without_replaying_old_rows(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'decisions.jsonl.gz'
            with gzip.open(path, 'wb') as stream:
                stream.write(b'{"step":'); stream.flush()
                reader = GrowingTrace(path)
                try:
                    self.assertEqual(list(reader.rows()), [])
                    stream.write(b'1}\n'); stream.flush()
                    self.assertEqual(list(reader.rows()), [{'step': 1}])
                    self.assertEqual(list(reader.rows()), [])
                    stream.write(b'{"step":2}\n'); stream.flush()
                    self.assertEqual(list(reader.rows()), [{'step': 2}])
                finally:
                    reader.close()


class NativeObserverTests(unittest.TestCase):
    def test_real_flushed_actions_without_training_changes_or_repeat_revisions(self):
        seed = 'live-observer-native-smoke'
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'game'; source.mkdir()
            env = Environment(seed, 2000)
            with gzip.open(source / 'decisions.jsonl.gz', 'wt') as stream:
                stream.flush()
                observer = GameObserver(source, {'versions': runtime_versions()}, root / 'live', seed)
                try:
                    self.assertEqual(observer.poll(), 'waiting')
                    for _ in range(3):
                        snapshot = json.loads(env.snapshot_json())
                        stream.write(json.dumps({'snapshot': snapshot, 'index': 0}) + '\n'); stream.flush()
                        env.step(snapshot['decision_id'], 0)
                        self.assertEqual(observer.poll(), 'running')
                        expected = json.loads(env.snapshot_json())['state']; expected.pop('event_log', None)
                        self.assertEqual(observer.replay['frames'][-1]['state'], expected)
                    revision = observer.writer.revision
                    observer.poll()
                    self.assertEqual(observer.writer.revision, revision)
                    bad = copy.deepcopy(json.loads(env.snapshot_json()))
                    bad['state']['players'][0]['vp'] += 99
                    with self.assertRaisesRegex(ValueError, 'mismatch'):
                        observer.accept({'snapshot': bad, 'index': 0})
                    self.assertEqual(observer.writer.revision, revision)
                    (source / 'failure.json').write_text('{}')
                    self.assertEqual(observer.poll(), 'failed')
                    catalog = json.loads((root / 'live/index.json').read_text())
                    self.assertEqual(catalog['games'][0]['status'], 'failed')
                finally:
                    observer.close()


if __name__ == '__main__':
    unittest.main()
