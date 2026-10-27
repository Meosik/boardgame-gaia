"""publish_faction_replays.py: the median-charge seat pick."""
import unittest

from publish_faction_replays import group_by_game, pick_median_seats


class PickTests(unittest.TestCase):
    def test_picks_the_seat_closest_to_each_factions_median(self):
        seats = {
            'pair-001/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 2}, {'faction': 'Y', 'arm': 'A', 'charges': 10}],
            'pair-002/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 6}, {'faction': 'Y', 'arm': 'B', 'charges': 4}],
            'pair-003/game-0-A00': [{'faction': 'Y', 'arm': 'A', 'charges': 7}, {'faction': 'X', 'arm': 'B', 'charges': 9}],
        }
        picks = pick_median_seats(seats)
        self.assertEqual(picks['X'], ('pair-002/game-0-A00', 0, 6, 6))
        self.assertEqual(picks['Y'], ('pair-003/game-0-A00', 0, 7, 7))

    def test_group_by_game(self):
        seats = {
            'pair-001/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 2}, {'faction': 'Y', 'arm': 'A', 'charges': 10}],
            'pair-002/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 6}, {'faction': 'Y', 'arm': 'B', 'charges': 4}],
            'pair-003/game-0-A00': [{'faction': 'Y', 'arm': 'A', 'charges': 7}, {'faction': 'X', 'arm': 'B', 'charges': 9}],
        }
        groups = group_by_game(pick_median_seats(seats))
        self.assertEqual(groups, {'pair-002/game-0-A00': [('X', 0, 6, 6)],
                                  'pair-003/game-0-A00': [('Y', 0, 7, 7)]})
        shared = {'pair-004/game-0-A01': [{'faction': 'Z', 'arm': 'A', 'charges': 5}, {'faction': 'W', 'arm': 'B', 'charges': 3}]}
        self.assertEqual(group_by_game(pick_median_seats(shared)),
                         {'pair-004/game-0-A01': [('W', 1, 3, 3), ('Z', 0, 5, 5)]})


if __name__ == '__main__':
    unittest.main()
