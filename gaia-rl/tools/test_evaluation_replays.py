import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation_replays import ROOT, export_evaluation, validate_batch, validate_replay


def fixture():
    replay = json.loads((ROOT/'gaia-frontend/src/tests/fixtures/replay.json').read_text())
    scores = {'0': 40, '1': 30, '2': 20, '3': 10}
    replay['metadata'].update(scores=scores, steps=len(replay['frames']) - 1)
    replay['metadata']['faction'] = replay['frames'][0]['state']['players'][replay['metadata']['focus_player']]['faction']
    replay['frames'][-1]['state']['phase'] = {'Ended': {'final_scores': [[int(k), v] for k, v in scores.items()], 'winners': [0]}}
    return replay


class EvaluationReplayTests(unittest.TestCase):
    def test_terminal_scores_and_boundaries_required(self):
        replay = fixture()
        validate_replay(replay)
        for mutate in (
            lambda r: r['frames'][-1]['state'].update(phase='Action'),
            lambda r: r['metadata']['scores'].update({'0': 999}),
            lambda r: r['frames'][-1].update(event_end=99999),
            lambda r: r['metadata'].update(steps=999),
        ):
            bad = copy.deepcopy(replay)
            mutate(bad)
            with self.assertRaises(ValueError):
                validate_replay(bad)

    def test_export_retry_preserves_bytes_and_rejects_changed_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'report.json').write_text('{"games": []}')
            with patch('evaluation_replays.reproduce_ppo', return_value=iter([fixture()])):
                batch = export_evaluation(run)
            before = {p.name: p.read_bytes() for p in batch.iterdir()}
            self.assertEqual(export_evaluation(run), batch)
            self.assertEqual(before, {p.name: p.read_bytes() for p in batch.iterdir()})
            (run/'report.json').write_text('{"games": [], "changed": true}')
            with self.assertRaisesRegex(ValueError, 'changed'):
                export_evaluation(run)

    def test_partial_or_invalid_export_never_becomes_publishable(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'report.json').write_text('{"games": []}')
            def failed():
                yield fixture()
                raise RuntimeError('simulation interrupted')
            with patch('evaluation_replays.reproduce_ppo', return_value=failed()):
                with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                    export_evaluation(run)
            self.assertFalse((run/'browser-replays').exists())

    def test_incomplete_teacher_report_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'report.json').write_text('{"all_complete": false}')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                export_evaluation(run)

    def test_complete_teacher_export_uses_saved_states_without_simulation(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            replay = fixture()
            meta = replay['metadata']
            meta['stage'] = 0
            spec = {'seed': meta['seed'], 'faction': meta['faction'], 'seat': meta['focus_player']}
            (run/'report.json').write_text('{"all_complete": true}')
            (run/'manifest.json').write_text(json.dumps({'specs': [spec], 'stages': [0], 'versions': meta['versions']}))
            (run/'stage0-0.json').write_text(json.dumps({'complete': True, 'steps': meta['steps'],
                                                       'vp': meta['scores'][str(spec['seat'])]}))
            raw = gzip.compress(json.dumps(replay).encode(), mtime=0)
            (run/'stage0-0.json.gz').write_bytes(raw)
            with patch('evaluation_replays.reproduce_ppo') as simulation:
                batch = export_evaluation(run)
                simulation.assert_not_called()
            game = validate_batch(batch)[0]
            exported = json.loads(gzip.decompress((batch/game['file']).read_bytes()))
            self.assertEqual(exported['frames'], replay['frames'])
            self.assertEqual((run/'stage0-0.json.gz').read_bytes(), raw)

    def test_catalog_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run/'report.json').write_text('{"games": []}')
            with patch('evaluation_replays.reproduce_ppo', return_value=iter([fixture()])):
                batch = export_evaluation(run)
            catalog = json.loads((batch/'index.json').read_text())
            catalog['games'][0]['vp'] += 1
            (batch/'index.json').write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError, 'Catalog differs'):
                validate_batch(batch)


if __name__ == '__main__':
    unittest.main()
