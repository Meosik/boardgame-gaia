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
        with self.assertRaises(RuntimeError):
            lab.allocate(3)

    def test_short_seed_file_is_refilled_by_a_scan_or_the_experiment_is_held(self):
        """User 2026-10-21 "실험을 왜 건너뛰게 하지?": a short seeds.txt refills itself; if the scan finds
        nothing the experiment waits (announced once) instead of ending the service."""
        sent, scans = [], []
        original = lab.notify, lab.scan_seeds, lab.publish, lab.run_ab
        lab.notify = sent.append
        lab.publish = lambda paths, message: scans.append(('publish', [Path(p).name for p in paths], message))

        def scan(start, count, jobs):
            scans.append((start, count))
            with (self.dir/'seeds.txt').open('a') as f:
                f.write(f's-{start}\n')
            return 1
        lab.scan_seeds = scan
        try:
            self.assertEqual(lab.ensure_seeds('x', 5, 1, push=True), ['s-1', 's-2', 's-3', 's-4', 's-5'])
            self.assertEqual(scans, [(5, lab.SCAN_WINDOW), ('publish', ['seeds.txt'], 'lab: seeds +1 for x')])
            self.assertIn('+1', sent[-1])
            lab.scan_seeds = lambda start, count, jobs: 0  # nothing found: hold, announce once
            self.queue('big', {'kind': 'ab', 'pairs': 9, 'teacher_a': 'a', 'teacher_b': 'b'})
            self.assertEqual(lab.run_pending(jobs=1, push=False), 0)
            self.assertEqual(lab.run_pending(jobs=1, push=False), 0)
            self.assertEqual([s for s in sent if '보류' in s and 'big' in s], [s for s in sent if '보류' in s])
            self.assertEqual(len([s for s in sent if '보류' in s]), 1)
            self.assertIsNone(lab.result('big'))
            ran = []
            lab.run_ab = lambda name, spec, jobs: (ran.append(spec['seeds']), ('done', {'seeds': spec['seeds']}, 'ok'))[1]
            self.queue('small', {'kind': 'ab', 'pairs': 2, 'teacher_a': 'a', 'teacher_b': 'b'})
            self.assertEqual(lab.run_pending(jobs=1, push=False), 1)  # the held one does not block others
            self.assertEqual(ran, [['s-1', 's-2']])
            self.assertEqual(lab.result('small')['seeds'], ['s-1', 's-2'])
        finally:
            lab.notify, lab.scan_seeds, lab.publish, lab.run_ab = original

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
        self.assertEqual(stats['A']['median'], 2.0)  # review-000 finding 5: even n averages the middle pair

    def test_charge_table_survives_a_faction_without_a_completed_pair(self):
        """review-000 finding 3: one arm missing for every pair of a faction must not stop the table."""
        import charge_rounds
        gained = {('pair-000', 'Terrans'): {'A': 100.0, 'B': 110.0},
                  ('pair-001', 'Terrans'): {'A': 120.0, 'B': 126.0},
                  ('pair-001', 'Ivits'): {'A': 90.0}}
        table = charge_rounds.summarize(gained)
        self.assertEqual(table['Ivits']['pairs'], 0)
        self.assertEqual((table['Terrans']['pairs'], table['Terrans']['mean_B_minus_A']), (2, 8.0))
        self.assertEqual((table['ALL']['pairs'], table['ALL']['mean_B_minus_A']), (2, 8.0))
        self.assertEqual(charge_rounds.summarize({})['ALL']['pairs'], 0)

    def test_round_start_waits_for_income_and_gaia_pauses(self):
        """review-000 finding 1: a round-1 IncomeOrderPending snapshot already shows round 1."""
        import charge_rounds
        pending = {'round': 1, 'phase': {'IncomeOrderPending': {'queue': [], 'round': 0}}}
        acting = {'round': 1, 'phase': {'ActionPhase': {'active_player': 0}}}
        self.assertFalse(charge_rounds.round_started(pending, 1))
        self.assertTrue(charge_rounds.round_started(acting, 1))
        self.assertFalse(charge_rounds.round_started({'round': 3, 'phase': 'RoundScoring'}, 4))


    def test_broken_files_are_skipped_and_a_broken_result_reruns(self):
        self.queue('ok', {'kind': 'command', 'run': ['true']})
        (self.dir/'queue'/'cut.json').write_text('')
        (self.dir/'results'/'ok.json').write_text('{"status": "do')
        self.assertEqual([n for n, _ in lab.pending()], ['ok'])
        self.assertEqual(lab.allocate(1), ['s-1'])
        self.assertTrue(any(p.endswith('cut.json') for p in lab._broken))

    def test_review_experiment_publishes_the_reviewer_text_verbatim_under_a_review_notice(self):
        """User 2026-10-21 "다른 agent의 검수": a review job runs codex read-only and keeps its text as is."""
        from unittest import mock
        self.queue('review-code-abc1234', {'kind': 'review', 'commits': 'abc1234..def5678',
                                           'paths': ['gaia-rl/tools/charge_rounds.py']})
        sent = []
        with mock.patch.object(lab, 'notify', sent.append), \
                mock.patch.object(lab, 'git', return_value=mock.Mock(stdout='diff --git a b\n', returncode=0)), \
                mock.patch.object(lab, 'codex_review', return_value=('결론: 지적 2건\n- tools/x.py:3 창이 하나 짧다', '')):
            self.assertEqual(lab.run_pending(jobs=1, push=False), 1)
        r = lab.result('review-code-abc1234')
        self.assertEqual((r['status'], r['kind'], r['findings']), ('done', 'review', 2))
        page = (self.dir/'results'/'review-code-abc1234.md').read_text()
        self.assertTrue(page.startswith('# review-code-abc1234 — 검수'))
        self.assertIn('창이 하나 짧다', page)
        self.assertTrue(sent[-1].startswith('🔍 # review-code-abc1234 — 검수'))

    def test_review_without_codex_is_a_failed_result_not_a_retry_loop(self):
        from unittest import mock
        self.queue('review-code-0000000', {'kind': 'review', 'paths': ['x.py']})
        with mock.patch.object(lab, 'notify', lambda *_: None), mock.patch.object(lab, 'codex_bin', lambda: None), \
                mock.patch.object(lab, 'git', return_value=mock.Mock(stdout='', returncode=0)):
            lab.run_pending(jobs=1, push=False)
        self.assertEqual(lab.result('review-code-0000000')['status'], 'failed')
        self.assertIn('codex 미설치', (self.dir/'results'/'review-code-0000000.md').read_text())
        self.assertEqual(lab.pending(), [])

    def test_findings_and_code_paths(self):
        self.assertEqual(lab.findings('결론: 이상 없음\n'), 0)
        self.assertEqual(lab.findings('머리말\n결론: 지적 3건\n...'), 3)
        self.assertIsNone(lab.findings('아무 말'))
        self.assertTrue(lab.is_code('gaia-rl/tools/charge_rounds.py'))
        self.assertTrue(lab.is_code('gaia-engine/src/lib.rs'))
        self.assertTrue(lab.is_code('gaia-rl/tools/teacher-a-ships.json'))
        self.assertFalse(lab.is_code('gaia-rl/lab/results/101.json'))
        self.assertFalse(lab.is_code('gaia-rl/lab/queue/102.json'))
        self.assertFalse(lab.is_code('gaia-rl/lab/HANDOFF.md'))
        self.assertFalse(lab.is_code('gaia-rl/lab/seeds-quartet-a.txt'))

    def test_a_pull_that_changes_code_queues_one_review_and_results_only_do_not(self):
        from unittest import mock
        def fake_git(*args, check=True):
            names = 'gaia-rl/lab/results/101.md\ngaia-rl/tools/lab.py\n' if args[:2] == ('diff', '--name-only') else ''
            return mock.Mock(stdout=names, returncode=0)
        with mock.patch.object(lab, 'git', fake_git):
            self.assertEqual(lab.queue_code_review('aaaaaaa1', 'bbbbbbb2', push=False), 'review-code-bbbbbbb')
            self.assertIsNone(lab.queue_code_review('aaaaaaa1', 'bbbbbbb2', push=False))  # already queued
            self.assertIsNone(lab.queue_code_review(None, 'bbbbbbb2', push=False))
        spec = json.loads((self.dir/'queue'/'review-code-bbbbbbb.json').read_text())
        self.assertEqual((spec['kind'], spec['commits'], spec['paths']), ('review', 'aaaaaaa1..bbbbbbb2', ['gaia-rl/tools/lab.py']))

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


class ChargeTableTests(unittest.TestCase):
    def test_charge_table_lists_factions_then_seat_mean(self):
        text = lab.charges_table({'factions': {
            'Taklons': {'pairs': 6, 'A': 115.9, 'B': 158.5, 'mean_B_minus_A': 42.6, 'ci95': [10.2, 74.9]},
            'ALL': {'pairs': 6, 'mean_B_minus_A': 29.7, 'ci95': [0.2, 59.2]}}})
        self.assertIn('| Taklons | 6 | +42.6 | [+10.2, +74.9] | 115.9 | 158.5 |', text)
        self.assertIn('| **전체 (좌석 평균)** | 6 | +29.7 | [+0.2, +59.2] |  |  |', text)
        self.assertIn('충전량 계산 실패', lab.charges_table({'error': 'boom'}))

    def test_watch_replay_is_the_lower_game_of_the_largest_gap(self):
        def row(faction, arm, charges):
            return {'faction': faction, 'arm': arm, 'charges': charges}
        seats = {'pair-000/game-0-A02': [row('Xenos', 'A', 262), row('Terrans', 'B', 123)],
                 'pair-000/game-1-A13': [row('Xenos', 'B', 79), row('Terrans', 'A', 118)],
                 'pair-001/game-0-A01': [row('Xenos', 'A', 100)]}
        game, seat, label = lab.watch_pick(seats)
        self.assertEqual((game, seat), ('pair-000/game-1-A13', 0))
        self.assertEqual(label, 'Xenos B팔 충전 79 (상대 팔 262)')
        self.assertIsNone(lab.watch_pick({}))


if __name__ == '__main__':
    unittest.main()
