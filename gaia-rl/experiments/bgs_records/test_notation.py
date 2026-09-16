"""Parser tests: every accepted shape came off a real record, every refusal is deliberate."""
import unittest

from bgs_records.notation import (Clause, NotationError, SHIP_FEDERATION,
                                  parse_history, parse_move)


class ParseTests(unittest.TestCase):
    def test_init_line_opens_a_record(self):
        move = parse_move('init 2 Amphibian-mint-2421', 0)
        self.assertIsNone(move.faction)
        self.assertEqual(move.clauses, (Clause('init', ('2', 'Amphibian-mint-2421')),))

    def test_setup_subjects_are_seats_not_factions(self):
        self.assertIsNone(parse_move('p1 faction terrans', 1).faction)
        self.assertEqual(parse_move('p2 bid ambas 5', 2).clauses[0],
                         Clause('bid', ('ambas', '5')))

    def test_a_move_splits_into_its_clauses(self):
        move = parse_move('terrans build lab 3A1. tech nav. up nav (0 ⇒ 1).', 13)
        self.assertEqual(move.faction, 'terrans')
        self.assertEqual(move.commands(), ('build', 'tech', 'up'))
        self.assertEqual(move.first('build'), Clause('build', ('lab', '3A1')))

    def test_annotations_are_kept_but_are_not_clauses(self):
        move = parse_move('xenos charge 2pw (1/5/0/0 ⇒ 0/5/1/0)', 15)
        self.assertEqual(move.commands(), ('charge',))
        self.assertEqual(move.annotations, ('1/5/0/0 ⇒ 0/5/1/0',))

    def test_brainstone_rides_along_in_a_bowl_annotation(self):
        move = parse_move('taklons burn 1. (0,B/4/0/0 ⇒ 0/2/2,B/0)', 40)
        self.assertEqual(move.commands(), ('burn',))

    def test_the_brainstone_can_be_discarded_as_well_as_moved(self):
        for destination in ('area1', 'area2', 'area3', 'gaia', 'discard'):
            with self.subTest(destination=destination):
                move = parse_move(f'taklons brainstone {destination}', 40)
                self.assertEqual(move.first('brainstone').args, (destination,))

    def test_spend_keeps_cost_and_gain_apart(self):
        self.assertEqual(parse_move('nevlas spend 4pw for 1q', 20).clauses[0],
                         Clause('spend', ('4pw', '1q')))

    def test_pass_distinguishes_the_booster_taken_from_the_one_returned(self):
        self.assertEqual(parse_move('terrans pass booster6 returning booster3', 90).clauses[0],
                         Clause('pass', ('booster6', 'booster3')))
        self.assertEqual(parse_move('xenos pass returning booster6', 166).clauses[0],
                         Clause('pass', ('', 'booster6')))

    def test_a_missing_separator_after_pass_still_yields_both_clauses(self):
        # Recorded verbatim in S3-2313 move 164; the site omitted the '.' itself.
        move = parse_move('bescods pass booster4 spend 1pw for 1c', 164)
        self.assertEqual(move.commands(), ('pass', 'spend'))
        self.assertEqual(move.first('spend'), Clause('spend', ('1pw', '1c')))

    def test_power_payment_is_split_off_the_clause(self):
        move = parse_move('terrans build gf 6A9 using area1: 4, area2: 2. (4/4/0/0 ⇒ 0/2/0/6)', 18)
        self.assertEqual(move.first('build').args, ('gf', '6A9'))
        self.assertEqual(move.first('build').using, (('area1', 4), ('area2', 2)))

    def test_a_taklons_brainstone_pays_like_a_token(self):
        move = parse_move('taklons federation 2A10,8C fed1 using area2: 4, brainstone: 1.', 334)
        self.assertEqual(move.first('federation').using, (('area2', 4), ('brainstone', 1)))

    def test_federation_keeps_its_hexes_and_tile(self):
        clause = parse_move('ivits federation 7B1,7B3,7B5,7C fed4', 78).clauses[0]
        self.assertEqual(clause.args, ('7B1,7B3,7B5,7C', 'fed4'))

    def test_every_observed_coordinate_shape_is_accepted(self):
        for coordinate in ('3A1', '7C', '10A8', 'IS5', 'DS12_0'):
            with self.subTest(coordinate=coordinate):
                move = parse_move(f'darkanians build m {coordinate}', 6)
                self.assertEqual(move.first('build').args[1], coordinate)

    def test_lost_fleet_commands_are_understood(self):
        move = parse_move('darkanians spaceshipAction tfmars power. gaiaFormTransdim 1A11.', 44)
        self.assertEqual(move.commands(), ('spaceshipAction', 'gaiaFormTransdim'))

    def test_spaceship_federation_tokens_are_matched_by_shape(self):
        self.assertTrue(SHIP_FEDERATION.fullmatch('ship-fed-credit'))
        clause = parse_move('nevlas federation 1A0,3A3 ship-fed-credit using area1: 3.',
                            89).clauses[0]
        self.assertEqual(clause.args[1], 'ship-fed-credit')

    def test_move_index_is_the_zero_based_history_offset(self):
        moves = parse_history(['init 2 g', 'p1 faction terrans', 'terrans build m 3A1'])
        self.assertEqual([m.index for m in moves], [0, 1, 2])
        self.assertEqual(moves[2].faction, 'terrans')

    def test_unreadable_lines_raise_rather_than_being_skipped(self):
        lines = (
            'terrans teleport 3A1',            # command the site has never emitted
            'terrans build castle 3A1',        # structure that does not exist
            'terrans up philosophy',           # research track that does not exist
            'terrans build m 3Z1',             # coordinate outside every known shape
            'martians build m 3A1',            # faction that does not exist
            'terrans action power9',           # board action outside power1-7 / qic1-3
            'terrans booster booster42',       # booster outside the ten printed ones
            'terrans spend 3pw 1o',            # spend without its 'for'
            'p1 faction',                      # a declaration with no faction
            'terrans build gf 6A9 using area9: 4',      # power bowl that does not exist
            'terrans charge 2pw (1/5/0/0 -> 0/5/1/0)',  # annotation it cannot read
        )
        for line in lines:
            with self.subTest(line=line), self.assertRaises(NotationError):
                parse_move(line, 1)

    def test_an_empty_history_is_refused(self):
        with self.assertRaises(NotationError):
            parse_history([])


if __name__ == '__main__':
    unittest.main()
