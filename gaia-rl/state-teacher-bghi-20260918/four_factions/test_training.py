import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from four_factions import FACTIONS
from four_factions.train import samples_from, summary


class TrainingBoundaryTests(unittest.TestCase):
    def test_failed_evaluation_is_counted_without_improvement_claim(self):
        games = [{'complete': True, 'focal': 'Terrans', 'rows': [
            {'faction': 'Terrans', 'vp': 100, 'win_share': 1}]},
            {'complete': False, 'focal': 'Terrans', 'error': 'native failure'}]
        result = summary(games)['Terrans']
        self.assertEqual(result['attempted'], 2)
        self.assertEqual(result['completed'], 1)
        self.assertEqual(result['mean_vp_completed_only'], 100)

    def test_incomplete_tampered_or_missing_faction_demos_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            trace = path/'decisions.jsonl.gz'
            with gzip.open(trace, 'wt') as stream:
                stream.write('')
            receipt = {'native_complete': False, 'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest()}
            audit = path/'native-audit.json'
            audit.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'completion audit'):
                samples_from([path], None)
            receipt['native_complete'] = True
            audit.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'Missing eligible'):
                samples_from([path], None)
            receipt['trace_sha256'] = 'tampered'
            audit.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'changed after'):
                samples_from([path], None)


if __name__ == '__main__':
    unittest.main()
