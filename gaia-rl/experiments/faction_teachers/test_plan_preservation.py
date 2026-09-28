"""Native saved-branch regressions, plus explicitly synthetic search comparisons."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

from gaia_rl import Environment
from current_actions.conservation import BLOCKED, PREFIX
from faction_teachers.guidance import comparison_variants, preserves_plan
from four_factions.preparation import (Policies, advance_goal, goal_from_dict,
                                      rollout, search, select_goal, viable, SearchExpired)


PRESERVE = 'faction-tech-preserve'


class PlanPreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent / 'fixtures' / 'ambas-plan-cancellation.json'
        cls.fixture = json.loads(path.read_text())['fixture']
        cls.env = Environment(cls.fixture['seed'], 2000)
        for index in cls.fixture['prefix']:
            snapshot = json.loads(cls.env.snapshot_json())
            cls.env.step(snapshot['decision_id'], index)
        cls.original = cls.env.snapshot_json()
        canonical = json.dumps(json.loads(cls.original), sort_keys=True, separators=(',', ':'))
        assert hashlib.sha256(canonical.encode()).hexdigest() == cls.fixture['snapshot_sha256']

    def setUp(self):
        self.snapshot = json.loads(self.original)
        self.goal = goal_from_dict(self.fixture['goal'])
        self.preserve = replace(self.goal, name='preserve-plan: ' + self.goal.name,
                                sources=(*self.goal.sources, PRESERVE))
        self.bad = self.fixture['destructive_index']
        self.wait = next(i for i, c in enumerate(self.snapshot['candidates'])
                         if c['action']['type'] == 'Pass')
        # Isolate the recorded destructive fallback versus a real legal Pass.
        # These fixture ranks are not strength measurements.
        self.scores = [(BLOCKED, PREFIX + 'fixture restriction')
                       for _ in self.snapshot['candidates']]
        self.scores[self.bad] = (100, 'fixture preferred ordinary federation')
        self.scores[self.wait] = (0, 'fixture wait')
        self.policies = Policies(shared_factions=True, faction_tech_plans=True)

    def tearDown(self):
        self.assertEqual(self.env.snapshot_json(), self.original)

    def select(self, goal, policies=None):
        return select_goal(self.env, self.snapshot, self.scores, goal,
                           policies or self.policies, time.monotonic() + 10)

    def test_existing_path_reproduces_the_recorded_cancellation(self):
        self.assertTrue(viable(self.snapshot, self.snapshot['player'], self.goal))
        self.assertEqual(self.select(self.goal), self.bad)
        action = self.snapshot['candidates'][self.bad]['action']
        self.assertEqual(action, self.fixture['destructive_action'])
        after = json.loads(self.env.fork(self.snapshot['decision_id'], self.bad).snapshot_json())
        remaining = advance_goal(after, self.snapshot['player'], self.goal, action, before=self.snapshot)
        self.assertFalse(viable(after, self.snapshot['player'], remaining))

    def test_preserved_path_does_not_federate_its_future_swap_mine(self):
        self.assertEqual(self.select(self.preserve), self.wait)
        self.assertEqual(self.scores[self.bad][0], 100)  # No global rank/legality mutation.

    def test_flag_off_keeps_ordinary_choice_even_with_saved_marker(self):
        off = Policies(shared_factions=True, faction_tech_plans=False)
        self.assertEqual(self.select(self.preserve, off), self.bad)

    def test_no_safe_policy_eligible_action_is_unknown_not_a_forced_pass(self):
        self.scores[self.wait] = (BLOCKED, PREFIX + 'fixture restriction')
        self.assertIsNone(self.select(self.preserve))

    def test_fixed_first_action_cannot_bypass_preservation(self):
        result = rollout(self.env, self.snapshot, self.bad, self.preserve,
                         self.policies, time.monotonic() + 10, limit=1)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['value'])
        self.assertEqual(result['actions'], [])
        self.assertIn('preserv', result['reason'])

    def test_preserved_goal_roundtrips_in_existing_memory_schema(self):
        restored = goal_from_dict(json.loads(json.dumps(asdict(self.preserve))))
        self.assertEqual(restored, self.preserve)

    def test_variants_retain_original_then_preserved_without_recursive_pairing(self):
        self.assertEqual(comparison_variants(self.goal), (self.goal, self.preserve))
        self.assertEqual(comparison_variants(self.preserve), (self.goal, self.preserve))
        unrelated = replace(self.goal, sources=('B06',))
        self.assertEqual(comparison_variants(unrelated), (unrelated,))
        paired = replace(self.preserve, name='tile-action-1-then-' + self.preserve.name, first=1)
        ordinary, preserved = comparison_variants(paired)
        self.assertNotIn('preserve-plan: ', ordinary.name)
        self.assertEqual(preserved.name.count('preserve-plan: '), 1)
        self.assertEqual((ordinary.first, preserved.first), (1, 1))

    def test_already_cancelled_plan_uses_existing_fallback(self):
        invalid = replace(self.preserve, payoff='cancelled')
        self.assertEqual(self.select(invalid), self.bad)

    def test_opponent_policy_failure_is_not_hidden_as_preservation_failure(self):
        # Structural control-flow fixture: not a simulated native opponent turn.
        after = json.loads(self.original)
        after['player'] = (after['player'] + 1) % 4
        env = Mock()
        env.fork.return_value.snapshot_json.return_value = json.dumps(after)
        with patch('four_factions.preparation.keeps_plan', return_value=True), \
                patch('four_factions.preparation.reached_horizon', return_value=False), \
                patch('four_factions.preparation.Policies.rank', return_value=[(BLOCKED, PREFIX)]):
            with self.assertRaisesRegex(ValueError, 'No eligible continuation'):
                rollout(env, self.snapshot, self.wait, self.preserve,
                        self.policies, time.monotonic() + 10, limit=1)

    def test_preservation_does_not_extend_deadline(self):
        with self.assertRaises(SearchExpired):
            select_goal(self.env, self.snapshot, self.scores, self.preserve,
                        self.policies, time.monotonic() - 1)

    def run_comparison(self, preserved_value, enabled=True):
        def forecast(env, snapshot, first, goal, policies, deadline, **kwargs):
            # Test search arbitration only, not the native quality of these values.
            value = preserved_value if preserves_plan(goal) else 10 if goal == self.goal else 0
            return dict(complete=value is not None, value=value, actions=[], goal_acquired=False,
                        remaining_goal=asdict(goal), end_round=snapshot['state']['round'] + 2)

        deadline = time.monotonic() + 10
        with patch('four_factions.preparation.Policies.rank', return_value=self.scores), \
                patch('four_factions.preparation.goals_for', return_value=[self.goal]), \
                patch('four_factions.preparation.scoring_pairs', return_value=[]), \
                patch('four_factions.preparation.rollout', side_effect=forecast):
            return search(self.env, self.snapshot, {}, lambda result: None,
                          soft_deadline=deadline, hard_deadline=deadline,
                          shared_factions=True, faction_tech_plans=enabled)

    def test_preserving_route_wins_only_when_its_comparable_value_is_higher(self):
        for value, expected in [(20, self.preserve), (10, self.goal), (5, self.goal), (None, self.goal)]:
            with self.subTest(value=value):
                result = self.run_comparison(value)
                self.assertEqual(result['selected'], expected.name)
                names = [p['goal'] for p in result['comparison_stages'][0]['plans']]
                self.assertEqual(names.index(self.preserve.name), names.index(self.goal.name) + 1)
                self.assertEqual(result['index'], self.wait if preserves_plan(expected) else self.bad)
                saved = goal_from_dict(result['memory']['_plans'][str(self.snapshot['player'])])
                self.assertEqual(saved, expected)

    def test_off_search_never_adds_a_preserving_comparison(self):
        result = self.run_comparison(1000, enabled=False)
        self.assertEqual(result['selected'], self.goal.name)
        self.assertFalse(any(preserves_plan(goal_from_dict(p['goal_spec'])) for p in result['plans']))


if __name__ == '__main__':
    unittest.main()
