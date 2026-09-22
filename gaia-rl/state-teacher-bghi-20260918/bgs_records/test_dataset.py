"""Row tests. A row that silently carries an unverified feature is the failure to avoid."""
import gzip
import json
import tempfile
import unittest
from pathlib import Path

from bgs_records import fixture
from bgs_records.corpus import Corpus
from bgs_records.dataset import (REQUIRED_FIELDS, SCHEMA_VERSION, player_key, rows,
                                 write)
from bgs_records.timeline import build


class RowTests(unittest.TestCase):
    def setUp(self):
        self.data = fixture.data()
        self.record = build('Test-game-0001', self.data, fixture.summary())
        self.rows = list(rows(self.record, self.data))

    def test_setup_lines_without_an_acting_faction_produce_no_row(self):
        self.assertTrue(all(row.faction is not None for row in self.rows))
        self.assertNotIn(1, [row.move_index for row in self.rows])  # 'p1 faction terrans'

    def test_reactions_are_left_out_unless_asked_for(self):
        self.assertNotIn('charge', [row.action['command'] for row in self.rows])
        with_reactions = list(rows(self.record, self.data, include_reactions=True))
        self.assertIn('charge', [row.action['command'] for row in with_reactions])

    def test_a_row_names_the_leading_clause_and_keeps_the_rest(self):
        row = next(r for r in self.rows if r.move_index == 11)
        self.assertEqual(row.action['command'], 'build')
        self.assertEqual([c['command'] for c in row.action['clauses']],
                         ['build', 'tech', 'up'])
        self.assertEqual(row.action['raw'], fixture.MOVES[11])

    def test_power_payment_survives_into_the_row(self):
        row = next(r for r in self.rows if r.action['command'] == 'federation')
        self.assertEqual(row.action['clauses'][0]['using'], [['area1', 2]])

    def test_features_describe_the_position_before_the_move(self):
        row = next(r for r in self.rows if r.move_index == 11)
        self.assertEqual(row.features['buildings']['ts'], 1)
        self.assertEqual(row.features['buildings']['lab'], 0)
        self.assertEqual(row.features['victory_points'], 10)

    def test_rows_carry_where_the_seat_sat_in_the_round_order(self):
        row = next(r for r in self.rows if r.move_index == 11)
        self.assertEqual(row.features['turn_order'], [0, 1])
        self.assertEqual(row.features['turn_position'], 0)

    def test_features_describe_the_opponents_board_not_just_their_score(self):
        row = next(r for r in self.rows if r.move_index == 11)
        opponent, = row.features['opponents']
        self.assertEqual(opponent['seat'], 1)
        self.assertEqual(opponent['faction'], 'xenos')
        self.assertEqual(opponent['buildings']['m'], 2)
        self.assertEqual(opponent['colonised'], 2)
        self.assertEqual(opponent['victory_points'], 9)   # paid a VP to charge

    def test_features_never_claim_the_power_bowls(self):
        # A move log cannot recover them, so no row may imply otherwise.
        for row in self.rows:
            self.assertNotIn('power', row.features)

    def test_outcomes_look_forward_from_the_move(self):
        row = next(r for r in self.rows if r.move_index == 11)
        self.assertEqual(row.outcome['final_victory_points'], 24)
        self.assertEqual(row.outcome['victory_points_still_to_come'], 14)
        self.assertTrue(row.outcome['won'])
        self.assertEqual(row.outcome['placement'], 1)
        self.assertEqual(row.outcome['margin'], 12)

    def test_the_losing_seat_is_labelled_as_such(self):
        row = next(r for r in self.rows if r.seat == 1)
        self.assertFalse(row.outcome['won'])
        self.assertEqual(row.outcome['placement'], 2)

    def test_a_rating_floor_drops_only_the_seats_below_it(self):
        # Seat 1 (xenos) entered on 180, seat 0 (terrans) on 200 — see the fixture.
        both = {r.seat for r in rows(self.record, self.data, min_elo=120)}
        self.assertEqual(both, {0, 1})
        strong = {r.seat for r in rows(self.record, self.data, min_elo=190)}
        self.assertEqual(strong, {0})

    def test_rows_group_by_player_without_carrying_the_name(self):
        by_seat = {r.seat: r.player for r in self.rows}
        self.assertEqual(len(set(by_seat.values())), 2)
        self.assertEqual(by_seat[0], player_key('first'))
        self.assertNotIn('first', by_seat[0])

    def test_the_same_account_keys_the_same_across_games(self):
        self.assertEqual(player_key('someone'), player_key('someone'))
        self.assertNotEqual(player_key('someone'), player_key('someone else'))
        self.assertEqual(player_key(''), '')

    def test_rows_carry_the_whole_table_rating_so_they_can_be_weighed(self):
        row = self.rows[0]
        self.assertEqual(row.setup['table_elo'], [200, 180])
        self.assertEqual(row.setup['table_min_elo'], 180)

    def test_every_row_carries_the_setup_it_came_from(self):
        for row in self.rows:
            self.assertEqual(row.setup['nb_players'], 2)
            self.assertEqual(row.setup['faction_variant'], 'standard')
            self.assertEqual(row.setup['expansions'], [])
            self.assertEqual(row.setup['engine_version'], '4.8.51')

    def test_the_engine_faction_spelling_is_carried_for_joining(self):
        self.assertEqual({r.engine_faction for r in self.rows}, {'Terrans', 'Xenos'})

    def test_a_game_whose_rebuild_does_not_verify_contributes_nothing(self):
        skewed = fixture.data()
        skewed['players'][0]['data']['buildings']['lab'] = 3
        self.assertEqual(list(rows(self.record, skewed)), [])

    def test_the_required_fields_are_the_ones_state_can_verify(self):
        self.assertEqual(REQUIRED_FIELDS, ('victory_points', 'structures', 'research'))


class WriteTests(unittest.TestCase):
    def test_the_file_opens_with_a_schema_header_then_one_row_per_line(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Corpus(Path(directory) / 'mirror')
            corpus.store('Test-game-0001', fixture.data(), fixture.summary())
            out = Path(directory) / 'decisions.jsonl'
            report = write(corpus, out)
            lines = out.read_text().splitlines()
            header = json.loads(lines[0])
            self.assertEqual(header['schema'], SCHEMA_VERSION)
            self.assertEqual(header['source'], 'boardgamers.space')
            # A file found later must be able to say which filters produced it.
            self.assertEqual(header['filters']['min_elo'], None)
            self.assertEqual(header['filters']['include_reactions'], False)
            self.assertEqual(report.rows, len(lines) - 1)
            self.assertEqual(report.games, 1)
            self.assertTrue(all(json.loads(line)['game_id'] == 'Test-game-0001'
                                for line in lines[1:]))

    def test_a_gz_suffix_writes_the_same_file_compressed(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Corpus(Path(directory) / 'mirror')
            corpus.store('Test-game-0001', fixture.data(), fixture.summary())
            plain = Path(directory) / 'decisions.jsonl'
            packed = Path(directory) / 'decisions.jsonl.gz'
            write(corpus, plain)
            write(corpus, packed)
            with gzip.open(packed, 'rt') as stream:
                self.assertEqual(stream.read(), plain.read_text())
            self.assertLess(packed.stat().st_size, plain.stat().st_size)

    def test_the_header_records_a_rating_floor_that_was_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Corpus(Path(directory) / 'mirror')
            corpus.store('Test-game-0001', fixture.data(), fixture.summary())
            out = Path(directory) / 'decisions.jsonl'
            write(corpus, out, min_elo=190)
            header = json.loads(out.read_text().splitlines()[0])
            self.assertEqual(header['filters']['min_elo'], 190)


if __name__ == '__main__':
    unittest.main()
