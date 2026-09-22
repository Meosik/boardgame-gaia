"""Selection tests: the target setup, the widening, and the strength floor."""
import unittest
from dataclasses import dataclass

from bgs_records.corpus import Stored
from bgs_records.selection import (DEFAULT_MIN_ELO, qualifying_seats, select,
                                   table_ratings)


@dataclass(frozen=True)
class FakeSeat:
    seat: int
    elo_initial: int | None


@dataclass(frozen=True)
class FakeRecord:
    """Only `qualifying_seats` and `table_ratings` still take a rebuilt game."""
    game_id: str
    seats: tuple


def record(game_id='a', ratings=(200, 200, 200, 200)):
    return FakeRecord(game_id, tuple(FakeSeat(i, r) for i, r in enumerate(ratings)))


def game(game_id, players=4, lost_fleet=False, ratings=(200, 200, 200, 200)):
    """An index entry, which is what `select` reads."""
    return Stored(game_id, '2026-01-01T00:00:00Z', 'x' * 64, players,
                  ('lost-fleet',) if lost_fleet else (), 'standard', '4.8.51',
                  tuple(ratings))


class QualifyingSeatTests(unittest.TestCase):
    def test_only_the_seats_that_clear_the_floor_qualify(self):
        self.assertEqual(qualifying_seats(record(ratings=(300, 40, 220, 110)), 120),
                         frozenset({0, 2}))

    def test_an_unrated_seat_never_qualifies(self):
        self.assertEqual(qualifying_seats(record(ratings=(300, None, 220, 190)), 120),
                         frozenset({0, 2, 3}))

    def test_the_whole_table_is_carried_so_a_row_can_be_weighed(self):
        self.assertEqual(table_ratings(record(ratings=(300, None, 220, 190))),
                         [300, None, 220, 190])


class SelectTests(unittest.TestCase):
    def test_lost_fleet_is_taken_when_there_is_enough_of_it(self):
        records = [game(f'lf{i}', lost_fleet=True) for i in range(30)]
        records += [game(f'base{i}') for i in range(50)]
        chosen = select(records, fallback_below=30)
        self.assertTrue(chosen.lost_fleet)
        self.assertEqual(len(chosen.game_ids), 30)
        self.assertIsNone(chosen.widened_from)

    def test_too_few_lost_fleet_games_widen_to_base_game_and_say_so(self):
        records = [game('lf0', lost_fleet=True)] + [game(f'base{i}') for i in range(12)]
        chosen = select(records, fallback_below=30)
        self.assertFalse(chosen.lost_fleet)
        self.assertEqual(len(chosen.game_ids), 12)
        self.assertEqual(chosen.widened_from, 1)
        self.assertIn('widened to 4p base game', chosen.describe())

    def test_widening_can_be_refused(self):
        records = [game('lf0', lost_fleet=True)] + [game(f'base{i}') for i in range(12)]
        chosen = select(records, fallback_below=30, allow_fallback=False)
        self.assertTrue(chosen.lost_fleet)
        self.assertEqual(len(chosen.game_ids), 1)

    def test_a_weak_seat_costs_its_own_rows_not_the_whole_table(self):
        # A strong player's moves stay a strong player's moves with a beginner present.
        records = [game('strong'), game('mixed', ratings=(400, 400, 400, 40))]
        chosen = select(records, min_elo=120, fallback_below=1)
        self.assertEqual(list(chosen.game_ids), ['strong', 'mixed'])
        self.assertEqual((chosen.seats_kept, chosen.seats_dropped), (7, 1))
        self.assertIn('learning only from seats rated 120+', chosen.describe())

    def test_the_stricter_reading_is_still_available(self):
        records = [game('strong'), game('mixed', ratings=(400, 400, 400, 40))]
        chosen = select(records, min_elo=120, fallback_below=1, require_all_seats=True)
        self.assertEqual(list(chosen.game_ids), ['strong'])
        self.assertEqual(chosen.dropped_rating, 1)
        self.assertIn('every seat rated 120+', chosen.describe())

    def test_a_game_with_no_qualifying_seat_is_dropped_entirely(self):
        records = [game('allweak', ratings=(10, 20, 30, 40))]
        chosen = select(records, min_elo=120, fallback_below=1)
        self.assertEqual(chosen.game_ids, ())
        self.assertEqual(chosen.dropped_rating, 1)

    def test_an_unrated_seat_is_dropped_but_its_table_is_kept(self):
        records = [game('rated'), game('partly', ratings=(400, 400, 400, None))]
        chosen = select(records, fallback_below=1)
        self.assertEqual(list(chosen.game_ids), ['rated', 'partly'])
        self.assertEqual((chosen.seats_kept, chosen.seats_dropped), (7, 1))

    def test_the_floor_can_be_switched_off(self):
        records = [game('weak', ratings=(0, 0, 0, 0))]
        self.assertEqual(len(select(records, min_elo=0, fallback_below=1).game_ids), 1)
        self.assertEqual(len(select(records, min_elo=120, fallback_below=1).game_ids), 0)

    def test_the_default_is_the_per_seat_reading(self):
        chosen = select([game('a')], fallback_below=1)
        self.assertFalse(chosen.require_all_seats)

    def test_other_player_counts_are_not_mixed_in(self):
        records = [game('four'), game('two', players=2, ratings=(300, 300))]
        chosen = select(records, players=4, fallback_below=1)
        self.assertEqual(list(chosen.game_ids), ['four'])
        self.assertEqual(chosen.dropped_setup, 1)

    def test_the_default_floor_is_stated_rather_than_implied(self):
        self.assertEqual(DEFAULT_MIN_ELO, 120)
        chosen = select([game('a')], fallback_below=1)
        self.assertIn('rated 120+', chosen.describe())

    def test_a_zero_threshold_means_never_widen(self):
        records = [game('base0'), game('base1')]
        chosen = select(records, fallback_below=0)
        self.assertTrue(chosen.lost_fleet)
        self.assertEqual(chosen.game_ids, ())

    def test_an_impossible_selection_is_refused(self):
        with self.assertRaises(ValueError):
            select([], players=1)
        with self.assertRaises(ValueError):
            select([], min_elo=-1)


if __name__ == '__main__':
    unittest.main()
