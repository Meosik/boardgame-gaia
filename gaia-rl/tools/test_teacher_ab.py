import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import teacher_ab as ab


def game(a_seats, scores, factions=('Terrans', 'Xenos', 'Ivits', 'Firaks'), counters=None, **extra):
    return {'seed': 's', 'factions': list(factions), 'a_seats': list(a_seats), 'complete': True,
            'scores': {str(i): v for i, v in enumerate(scores)}, 'counters': counters or {}, **extra}


class ScheduleTests(unittest.TestCase):
    def test_every_pair_swaps_seats_so_each_teacher_plays_every_seat_once(self):
        for pair in ab.schedule(['x', 'y'], 12):
            first, second = pair['games']
            self.assertEqual(sorted(first['a_seats'] + second['a_seats']), [0, 1, 2, 3])
            self.assertEqual(first['a_seats'], second['b_seats'])
            self.assertEqual(len(first['a_seats']), 2)

    def test_repeated_seed_moves_to_a_different_seat_split(self):
        for seeds in (['x'], ['x', 'y'], ['x', 'y', 'z']):
            splits = {}
            for pair in ab.schedule(seeds, 2*3*len(seeds)):
                half = frozenset(min(pair['games'], key=lambda g: g['a_seats'])['a_seats'])
                half = half if 0 in half else frozenset(range(4)) - half
                splits.setdefault(pair['seed'], []).append(half)
            for seed, halves in splits.items():
                self.assertEqual(len(set(halves)), 3, (seeds, seed))

    def test_odd_or_empty_inputs_are_rejected(self):
        for seeds, games in ((['x'], 3), (['x'], 0), ([], 2), (['x', 'x'], 2)):
            with self.subTest(seeds=seeds, games=games), self.assertRaises(ValueError):
                ab.schedule(seeds, games)


class StatisticsTests(unittest.TestCase):
    def test_pair_difference_uses_the_game_where_each_teacher_held_the_seat(self):
        rows = ab.pair_differences(game((0, 2), [100, 90, 80, 70]), game((1, 3), [110, 95, 60, 75]))
        self.assertEqual([r['B_minus_A'] for r in rows], [10, -5, -20, -5])
        with self.assertRaises(ValueError):
            ab.pair_differences(game((0, 2), [1, 1, 1, 1]), game((0, 1), [1, 1, 1, 1]))

    def test_confidence_interval_matches_t_distribution(self):
        low, high = ab.confidence_interval([1, 2, 3, 4, 5])
        self.assertAlmostEqual(low, 1.0367568385224393)
        self.assertAlmostEqual(high, 4.963243161477561)
        self.assertIsNone(ab.confidence_interval([3]))

    def test_summary_counts_failures_timeouts_and_limit_omissions_per_arm(self):
        counts = {'Terrans': {'A': Counter(decisions=10, federation_limit_hits=2, unsearched_comparisons=40,
                                           unsearched_decisions=4),
                              'B': Counter(decisions=9, fallback_timeouts=1)}}
        done = [game((0, 2), [100, 90, 80, 70], counters=counts), game((1, 3), [110, 95, 60, 75])]
        failed = [{'seed': 't', 'factions': ['Terrans', 'Nevlas', 'Itars', 'Gleens'], 'complete': False,
                   'failure_kind': 'timeout', 'counters': {}},
                  {'seed': 't', 'factions': ['Terrans', 'Nevlas', 'Itars', 'Gleens'], 'complete': False,
                   'failure_kind': 'error', 'counters': {}}]
        summary = ab.summarize([ab.pair_differences(*done)], done + failed)
        total = summary['factions']['ALL']
        self.assertEqual((total['pairs'], total['mean_B_minus_A']), (1, -5))
        self.assertEqual((total['error_games'], total['timeout_games']), (1, 1))
        self.assertEqual((total['A_federation_limit_hits'], total['A_unsearched_decisions'],
                          total['A_unsearched_comparisons'], total['B_fallback_timeouts']), (2, 4, 40, 1))
        self.assertEqual(summary['factions']['Nevlas']['pairs'], 0)
        self.assertEqual(summary['factions']['Nevlas']['timeout_games'], 1)
        table = ab.report_table(summary)
        self.assertEqual(table.count('\n|---'), 1)   # exactly one table
        self.assertIn('| Terrans | 1 | +10.0 | — | 1 | 1 | 0 / 1 | 2 / 0 | 4 / 0 |', table)


class TeacherSpecTests(unittest.TestCase):
    def test_frozen_teacher_detects_any_source_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'teacher'
            (source/'pkg').mkdir(parents=True)
            (source/'pkg/a.py').write_text('x = 1\n')
            record = {'files': {'pkg/a.py': ab.sha256(source/'pkg/a.py')}, 'external_data': {}}
            (source/'FROZEN.json').write_text(json.dumps(record))
            teacher = {'source': str(source), 'frozen': True}
            self.assertEqual(ab.frozen_problems(teacher), [])
            (source/'pkg/a.py').write_text('x = 2\n')
            (source/'pkg/b.py').write_text('')
            self.assertEqual(sorted(ab.frozen_problems(teacher)),
                             ['added: pkg/b.py', 'changed or missing: pkg/a.py'])
            self.assertEqual(ab.frozen_problems({**teacher, 'frozen': False}), [])

    def test_untracked_agent_runtime_state_is_not_teacher_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'teacher'
            (source/'pkg').mkdir(parents=True)
            (source/'pkg/a.py').write_text('x = 1\n')
            record = {'files': {'pkg/a.py': ab.sha256(source/'pkg/a.py'),
                                '.omc/state/log.json': 'recorded-but-never-committed'}}
            (source/'FROZEN.json').write_text(json.dumps(record))
            teacher = {'source': str(source), 'frozen': True}
            self.assertEqual(ab.frozen_problems(teacher), [])
            (source/'pkg/.omc').mkdir()
            (source/'pkg/.omc/new.json').write_text('{}')
            self.assertEqual(ab.frozen_problems(teacher), [])
            (source/'pkg/a.py').write_text('x = 2\n')
            self.assertEqual(ab.frozen_problems(teacher), ['changed or missing: pkg/a.py'])

    def test_spec_environment_must_be_string_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'teacher'
            source.mkdir()
            for env, ok in (({'GAIA_X': '1'}, True), ({'GAIA_X': 1}, False)):
                spec = Path(temporary)/'spec.json'
                spec.write_text(json.dumps({'source': str(source), 'factory': 'm:f', 'env': env}))
                with self.subTest(env=env):
                    if ok:
                        self.assertEqual(ab.resolve_teacher(str(spec))['env'], env)
                    else:
                        with self.assertRaises(ValueError):
                            ab.resolve_teacher(str(spec))

    def test_per_teacher_comparison_budget_is_validated(self):
        spec = ab.resolve_teacher(str(Path(ab.__file__).with_name('teacher-a-search2.json')))
        self.assertEqual(spec['comparisons'], 2)
        self.assertTrue(spec['frozen'])
        self.assertIsNone(ab.resolve_teacher('baseline')['comparisons'])

    def test_one_income_horizon_spec_is_validated(self):
        spec = ab.resolve_teacher(str(Path(ab.__file__).with_name('teacher-a-search2-h1.json')))
        self.assertEqual((spec['comparisons'], spec['horizon_incomes']), (2, 1))
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'teacher'
            source.mkdir()
            bad = Path(temporary)/'bad.json'
            bad.write_text(json.dumps({'source': str(source), 'factory': 'm:f', 'horizon_incomes': 3}))
            with self.assertRaises(ValueError):
                ab.resolve_teacher(str(bad))

    def test_safety_cap_spec_is_validated(self):
        spec = ab.resolve_teacher(str(Path(ab.__file__).with_name('teacher-a-search2-h1-cap5.json')))
        self.assertEqual(spec['max_seconds'], 5)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'teacher'
            source.mkdir()
            for cap in (0, -1, True, '5'):
                bad = Path(temporary)/'bad.json'
                bad.write_text(json.dumps({'source': str(source), 'factory': 'm:f', 'max_seconds': cap}))
                with self.subTest(cap=cap), self.assertRaises(ValueError):
                    ab.resolve_teacher(str(bad))

    def test_comparison_budget_clock_is_a_count_not_a_deadline(self):
        clock = ab.budget_clock(0)
        self.assertEqual(clock['comparisons'], 0)
        self.assertEqual(clock['uses'], 0)
        with self.assertRaises(ValueError):
            ab.budget_clock(-1)

    def test_registry_baseline_is_frozen_and_currently_intact(self):
        baseline = ab.resolve_teacher('baseline')
        self.assertTrue(baseline['frozen'])
        self.assertEqual(ab.frozen_problems(baseline), [])
        with self.assertRaises(ValueError):
            ab.resolve_teacher('no-such-teacher')


if __name__ == '__main__':
    unittest.main()
