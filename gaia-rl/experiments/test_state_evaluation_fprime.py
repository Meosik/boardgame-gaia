"""Explicit held-resource prices leave the power/penalty arm unchanged."""
import unittest

from validate_bc import representative
import state_evaluation_bef as model


OPTIONS = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
               round_resource_prices=True, booster_one_income=True, gaia_token_return=True,
               fixed_income_and_planets=True)


class DirectStockPricesTests(unittest.TestCase):
    def test_exact_round_prices(self):
        for round_number, unit in enumerate(model.F_PRIME_ORE_KNOWLEDGE[1:], 1):
            self.assertEqual(model.stock_prices(round_number, direct_stock_prices=True),
                             {'ore': unit, 'credits': unit * 0.3,
                              'knowledge': unit, 'qic': unit * 1.75})

    def test_flag_only_reprices_held_stocks_and_paid_options(self):
        state, actor = representative(5)
        old = model.evaluate_state(state, actor, **OPTIONS)
        changed = model.evaluate_state(state, actor, direct_stock_prices=True, **OPTIONS)
        self.assertEqual(old, model.evaluate_state(state, actor, **OPTIONS))
        self.assertEqual(changed.breakdown['power_stock'], old.breakdown['power_stock'])
        self.assertEqual(changed.breakdown['token_shortfall'], old.breakdown['token_shortfall'])
        resources = state['players'][actor]['resources']
        old_prices = model.stock_prices(5)
        new_prices = model.stock_prices(5, direct_stock_prices=True)
        for key in ('ore', 'credits', 'knowledge', 'qic'):
            self.assertAlmostEqual(changed.breakdown[key+'_stock']-old.breakdown[key+'_stock'],
                                   resources[key]*(new_prices[key]-old_prices[key]))


if __name__ == '__main__':
    unittest.main()
