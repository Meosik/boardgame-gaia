import copy
import unittest
from economy.test_teacher import fixture, line_board
from federation.teacher import FederationTeacher, formations, goal_weight, minimum, power, preparation


class FederationTests(unittest.TestCase):
    def setUp(self):
        self.s, self.p = fixture()
        self.state = self.s['state']
        line_board(self.state)
        self.p['structures'] = [{'hex': '0,0', 'kind': 'TradingStation'}, {'hex': '2,0', 'kind': 'Mine'}]
        self.p['federated_hexes'] = []
        self.p['federation_tokens'] = []
        self.p['gray_federation_tokens'] = []
        self.state['final_scoring_tiles'] = []
        self.teacher = FederationTeacher()

    def test_federated_lab_is_neutral_but_power_increase_prefers_outside(self):
        self.p['federated_hexes'] = ['0,0']
        self.assertEqual(preparation(self.state, self.p, '0,0', 'TradingStation', 'ResearchLab'), 0)
        self.assertLess(preparation(self.state, self.p, '0,0', 'TradingStation', 'PlanetaryInstitute'), 0)
        self.assertGreater(preparation(self.state, self.p, '2,0', 'Mine', 'TradingStation'), 0)

    def test_new_mine_adjacent_to_existing_federation_is_not_new_federation_power(self):
        self.p['federated_hexes'] = ['0,0']
        self.assertLess(preparation(self.state, self.p, '1,0', None, 'Mine'), 0)
        self.assertGreater(preparation(self.state, self.p, '3,0', None, 'Mine'), 0)

    def test_power_and_xenos_threshold_follow_engine(self):
        self.assertEqual(minimum(self.p), 7)
        self.p['structures'].append({'hex': '4,0', 'kind': 'PlanetaryInstitute'})
        self.assertEqual(minimum(self.p), 6)
        self.p['tech_tiles'] = [6]
        self.assertEqual(power(self.p, {'Academy': 'Knowledge'}), 4)
        self.assertEqual(power(self.p, 'ResearchLab'), 2)
        self.p['covered_tech_tiles'] = [6]
        self.assertEqual(power(self.p, {'Academy': 'Qic'}), 3)
        self.p['faction'] = 'HadschHallas'
        self.assertEqual(minimum(self.p), 7)

    def test_three_goal_satellite_exception_and_terraform_bonus(self):
        self.p['federation_tokens'] = [1, 2]
        self.p['gray_federation_tokens'] = [3]
        self.p['research_tracks']['terraforming'] = 5
        self.assertEqual(formations(self.p), 2)
        self.assertEqual(goal_weight(self.state, self.p), 1)
        self.p['federation_tokens'].append(4)
        self.assertEqual(goal_weight(self.state, self.p), .35)
        self.p['federation_tokens'] = []
        self.state['final_scoring_tiles'] = [{'condition': 'MostSatellites'}]
        self.assertEqual(goal_weight(self.state, self.p), .35)

    def test_reserve_and_route_penalties_do_not_ban_federations(self):
        self.state['round'] = 3
        self.p['resources']['power'].update(bowl1=2, bowl2=3, bowl3=2)
        action = {'type': 'FormFederation', 'hexes': ['0,0', '2,0'], 'satellite_hexes': ['1,0']}
        short = self.teacher.adjustment(self.state, self.p, action)
        long = self.teacher.adjustment(self.state, self.p, action | {'satellite_hexes': ['1,0', '3,0', '4,0', '5,0', '6,0']})
        self.assertGreater(short, long)
        self.state['round'] = 6
        self.assertGreater(self.teacher.adjustment(self.state, self.p, action | {'satellite_hexes': ['1,0']*5}), long)

    def test_rank_preserves_input_and_candidate_legality(self):
        self.s['candidates'] = [{'action': {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab', 'tech_tile_choice': None}},
                                {'action': {'type': 'Upgrade', 'coord': '2,0', 'to': 'TradingStation', 'tech_tile_choice': None}}]
        before = copy.deepcopy(self.s)
        decision, index = self.teacher.choose(self.s)
        self.assertEqual(decision, self.s['decision_id'])
        self.assertIn(index, (0, 1))
        self.assertEqual(self.s, before)


if __name__ == '__main__':
    unittest.main()
