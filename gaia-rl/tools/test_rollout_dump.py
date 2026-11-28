import dataclasses
import gzip
import json
import tempfile
import unittest
from pathlib import Path

import rollout_dump

SOURCE = '''
def rollout(current, scores, remaining, goal, actor, step):
    index = 0
    raise ValueError('No eligible continuation; do not silently pass')
'''


@dataclasses.dataclass
class Goal:
    family: str
    target: int


def failing(directory):
    namespace = {}
    exec(compile(SOURCE, str(Path(directory)/'preparation.py'), 'exec'), namespace)
    current = {'player': 2, 'decision_id': 'd7', 'state': {'round': 3},
               'candidates': [{'action': {'type': 'Pass'}}, {'action': {'type': 'Build'}}]}
    scores = [(0, 'conservation blocked: no minimum-cost native PI'), (1, 'fine')]
    try:
        namespace['rollout'](current, scores, Goal('fed', 3), Goal('fed', 5), 1, 4)
    except ValueError as exc:
        return exc


class RolloutDumpTest(unittest.TestCase):
    def test_dump(self):
        with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as src:
            path = rollout_dump.dump_no_continuation(failing(src), out)
            files = list(Path(out).glob('no-continuation-*.json.gz'))
            self.assertEqual([str(files[0])], [path])
            data = json.loads(gzip.open(path, 'rt').read())
            self.assertEqual((data['player'], data['decision_id'], data['round'], data['actor'], data['step']),
                             (2, 'd7', 3, 1, 4))
            self.assertEqual(data['remaining'], {'family': 'fed', 'target': 3})
            self.assertEqual([c['blocked'] for c in data['candidates']], [True, False])
            self.assertEqual(data['candidates'][1]['action'], {'type': 'Build'})
            self.assertEqual(data['current']['decision_id'], 'd7')

    def test_no_rollout_frame(self):
        with tempfile.TemporaryDirectory() as out:
            try:
                raise ValueError('No eligible continuation; do not silently pass')
            except ValueError as exc:
                self.assertIsNone(rollout_dump.dump_no_continuation(exc, out))
            self.assertEqual(list(Path(out).iterdir()), [])

    def test_worker_env_dump_dir_absolute(self):
        import os
        from unittest import mock
        import teacher_ab
        teacher = {'source': '/tmp/teacher-source'}
        with mock.patch.dict(os.environ, clear=False):
            os.environ.pop('GAIA_ROLLOUT_DUMP_DIR', None)
            env = teacher_ab._worker_env(teacher, 'runs/lab-x/pair-000/game-0-A02')
            self.assertEqual(env['GAIA_ROLLOUT_DUMP_DIR'], str(Path('runs/lab-x/pair-000/game-0-A02').resolve()))
            self.assertTrue(Path(env['GAIA_ROLLOUT_DUMP_DIR']).is_absolute())
            self.assertNotIn('GAIA_ROLLOUT_DUMP_DIR', teacher_ab._worker_env(teacher, None))


if __name__ == '__main__':
    unittest.main()
