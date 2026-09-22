"""Round-independent income and secured-colony valuation are opt-in."""
import copy
import unittest

from validate_bc import representative
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True)


class FixedIncomeAndPlanetsTests(unittest.TestCase):
    def test_disabled_model_unchanged_and_enabled_income_horizon(self):
        for round_number in (1, 3, 5, 6):
            state, actor = representative(round_number)
            state['players'][actor]['booster'] = None
            before = copy.deepcopy(state)
            old = model.evaluate_state(state, actor, **OPTIONS)
            enabled = model.evaluate_state(state, actor, fixed_income_and_planets=True, **OPTIONS)
            player = state['players'][actor]
            facts = model.base.base.engine_facts(state, player)
            per_income = (model.base.base._payout_vp(facts['income'])
                          + facts['income'].get('power_charge', 0) * model.base.base.INCOME_CHARGE_VP
                          + facts['income'].get('power_tokens', 0) / 3)
            self.assertAlmostEqual(enabled.breakdown['future_income'],
                                   per_income * 3.5)
            self.assertAlmostEqual(enabled.breakdown['secured_planets'],
                len(model.base.base.secured_planet_coords(state, actor))
                * model.N_SECURED_PLANET_VP[round_number])
            self.assertEqual(old, model.evaluate_state(state, actor, **OPTIONS))
            self.assertEqual(state, before)

    def test_held_booster_is_counted_once(self):
        state, actor = representative(3)
        state['players'][actor]['booster'] = 3
        with_booster = model.evaluate_state(state, actor, fixed_income_and_planets=True, **OPTIONS)
        without = copy.deepcopy(state)
        without['players'][actor]['booster'] = None
        no_booster = model.evaluate_state(without, actor, fixed_income_and_planets=True, **OPTIONS)
        self.assertAlmostEqual(with_booster.breakdown['future_income'] - no_booster.breakdown['future_income'],
                               model._booster_income_vp(state['players'][actor]))


if __name__ == '__main__':
    unittest.main()
