"""Source semantics, not a claim that these historical openings win in Lost Fleet."""
from dataclasses import FrozenInstanceError
import unittest

from bgg_openings.catalog import Opening, load_catalog, parse_buildings


class CatalogTests(unittest.TestCase):
    def test_all_source_rows_and_only_base_factions(self):
        expected = {'Ambas': 23, 'BalTaks': 11, 'Bescods': 15, 'Firaks': 13,
            'Geodens': 15, 'Gleens': 15, 'HadschHallas': 15, 'Itars': 17,
            'Ivits': 15, 'Lantids': 15, 'Nevlas': 16, 'Taklons': 18,
            'Terrans': 18, 'Xenos': 16}
        catalog = load_catalog()
        self.assertEqual({f: len(rows) for f, rows in catalog.items()}, expected)
        self.assertEqual(sum(map(len, catalog.values())), 222)
        for faction, rows in catalog.items():
            self.assertEqual([r.source_row for r in rows], list(range(1, len(rows) + 1)))
            self.assertEqual([r.games for r in rows], sorted((r.games for r in rows), reverse=True))
            self.assertEqual(len({r.buildings for r in rows}), len(rows), faction)
            self.assertTrue(all(r.faction == faction and r.games >= 5 for r in rows))

    def test_directly_inspected_image_values_and_no_win_rate(self):
        catalog = load_catalog()
        for faction, label, games, score in (
            ('Geodens', '1PI+4M', 228, 153), ('HadschHallas', '1AC+2M', 244, 149),
            ('Itars', '1PI+2M', 326, 157), ('Taklons', '2RL+2M', 59, 168),
            ('Ambas', '1TS+7M', 7, 176), ('Terrans', '1RL+5M', 14, 172),
        ):
            row = next(r for r in catalog[faction] if r.label == label)
            self.assertEqual((row.games, row.average_score), (games, score))
            self.assertFalse(hasattr(row, 'win_rate'))
            with self.assertRaises(FrozenInstanceError):
                row.games = 1

    def test_inventory_parser_does_not_invent_academy_type_or_action_sequence(self):
        result = parse_buildings('1AC+1PI+2M')
        self.assertEqual(result, parse_buildings('1PI+2M+1AC'))
        self.assertEqual(result.academy, 1)
        self.assertEqual(result.research_lab, 0)  # No historical intermediate Lab counted.
        self.assertEqual(parse_buildings('1RL+5M').mine, 5)
        self.assertEqual(parse_buildings('2RL').mine, 0)

    def test_invalid_notation_and_invented_metrics_rejected(self):
        for label in ('', '0M', '9M', '1PI+1PI', '3AC', '1QIC', 'AC+2M', '1RL+5M+', '1M+1TSx'):
            with self.subTest(label=label), self.assertRaises(ValueError):
                parse_buildings(label)
        with self.assertRaises(ValueError):
            Opening('Tinkeroids', '1PI+2M', 5, 150, 5, 1)
        with self.assertRaises(ValueError):
            Opening('Itars', '1PI+2M', 0, 150, 5, 1)


if __name__ == '__main__':
    unittest.main()
