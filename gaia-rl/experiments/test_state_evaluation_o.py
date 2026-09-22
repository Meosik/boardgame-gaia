"""Federation satellite tokens pay stock value once, not a second shortage penalty."""
import copy
import unittest

from validate_bc import representative
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True)


class FederationValueTests(unittest.TestCase):
    def test_satellites_count_only_for_structural_shortfall(self):
        state, actor = representative(3)
        player = state['players'][actor]
        player['resources']['power'].update(bowl1=0, bowl2=0, bowl3=0,
                                             gaia_forming=0, gaia_bowl=0,
                                             brainstone=None)
        coords = list(state['board']['hexes'])[:3]
        for coord in coords:
            state['board']['hexes'][coord].setdefault('satellites', []).append(actor)
        before = copy.deepcopy(state)
        old = model.evaluate_state(state, actor, **OPTIONS)
        enabled = model.evaluate_state(state, actor, federation_satellite_tokens=True, **OPTIONS)
        multiplier = model.ROUND_MULTIPLIERS[state['round']]
        target = model.base.base.faction_modifier(state, player).token_target
        expected = -model.base.base.TOKEN_SHORTFALL_VP * max(0, target-len(coords)) * multiplier
        self.assertAlmostEqual(enabled.breakdown['token_shortfall'], expected)
        for key in enabled.breakdown.keys() - {'token_shortfall'}:
            self.assertAlmostEqual(enabled.breakdown[key], old.breakdown[key])
        self.assertEqual(state, before)

    def test_disabled_flag_is_identical(self):
        state, actor = representative(5)
        self.assertEqual(model.evaluate_state(state, actor, **OPTIONS),
                         model.evaluate_state(state, actor,
                                              federation_satellite_tokens=False, **OPTIONS))


if __name__ == '__main__':
    unittest.main()
