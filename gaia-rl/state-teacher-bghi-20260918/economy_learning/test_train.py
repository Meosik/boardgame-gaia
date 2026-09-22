import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from gaia_rl.encoding import FeatureEncoder
from economy_learning.train import load_initial, validate_splits

ROOT = Path(__file__).resolve().parents[3]


class ContinuedLearningTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/'gaia-rl/runs/strategy-pilot-v2/manifest.json').read_text())

    def test_original_splits_are_native_compatible_disjoint_and_seat_balanced(self):
        before = copy.deepcopy(self.manifest)
        train, validation, evaluation = validate_splits(self.manifest)
        self.assertEqual([len(train), len(validation), len(evaluation)], [6, 2, 4])
        self.assertEqual(before, self.manifest)

    def test_overlap_is_rejected_before_simulation(self):
        self.manifest['validation'][0] = self.manifest['training'][0]
        with patch('economy_learning.train.Environment') as native:
            with self.assertRaisesRegex(ValueError, 'Overlapping'):
                validate_splits(self.manifest)
            native.assert_not_called()

    def test_weights_are_exact_independent_and_original_file_preserved(self):
        path = ROOT/'gaia-rl/runs/strategy-pilot-v2/baseline/inference.pt'
        original = path.read_bytes()
        model, initial = load_initial(FeatureEncoder(2048), path)
        key = next(iter(initial))
        before = initial[key].clone()
        with torch.no_grad():
            model.state_dict()[key].add_(1)
        torch.testing.assert_close(initial[key], before, rtol=0, atol=0)
        self.assertEqual(path.read_bytes(), original)

    def test_nonfinite_starting_weights_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad.pt'
            torch.save({'bad': torch.tensor(float('nan'))}, path)
            with self.assertRaisesRegex(ValueError, 'Invalid'):
                load_initial(FeatureEncoder(2048), path)


if __name__ == '__main__':
    unittest.main()
