"""Alignment tests. A wrong move-to-seat join is invisible in the output, so it is checked."""
import unittest

from bgs_records import fixture
from bgs_records.timeline import RecordError, build, decode_expansions, turn_orders


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.record = build('Test-game-0001', fixture.data(), fixture.summary())

    def test_seats_carry_both_halves_the_site_serves(self):
        first = self.record.seats[0]
        self.assertEqual((first.faction, first.victory_points), ('terrans', 24))
        self.assertEqual((first.ranking, first.elo_initial, first.elo_delta), (1, 200, 8))
        self.assertEqual(first.engine_faction, 'Terrans')

    def test_the_init_line_gets_no_turn(self):
        self.assertEqual(len(self.record.turns), len(fixture.MOVES) - 1)
        self.assertNotIn(0, {turn.move_index for turn in self.record.turns})

    def test_moves_before_the_first_round_marker_are_setup(self):
        setup = [t for t in self.record.turns if t.is_setup]
        self.assertEqual([t.move_index for t in setup], list(range(1, 9)))
        self.assertTrue(all(t.phase == 'setup' for t in setup))

    def test_every_turn_is_joined_to_the_seat_that_made_it(self):
        for turn in self.record.turns:
            faction = turn.move.faction
            if faction is not None:
                self.assertEqual(self.record.seats[turn.seat].faction, faction)

    def test_effects_keep_their_source_round_and_seat(self):
        federation = [e for e in self.record.effects if e.source == 'federation']
        self.assertEqual([(e.seat, e.round, e.resource, e.delta) for e in federation],
                         [(0, 1, 'vp', 7)])

    def test_a_move_entry_that_also_carries_changes_keeps_both(self):
        # The log merges them on the same entry for most moves; dropping the changes
        # would lose the majority of the corpus.
        eleven = [e for e in self.record.effects if e.move_index == 11]
        self.assertEqual({(e.source, e.resource, e.delta) for e in eleven},
                         {('build', 'c', -5), ('build', 'o', -3), ('nav', 'vp', 2)})

    def test_winners_report_ties_rather_than_breaking_them(self):
        self.assertEqual(self.record.winners, (0,))
        tied = fixture.data()
        tied['players'][1]['data']['victoryPoints'] = 24
        tied['advancedLog'] = tied['advancedLog'] + [
            {'player': 1, 'changes': {'final2': {'vp': 12}}}]
        self.assertEqual(build('t', tied).winners, (0, 1))

    def test_a_score_that_does_not_match_its_logged_vp_is_refused(self):
        wrong = fixture.data()
        wrong['players'][0]['data']['victoryPoints'] = 25
        with self.assertRaises(RecordError) as caught:
            build('Test-game-0001', wrong)
        self.assertIn('logged VP sums to', str(caught.exception))

    def test_a_game_that_did_not_reach_round_six_is_refused(self):
        short = fixture.data()
        short['advancedLog'] = [e for e in short['advancedLog'] if e.get('round') != 6]
        with self.assertRaises(RecordError):
            build('Test-game-0001', short)

    def test_a_log_pointing_past_the_history_is_refused(self):
        stray = fixture.data()
        stray['advancedLog'] = stray['advancedLog'] + [{'player': 0, 'move': 999}]
        with self.assertRaises(RecordError):
            build('Test-game-0001', stray)

    def test_an_unfinished_game_is_refused(self):
        with self.assertRaises(RecordError):
            build('Test-game-0001', fixture.data(ended=False))

    def test_an_unknown_resource_is_refused_rather_than_ignored(self):
        odd = fixture.data()
        odd['advancedLog'] = odd['advancedLog'] + [
            {'player': 0, 'changes': {'build': {'dilithium': 3}}}]
        with self.assertRaises(RecordError):
            build('Test-game-0001', odd)

    def test_an_abandoned_game_the_listing_calls_ended_is_refused(self):
        # The listing reports resigned games with status 'ended'; only the gameplay
        # record's own flag says whether six rounds were actually played.
        with self.assertRaises(RecordError):
            build('Frontiers-3', fixture.data(ended=False))

    def test_an_expansion_this_package_cannot_read_is_refused_by_name(self):
        with self.assertRaises(RecordError) as caught:
            build('Test-game-0001', fixture.data(expansions=2))
        self.assertIn('frontiers is not supported', str(caught.exception))

    def test_an_unreadable_move_is_a_skipped_game_not_a_dead_crawl(self):
        # `sync` catches RecordError. A NotationError escaping it would end a crawl of
        # thousands of games because one record used a move shape the parser lacks.
        odd = fixture.data()
        odd['moveHistory'] = list(fixture.MOVES)
        odd['moveHistory'][3] = 'terrans teleport 3A1'
        with self.assertRaises(RecordError) as caught:
            build('Test-game-0001', odd)
        self.assertIn('teleport', str(caught.exception))

    def test_round_scoring_tiles_are_carried_and_counted(self):
        self.assertEqual(len(self.record.round_scorings), 6)
        self.assertEqual(self.record.final_scorings, ('gaia', 'satellite'))


class TurnOrderTests(unittest.TestCase):
    def setUp(self):
        self.record = build('Test-game-0001', fixture.data(), fixture.summary())

    def test_round_one_follows_the_setup_order(self):
        self.assertEqual(self.record.setup_order, ('terrans', 'xenos'))
        self.assertEqual(turn_orders(self.record)[1], (0, 1))

    def test_later_rounds_follow_the_previous_round_pass_order(self):
        # Terrans passed first in round 1, so they lead round 2.
        self.assertEqual(turn_orders(self.record)[2], (0, 1))

    def test_a_round_nobody_passed_in_gets_no_derived_order(self):
        self.assertNotIn(4, turn_orders(self.record))

    def test_a_setup_order_that_is_not_the_seated_factions_is_refused(self):
        wrong = fixture.data()
        wrong['setup'] = ['terrans', 'gleens']
        with self.assertRaises(RecordError):
            build('Test-game-0001', wrong)


class ExpansionTests(unittest.TestCase):
    def test_the_two_endpoints_disagree_on_shape_and_both_are_read(self):
        self.assertEqual(decode_expansions(0), ())
        self.assertEqual(decode_expansions(2), ('frontiers',))
        self.assertEqual(decode_expansions(4), ('lost-fleet',))
        self.assertEqual(decode_expansions(6), ('frontiers', 'lost-fleet'))
        self.assertEqual(decode_expansions(['lost-fleet']), ('lost-fleet',))

    def test_an_unknown_expansion_bit_is_refused(self):
        # Mislabelling an expansion game as base-game would poison the setup filters.
        with self.assertRaises(RecordError):
            decode_expansions(8)


if __name__ == '__main__':
    unittest.main()
