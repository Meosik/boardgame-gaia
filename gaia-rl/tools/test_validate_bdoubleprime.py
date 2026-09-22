"""Scope, native action payments, and untouched Gaia values for Bdoubleprime."""
import copy
import unittest

from validate_bdoubleprime import (bprime, bdoubleprime, action_cases, representative,
                                   source_check, successor, expected_sign)


class PowerPriceVariantTests(unittest.TestCase):
    def power(self, **changes):
        return {'bowl1': 0, 'bowl2': 0, 'bowl3': 0, 'brainstone': None,
                'gaia_forming': 0, **changes}

    def test_only_power_function_changed(self):
        source_check()
        self.assertEqual(bdoubleprime.PRICES,
                         {'credits': .8, 'ore': 2.67, 'knowledge': 2.67, 'qic': 4.67})

    def test_exact_normal_and_brainstone_prices(self):
        for bowl, price in (('bowl1', 0), ('bowl2', .6), ('bowl3', 1.2)):
            self.assertAlmostEqual(bdoubleprime.power_value(self.power(**{bowl: 1}), 'Area1'), price)
        for bowl, price in (('Area1', 0), ('Area2', 1.8), ('Area3', 3.6)):
            self.assertAlmostEqual(bdoubleprime.power_value(self.power(brainstone=bowl), 'Area1'), price)

    def test_gaia_normal_and_brainstone_valuations_unchanged(self):
        for tokens in (0, 1, 8):
            for stone in (None, 'Gaia'):
                for destination in (None, 'Area1', 'Area2', 'Area3'):
                    for future in (False, True):
                        power = self.power(gaia_forming=tokens, brainstone=stone)
                        self.assertEqual(bprime.power_value(power, destination, future=future),
                                         bdoubleprime.power_value(power, destination, future=future))

    def test_token_income_coefficient_is_not_changed(self):
        income = {'power_charge': 0, 'power_tokens': 1}
        self.assertEqual(bprime.income_vp(income), 1/3)
        self.assertEqual(bdoubleprime.income_vp(income), 1/3)

    def test_all_representative_native_actions_are_legal_and_leave_input_unchanged(self):
        count = 0
        for category, label, expected, before, actor, action in action_cases():
            old = copy.deepcopy(before)
            after = successor(before, actor, action)
            self.assertEqual(old, before)
            self.assertEqual(after['round'], before['round'])
            player = after['players'][actor]
            if category == '리치':
                amount = before['phase']['ChargePowerPending']['queue'][0]['max_power']
                self.assertEqual(before['players'][actor]['vp']-player['vp'], amount-1)
                self.assertEqual(player['resources']['power']['bowl1'], 4-amount)
            if action['type'] == 'PowerAction':
                self.assertIn(action['id'], after['used_power_actions'])
                if action['coord'] is not None:
                    self.assertTrue(any(s['hex'] == action['coord'] and s['kind'] == 'Mine'
                                        for s in player['structures']))
                    self.assertLess(player['resources']['ore'], before['players'][actor]['resources']['ore'])
                    self.assertEqual(player['resources']['credits'], before['players'][actor]['resources']['credits']-2)
            count += 1
        self.assertEqual(count, 45)

    def test_normal_burn_is_zero_but_stone_exception_can_gain(self):
        state, actor = representative(1)
        action = {'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1}
        after = successor(state, actor, action)
        self.assertAlmostEqual(bdoubleprime.power_value(after['players'][actor]['resources']['power'], None),
                               bdoubleprime.power_value(state['players'][actor]['resources']['power'], None))
        state['players'][actor]['faction'] = 'Taklons'
        state['players'][actor]['resources']['power']['brainstone'] = 'Area2'
        after = successor(state, actor, action)
        delta = (bdoubleprime.power_value(after['players'][actor]['resources']['power'], None)
                 -bdoubleprime.power_value(state['players'][actor]['resources']['power'], None))
        self.assertAlmostEqual(delta, 1.2)

    def test_expected_signs_do_not_treat_zero_as_strictly_positive_or_negative(self):
        self.assertFalse(expected_sign(0, 'negative'))
        self.assertFalse(expected_sign(0, 'positive'))
        self.assertTrue(expected_sign(0, 'nonpositive'))
        self.assertIsNone(expected_sign(-5, None))


if __name__ == '__main__':
    unittest.main()
