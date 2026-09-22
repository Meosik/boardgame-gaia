"""Tiny synthetic records prove wiring/isolation, not teacher quality or strength."""
import json
from pathlib import Path
import tempfile
import unittest

import torch

from gaia_rl import Environment
from gaia_rl.encoding import FeatureEncoder
from faction_learning.behavior import dataset, train
from faction_learning.models import initialize, read_catalog
from faction_learning.test_teacher_records import record


class TeacherBCTests(unittest.TestCase):
    def test_native_teacher_records_update_only_the_same_faction_in_a_new_branch(self):
        torch.set_num_threads(2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            initial = record(path/'training')
            faction = initial['state']['players'][1]['faction']
            validation_seed = None
            for i in range(100):
                seed = f'teacher-bc-validation-{i}'
                state = json.loads(Environment(seed, 2000).snapshot_json())
                if faction in [p['faction'] for p in state['state']['players'][1:3]]:
                    validation_seed = seed
                    break
            self.assertIsNotNone(validation_seed)
            record(path/'validation', validation_seed)
            catalog = initialize(path/'models')
            report = train(path/'models', path/'branch', faction,
                           [path/'training'], [path/'validation'], epochs=1, label_source='teacher')
            self.assertEqual(report['label_source'], 'teacher')
            self.assertGreater(report['gradient_steps'], 0)
            self.assertFalse(report['promotion'])
            self.assertEqual(read_catalog(path/'models'), catalog)
            branch = read_catalog(path/'branch')
            for other in catalog['models']:
                changed = branch['models'][other]['sha256'] != catalog['models'][other]['sha256']
                self.assertEqual(changed, other == faction)
            for split in ('training', 'validation'):
                self.assertTrue(report['datasets'][split][0]['native_replayed'])
                self.assertEqual(report['datasets'][split][0]['label_source'], 'teacher')

    def test_train_validation_overlap_and_wrong_role_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'game'
            initial = record(path)
            faction = initial['state']['players'][1]['faction']
            encoder = FeatureEncoder(4096)
            with self.assertRaisesRegex(ValueError, 'Duplicate/leaked'):
                dataset([path], [path], faction, encoder, label_source='teacher')
            with self.assertRaisesRegex(ValueError, 'human labels'):
                dataset([path], [path], faction, encoder)


if __name__ == '__main__':
    unittest.main()
