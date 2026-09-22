"""The approved Brainstone exception must not excuse other free-action gains."""
import copy
import json
import unittest

from validate_bprime import (brainstone_burn_exception, compare, fixtures,
                             evaluation_successor_json)


class BrainstoneExceptionTests(unittest.TestCase):
    def setUp(self):
        _, self.before, self.actor = next(
            row for row in fixtures() if row[1]['players'][row[2]]['faction'] == 'Taklons')

    def successor(self, state, kind='BurnPower'):
        return json.loads(evaluation_successor_json(json.dumps(state), self.actor,
            json.dumps({'type': 'FreeAction', 'kind': kind, 'count': 1})))

    def test_native_normal_token_payment_and_stone_preservation_each_round(self):
        for round_number in (1, 3, 6):
            self.before['round'] = round_number
            after = self.successor(self.before)
            power = after['players'][self.actor]['resources']['power']
            old = self.before['players'][self.actor]['resources']['power']
            self.assertEqual(power['brainstone'], 'Area3')
            self.assertEqual(power['bowl2'], old['bowl2']-1)
            self.assertTrue(brainstone_burn_exception(self.before, after, self.actor, 'BurnPower'))
            for conserve in (True, False):
                row = compare(self.before, after, self.actor, 'BurnPower', 'isolated', conserve)
                self.assertTrue(row['passed'])
                self.assertEqual(row['status'], 'exception')
                self.assertAlmostEqual(row['delta'], 1/9)

    def test_normal_burns_and_other_factions_not_exempt(self):
        for faction in ('Xenos', 'HadschHallas', 'Terrans', 'Taklons'):
            before = copy.deepcopy(self.before)
            player = before['players'][self.actor]
            player['faction'] = faction
            player['resources']['power']['brainstone'] = 'Area3' if faction == 'Taklons' else None
            self.assertFalse(brainstone_burn_exception(before, self.successor(before), self.actor, 'BurnPower'))

    def test_missing_payment_destroyed_stone_or_extra_gain_not_exempt(self):
        after = self.successor(self.before)
        for field, value in (('bowl2', 4), ('brainstone', None), ('brainstone', 'Area1')):
            invalid = copy.deepcopy(after)
            invalid['players'][self.actor]['resources']['power'][field] = value
            self.assertFalse(brainstone_burn_exception(self.before, invalid, self.actor, 'BurnPower'))
        after['players'][self.actor]['resources']['credits'] += 1
        self.assertFalse(brainstone_burn_exception(self.before, after, self.actor, 'BurnPower'))

    def test_power_to_resource_arbitrage_still_fails(self):
        after = self.successor(self.before, 'PowerToQic')
        row = compare(self.before, after, self.actor, 'PowerToQic', 'isolated', True)
        self.assertFalse(row['passed'])
        self.assertEqual(row['status'], 'fail')
        self.assertIsNone(row['exception'])


if __name__ == '__main__':
    unittest.main()
