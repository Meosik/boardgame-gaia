import argparse
import unittest

from worker_times import diverged, replay_positions, snapshot_digest, summarise


def make_rows():
    # rounds 1..6, four rows each
    rows = []
    for rnd in range(1, 7):
        for k in range(4):
            rows.append({'round': rnd, 'seconds': float(k)})
    return rows


class ReplayPositionsTest(unittest.TestCase):
    def test_every_second_of_chosen_rounds(self):
        rows = make_rows()
        # round 4 = indices 12..15, round 5 = 16..19; counted inside the chosen rounds
        self.assertEqual(replay_positions(rows, {4, 5}, 2, [], 0), [12, 14, 16, 18])

    def test_slowest_only_in_chosen_rounds(self):
        rows = make_rows()
        rows[0]['seconds'] = 99.0  # round 1, not chosen
        rows[13]['seconds'] = 50.0
        rows[18]['seconds'] = 40.0
        del rows[12]['seconds']  # counts as 0
        self.assertEqual(replay_positions(rows, {4, 5}, 0, [], 2), [13, 18])

    def test_explicit_steps(self):
        rows = make_rows()
        self.assertEqual(replay_positions(rows, {4}, 0, [0, 5, 24, 100, -1], 0), [0, 5])

    def test_sorted_without_duplicates(self):
        rows = make_rows()
        rows[14]['seconds'] = 70.0
        got = replay_positions(rows, {4}, 2, [14, 12, 3], 1)
        self.assertEqual(got, [3, 12, 14])


class SummariseTest(unittest.TestCase):
    def test_counts(self):
        rows = [{'wall': 1.0, 'round': 4}, {'wall': 40.0, 'round': 4, 'time_capped': True},
                {'wall': 5.0, 'round': 5}, {'timed_out': True, 'wall': 120.0, 'round': 5}]
        cell = summarise({}, rows, argparse.Namespace(guard=30))
        self.assertEqual(cell['decisions'], 3)
        self.assertEqual(cell['timed_out'], 1)
        self.assertEqual(cell['max'], 40.0)
        self.assertEqual(cell['over_guard'], 1)
        self.assertEqual(cell['time_capped'], 1)
        self.assertEqual(cell['by_round']['4']['n'], 2)


class DivergedTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'decision_id': 7, 'candidates': [{'a': 1}, {'a': 2}], 'state': {'round': 4}}
        self.row = {'decision_id': 7, 'index': 1, 'chosen': {'a': 2},
                    'digest': snapshot_digest(self.snapshot)}

    def test_matching_row(self):
        self.assertIsNone(diverged(self.snapshot, self.row))

    def test_row_without_digest(self):
        del self.row['digest']
        self.assertIsNone(diverged(self.snapshot, self.row))

    def test_wrong_digest(self):
        self.row['digest'] = '0'*64
        self.assertEqual(diverged(self.snapshot, self.row), 'state digest')

    def test_wrong_decision_id(self):
        self.row['decision_id'] = 8
        self.assertEqual(diverged(self.snapshot, self.row), 'decision id')

    def test_chosen_differs(self):
        self.row['chosen'] = {'a': 3}
        self.assertEqual(diverged(self.snapshot, self.row), 'chosen move')

    def test_record_of_another_engine_build(self):
        # the record's digest was taken with the recording build's id in the snapshot
        self.row['digest'] = snapshot_digest({**self.snapshot, 'engine_build_id': 'old'})
        replayed = {**self.snapshot, 'engine_build_id': 'new'}
        self.assertEqual(diverged(replayed, self.row), 'state digest')
        self.assertIsNone(diverged(replayed, self.row, 'old'))
        replayed['state'] = {'round': 5}
        self.assertEqual(diverged(replayed, self.row, 'old'), 'state digest')


if __name__ == '__main__':
    unittest.main()
