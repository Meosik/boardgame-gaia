from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gaia_rl.versions import runtime_versions
from faction_learning.models import digest, write_json
from faction_learning.records import NativeRecorder, state_hash
from faction_teachers.clock import AdaptiveClock
from faction_teachers.continuation import load_continuation
from faction_teachers.__main__ import collect
from four_factions.provenance import hashes


class ContinuationTests(unittest.TestCase):
    def fixture(self, root):
        seed = 'clock-continuation-fixture'
        source = root/'old'
        manifest = {'versions': runtime_versions(), 'source_hashes': hashes()}
        recorder = NativeRecorder(source, seed, teacher_seats=range(4),
                                  teacher_spec={'name': 'fixture-not-expert', **manifest})
        prefix, audits = [], []
        for _ in range(3):
            before = recorder.current
            recorder.step(before['decision_id'], 0, controller='teacher')
            prefix.append(0)
            audits.append({'decision_id': before['decision_id'], 'index': 0, 'audit': {'fixture': True}})
        recorder.close()
        current = recorder.current
        (source/'teacher-audit.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in audits))
        clock = AdaptiveClock()
        clock.spend({'player': 0, 'decision_id': 1})
        checkpoint = {'schema': 1, 'source': str(source), 'seed': seed, 'prefix': prefix,
                      'snapshot': current, 'snapshot_sha256': state_hash(current),
                      'header_sha256': digest(source/'recording.json'),
                      'trace_sha256': digest(source/'decisions.jsonl'), 'source_manifest': manifest,
                      'memory': {'_plans': {}, '_clock': clock.state()}}
        path = root/'checkpoint.json'; write_json(path, checkpoint)
        return path, checkpoint

    def test_same_position_memory_clock_and_old_provenance_survive_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, saved = self.fixture(root)
            new = root/'new'
            def stop_at_resume(policy, snapshot):
                self.assertEqual(snapshot, saved['snapshot'])
                self.assertEqual(policy.prefix, saved['prefix'])
                self.assertEqual(policy.memory, saved['memory'])
                self.assertEqual(policy.adaptive_clock.remaining(0), 5)
                raise RuntimeError('diagnostic stop before any new move')
            with patch('faction_teachers.teacher.SharedTeacher.choose', new=stop_at_resume):
                with self.assertRaisesRegex(RuntimeError, 'diagnostic stop'):
                    collect(new, saved['seed'], adaptive=True, resume_checkpoint=path)
            self.assertEqual((new/'decisions.jsonl').read_bytes(),
                             (Path(saved['source'])/'decisions.jsonl').read_bytes())
            header = json.loads((new/'recording.json').read_text())
            self.assertEqual(header['teacher_spec']['continuation']['imported_steps'], 3)
            self.assertEqual(header['teacher_spec']['continuation']['original_teacher_spec']['name'],
                             'fixture-not-expert')
            self.assertTrue((new/'failure.json').exists())
            self.assertFalse((new/'complete.json').exists())

    def test_changed_trace_wrong_seed_and_fake_snapshot_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path, saved = self.fixture(root)
            with self.assertRaises(ValueError):
                load_continuation(path, 'different-seed')
            altered = deepcopy(saved); altered['snapshot']['state']['round'] = 6
            path.write_text(json.dumps(altered))
            with self.assertRaises(ValueError):
                load_continuation(path, saved['seed'])
            path.write_text(json.dumps(saved))
            with (Path(saved['source'])/'decisions.jsonl').open('a') as stream:
                stream.write('{}\n')
            with self.assertRaises(ValueError):
                load_continuation(path, saved['seed'])


if __name__ == '__main__':
    unittest.main()
