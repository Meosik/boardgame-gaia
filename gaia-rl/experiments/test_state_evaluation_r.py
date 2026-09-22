"""Reachable-planet value is opt-in, bounded, state-only, and directional."""
import copy
import json
import unittest

from gaia_rl._native import evaluation_successor_json
from test_state_evaluation import opportunity_fixture
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True, token_ore_price=True)


def successor(state: dict, actor: int, track: str) -> dict:
    action = {'type': 'ResearchAdvance', 'track': track}
    return json.loads(evaluation_successor_json(json.dumps(state), actor, json.dumps(action)))


class ReachablePlanetTests(unittest.TestCase):
    def setUp(self):
        model._reachable_planets.cache_clear()

    def test_top_k_weights_use_round_mine_value(self):
        state, actor = opportunity_fixture(target='Desert', distance=1, count=3)
        value, coords = model.reachable_planet_value(state, actor)
        self.assertEqual(len(coords), 3)
        self.assertAlmostEqual(value, model.N_SECURED_PLANET_VP[2] * (1.0+0.6+0.4))

    def test_navigation_beats_science_when_mines_are_out_of_reach(self):
        state, actor = opportunity_fixture(target='Desert', distance=2, count=3)
        player = state['players'][actor]
        player['research_tracks'].update(navigation=0, science=0, terraforming=0)
        player['resources'].update(qic=0, knowledge=4)
        self.assertLessEqual(len(model.reachable_planet_value(state, actor)[1]), 1)
        navigation = successor(state, actor, 'Navigation')
        science = successor(state, actor, 'Science')
        nav_value = model.evaluate_state(
            navigation, actor, reachable_planets=True, **OPTIONS).total_vp
        science_value = model.evaluate_state(
            science, actor, reachable_planets=True, **OPTIONS).total_vp
        self.assertGreater(nav_value, science_value)

    def test_flag_off_is_identical_and_inputs_are_immutable(self):
        state, actor = opportunity_fixture(target='Desert', distance=1, count=3)
        before = copy.deepcopy(state)
        old = model.evaluate_state(state, actor, **OPTIONS)
        self.assertEqual(old, model.evaluate_state(
            state, actor, reachable_planets=False, **OPTIONS))
        self.assertEqual(state, before)


if __name__ == '__main__':
    unittest.main()
