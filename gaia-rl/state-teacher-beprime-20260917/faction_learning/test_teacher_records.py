"""Synthetic controller ownership fixtures, not expert demonstrations."""
import json
from pathlib import Path
import tempfile
import unittest

from gaia_rl.encoding import FeatureEncoder
from faction_learning.records import NativeRecorder, audited_samples
from faction_learning.models import digest


SPEC = {'name': 'test-controller-only', 'source_hashes': {'fixture': '0' * 64}}


def record(path, seed='teacher-record-test-0'):
    recorder = NativeRecorder(path, seed, [0], teacher_seats=[1, 2], teacher_spec=SPEC)
    initial = recorder.current
    while recorder.current['candidates']:
        before = recorder.current
        index = next((i for i, c in enumerate(before['candidates'])
                      if c['action']['type'] == 'Pass'), 0)
        actor = before['player']
        controller = 'human' if actor == 0 else 'teacher' if actor in (1, 2) else 'ai'
        recorder.step(before['decision_id'], index, controller=controller)
    recorder.finish()
    return initial


class TeacherRecordTests(unittest.TestCase):
    def test_same_faction_teacher_labels_only_after_complete_native_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'game'
            initial = record(path)
            encoder = FeatureEncoder(4096)
            for actor, player in enumerate(initial['state']['players']):
                rows, audit = audited_samples(path, player['faction'], encoder, controller='teacher')
                self.assertEqual(bool(rows), actor in (1, 2))
                self.assertTrue(all(row[3] == player['faction'] for row in rows))
                self.assertTrue(audit['native_replayed'])
                self.assertEqual(audit['label_source'], 'teacher')
                self.assertEqual(audit['teacher_spec'], SPEC)
            human, audit = audited_samples(path, initial['state']['players'][0]['faction'], encoder)
            self.assertTrue(human)
            self.assertEqual(audit['label_source'], 'human')

    def test_teacher_seats_need_provenance_and_cannot_overlap_humans(self):
        with tempfile.TemporaryDirectory() as folder:
            for kwargs in ({'teacher_seats': [0], 'teacher_spec': SPEC},
                           {'teacher_seats': [1]}, {'teacher_seats': [True], 'teacher_spec': SPEC}):
                with self.assertRaises(ValueError):
                    NativeRecorder(Path(folder)/'invalid', 'test', [0], **kwargs)
            self.assertFalse((Path(folder)/'invalid').exists())

    def test_relabeling_ai_as_teacher_fails_even_with_recomputed_file_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'game'
            initial = record(path)
            lines = [json.loads(line) for line in (path/'decisions.jsonl').read_text().splitlines()]
            row = next(row for row in lines if row['controller'] == 'ai')
            row['controller'] = 'teacher'
            (path/'decisions.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in lines))
            complete = json.loads((path/'complete.json').read_text())
            complete['trace_sha256'] = digest(path/'decisions.jsonl')
            (path/'complete.json').write_text(json.dumps(complete))
            with self.assertRaisesRegex(ValueError, 'controller/native state differs'):
                audited_samples(path, initial['state']['players'][1]['faction'],
                                FeatureEncoder(4096), controller='teacher')

    def test_ai_cannot_be_requested_as_imitation_labels(self):
        with self.assertRaises(ValueError):
            audited_samples('/not-read', 'Terrans', FeatureEncoder(4096), controller='ai')


if __name__ == '__main__':
    unittest.main()
