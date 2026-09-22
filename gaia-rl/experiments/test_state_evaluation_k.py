"""Opt-in pass timing uses a private native round transition."""
import gzip
import importlib.util
import json
import os
from pathlib import Path
import unittest

from gaia_rl._native import Environment, evaluation_pass_next_round_json, evaluation_successor_json
import state_evaluation_btripleprime as valuation
import state_evaluation_bef as current

BRIDGE_PATH = Path(__file__).resolve().parents[1] / 'state-teacher-bghi-20260918/state_evaluation_bridge.py'
BRIDGE_SPEC = importlib.util.spec_from_file_location('bghi_pass_timing_bridge', BRIDGE_PATH)
bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
BRIDGE_SPEC.loader.exec_module(bridge)


TRACE = Path(__file__).resolve().parents[1] / 'runs/bghi-lite-smoke-20260918/decisions.jsonl.gz'
SEED = 'state-evaluation-ab-20260917-1580'


class PassTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = Environment(SEED, 2000)
        cls.cases = {}
        with gzip.open(TRACE, 'rt') as stream:
            for line in stream:
                row = json.loads(line)
                snapshot = json.loads(env.snapshot_json())
                action = row['action']
                if action['type'] == 'Pass' and snapshot['state']['round'] in (1, 5, 6):
                    cls.cases.setdefault(snapshot['state']['round'], (snapshot, action))
                index = next(i for i, candidate in enumerate(snapshot['candidates'])
                             if candidate['action'] == action)
                env.step(snapshot['decision_id'], index)
        assert set(cls.cases) == {1, 5, 6}

    def test_next_round_receives_only_own_income_and_does_not_mutate_input(self):
        snapshot, action = self.cases[1]
        actor = snapshot['player']
        passed = json.loads(evaluation_successor_json(json.dumps(snapshot['state']), actor, json.dumps(action)))
        original = json.dumps(passed, sort_keys=True)
        projected = json.loads(evaluation_pass_next_round_json(json.dumps(passed), actor))
        self.assertEqual(json.dumps(passed, sort_keys=True), original)
        self.assertEqual(projected['round'], 2)
        self.assertFalse(projected['players'][actor]['passed'])
        for before, after in zip(passed['players'], projected['players']):
            if before['player_id'] != actor:
                self.assertEqual(after, before)
        self.assertNotEqual(projected['players'][actor]['resources'], passed['players'][actor]['resources'])
        income = {'ore': 1, 'credits': 0, 'knowledge': 0, 'qic': 0,
                  'power_charge': 0, 'power_tokens': 0, 'vp': 0}
        before_value = valuation.future_income_value(passed, income, remaining_income=True)
        after_value = valuation.future_income_value(projected, income, remaining_income=True)
        self.assertAlmostEqual(before_value - after_value,
                               valuation.income_vp(income) * valuation.REMAINING_INCOME_DISCOUNT)

    def test_final_round_projects_terminal_scoring_without_income(self):
        snapshot, action = self.cases[6]
        actor = snapshot['player']
        passed = json.loads(evaluation_successor_json(json.dumps(snapshot['state']), actor, json.dumps(action)))
        projected = json.loads(evaluation_pass_next_round_json(json.dumps(passed), actor))
        self.assertEqual(projected['round'], 6)
        self.assertIn('Ended', projected['phase'])
        for before, after in zip(passed['players'], projected['players']):
            self.assertEqual(after['resources'], before['resources'])

    def test_flag_changes_only_pass_scoring(self):
        snapshot, passed_action = self.cases[1]
        normal_action = next(candidate['action'] for candidate in snapshot['candidates']
                             if candidate['action']['type'] == 'Build')
        old = {key: os.environ.get(key) for key in
               ('GAIA_STATE_EVALUATION', 'GAIA_EXPANSION_MODE', 'GAIA_PASS_TIMING')}
        try:
            os.environ.update(GAIA_STATE_EVALUATION='1', GAIA_EXPANSION_MODE='lite')
            os.environ['GAIA_PASS_TIMING'] = '0'
            old_pass = bridge.score(snapshot, passed_action)[0]
            old_build = bridge.score(snapshot, normal_action)[0]
            os.environ['GAIA_PASS_TIMING'] = '1'
            self.assertNotEqual(bridge.score(snapshot, passed_action)[0], old_pass)
            self.assertEqual(bridge.score(snapshot, normal_action)[0], old_build)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_realized_income_decrements_only_future_horizon_and_preserves_r6(self):
        options = dict(token_shortfall=True, remaining_income=True,
                       distributed_research=True, round_resource_prices=True,
                       booster_one_income=True, gaia_token_return=True,
                       fixed_income_and_planets=True, direct_stock_prices=True,
                       federation_satellite_tokens=True, density_bonus=False,
                       token_ore_price=True, reachable_planets=False)
        for round_number in (1, 5):
            snapshot, action = self.cases[round_number]
            actor = snapshot['player']
            passed = json.loads(evaluation_successor_json(
                json.dumps(snapshot['state']), actor, json.dumps(action)))
            projected = json.loads(evaluation_pass_next_round_json(json.dumps(passed), actor))
            before = current.evaluate_state(projected, actor, **options)
            explicit_off = current.evaluate_state(
                projected, actor, pass_realized_income=False, **options)
            self.assertEqual(before.total_vp, explicit_off.total_vp)
            self.assertEqual(before.breakdown, explicit_off.breakdown)
            after = current.evaluate_state(
                projected, actor, pass_realized_income=True, **options)
            changes = {key for key in before.breakdown
                       if abs(before.breakdown[key] - after.breakdown[key]) > 1e-9}
            self.assertEqual(changes, {'future_income'})
            self.assertLess(after.breakdown['future_income'], before.breakdown['future_income'])

        keys = ('GAIA_STATE_EVALUATION', 'GAIA_EXPANSION_MODE', 'GAIA_PASS_TIMING',
                'GAIA_FIXED_INCOME_PLANETS', 'GAIA_DIRECT_STOCK_PRICES',
                'GAIA_FEDERATION_VALUE', 'GAIA_DENSITY_BONUS', 'GAIA_TOKEN_ORE_PRICE',
                'GAIA_REACHABLE_PLANETS', 'GAIA_PASS_REALIZED_INCOME')
        old = {key: os.environ.get(key) for key in keys}
        try:
            os.environ.update(
                GAIA_STATE_EVALUATION='1', GAIA_EXPANSION_MODE='lite',
                GAIA_PASS_TIMING='1', GAIA_FIXED_INCOME_PLANETS='1',
                GAIA_DIRECT_STOCK_PRICES='1', GAIA_FEDERATION_VALUE='1',
                GAIA_DENSITY_BONUS='0', GAIA_TOKEN_ORE_PRICE='1',
                GAIA_REACHABLE_PLANETS='0')
            snapshot, action = self.cases[1]
            build = next(candidate['action'] for candidate in snapshot['candidates']
                         if candidate['action']['type'] == 'Build')
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '0'
            control_pass = bridge.score(snapshot, action)[0]
            control_build = bridge.score(snapshot, build)[0]
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '1'
            self.assertLess(bridge.score(snapshot, action)[0], control_pass)
            self.assertEqual(bridge.score(snapshot, build)[0], control_build)

            snapshot, action = self.cases[5]
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '0'
            control_pass = bridge.score(snapshot, action)[0]
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '1'
            self.assertLess(bridge.score(snapshot, action)[0], control_pass)

            snapshot, action = self.cases[6]
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '0'
            control = bridge.score(snapshot, action)[0]
            os.environ['GAIA_PASS_REALIZED_INCOME'] = '1'
            self.assertEqual(bridge.score(snapshot, action)[0], control)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == '__main__':
    unittest.main()
