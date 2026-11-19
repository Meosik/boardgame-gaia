import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import teacher_version as tv

FILES = {
    'gaia-rl/tools/ai_worker.py': '# worker\n',
    'gaia-rl/tools/teacher_patches.py': 'def good_factory(seed, **kwargs):\n    pass\n',
    'gaia-rl/baseline-teacher-20260917/x.py': 'x = 1\n',
    'gaia-rl/research/strategy/bgg-openings-part2.csv': 'a,b\n',
    'gaia-frontend/src/data/a.json': '{}\n',
    'gaia-engine/data/b.json': '{}\n',
    'gaia-engine/src/lib.rs': '// one\n',
    'README.md': 'readme\n',
}


def run(cwd, *args):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit(repo, msg):
    run(repo, 'git', 'add', '-A')
    run(repo, 'git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', msg)
    return run(repo, 'git', 'rev-parse', 'HEAD')


class TeacherVersionTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.repo = self.tmp / 'repo'
        self.repo.mkdir()
        run(self.repo, 'git', 'init', '-q')
        for rel, text in FILES.items():
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        self.first = commit(self.repo, 'first')
        self.vdir = self.tmp / 'versions'

    def add(self, **kw):
        kw.setdefault('live_dir', self.repo)
        kw.setdefault('factory', 'good_factory')
        return tv.add(self.repo, self.vdir, self.first, **kw)

    def test_add(self):
        name = self.add(today=date(2026, 11, 19))
        self.assertRegex(name, r'^20261119-[0-9a-f]{7}$')
        d = self.vdir / name
        for rel in ['gaia-rl/baseline-teacher-20260917/x.py', 'gaia-rl/tools/ai_worker.py',
                    'gaia-rl/research/strategy/bgg-openings-part2.csv',
                    'gaia-frontend/src/data/a.json', 'gaia-engine/data/b.json']:
            self.assertTrue((d / rel).is_file(), rel)
        meta = json.loads((d / 'teacher.json').read_text())
        self.assertEqual(meta['factory'], 'good_factory')
        self.assertEqual(meta['commit'], self.first)
        self.assertIs(meta['engine_same_as_deployed'], True)
        self.assertFalse((d / 'README.md').exists())
        self.assertFalse((d / 'gaia-engine/src').exists())
        self.assertEqual([p.name for p in self.vdir.glob('.tmp-*')], [])
        self.assertFalse((self.vdir / 'current').exists())

    def test_unknown_factory(self):
        with self.assertRaises(SystemExit):
            self.add(factory='nope')
        self.assertEqual(list(self.vdir.glob('*')) if self.vdir.exists() else [], [])

    def test_engine_differs(self):
        (self.repo / 'gaia-engine/src/lib.rs').write_text('// two\n')
        second = commit(self.repo, 'second')
        live = self.tmp / 'live'
        run(self.repo, 'git', 'worktree', 'add', '-q', '--detach', str(live), self.first)
        with self.assertRaises(SystemExit) as cm:
            tv.add(self.repo, self.vdir, second, 'good_factory', live_dir=live)
        self.assertIn('deploy', str(cm.exception))
        name = tv.add(self.repo, self.vdir, second, 'good_factory', live_dir=live, force_engine=True)
        meta = json.loads((self.vdir / name / 'teacher.json').read_text())
        self.assertIs(meta['engine_same_as_deployed'], False)

    def test_no_live_dir(self):
        missing = self.tmp / 'nolive'
        with self.assertRaises(SystemExit):
            self.add(live_dir=missing)
        name = self.add(live_dir=missing, force_engine=True)
        meta = json.loads((self.vdir / name / 'teacher.json').read_text())
        self.assertIsNone(meta['deployed_commit'])

    def test_bad_names(self):
        for bad in ['../x', '.hidden', 'current', 'builtin', 'a b']:
            with self.assertRaises(SystemExit, msg=bad):
                self.add(name=bad)
        self.add(name='v1')
        with self.assertRaises(SystemExit):
            self.add(name='v1')

    def test_use(self):
        name = self.add(name='v1')
        with self.assertRaises(SystemExit):
            tv.use(self.vdir, 'nope')
        self.assertFalse((self.vdir / 'current').exists())
        tv.use(self.vdir, name)
        self.assertEqual((self.vdir / 'current').read_text(), name + '\n')
        self.assertEqual(tv.current(self.vdir), name)
        with self.assertRaises(SystemExit):
            tv.use(self.vdir, 'nope')
        self.assertEqual(tv.current(self.vdir), name)
        tv.use(self.vdir, 'builtin')
        self.assertEqual((self.vdir / 'current').read_text(), '')
        self.assertFalse((self.vdir / '.current.tmp').exists())

    def test_versions(self):
        self.add(name='v1')
        (self.vdir / '.tmp-x/gaia-rl/tools').mkdir(parents=True)
        (self.vdir / '.tmp-x/gaia-rl/tools/ai_worker.py').write_text('')
        (self.vdir / 'plain').mkdir()
        self.assertEqual([n for n, _ in tv.versions(self.vdir)], ['v1'])


if __name__ == '__main__':
    unittest.main()
