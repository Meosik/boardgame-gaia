import copy
import math
import unittest

from research_context import test_teacher as research_tests
from strategy_teacher import TRACK_KEYS
from research_context.teacher import ContextResearchTeacher, advance, gaia_opportunity
from source_routes.teacher import SourceRouteTeacher
from source_routes.planning import asteroid_opportunity, best_route, immediate_funding, rebellion_funding


class SourceRouteTests(unittest.TestCase):
    def setUp(self):
        research_tests.ResearchContextTests.setUp(self)
        self.teacher = SourceRouteTeacher()
        self.p['tech_tiles'] = [7]
        self.p['resources'].update(knowledge=8)
        self.s['candidates'] = []

    def route(self):
        return best_route(self.state, self.p, self.teacher.standard_retained_value)

    def asteroid(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Asteroid'

    def test_gaia_unlocks_asteroid_without_power_ore_or_credits(self):
        self.asteroid()
        self.p['resources'].update(ore=0, credits=0)
        self.p['resources']['power'].update(bowl1=0, bowl2=0, bowl3=0)
        after = advance(self.p, 'GaiaProject')
        self.assertEqual(gaia_opportunity(self.state, after), 0)
        self.assertGreater(asteroid_opportunity(self.state, after), 0)
        self.assertGreater(self.teacher.research(self.state, self.p, 'GaiaProject'),
                           ContextResearchTeacher().research(self.state, self.p, 'GaiaProject'))

    def test_asteroid_requires_former_range_and_mine_supply(self):
        self.asteroid()
        self.assertEqual(asteroid_opportunity(self.state, self.p), 0)
        self.p = advance(self.p, 'GaiaProject')
        self.p['gaiaformers_deployed'] = 1
        self.assertEqual(asteroid_opportunity(self.state, self.p), 0)
        self.p['gaiaformers_deployed'] = 0
        self.state['board']['hexes']['1,0']['planet']['owner'] = 2
        self.state['board']['hexes']['4,0']['planet']['planet_type'] = 'Asteroid'
        self.assertEqual(asteroid_opportunity(self.state, self.p), 0)
        self.p['resources']['qic'] = 2
        self.assertGreater(asteroid_opportunity(self.state, self.p), 0)
        self.p['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]*8
        self.assertEqual(asteroid_opportunity(self.state, self.p), 0)

    def test_round6_asteroid_still_possible_unlike_delayed_gaia(self):
        self.asteroid()
        self.state['round'] = 6
        self.assertGreater(asteroid_opportunity(self.state, advance(self.p, 'GaiaProject')), 0)

    def test_one_former_not_counted_as_two_promised_colonies(self):
        self.asteroid()
        self.state['board']['hexes']['2,0']['planet']['planet_type'] = 'Transdim'
        after = advance(self.p, 'GaiaProject')
        delta = self.teacher.research(self.state, self.p, 'GaiaProject') - ContextResearchTeacher().research(self.state, self.p, 'GaiaProject')
        self.assertAlmostEqual(delta, max(0, asteroid_opportunity(self.state, after)-gaia_opportunity(self.state, after)))

    def test_eclipse_no_former_needed_in_ship_value(self):
        self.asteroid()
        self.state['board']['spaceship_tiles']['Eclipse'] = '3,0'
        template = copy.deepcopy(self.state['spaceship_boards'][0])
        template.update(id='Eclipse', explorers=[None]*4)
        self.state['spaceship_boards'].append(template)
        self.p['resources']['qic'] = 1
        self.p['explored_ships'] = []
        self.p['exploration_shuttles_available'] = 1
        self.p['vp'] = 10
        self.assertEqual(self.p['gaiaformers_total'], 0)
        self.assertGreater(self.teacher.ship_value(self.state, self.p, 'Eclipse', ['0,0']), 0)
        self.p['resources']['credits'] = 0
        self.assertEqual(self.teacher.ship_value(self.state, self.p, 'Eclipse', ['0,0']), 0)

    def test_advanced_route_requires_shared_resource_budget(self):
        self.p['research_tracks']['science'] = 2
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        self.assertIsNotNone(self.route())
        self.p['resources'].update(ore=0, credits=0)
        self.assertIsNone(self.route())

    def test_advanced_route_requires_green_or_local_federation_path(self):
        self.p['research_tracks']['science'] = 2
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        self.assertIsNotNone(self.route())
        self.p['federation_tokens'] = []
        self.assertIsNone(self.route())
        self.p['structures'].append({'hex': '1,0', 'kind': 'PlanetaryInstitute'})
        self.p['resources']['power']['bowl1'] = 8
        self.assertIsNotNone(self.route())

    def test_advanced_route_bootstraps_cover_with_standard_acquisition(self):
        self.p['structures'][0]['kind'] = 'TradingStation'
        self.p['research_tracks']['science'] = 2
        self.p['tech_tiles'] = []
        self.p['resources'].update(ore=12, credits=20)
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        self.assertIsNotNone(self.route())
        self.state['research_board']['tech_tiles'] = []
        self.p['explored_ships'] = []
        self.assertIsNone(self.route())

    def test_route_abandons_taken_tile_and_discounts_ready_rival(self):
        self.p['research_tracks']['science'] = 2
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        before = self.route().utility
        rival = next(p for p in self.state['players'] if p['player_id'] != self.p['player_id'])
        rival['research_tracks']['science'] = 4
        rival['federation_tokens'] = [2]
        rival['tech_tiles'] = [7]
        rival['covered_tech_tiles'] = []
        self.assertLess(self.route().utility, before)
        self.state['research_board']['advanced_tech_tiles'][5] = None
        self.assertIsNone(self.route())

    def test_no_forced_science_route_when_materials_missing(self):
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        self.p['research_tracks']['science'] = 2
        self.p['resources'].update(ore=0, credits=0)
        self.assertIsNone(self.route())
        self.assertLess(self.teacher.research(self.state, self.p, 'Science'),
                        ContextResearchTeacher().research(self.state, self.p, 'Science'))

    def test_immediate_resource_only_extra_value_when_it_opens_action(self):
        self.p['resources'].update(ore=0, credits=2)
        self.assertEqual(immediate_funding(self.state, self.p, {'ore': 1}), 6)
        self.p['resources']['credits'] = 0
        self.assertEqual(immediate_funding(self.state, self.p, {'ore': 1}), 0)

    def test_immediate_technology_uses_post_upgrade_balances(self):
        self.p['resources'].update(ore=6, credits=6)
        choice = {'kind': 'Standard', 'tile': 4, 'advance_track': None}
        plain = ContextResearchTeacher()
        action = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}}
        self.teacher._candidate = action
        plain._candidate = action
        self.assertAlmostEqual(self.teacher.technology(self.state, self.p, choice),
                               plain.technology(self.state, self.p, choice))

    def test_qic_academy_bonus_only_with_real_rebellion_funding(self):
        self.p['resources']['qic'] = 2
        self.p['explored_ships'] = [1]
        self.assertTrue(rebellion_funding(self.state, self.p))
        a = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Qic'}, 'tech_tile_choice': None}
        funded = self.teacher.score(self.s, a)[0] - ContextResearchTeacher().score(self.s, a)[0]
        self.p['explored_ships'] = []
        unfunded = self.teacher.score(self.s, a)[0] - ContextResearchTeacher().score(self.s, a)[0]
        self.assertEqual(funded-unfunded, 10)

    def test_ship_points_follow_actual_count_not_round5_switch(self):
        a = {'type': 'TFMarsTechBonus'}
        before = self.teacher.score(self.s, a)[0]
        self.p['tech_tiles'].append(4)
        self.assertEqual(self.teacher.score(self.s, a)[0]-before, 2)
        self.state['round'] = 5
        self.assertEqual(self.teacher.score(self.s, a)[0]-before, 2)

    def test_ranking_is_deterministic_finite_and_does_not_mutate(self):
        self.asteroid()
        self.state['research_board']['advanced_tech_tiles'][5] = 21
        self.s['candidates'] = [{'action': {'type': 'ResearchAdvance', 'track': t}}
                                for t in TRACK_KEYS]
        before = copy.deepcopy(self.s)
        ranks = self.teacher.rank(self.s)
        self.assertEqual(ranks, self.teacher.rank(self.s))
        self.assertTrue(all(math.isfinite(v) for v, _ in ranks))
        self.assertEqual(before, self.s)


if __name__ == '__main__':
    unittest.main()
