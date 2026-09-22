from copy import deepcopy
import unittest

from bgg_openings.catalog import load_catalog, parse_buildings
from bgg_openings.inventory import building_counts, matches, round_one_result


def player(faction='Itars', player_id=17, kinds=()):
    return {'player_id': player_id, 'faction': faction,
            'structures': [{'hex': f'{i},0', 'kind': kind} for i, kind in enumerate(kinds)]}


class InventoryTests(unittest.TestCase):
    def test_current_pieces_not_historical_milestones(self):
        p = player(kinds=('ResearchLab', 'Mine', 'Mine'))
        self.assertEqual(building_counts(p), parse_buildings('1RL+2M'))
        p['structures'][0]['kind'] = {'Academy': 'Science'}
        self.assertEqual(building_counts(p), parse_buildings('1AC+2M'))
        p['structures'][0]['kind'] = {'Academy': 'Qic'}
        self.assertEqual(building_counts(p), parse_buildings('1AC+2M'))

    def test_starting_mines_already_count_and_upgrades_remove_mine(self):
        p = player('Ambas', kinds=('ResearchLab',) + ('Mine',) * 5)
        self.assertEqual(building_counts(p).mine, 5)
        opening = next(r for r in load_catalog()['Ambas'] if r.label == '1RL+5M')
        self.assertTrue(matches(p, opening))
        p['structures'][1]['kind'] = 'TradingStation'
        self.assertFalse(matches(p, opening))

    def test_exact_composition_not_minimum_and_correct_faction(self):
        opening = next(r for r in load_catalog()['Itars'] if r.label == '1PI+2M')
        p = player(kinds=('PlanetaryInstitute', 'Mine', 'Mine'))
        self.assertTrue(matches(p, opening))
        p['structures'].append({'hex': '4,0', 'kind': 'TradingStation'})
        self.assertFalse(matches(p, opening))
        p['structures'].pop()
        p['faction'] = 'Terrans'
        self.assertFalse(matches(p, opening))

    def test_ivits_initial_pi_and_firaks_downgrade(self):
        p = player('Ivits', kinds=('PlanetaryInstitute', 'ResearchLab', 'Mine', 'SpaceStation'))
        self.assertEqual(building_counts(p), parse_buildings('1PI+1RL+1M'))
        p = player('Firaks', kinds=('PlanetaryInstitute', 'TradingStation'))
        self.assertEqual(building_counts(p), parse_buildings('1PI+1TS'))

    def test_only_actual_round_one_boundary_not_a_round_two_rescue(self):
        p = player(kinds=('PlanetaryInstitute', 'Mine', 'Mine'))
        before = {'state': {'round': 1, 'players': [p]}, 'steps': 20, 'decision_id': 20}
        after = deepcopy(before)
        after.update(steps=21, decision_id=21)
        after['state']['round'] = 2
        result = round_one_result(before, after, 17)
        self.assertEqual([r.label for r in result], ['1PI+2M'])
        self.assertEqual(before['state']['players'][0], p)
        # A later R2 improvement must not be attributed to the R1 opening.
        after['state']['players'][0]['structures'].append({'hex': '4,0', 'kind': 'Mine'})
        self.assertEqual([r.label for r in round_one_result(before, after, 17)], ['1PI+2M'])
        before['state']['round'] = 2
        with self.assertRaises(ValueError):
            round_one_result(before, after, 17)

    def test_unknown_kind_and_missing_actor_do_not_silently_match(self):
        with self.assertRaises(ValueError):
            building_counts(player(kinds=('UnknownBuilding',)))
        before = {'state': {'round': 1, 'players': []}, 'steps': 1, 'decision_id': 1}
        after = {'state': {'round': 2, 'players': []}, 'steps': 2, 'decision_id': 2}
        with self.assertRaises(ValueError):
            round_one_result(before, after, 17)


if __name__ == '__main__':
    unittest.main()
