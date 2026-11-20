"""Tests for faction_strength: without_order, the board list, and the committed AI test order table."""
import json
import unittest
from pathlib import Path

import faction_strength
from faction_strength import BOARDS, without_order

TABLE = Path(__file__).resolve().parents[2] / 'gaia-frontend/src/aiTestOrder.json'


class WithoutOrderTest(unittest.TestCase):
    def test_unchanged_without_order(self):
        self.assertEqual(without_order('quartet-e-88365'), 'quartet-e-88365')

    def test_order_dropped(self):
        self.assertEqual(without_order('quartet-e-88365@order=3,0,2,1'), 'quartet-e-88365')
        self.assertEqual(
            without_order('quartet-e-88365@factions=A,B,C,D@order=1,0,3,2'),
            'quartet-e-88365@factions=A,B,C,D',
        )
        self.assertEqual(
            without_order('quartet-e-88365@order=1,0,3,2@tiles=x'),
            'quartet-e-88365@tiles=x',
        )


class BoardsTest(unittest.TestCase):
    def test_nine_boards_eighteen_names(self):
        names = [name for sides in BOARDS for name in sides]
        self.assertEqual(len(BOARDS), 9)
        self.assertEqual(len(names), 18)
        self.assertEqual(len(set(names)), 18)
        self.assertEqual(set(names), set(faction_strength.TIER))


class OrderTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = json.loads(TABLE.read_text())

    def test_factions_follow_boards(self):
        self.assertEqual(self.table['factions'], [name for sides in BOARDS for name in sides])

    def test_orders(self):
        orders = self.table['orders']
        self.assertEqual(len(orders), 2016)
        board_of = {}
        for index, sides in enumerate(BOARDS):
            board_of[chr(97 + 2 * index)] = index
            board_of[chr(98 + 2 * index)] = index
        for key, value in orders.items():
            self.assertEqual(len(key), 4, key)
            self.assertEqual(list(key), sorted(key), key)
            self.assertEqual(len({board_of[letter] for letter in key}), 4, key)
            self.assertEqual(sorted(value), list(key), key)

    def test_known_entry(self):
        self.assertEqual(self.table['orders']['aceg'], 'ecag')


if __name__ == '__main__':
    unittest.main()
