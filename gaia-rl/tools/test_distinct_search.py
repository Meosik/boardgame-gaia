"""distinct_search: root order, value-led openings and the distinct-first budget."""
import unittest

import budget_teacher
import teacher_patches as tp


class Goal:
    def __init__(self, first):
        self.first, self.family = first, 'root'


def candidate(action):
    return {'action': action}


class DistinctSearchTests(unittest.TestCase):
    def test_later_gain_choices(self):
        self.assertTrue(tp.later_gain(candidate({'type': 'SelectStartingBooster', 'booster_id': 8})))
        self.assertTrue(tp.later_gain(candidate({'type': 'Pass', 'booster_id': 12})))
        self.assertFalse(tp.later_gain(candidate({'type': 'SelectStartingBooster', 'booster_id': 13})))
        self.assertTrue(tp.later_gain(candidate({'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'})))
        self.assertTrue(tp.later_gain(candidate({'type': 'ExploreSpaceship', 'ship': 'Twilight'})))
        self.assertFalse(tp.later_gain(candidate({'type': 'ResearchAdvance', 'track': 'Economy'})))

    def test_order_roots_puts_later_gain_first_and_keeps_ranking_order(self):
        snapshot = {'candidates': [
            candidate({'type': 'SelectStartingBooster', 'booster_id': 13}),
            candidate({'type': 'SelectStartingBooster', 'booster_id': 14}),
            candidate({'type': 'SelectStartingBooster', 'booster_id': 8}),
            candidate({'type': 'SelectStartingBooster', 'booster_id': 12}),
            candidate({'type': 'Upgrade', 'tech_tile_choice': {'tile': 5}}),
            candidate({'type': 'Upgrade', 'tech_tile_choice': {'tile': 10}}),
        ]}
        ordered = tp.order_roots(snapshot, [Goal(i) for i in (1, 0, 3, 4, 2, 5)])
        self.assertEqual([g.first for g in ordered], [5, 3, 4, 2, 1, 0])

    def test_opening_only_from_best_value(self):
        seen = []

        def original(rows, remembered, comparisons):
            seen.append(comparisons)
            return comparisons[0] if comparisons else None
        plans = [{'goal': 'BGG', 'complete': True, 'value': 122.8},
                 {'goal': 'current-choice', 'complete': True, 'value': 154.4},
                 {'goal': 'unfinished', 'complete': False, 'value': 200.0}]
        self.assertEqual(tp.value_first_forecast(original, (), None, plans)['goal'], 'current-choice')
        self.assertEqual(seen[-1], [plans[1]])
        self.assertIsNone(tp.value_first_forecast(original, (), None, [plans[2]]))

    def test_budget_counts_distinct_first_moves(self):
        plans = [{'first': 1}, {'first': 1}, {'first': 2}]
        try:
            budget_teacher.count_distinct_firsts(True)
            self.assertEqual(budget_teacher._spent(plans), 2)
            budget_teacher.count_distinct_firsts(False)
            self.assertEqual(budget_teacher._spent(plans), 3)
        finally:
            budget_teacher.count_distinct_firsts(False)


if __name__ == '__main__':
    unittest.main()
