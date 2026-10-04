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


    def test_broken_files_are_skipped_and_a_broken_result_reruns(self):
        self.queue('ok', {'kind': 'command', 'run': ['true']})
        (self.dir/'queue'/'cut.json').write_text('')
        (self.dir/'results'/'ok.json').write_text('{"status": "do')
        self.assertEqual([n for n, _ in lab.pending()], ['ok'])
        self.assertEqual(lab.allocate(1), ['s-1'])
        self.assertTrue(any(p.endswith('cut.json') for p in lab._broken))

    def test_low_disk_is_announced_once_until_it_recovers(self):
        import shutil
        from unittest import mock
        sent = []
        with mock.patch.object(lab, 'notify', sent.append), \
                mock.patch.object(shutil, 'disk_usage', return_value=mock.Mock(free=5*1024**3)):
            warned = lab.disk_warning(self.dir, False)
            warned = lab.disk_warning(self.dir, warned)
        self.assertTrue(warned)
        self.assertEqual(len(sent), 1)
        with mock.patch.object(shutil, 'disk_usage', return_value=mock.Mock(free=50*1024**3)):
            self.assertFalse(lab.disk_warning(self.dir, warned))


class DiscordTextTests(unittest.TestCase):
    def test_tables_become_short_code_blocks_and_chunks_stay_fenced(self):
        md = ('# x — 완료\n\n| 종족 | 완료 쌍 | 차이 | 구간 | 오류 |\n|---|---:|---:|---|---:|\n'
              '| Geodens | 12 | +2.2 | [-5.5, +9.8] | 0 |\n| **전체** | 12 | -0.9 | [-6.4, +4.6] | 0 |\n\n<sub>vm</sub>\n')
        text = lab.discord_text(md)
        rows = text.split('```')[1].strip().splitlines()
        self.assertEqual([r.split()[0] for r in rows], ['종족', 'Geodens', '전체'])
        self.assertEqual(len({lab._width(r.split('  [')[0]) for r in rows[1:]}), 1)  # columns line up
        self.assertIn('-0.9', rows[2])
        self.assertNotIn('오류', text)
        self.assertNotIn('<sub>', text)
        parts = lab.chunks('a\n```\n' + '\n'.join(['row ' * 20] * 60) + '\n```\nb', size=500)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 520 and p.count('```') % 2 == 0 for p in parts))


class AnnounceTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir/'queue').mkdir()
        (self.dir/'results').mkdir()
        lab.LAB = self.dir
        self.sent = []
        self.original_notify = lab.notify
        lab.notify = self.sent.append

    def tearDown(self):
        lab.notify = self.original_notify

    def test_only_experiments_queued_after_start_are_announced_once(self):
        (self.dir/'queue'/'old.json').write_text(json.dumps({'kind': 'command', 'run': ['true']}))
        seen = lab.announce_new(None)
        self.assertEqual(self.sent, [])
        (self.dir/'queue'/'new.json').write_text(json.dumps(
            {'kind': 'ab', 'note': '깊이 확인', 'teacher_a': 'tools/a.json', 'teacher_b': 'tools/b.json'}))
        seen = lab.announce_new(seen)
        lab.announce_new(seen)
        self.assertEqual(len(self.sent), 1)
        self.assertIn('new', self.sent[0])
        self.assertIn('깊이 확인', self.sent[0])
        self.assertIn('`a.json` vs B `b.json`', self.sent[0])


class FinalScoreTests(unittest.TestCase):
    def test_final_scores_are_averaged_per_faction_and_arm(self):
        run = Path(tempfile.mkdtemp())
        for name, a_seats, scores in [('game-0-A02', [0, 2], [100, 90, 80, 70]), ('game-1-A13', [1, 3], [60, 110, 50, 120])]:
            game = run/'pair-000'/name
            game.mkdir(parents=True)
            (game/'result.json').write_text(json.dumps({'complete': True, 'a_seats': a_seats,
                'factions': ['Xenos', 'Taklons', 'Terrans', 'Geodens'], 'scores': {str(i): v for i, v in enumerate(scores)}}))
        table = lab.final_scores(run)
        self.assertEqual(table['Xenos'], {'A': [100], 'B': [60]})
        self.assertEqual(table['Taklons'], {'A': [110], 'B': [90]})
        text = lab.scores_table(table)
        self.assertIn('| **전체** | 102.5 | 67.5 | 120 |', text)


if __name__ == '__main__':
    unittest.main()
