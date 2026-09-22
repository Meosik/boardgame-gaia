import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from current_actions.ab_match import assignments, paired_scores, run, summarize, validate_seeds
from four_factions import FACTIONS
from four_factions.test_preparation import SEED


def results():
    specs = {'seed': 'same', 'factions': list(FACTIONS)}
    first = {'complete': True, **specs, 'scores': {0: 100, 1: 120, 2: 50, 3: 60},
             'delta_factions': ['HadschHallas', 'Taklons']}
    second = {'complete': True, **specs, 'scores': {0: 130, 1: 110, 2: 51, 3: 61},
              'delta_factions': ['Xenos', 'Terrans']}
    return first, second


class ABMatchTests(unittest.TestCase):
    def test_every_pair_swaps_policies_not_native_factions_or_seats(self):
        spec = {'seed': 'same', 'factions': list(reversed(FACTIONS))}
        original = copy.deepcopy(spec)
        teams = set()
        for pair in range(6):
            schedule = assignments(spec, pair)
            left, right = (set(s['delta_factions']) for s in schedule)
            self.assertEqual(len(left), 2)
            self.assertEqual(len(right), 2)
            self.assertEqual(left | right, set(FACTIONS))
            self.assertFalse(left & right)
            teams.add(tuple(sorted(next(t for t in (left, right) if 'Xenos' in t))))
        self.assertEqual(len(teams), 3)
        self.assertEqual(spec, original)

    def test_vp_differences_are_paired_by_faction_not_seat_or_run_order(self):
        a, b = results()
        pair = paired_scores(a, b)
        self.assertEqual(pair['by_faction']['Xenos'], {'A': 100, 'B': 130, 'B_minus_A': 30})
        self.assertEqual(pair['by_faction']['HadschHallas'], {'A': 110, 'B': 120, 'B_minus_A': 10})
        self.assertEqual(pair['by_faction']['Terrans']['B_minus_A'], 1)
        self.assertEqual(pair['by_faction']['Taklons']['B_minus_A'], -1)
        self.assertEqual(pair['mean_B_minus_A'], 10)
        self.assertEqual(paired_scores(b, a), pair)
        report = summarize([pair, {**pair, 'seed': 'other'}])
        self.assertEqual(report['games'], 4)
        self.assertEqual(report['mean_B_minus_A'], 10)
        self.assertFalse(report['promotion'])

    def test_incomplete_mismatched_or_duplicate_pairs_cannot_be_averaged(self):
        a, b = results()
        for changed in ({**b, 'complete': False}, {**b, 'seed': 'other'},
                        {**b, 'factions': list(reversed(FACTIONS))}, {**b, 'scores': {0: 99}},
                        {**b, 'delta_factions': a['delta_factions']}):
            with self.assertRaises(ValueError):
                paired_scores(a, changed)
        pair = paired_scores(a, b)
        with self.assertRaises(ValueError):
            summarize([pair, pair])

    def test_real_native_preflight_checks_roster_and_duplicate_seeds(self):
        specs = validate_seeds([SEED])
        self.assertEqual(set(specs[0]['factions']), set(FACTIONS))
        self.assertEqual(len(specs[0]['initial_snapshot_sha256']), 64)
        for invalid in ([], [SEED, SEED], [''], [None]):
            with self.assertRaises(ValueError):
                validate_seeds(invalid)

    def test_runner_preserves_results_records_failures_and_never_promotes(self):
        spec = {'seed': 'same', 'factions': list(FACTIONS), 'initial_snapshot_sha256': 'test'}
        first, second = results()
        manifest = {'source_hashes': {}, 'versions': {}, 'specs': [spec]}
        seen = []

        def play(spec, output, *, factory, focal):
            policy = factory()
            seen.append(policy.delta_factions)
            self.assertEqual(policy.adaptive_clock.uses, 6)
            self.assertEqual((policy.target_seconds, policy.maximum_seconds), (10, 120))
            self.assertTrue(policy.bgg_openings)
            output.mkdir(parents=True)
            return first if 'HadschHallas' in policy.delta_factions else second

        with tempfile.TemporaryDirectory() as directory, \
                patch('current_actions.ab_match.verify'), \
                patch('current_actions.ab_match.make_manifest', return_value=manifest), \
                patch('current_actions.ab_match.play', side_effect=play), \
                patch('current_actions.ab_match.audit', return_value={'native_complete': True}), \
                patch('current_actions.ab_match.trace_statistics', return_value={}):
            output = Path(directory)/'success'
            report = run([spec], output)
            self.assertEqual(seen, [('HadschHallas', 'Taklons'), ('Terrans', 'Xenos')])
            self.assertEqual(report['mean_B_minus_A'], 10)
            self.assertEqual(json.loads((output/'report.json').read_text()), report)
            with self.assertRaises(FileExistsError):
                run([spec], output)
            with patch('current_actions.ab_match.play', side_effect=RuntimeError('native failure')):
                failed = Path(directory)/'failure'
                with self.assertRaisesRegex(RuntimeError, 'native failure'):
                    run([spec], failed)
                self.assertFalse((failed/'report.json').exists())
                self.assertEqual(json.loads((failed/'progress.json').read_text())['state'], 'failed')


if __name__ == '__main__':
    unittest.main()
