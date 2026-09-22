"""Opt-in income, Gaia-return, and bounded-option regression checks."""
import copy
import unittest

from validate_bc import representative
import state_evaluation_bef as model


BASE = dict(token_shortfall=True, remaining_income=True, distributed_research=True,
            round_resource_prices=True, discounted_expansion=True)


class GhiEvaluationTests(unittest.TestCase):
    def test_g_counts_held_booster_once_and_leaves_disabled_model_unchanged(self):
        for round_number in (1, 3, 5, 6):
            state, actor = representative(round_number)
            state['players'][actor]['booster'] = 3
            before = copy.deepcopy(state)
            old = model.evaluate_state(state, actor, **BASE)
            enabled = model.evaluate_state(state, actor, booster_one_income=True, **BASE)
            one_booster = model._booster_income_vp(state['players'][actor])
            expected = -max(0, 5-round_number) * model.base.base.REMAINING_INCOME_DISCOUNT * one_booster
            self.assertAlmostEqual(enabled.breakdown['future_income']-old.breakdown['future_income'], expected)
            self.assertEqual(state, before)

    def test_h_counts_forming_tokens_and_prices_their_return_bowl(self):
        for faction, expected_return in (('Terrans', 0.6), ('Xenos', 0.0)):
            state, actor = representative(1)
            player = state['players'][actor]
            player['faction'] = faction
            power = player['resources']['power']
            power.update(bowl1=6, bowl2=2, bowl3=0, gaia_forming=0, gaia_bowl=0,
                         brainstone=None)
            held = model.evaluate_state(state, actor, gaia_token_return=True, **BASE)
            for area in ('gaia_forming', 'gaia_bowl'):
                forming = copy.deepcopy(state)
                forming_power = forming['players'][actor]['resources']['power']
                forming_power['bowl1'] = 0
                forming_power[area] = 6
                sent = model.evaluate_state(forming, actor, gaia_token_return=True, **BASE)
                self.assertEqual(held.breakdown['token_shortfall'], sent.breakdown['token_shortfall'])
                self.assertAlmostEqual(sent.breakdown['power_stock']-held.breakdown['power_stock'],
                                       6 * expected_return * model.GAIA_TOKEN_RETURN_DISCOUNT)
                # Keeping the flag off reproduces the recorded shortage treatment.
                without = model.evaluate_state(forming, actor, **BASE)
                self.assertLess(without.breakdown['token_shortfall'], held.breakdown['token_shortfall'])

    def test_i_shortlist_keeps_a_native_paid_route(self):
        state, actor = representative(1)
        state['players'][actor]['booster'] = None
        options = dict(BASE, booster_one_income=True, gaia_token_return=True,
                       fast_expansion=True)
        result = model.evaluate_state(state, actor, **options)
        self.assertAlmostEqual(result.total_vp, sum(result.breakdown.values()))
        self.assertGreaterEqual(result.breakdown['expansion_opportunity'], 0)
        self.assertEqual(state['players'][actor]['booster'], None)

    def test_i_prime_reuses_identical_state_without_changing_it(self):
        state, actor = representative(1)
        original = copy.deepcopy(state)
        model._i_prime_cache.clear()
        options = dict(BASE, booster_one_income=True, gaia_token_return=True,
                       cached_expansion=True)
        first = model.evaluate_state(state, actor, **options)
        size = len(model._i_prime_cache)
        second = model.evaluate_state(state, actor, **options)
        self.assertEqual(len(model._i_prime_cache), size)
        self.assertEqual(first, second)
        self.assertEqual(state, original)


if __name__ == '__main__':
    unittest.main()
