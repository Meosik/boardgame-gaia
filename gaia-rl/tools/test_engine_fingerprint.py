import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import engine_fingerprint as ef

FILES = {
    'gaia-engine/Cargo.toml': '[package]\n',
    'gaia-engine/src/lib.rs': '// one\n',
    'gaia-engine/data/b.json': '{}\n',
    'gaia-rl/src/lib.rs': '// rl\n',
    'gaia-rl/python/gaia_rl/__init__.py': 'x = 1\n',
    'gaia-rl/tools/x.py': 'print(1)\n',
    'README.md': 'readme\n',
}


def run(cwd, *args):
    r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit(repo, msg):
    run(repo, 'git', 'add', '-A')
    run(repo, 'git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', msg)


def write(repo, rel, text):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class EngineFingerprintTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.repo = Path(self._td.name)
        run(self.repo, 'git', 'init', '-q')
        for rel, text in FILES.items():
            write(self.repo, rel, text)
        commit(self.repo, 'first')

    def test_folder_equals_commit(self):
        fp = ef.of_folder(self.repo)
        self.assertRegex(fp, r'^[0-9a-f]{64}$')
        self.assertEqual(fp, ef.of_commit(self.repo, 'HEAD'))

    def test_build_leftovers_ignored(self):
        before = ef.of_folder(self.repo)
        write(self.repo, 'gaia-rl/python/gaia_rl/__pycache__/x.pyc', 'junk')
        write(self.repo, 'gaia-rl/python/gaia_rl/_native.so', 'junk')
        write(self.repo, 'gaia-rl/tools/y.py', 'untracked')
        self.assertEqual(ef.of_folder(self.repo), before)

    def test_commits(self):
        fp1 = ef.of_commit(self.repo, 'HEAD')
        write(self.repo, 'README.md', 'changed\n')
        write(self.repo, 'gaia-rl/tools/x.py', 'print(2)\n')
        commit(self.repo, 'second')
        fp2 = ef.of_commit(self.repo, 'HEAD')
        self.assertEqual(fp1, fp2)
        write(self.repo, 'gaia-engine/src/lib.rs', '// two\n')
        commit(self.repo, 'third')
        fp3 = ef.of_commit(self.repo, 'HEAD')
        self.assertNotEqual(fp2, fp3)
        write(self.repo, 'gaia-rl/python/gaia_rl/__init__.py', 'x = 2\n')
        commit(self.repo, 'fourth')
        fp4 = ef.of_commit(self.repo, 'HEAD')
        self.assertNotEqual(fp3, fp4)

    def test_path_is_part_of_it(self):
        d = 'a' * 64
        self.assertNotEqual(ef.combine({'a': d}), ef.combine({'b': d}))
        self.assertRegex(ef.combine({}), r'^[0-9a-f]{64}$')

    def test_counted(self):
        self.assertTrue(ef.counted('gaia-rl/src/lib.rs'))
        self.assertFalse(ef.counted('gaia-rl/python/gaia_rl/__pycache__/x.py'))
        self.assertFalse(ef.counted('gaia-rl/target/x.rs'))
        self.assertFalse(ef.counted('gaia-rl/python/gaia_rl/_native.so'))


if __name__ == '__main__':
    unittest.main()
