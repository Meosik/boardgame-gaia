from dataclasses import asdict
import math
import unittest

from bgg_openings.catalog import load_catalog, parse_buildings
from bgg_openings.planning import distance_to, select_forecast


class OpeningPlanningTests(unittest.TestCase):
    def test_optimistic_inventory_distance_allows_intermediate_upgrades(self):
        target = parse_buildings('1AC+2M')
        self.assertEqual(distance_to(parse_buildings('3M'), target, 'Terrans'), 3)
        self.assertEqual(distance_to(parse_buildings('1TS+2M'), target, 'Terrans'), 2)
        self.assertEqual(distance_to(parse_buildings('1RL+2M'), target, 'Terrans'), 1)
        self.assertEqual(distance_to(target, target, 'Terrans'), 0)
        self.assertIsNone(distance_to(parse_buildings('1PI+2M'), target, 'Terrans'))

    def test_faction_paths_are_only_optimistic_ordering_not_native_legality(self):
        self.assertEqual(distance_to(parse_buildings('1TS+2M'), parse_buildings('1AC+2M'), 'Bescods'), 1)
        self.assertEqual(distance_to(parse_buildings('1RL+2M'), parse_buildings('1PI+2M'), 'Bescods'), 1)
        self.assertEqual(distance_to(parse_buildings('1PI+1RL'), parse_buildings('1PI+1TS'), 'Firaks'), 1)
        self.assertIsNone(distance_to(parse_buildings('1PI+1RL'), parse_buildings('1PI+1TS'), 'Terrans'))

    def forecast(self, label, value, first=0, **extra):
        return {'complete': True, 'value': value, 'first': first,
            'r1_buildings': asdict(parse_buildings(label)), **extra}

    def test_choose_keep_and_switch_only_from_completed_native_forecasts(self):
        rows = load_catalog()['Terrans']
        a = self.forecast('1PI+2M', 10)
        b = self.forecast('1AC+2M', 20, 1)
        chosen, opening = select_forecast(rows, None, [a, b])
        self.assertIs(chosen, b)
        self.assertEqual(opening.label, '1AC+2M')
        chosen, opening = select_forecast(rows, '1PI+2M', [a, b])
        self.assertIs(chosen, a)  # Keep a still-verifiable target, not chase a new score every turn.
        chosen, opening = select_forecast(rows, '1PI+2M', [b])
        self.assertIs(chosen, b)
        self.assertEqual(opening.label, '1AC+2M')

    def test_unknown_failed_nonmatching_or_later_round_results_cannot_force_actions(self):
        rows = load_catalog()['Terrans']
        candidates = [self.forecast('1PI+2M', 100, complete=False),
            self.forecast('1AC+2M', 100, r1_buildings=None),
            self.forecast('8M', 100), self.forecast('1PI+2M', math.nan)]
        self.assertIsNone(select_forecast(rows, None, candidates))
        self.assertIsNone(select_forecast((), None, [self.forecast('1PI+2M', 100)]))

    def test_observed_average_score_is_not_added_to_teacher_value(self):
        rows = load_catalog()['Terrans']
        low_average = self.forecast('1PI+2M', 10)
        high_average = self.forecast('1RL+5M', 9)
        chosen, _ = select_forecast(rows, None, [low_average, high_average])
        self.assertIs(chosen, low_average)


if __name__ == '__main__':
    unittest.main()
