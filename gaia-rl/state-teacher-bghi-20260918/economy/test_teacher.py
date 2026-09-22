import copy
import json
from pathlib import Path
import unittest

from gaia_rl._native import Environment
from economy.teacher import (EconomyTeacher, construction_cost, steps_for, paths,
                             range_qic, neighbors)


def fixture():
    state = json.loads(Environment('strategy-19-heldout-192').snapshot_json())
    state['player'] = 1
    player = state['state']['players'][1]
    return state, player


def line_board(state):
    state['board']['hexes'] = {f'{q},0': {'planet': None, 'structures': [], 'satellites': []}
                               for q in range(7)}
    for q in (0, 1, 2, 3, 4):
        state['board']['hexes'][f'{q},0']['planet'] = {
            'planet_type': 'Desert', 'owner': None, 'is_gaia_formed': False}
    state['board']['hexes']['0,0']['structures'] = [{'owner': 1, 'kind': 'Mine'}]
    state['board']['hexes']['0,0']['planet']['owner'] = 1
    state['board']['spaceship_tiles'] = {'Rebellion': '5,0', 'TFMars': '6,0'}


class CostTests(unittest.TestCase):
    def setUp(self):
        self.s, self.p = fixture()
        self.state = self.s['state']
        line_board(self.state)
        self.teacher = EconomyTeacher()

    def cost(self, **action):
        return construction_cost(self.state, self.p, action)

    def test_trading_discount_requires_opponent_not_own_structure(self):
        action = dict(type='Upgrade', coord='0,0', to='TradingStation')
        self.assertEqual(self.cost(**action).credits, 6)
        self.state['board']['hexes']['2,0']['structures'] = [{'owner': 1, 'kind': 'Mine'}]
        self.assertEqual(self.cost(**action).credits, 6)
        self.state['board']['hexes']['2,0']['structures'][0]['owner'] = 2
        self.assertEqual(self.cost(**action).credits, 3)
        self.assertEqual(self.cost(**action).ore, 2)

    def test_paid_steps_research_and_tf_mars_activation(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Volcanic'
        self.assertEqual(self.cost(type='Build', coord='1,0').terraform_ore, 3)
        tf = self.cost(type='SpaceshipCreditTerraform', coord='1,0')
        self.assertEqual((tf.ore, tf.credits, tf.terraform_ore), (1, 5, 0))
        for level, ore in enumerate((3, 3, 2, 1, 1, 1)):
            self.p['research_tracks']['terraforming'] = level
            self.assertEqual(self.cost(type='Build', coord='1,0').terraform_ore, ore)

    def test_power_steps_are_free_but_activation_is_not(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Oxide'
        one = self.cost(type='PowerAction', id=6, coord='1,0')
        two = self.cost(type='PowerAction', id=2, coord='1,0')
        self.assertEqual((one.terraform_ore, one.power), (3, 3))
        self.assertEqual((two.terraform_ore, two.power), (0, 5))

    def test_gaia_owned_former_and_natural_qic(self):
        planet = self.state['board']['hexes']['1,0']['planet']
        planet.update(planet_type='Gaia', is_gaia_formed=False)
        self.assertEqual(self.cost(type='Build', coord='1,0').qic, 0)
        planet.update(planet_type='Gaia', is_gaia_formed=True)
        self.assertEqual(self.cost(type='Build', coord='1,0').qic, 1)
        planet.update(planet_type='Transdim', owner=1)
        self.assertEqual(self.cost(type='Build', coord='1,0').qic, 0)

    def test_asteroid_eclipse_and_protoplanet(self):
        planet = self.state['board']['hexes']['1,0']['planet']
        planet['planet_type'] = 'Asteroid'
        normal = self.cost(type='Build', coord='1,0')
        eclipse = self.cost(type='EclipseAsteroidMine', coord='1,0')
        self.assertEqual((normal.ore, normal.credits), (0, 0))
        self.assertEqual((eclipse.ore, eclipse.credits), (0, 6))
        planet['planet_type'] = 'ProtoPlanet'
        self.assertEqual(self.cost(type='Build', coord='1,0').terraform_ore, 9)

    def test_free_upgrades_keep_activation_cost_not_normal_cost(self):
        c = self.cost(type='RebellionFreeTradingStation', coord='0,0')
        self.assertEqual((c.credits, c.ore, c.power), (0, 1, 3))
        c = self.cost(type='TwilightFreeResearchLab', coord='0,0')
        self.assertEqual((c.credits, c.ore, c.power), (0, 2, 3))

    def test_range_booster_and_covered_navigation_tile(self):
        self.assertEqual(self.cost(type='Build', coord='4,0').qic, 2)
        self.assertEqual(self.cost(type='RoundBoosterRangeBuild', coord='4,0').qic, 0)
        self.p['tech_tiles'] = [12]
        self.assertEqual(self.cost(type='Build', coord='4,0').qic, 1)
        self.p['covered_tech_tiles'] = [12]
        self.assertEqual(self.cost(type='Build', coord='4,0').qic, 2)

    def test_disconnected_board_is_not_straight_hex_reachable(self):
        del self.state['board']['hexes']['2,0']
        self.assertGreater(range_qic(self.state, self.p, '3,0'), 100)
        self.assertNotIn('3,0', paths(frozenset(self.state['board']['hexes']), '0,0'))

    def test_unknown_cost_is_not_treated_as_free(self):
        self.assertIsNone(self.cost(type='FormFederation'))
        self.p['faction'] = 'Terrans'
        with self.assertRaises(ValueError): self.cost(type='Build', coord='1,0')

    def test_one_step_opportunities_with_distance_and_no_double_count(self):
        planet = self.state['board']['hexes']['3,0']['planet']
        planet['planet_type'] = 'Volcanic'
        self.assertGreater(self.teacher.opportunity(self.state, self.p, ['0,0'], '3,0'), 0)
        self.assertEqual(self.teacher.opportunity(self.state, self.p, ['0,0'], '4,0'), 0)
        planet['owner'] = 2
        self.assertEqual(self.teacher.opportunity(self.state, self.p, ['0,0'], '3,0'), 0)
        # Already-owned origin adds no expansion or fleet access (no nearby opponents).
        self.assertEqual(self.teacher.location(self.state, self.p, '0,0'), 0)

    def test_neighbor_opportunity_requires_power_and_has_time_horizon(self):
        self.state['board']['hexes']['1,0']['structures'] = [{'owner': 2, 'kind': 'Mine'}]
        early = self.teacher.charge_potential(self.state, self.p, '0,0')
        self.p['resources']['power'].update(bowl1=0, bowl2=0, bowl3=0)
        self.assertLess(self.teacher.charge_potential(self.state, self.p, '0,0'), early)
        self.state['round'] = 6
        self.assertEqual(self.teacher.charge_potential(self.state, self.p, '0,0'), 0)

    def test_ship_funding_targets_and_numeric_exploration_ids(self):
        self.p['resources'].update(qic=5, ore=2, credits=15)
        self.state['board']['hexes']['2,0']['planet']['planet_type'] = 'Volcanic'
        xenos = self.teacher.ship_value(self.state, self.p, 'Rebellion', ['4,0'])
        self.assertGreater(xenos, 0)
        self.p['explored_ships'] = [1]
        self.assertEqual(self.teacher.ship_value(self.state, self.p, 'Rebellion', ['4,0']), 0)
        self.p['explored_ships'] = []
        funded = self.teacher.ship_value(self.state, self.p, 'TFMars', ['4,0'])
        self.assertGreater(funded, 0)
        self.p['resources']['credits'] = 0
        self.assertEqual(self.teacher.ship_value(self.state, self.p, 'TFMars', ['4,0']), 0)

    def test_cost_penalty_is_conditional_not_an_action_ban(self):
        a = dict(type='Upgrade', coord='0,0', to='TradingStation')
        expensive = self.teacher.score(self.s, a)[0]
        self.state['board']['hexes']['2,0']['structures'] = [{'owner': 2, 'kind': 'Mine'}]
        self.assertGreater(self.teacher.score(self.s, a)[0], expensive)
        self.assertGreater(expensive, 0)

    def test_native_placement_is_deterministic_legal_and_nonmutating(self):
        s, _ = fixture()
        # Advance original actor's native placement to the actual Xenos decision.
        env = Environment('strategy-19-heldout-192')
        env.step(0, 0)
        s = json.loads(env.snapshot_json())
        before = copy.deepcopy(s)
        first = self.teacher.choose(s)
        self.assertEqual(first, self.teacher.choose(s))
        self.assertEqual(s, before)
        self.assertEqual(first[0], s['decision_id'])
        self.assertLess(first[1], len(s['candidates']))


if __name__ == '__main__':
    unittest.main()

class ObservedDebitTests(unittest.TestCase):
    def test_tf_mars_underpayment_is_reported_not_treated_as_discount(self):
        from economy.evaluate import inspect_decision
        snapshot, player = fixture()
        state = snapshot['state']
        line_board(state)
        player['resources'].update(credits=4, ore=2)
        after = copy.deepcopy(state)
        after['players'][1]['resources'].update(credits=0, ore=1)
        row = inspect_decision(state, after, 1, {'type': 'SpaceshipCreditTerraform', 'coord': '1,0'})
        self.assertEqual(row['cost']['credits'], 5)
        self.assertEqual(row['engine_cost_anomaly']['paid_credits'], 4)
