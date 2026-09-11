import json
from pathlib import Path
import tempfile
import unittest

from publish_replays import publish


class PublishReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root/'published'

    def batch(self, name, count):
        path = self.root/name
        path.mkdir()
        games = [{'id': f'{name}-{i}', 'file': f'{name}-{i}.json.gz'} for i in range(count)]
        for game in games:
            (path/game['file']).write_bytes(game['id'].encode())
        (path/'index.json').write_text(json.dumps({'schema_version': 1, 'games': games}))
        return path

    def catalog(self, name='index.json'):
        return json.loads((self.dest/name).read_text())['games']

    def test_newest_24_preserves_files_and_old_metadata(self):
        old = self.batch('old', 24)
        # Bootstrap an existing catalog with no archive yet.
        import shutil
        shutil.copytree(old, self.dest)
        original = {p.name: p.read_bytes() for p in self.dest.glob('*.gz')}
        new = self.batch('new', 3)
        self.assertEqual(publish(new, self.dest), (24, 27))
        self.assertEqual([g['id'] for g in self.catalog()][:4], ['new-0', 'new-1', 'new-2', 'old-0'])
        self.assertEqual(len(self.catalog('archive-index.json')), 27)
        for name, data in original.items():
            self.assertEqual((self.dest/name).read_bytes(), data)
        publish(self.batch('latest', 24), self.dest)
        self.assertTrue(all(g['id'].startswith('latest') for g in self.catalog()))
        self.assertEqual(len(list(self.dest.glob('*.gz'))), 51)
        before = (self.dest/'index.json').read_bytes()
        publish(new, self.dest)
        self.assertEqual((self.dest/'index.json').read_bytes(), before)

    def test_collision_leaves_catalog_and_files_untouched(self):
        batch = self.batch('new', 2)
        publish(batch, self.dest)
        before = {p.name: p.read_bytes() for p in self.dest.iterdir()}
        (batch/'new-1.json.gz').write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'collision'):
            publish(batch, self.dest)
        self.assertEqual({p.name: p.read_bytes() for p in self.dest.iterdir()}, before)

    def test_incomplete_export_does_not_change_destination(self):
        batch = self.batch('new', 1)
        (batch/'new-0.json.gz').unlink()
        with self.assertRaises(FileNotFoundError):
            publish(batch, self.dest)
        self.assertFalse((self.dest/'index.json').exists())

    def test_unsafe_filename_rejected(self):
        batch = self.batch('new', 1)
        catalog = json.loads((batch/'index.json').read_text())
        catalog['games'][0]['file'] = '../escape.json.gz'
        (batch/'index.json').write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            publish(batch, self.dest)


if __name__ == '__main__':
    unittest.main()
