"""The opt-in token shortage price follows the current f-prime ore price."""
import copy
import unittest

from validate_bdoubleprime import representative
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True, direct_stock_prices=True,
               federation_satellite_tokens=True)


class TokenOrePriceTests(unittest.TestCase):
    def test_shortfall_uses_eighty_percent_of_fprime_ore_price(self):
        for round_number in range(1, 7):
            state, actor = representative(round_number)
            power = state['players'][actor]['resources']['power']
            power.update(bowl1=2, bowl2=0, bowl3=0, gaia_forming=0, gaia_bowl=0,
                         brainstone=None)
            result = model.evaluate_state(state, actor, token_ore_price=True, **OPTIONS)
            target = model.base.base.faction_modifier(
                state, state['players'][actor]).token_target
            expected = -(target-2) * model.F_PRIME_ORE_KNOWLEDGE[round_number] * 0.8
            self.assertAlmostEqual(result.breakdown['token_shortfall'], expected)
            flag_alone = model.evaluate_state(
                state, actor, token_shortfall=True, token_ore_price=True)
            self.assertAlmostEqual(flag_alone.breakdown['token_shortfall'], expected)

    def test_flag_off_preserves_existing_result(self):
        state, actor = representative(5)
        before = copy.deepcopy(state)
        old = model.evaluate_state(state, actor, **OPTIONS)
        self.assertEqual(old, model.evaluate_state(
            state, actor, token_ore_price=False, **OPTIONS))
        self.assertEqual(state, before)


if __name__ == '__main__':
    unittest.main()
