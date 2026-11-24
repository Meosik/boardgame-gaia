import json
import unittest
from unittest import mock

import rank_terms


def build():
    return {'action': {'type': 'Build'}}


def upgrade(to):
    return {'action': {'type': 'Upgrade', 'to': to}}


BLOCKED = 'conservation blocked: x'


class BreakdownIndicesTest(unittest.TestCase):
    def test_watched_first_then_top_unblocked_by_score_with_ties_by_index(self):
        scores = [(1.0, 'a'), (5.0, 'b'), (5.0, 'c'), (3.0, 'd'), (2.0, 'e')]
        candidates = [build() for _ in scores]
        self.assertEqual(rank_terms.breakdown_indices(scores, candidates, [4, 0], top=3), [4, 0, 1, 2, 3])

    def test_blocked_candidates_are_not_in_the_top_list_but_a_watched_one_stays(self):
        scores = [(9.0, BLOCKED + ' y'), (2.0, 'a'), (1.0, 'b')]
        candidates = [build() for _ in scores]
        self.assertEqual(rank_terms.breakdown_indices(scores, candidates, [], top=5), [1, 2])
        self.assertEqual(rank_terms.breakdown_indices(scores, candidates, [0], top=5), [0, 1, 2])

    def test_a_watched_upgrade_adds_the_best_unblocked_siblings_with_the_same_target(self):
        scores = [(0.0, 'w'), (4.0, 'a'), (3.0, 'b'), (2.0, 'c'), (1.0, 'd'), (8.0, BLOCKED), (7.0, 'e')]
        candidates = [upgrade('TradingStation'), upgrade('TradingStation'), upgrade('Lab'),
                      upgrade('TradingStation'), upgrade('TradingStation'), upgrade('TradingStation'), build()]
        result = rank_terms.breakdown_indices(scores, candidates, [0], top=1, variants=2)
        self.assertEqual(result, [0, 6, 1, 3])

    def test_no_duplicates(self):
        scores = [(3.0, 'a'), (2.0, 'b'), (1.0, 'c')]
        candidates = [upgrade('Lab') for _ in scores]
        result = rank_terms.breakdown_indices(scores, candidates, [1, 1], top=2, variants=3)
        self.assertEqual(result, [1, 0, 2])

    def test_out_of_range_watch_indices_are_dropped(self):
        scores = [(1.0, 'a'), (2.0, 'b')]
        candidates = [build(), build()]
        self.assertEqual(rank_terms.breakdown_indices(scores, candidates, [-1, 2, 99, 0], top=1), [0, 1])


class FakeFork:
    def __init__(self, text):
        self.text = text

    def snapshot_json(self):
        return self.text


class FakeEnv:
    def __init__(self, afters, failing=()):
        self.afters = afters
        self.failing = failing

    def fork(self, decision_id, index):
        if index in self.failing:
            raise RuntimeError(f'cannot fork {index}')
        return FakeFork(json.dumps(self.afters[index]))


class RootScoresRecordTest(unittest.TestCase):
    def setUp(self):
        self.before = {'vp': 10.0, 'stock': 2.0, 'other': 0.0, 'total': 12.0}
        self.snapshot = {'player': 0, 'decision_id': 5,
                         'state': {'terms': self.before, 'players': [{'faction': 'X'}]},
                         'candidates': [build(), build(), build()]}
        self.scores = [(1.23456789, 'a'), (3.0, 'b'), (9.0, BLOCKED + ' z')]
        self.afters = {
            1: {'player': 0, 'state': {'terms': {'vp': 12.0, 'stock': 1.0, 'tiles': 0.5, 'total': 14.0}},
                'candidates': [{'action': {'type': 'FormFederation'}}, {'action': {'type': 'FormFederation'}},
                               {'action': {'type': 'Pass'}}]},
            0: {'player': 1, 'state': {'terms': {'vp': 10.0, 'stock': 2.0, 'other': 0.0, 'total': 12.5}},
                'candidates': [{'action': {'type': 'FormFederation'}}]}}
        patcher = mock.patch.object(rank_terms, 'potential_terms',
                                    side_effect=lambda state, actor, home: dict(state['terms']))
        self.terms = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(rank_terms, 'home_of', return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def record(self, failing=()):
        return rank_terms.root_scores_record(FakeEnv(self.afters, failing), self.snapshot, self.scores, [])

    def test_scores_carry_rounded_score_reason_and_rank_with_none_for_blocked(self):
        record = self.record()
        self.assertEqual(record['event'], 'root_scores')
        self.assertEqual(record['unblocked'], 2)
        self.assertEqual(record['scores'], [[1.2346, 'a', 2], [3.0, 'b', 1], [None, BLOCKED + ' z', None]])

    def test_breakdown_rows_hold_delta_next_player_and_federations(self):
        record = self.record()
        self.assertEqual(record['before'], self.before)
        rows = {row['index']: row for row in record['breakdown']}
        self.assertEqual(sorted(rows), [0, 1])
        one = rows[1]
        self.assertEqual(one['rank'], 1)
        self.assertEqual(one['delta'], {'vp': 2.0, 'stock': -1.0, 'other': 0.0, 'total': 2.0, 'tiles': 0.5})
        self.assertEqual(one['score_minus_delta'], 1.0)
        self.assertEqual(one['next_player'], 0)
        self.assertEqual(one['own_federations_after'], 2)
        zero = rows[0]
        self.assertEqual(zero['next_player'], 1)
        self.assertIsNone(zero['own_federations_after'])
        self.assertEqual(zero['delta']['total'], 0.5)
        self.assertAlmostEqual(zero['score_minus_delta'], 0.7346, places=4)

    def test_a_failing_before_state_gives_an_error_and_no_breakdown(self):
        self.terms.side_effect = RuntimeError('no engine')
        record = self.record()
        self.assertIn('no engine', record['error'])
        self.assertNotIn('breakdown', record)
        self.assertEqual(len(record['scores']), 3)

    def test_a_failing_fork_marks_only_that_row(self):
        record = self.record(failing=(1,))
        rows = {row['index']: row for row in record['breakdown']}
        self.assertIn('cannot fork 1', rows[1]['error'])
        self.assertNotIn('delta', rows[1])
        self.assertNotIn('error', rows[0])
        self.assertEqual(rows[0]['delta']['total'], 0.5)


if __name__ == '__main__':
    unittest.main()
