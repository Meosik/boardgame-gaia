"""Opt-in density bonus for expansion coordinates."""
import copy
import unittest

from validate_bc import representative
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True)


class DensityBonusTests(unittest.TestCase):
    def test_distance_weights_reduce_the_power_seven_deficit(self):
        facts = {'federation': {
            'buildings': [{'coord': '0,0', 'power': 4}],
            'mine_power': {'1,0': 1, '2,0': 1},
        }}
        self.assertEqual(model.base.base._density_bonus(facts, '1,0'), 1.0)
        self.assertEqual(model.base.base._density_bonus(facts, '2,0'), 0.5)

    def test_adjacent_mine_can_bridge_existing_components(self):
        facts = {'federation': {
            'buildings': [{'coord': '0,0', 'power': 3},
                          {'coord': '2,0', 'power': 2}],
            'mine_power': {'1,0': 1},
        }}
        self.assertEqual(model.base.base._density_bonus(facts, '1,0'), 3.0)

    def test_completed_power_target_has_no_bonus(self):
        facts = {'federation': {
            'buildings': [{'coord': '0,0', 'power': 7}],
            'mine_power': {'1,0': 1},
        }}
        self.assertEqual(model.base.base._density_bonus(facts, '1,0'), 0.0)

    def test_disabled_flag_is_identical_and_does_not_mutate_state(self):
        state, actor = representative(3)
        before = copy.deepcopy(state)
        disabled = model.evaluate_state(state, actor, **OPTIONS)
        explicit = model.evaluate_state(state, actor, density_bonus=False, **OPTIONS)
        self.assertEqual(disabled, explicit)
        self.assertEqual(state, before)

    def test_enabled_evaluation_uses_native_mine_power(self):
        state, actor = representative(3)
        disabled = model.evaluate_state(state, actor, **OPTIONS)
        enabled = model.evaluate_state(state, actor, density_bonus=True, **OPTIONS)
        self.assertEqual(enabled.breakdown['density_bonus'], 1.0)
        self.assertAlmostEqual(enabled.total_vp-disabled.total_vp, 1.0)


if __name__ == '__main__':
    unittest.main()
