import subprocess
import sys
import unittest
from unittest.mock import patch

from gaia_rl.versions import runtime_versions
from four_factions.provenance import hashes, verify


class ProvenanceTests(unittest.TestCase):
    def test_competition_import_and_guard_do_not_import_training(self):
        code = '''import sys
from importlib.abc import MetaPathFinder
class NoTraining(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'strategy_pilot') or fullname == 'four_factions.train':
            raise AssertionError('Competition imported training: '+fullname)
sys.meta_path.insert(0, NoTraining())
from four_factions import compete
from gaia_rl.versions import runtime_versions
compete.verify({'versions':runtime_versions(),'source_hashes':compete.hashes()})
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pinned_source_mismatch_still_fails_closed(self):
        manifest = {'versions': runtime_versions(), 'source_hashes': hashes()}
        verify(manifest)
        with patch('four_factions.provenance.hashes', return_value={}):
            with self.assertRaisesRegex(ValueError, 'Pinned experiment/income sources changed'):
                verify(manifest)


if __name__ == '__main__':
    unittest.main()
