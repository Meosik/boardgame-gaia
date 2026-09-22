"""Reconstruction tests, including the tiers the log cannot support."""
import unittest

from bgs_records import fixture
from bgs_records.state import PLACED, final_states, trajectory, verify
from bgs_records.timeline import build


class TrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.record = build('Test-game-0001', fixture.data(), fixture.summary())

    def test_a_snapshot_is_taken_before_the_move_it_belongs_to(self):
        first = next(iter(trajectory(self.record)))
        turn, states = first
        self.assertEqual(turn.move_index, 1)
        self.assertEqual(states[0].structures, {})
        self.assertEqual(states[0].victory_points, 10)

    def test_upgrading_replaces_the_structure_on_that_hex(self):
        seen = {}
        for turn, states in trajectory(self.record):
            seen[turn.move_index] = states[0].structures.get('3A1')
        self.assertEqual(seen[9], 'm')     # before the trading station goes up
        self.assertEqual(seen[11], 'ts')   # before the lab replaces it
        self.assertEqual(final_states(self.record)[0].structures['3A1'], 'lab')

    def test_the_rebuild_lands_on_the_recorded_final_board(self):
        self.assertEqual(
            verify(self.record, fixture.data()),
            ('victory_points', 'structures', 'research'))

    def test_research_holds_only_the_tracks_the_seat_advanced(self):
        self.assertEqual(final_states(self.record)[0].research, {'nav': 1})
        self.assertEqual(final_states(self.record)[1].research, {})

    def test_victory_points_move_for_seats_that_are_not_acting(self):
        # Seat 1 pays a VP to charge power on seat 0's move.
        self.assertEqual(final_states(self.record)[1].victory_points, 12)

    def test_end_game_scoring_outside_any_move_still_lands(self):
        self.assertEqual(final_states(self.record)[0].victory_points, 24)

    def test_a_wrong_final_board_is_reported_rather_than_accepted(self):
        skewed = fixture.data()
        skewed['players'][0]['data']['buildings']['lab'] = 3
        self.assertNotIn('structures', verify(self.record, skewed))

    def test_the_lost_planet_holds_a_hex_without_counting_as_a_mine(self):
        moves = list(fixture.MOVES)
        moves.insert(13, 'terrans up nav (1 ⇒ 5). lostPlanet 4A11.')
        data = fixture.data(moveHistory=moves)
        log = []
        for entry in data['advancedLog']:
            if entry.get('move', -1) >= 13:
                entry = {**entry, 'move': entry['move'] + 1}
            log.append(entry)
        log.insert(-4, {'player': 0, 'move': 13})
        data['advancedLog'] = log
        data['players'][0]['data']['research']['nav'] = 5
        record = build('Test-game-0001', data)
        state = final_states(record)[0]
        self.assertEqual(state.structures['4A11'], 'lost')
        self.assertEqual(state.buildings()['m'], 1)
        self.assertIn('structures', verify(record, data))

    def test_buildings_covers_exactly_the_kinds_the_site_counts(self):
        self.assertEqual(set(final_states(self.record)[0].buildings()), set(PLACED))


if __name__ == '__main__':
    unittest.main()
