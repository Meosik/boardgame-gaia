"""Regression checks for independently enabled Btripleprime state features."""
import copy
import ast
from pathlib import Path
import unittest

from validate_bdoubleprime import representative, successor, bdoubleprime
import state_evaluation_btripleprime as variant


class TokenShortfallTests(unittest.TestCase):
    def test_disabled_features_preserve_bdoubleprime_and_no_planet_value_is_enabled(self):
        for round_number in (1, 3, 6):
            state, actor = representative(round_number)
            baseline = bdoubleprime.evaluate_state(state, actor)
            result = variant.evaluate_state(state, actor)
            self.assertEqual(result.total_vp, baseline.total_vp)
            for key, value in baseline.breakdown.items():
                self.assertEqual(result.breakdown[key], value)
            self.assertEqual(result.breakdown['secured_planets'], 0)
            self.assertEqual(result.breakdown['token_shortfall'], 0)

    def test_shortfall_has_exact_target_and_never_rewards_surplus(self):
        state, actor = representative(1)
        power = state['players'][actor]['resources']['power']
        for faction, target in (('Xenos', 5), ('HadschHallas', 5), ('Terrans', 5), ('Taklons', 4)):
            state['players'][actor]['faction'] = faction
            for count in range(8):
                power.update(bowl1=count, bowl2=0, bowl3=0, brainstone=None)
                result = variant.evaluate_state(state, actor, token_shortfall=True)
                self.assertAlmostEqual(result.breakdown['token_shortfall'], -2.13*max(0, target-count))
                self.assertEqual(result.breakdown['secured_planets'], 0)

    def test_stone_counts_once_only_in_active_bowls_and_gaia_tokens_do_not_count(self):
        state, actor = representative(1)
        state['players'][actor]['faction'] = 'Taklons'
        power = state['players'][actor]['resources']['power']
        power.update(bowl1=1, bowl2=1, bowl3=1, gaia_forming=9)
        for location in ('Area1', 'Area2', 'Area3', 'Gaia'):
            power['brainstone'] = location
            result = variant.evaluate_state(state, actor, token_shortfall=True)
            self.assertAlmostEqual(result.breakdown['token_shortfall'], -2.13 if location == 'Gaia' else 0)

    def test_low_token_burn_pays_shortfall_without_erasing_brainstone(self):
        for round_number in (1, 3, 6):
            for count in (2, 3, 4):
                for faction in ('Xenos', 'Taklons'):
                    state, actor = representative(round_number)
                    player = state['players'][actor]
                    player['faction'] = faction
                    stone = faction == 'Taklons'
                    player['resources']['power'].update(
                        bowl1=count-2, bowl2=1 if stone else 2, bowl3=0,
                        brainstone='Area2' if stone else None)
                    after = successor(state, actor, {'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1})
                    before_value = variant.evaluate_state(state, actor, token_shortfall=True)
                    after_value = variant.evaluate_state(after, actor, token_shortfall=True)
                    self.assertLess(after_value.total_vp, before_value.total_vp)
                    if stone:
                        self.assertEqual(after['players'][actor]['resources']['power']['brainstone'], 'Area3')

    def test_native_mine_slot_three_still_has_zero_income_increment(self):
        state, actor = representative(1)
        for coord in ('1,0', '0,1'):
            state['board']['hexes'][coord]['planet']['planet_type'] = 'Desert'
        income = []
        for coord in (None, '1,0', '0,1'):
            if coord is not None:
                state['phase'] = {'ActionPhase': {'active_player': actor}}
                state = successor(state, actor, {'type': 'Build', 'coord': coord})
            income.append(variant.engine_facts(state, state['players'][actor])['income']['ore'])
        self.assertEqual(income, [2, 3, 3])

    def test_evaluation_does_not_mutate_state_and_terminal_score_stays_native(self):
        state, actor = representative(1)
        old = copy.deepcopy(state)
        result = variant.evaluate_state(state, actor, token_shortfall=True)
        self.assertEqual(state, old)
        self.assertAlmostEqual(result.total_vp, sum(result.breakdown.values()))
        state['phase'] = {'Ended': {'final_scores': [[i, 100+i] for i in range(4)]}}
        self.assertEqual(variant.evaluate_state(state, actor, token_shortfall=True).total_vp, 100+actor)


class RemainingIncomeTests(unittest.TestCase):
    def test_remaining_phases_discount_and_resource_price(self):
        for r, phases in ((1, 5), (3, 3), (6, 0)):
            value = variant.future_income_value({'round': r}, {'ore': 1},
                remaining_income=True, active_tokens=5)
            self.assertAlmostEqual(value, 2.67*phases*.7)

    def test_native_mine_slot_increments_use_new_horizon(self):
        for r, phases in ((1, 5), (3, 3), (6, 0)):
            state, actor = representative(r)
            for coord in ('1,0', '0,1'):
                state['board']['hexes'][coord]['planet']['planet_type'] = 'Desert'
            values = []
            for coord in (None, '1,0', '0,1'):
                if coord:
                    state['phase'] = {'ActionPhase': {'active_player': actor}}
                    state = successor(state, actor, {'type': 'Build', 'coord': coord})
                values.append(variant.evaluate_state(state, actor, remaining_income=True).breakdown['future_income'])
            self.assertAlmostEqual(values[1]-values[0], 2.67*phases*.7)
            self.assertAlmostEqual(values[2]-values[1], 0)

    def test_charge_income_is_linear_without_token_count_cap(self):
        for r, phases in ((1, 5), (3, 3), (6, 0)):
            for count in (None, 0, 3, 7):
                before = variant.future_income_value({'round': r}, {'power_charge': 4},
                    remaining_income=True, active_tokens=count)
                after = variant.future_income_value({'round': r}, {'power_charge': 8},
                    remaining_income=True, active_tokens=count)
                self.assertAlmostEqual(after-before, 4*.6*phases*.7)
            full = variant.future_income_value({'round': r}, {'power_charge': 6},
                remaining_income=True, active_tokens=3)
            overflow = variant.future_income_value({'round': r}, {'power_charge': 99},
                remaining_income=True, active_tokens=3)
            self.assertAlmostEqual(overflow-full, 93*.6*phases*.7)

    def test_charge_income_ignores_positions_and_stone_multiplier(self):
        for bowls, stone in (((3, 0, 0), None), ((0, 0, 3), None), ((0, 0, 2), 'Area3')):
            power = dict(zip(('bowl1', 'bowl2', 'bowl3'), bowls))
            power.update(brainstone=stone)
            count = variant.active_token_count(power)
            self.assertEqual(count, 3)
            self.assertAlmostEqual(variant.future_income_value({'round': 1}, {'power_charge': 8},
                remaining_income=True, active_tokens=count), 8*.6*5*.7)

    def test_ore_to_token_changes_only_stock_and_shortfall(self):
        from validate_bc import cap_state
        for r in (1, 3, 6):
            for count, expected in ((3, -.54), (7, -2.67)):
                state, actor = cap_state(r, count, stress=True)
                after = successor(state, actor, {'type': 'FreeAction', 'kind': 'OreToPower', 'count': 1})
                before_value = variant.evaluate_state(state, actor, remaining_income=True, token_shortfall=True)
                after_value = variant.evaluate_state(after, actor, remaining_income=True, token_shortfall=True)
                self.assertAlmostEqual(after_value.total_vp-before_value.total_vp, expected)
                self.assertEqual(before_value.breakdown['future_income'], after_value.breakdown['future_income'])

    def test_actual_four_charge_tile_is_not_automatic_income(self):
        state, actor = representative(1)
        facts = variant.engine_facts(state, state['players'][actor])
        tile = next(t for t in facts['tiles'] if t['id'] == 10 and not t['advanced'])
        self.assertEqual(tile['income']['power_charge'], 0)
        self.assertEqual(tile['action']['power_charge'], 4)
        before = variant.evaluate_state(state, actor, remaining_income=True)
        state['players'][actor]['tech_tiles'] = [10]
        after = variant.evaluate_state(state, actor, remaining_income=True)
        self.assertEqual(before.breakdown['future_income'], after.breakdown['future_income'])

    def test_controlled_income_plus_four_is_native_and_isolated(self):
        from validate_bc import cap_state
        for n in (3, 7):
            state, actor = cap_state(1, n)
            before = variant.engine_facts(state, state['players'][actor])['income']
            state['players'][actor]['booster'] = 4
            after = variant.engine_facts(state, state['players'][actor])['income']
            self.assertEqual((before['power_charge'], after['power_charge']), (4, 8))
            self.assertEqual({k: v for k, v in before.items() if k != 'power_charge'},
                             {k: v for k, v in after.items() if k != 'power_charge'})

    def test_unrelated_evaluation_functions_remain_identical(self):
        def functions(module):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(Path(module.__file__).read_text()).body
                    if isinstance(n, ast.FunctionDef)}
        original, changed = functions(bdoubleprime), functions(variant)
        allowed = {'faction_modifier', 'technology_values', 'future_income_value', 'ship_values', 'evaluate_state'}
        for name in original.keys()-allowed:
            self.assertEqual(original[name], changed[name], name)

    def test_tile_charge_income_has_no_token_count_cap(self):
        from validate_bc import cap_state
        state, actor = cap_state(1, 4, stress=True)
        result = variant.evaluate_state(state, actor, remaining_income=True)
        tile = next(t for t in result.tile_values if t['tile'] == 2 and not t['advanced'])
        # Tile2 adds ore1 and charge1 even when total income exceeds twice the token count.
        self.assertAlmostEqual(tile['breakdown']['income'], (2.67+.6)*5*.7)


if __name__ == '__main__':
    unittest.main()
