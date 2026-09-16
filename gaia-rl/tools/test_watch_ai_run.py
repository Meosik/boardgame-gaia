import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest

from gaia_rl._native import Environment
from gaia_rl.versions import runtime_versions
from watch_ai_run import RunObserver, recorded_games


class RunObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / 'run'
        self.run.mkdir()
        self.seed = 'run-observer-native-smoke'
        env = Environment(self.seed, 2000)
        self.snapshot = json.loads(env.snapshot_json())
        self.factions = [p['faction'] for p in self.snapshot['state']['players']]
        self.manifest = {'versions': runtime_versions(), 'factions': self.factions,
            'setups': {'training': [{'seed': self.seed}], 'validation': [],
                       'evaluation': [{'seed': self.seed}]}}
        (self.run / 'manifest.json').write_text(json.dumps(self.manifest))
        (self.run / 'progress.json').write_text('{"stage":"demonstrations"}')
        self.observer = RunObserver(self.run, self.root / 'live')
        self.addCleanup(self.observer.close)

    def trace(self, relative):
        path = self.run / relative
        path.mkdir(parents=True)
        with gzip.open(path / 'decisions.jsonl.gz', 'wt') as stream:
            stream.write(json.dumps({'snapshot': self.snapshot, 'index': 0}) + '\n')
        return path

    def catalog(self):
        return json.loads((self.root / 'live/index.json').read_text())['games']

    def test_waits_without_starting_games_and_rejects_reusing_output(self):
        self.assertEqual(self.observer.poll(), 'waiting')
        self.assertEqual(recorded_games(self.run, self.manifest), [])
        with self.assertRaises(FileExistsError):
            RunObserver(self.run, self.root / 'live')

    def test_new_game_switch_preserves_old_record_and_focal_identity(self):
        first = self.trace('training/0')
        self.observer.poll()
        old = self.catalog()[0]
        payload = (self.root / 'live' / old['file']).read_bytes()
        self.assertEqual(old['status'], 'running')
        (first / 'failure.json').write_text('{}')
        next_game = self.trace('evaluation/teacher/0-' + self.factions[1])
        timestamp = (first / 'decisions.jsonl.gz').stat().st_mtime_ns + 1_000_000
        os.utime(next_game / 'decisions.jsonl.gz', ns=(timestamp, timestamp))
        self.observer.poll()
        games = self.catalog()
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0]['faction'], self.factions[1])
        self.assertEqual(games[0]['status'], 'running')
        self.assertEqual(games[1]['status'], 'failed')
        self.assertEqual((self.root / 'live' / old['file']).read_bytes(), payload)
        replay = json.loads(gzip.decompress((self.root / 'live' / games[0]['file']).read_bytes()))
        self.assertEqual(replay['metadata']['focus_player'], 1)
        before = (self.root / 'live/index.json').read_bytes()
        self.observer.poll()
        self.assertEqual((self.root / 'live/index.json').read_bytes(), before)

    def test_stopped_producer_marks_partial_record_failed_without_final_scores(self):
        self.trace('training/0')
        self.observer.poll()
        self.observer.producer_stopped()
        game = self.catalog()[0]
        self.assertEqual(game['status'], 'failed')
        replay = json.loads(gzip.decompress((self.root / 'live' / game['file']).read_bytes()))
        self.assertNotIn('scores', replay['metadata'])

    def test_failed_run_ends_observer(self):
        self.trace('training/0')
        (self.run / 'progress.json').write_text('{"stage":"failed"}')
        self.assertEqual(self.observer.poll(), 'failed')
        self.assertEqual(self.catalog()[0]['status'], 'failed')

    def test_competitive_run_has_distinct_spectator_policy_label(self):
        self.observer.manifest['mode'] = 'competitive_teacher'
        self.trace('training/0')
        self.observer.poll()
        self.assertEqual(self.catalog()[0]['policy'], 'quartet_teacher')

    def test_retains_finished_previous_catalog_without_rewriting_payload(self):
        self.trace('training/0')
        self.observer.poll()
        self.observer.producer_stopped()
        old = self.catalog()[0]
        next_observer = RunObserver(self.run, self.root / 'next-live', previous=self.root / 'live')
        self.addCleanup(next_observer.close)
        self.assertEqual(next_observer.entries[old['id']], old)
        self.assertEqual((self.root / 'next-live' / old['file']).read_bytes(),
                         (self.root / 'live' / old['file']).read_bytes())

    def test_does_not_transfer_an_active_observer_as_finished(self):
        self.trace('training/0')
        self.observer.poll()
        with self.assertRaisesRegex(ValueError, 'finish'):
            RunObserver(self.run, self.root / 'next-live', previous=self.root / 'live')


if __name__ == '__main__':
    unittest.main()
