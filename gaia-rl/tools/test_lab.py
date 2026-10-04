"""lab.py: seed allocation, command experiments and recorded (external) results, without git."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

import lab


class LabTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir/'queue').mkdir()
        (self.dir/'results').mkdir()
        (self.dir/'seeds.txt').write_text('# header\ns-1\ns-2\ns-3\ns-4\n')
        lab.LAB = self.dir

    def queue(self, name, spec):
        (self.dir/'queue'/f'{name}.json').write_text(json.dumps(spec))

    def test_seeds_skip_those_queued_or_already_used(self):
        self.queue('a', {'kind': 'ab', 'seeds': ['s-1']})
        (self.dir/'results'/'old.json').write_text(json.dumps({'status': 'done', 'seeds': ['s-3']}))
        self.assertEqual(lab.allocate(2), ['s-2', 's-4'])
        with self.assertRaises(SystemExit):
            lab.allocate(3)

    def test_command_experiment_writes_a_result_and_leaves_the_queue(self):
        metrics = self.dir/'m.json'
        self.queue('cmd', {'kind': 'command', 'note': 'smoke',
                           'run': ['{python}', '-c', f'import json; json.dump({{"win": 0.5}}, open({str(metrics)!r}, "w")); print("hi")'],
                           'metrics': str(metrics)})
        self.queue('seraph', {'kind': 'external'})
        self.assertEqual([n for n, _ in lab.pending()], ['cmd', 'seraph'])
        self.assertEqual(lab.run_pending(jobs=1, push=False), 1)
        r = lab.result('cmd')
        self.assertEqual((r['status'], r['metrics']), ('done', {'win': 0.5}))
        self.assertIn('hi', (self.dir/'results'/'cmd.md').read_text())
        self.assertEqual([n for n, _ in lab.pending()], ['seraph'])

    def test_record_adds_an_external_result(self):
        self.queue('seraph', {'kind': 'external', 'note': 'PPO'})
        metrics = self.dir/'ppo.json'
        metrics.write_text(json.dumps({'updates': 1, 'loss': 0.25}))
        sys.argv = ['lab.py', 'record', 'seraph', '--metrics', str(metrics)]
        lab.main()
        r = lab.result('seraph')
        self.assertEqual((r['kind'], r['note'], r['metrics']['loss']), ('external', 'PPO', 0.25))
        self.assertEqual(lab.pending(), [])

    def test_timing_summarises_decision_seconds_per_arm(self):
        import gzip
        game = self.dir/'run'/'pair-000'/'game-0-A02'
        game.mkdir(parents=True)
        with gzip.open(game/'decisions.jsonl.gz', 'wt') as out:
            for arm, s in [('A', 1.0), ('A', 3.0), ('B', 2.0)]:
                out.write(json.dumps({'arm': arm, 'seconds': s})+'\n')
        stats = lab.timing(self.dir/'run')
        self.assertEqual((stats['A']['n'], stats['A']['mean'], stats['B']['max']), (2, 2.0, 2.0))


if __name__ == '__main__':
    unittest.main()
