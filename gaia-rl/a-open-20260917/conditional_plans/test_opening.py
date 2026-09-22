import copy
import unittest
from unittest.mock import patch

from conditional_plans.opening import OpeningPlanTeacher, compare_openings, opening_summary
from conditional_plans.teacher import PaiaReplanTeacher
from conditional_plans.test_native import replay_root
from research_plans.teacher import best_index


class OpeningSelectionTests(unittest.TestCase):
    def setUp(self):
        self.env, self.snapshot = replay_root(4)
        self.original = self.env.snapshot_json()
        self.baseline = PaiaReplanTeacher().bind(self.env).rank(self.snapshot)
        self.control = best_index(self.baseline, range(len(self.baseline)))

    def report(self, values):
        return {'plans': [{'goal': f'opening-{i}', 'first': i, 'complete': value is not None,
                           'value': value, 'actions': []} for i, value in enumerate(values)],
                'shared_prefixes': {}}

    def rank_with(self, values):
        policy = OpeningPlanTeacher().bind(self.env)
        with patch('conditional_plans.opening.compare_openings', return_value=self.report(values)) as probe:
            scores = policy.rank(self.snapshot)
        probe.assert_called_once()
        self.assertEqual(self.original, self.env.snapshot_json())
        return policy, scores

    def test_future_value_can_select_a_low_ranked_site_without_changing_other_scores(self):
        values = [20.0] * len(self.baseline)
        winner = min(range(len(values)), key=lambda i: self.baseline[i][0])
        values[winner] = 30.0
        policy, scores = self.rank_with(values)
        self.assertEqual(best_index(scores, range(len(scores))), winner)
        self.assertEqual(policy.plan_history[-1]['selected_first'], winner)
        for i in range(len(scores)):
            if i != winner:
                self.assertEqual(scores[i], self.baseline[i])

    def test_tied_future_values_preserve_the_existing_placement_preference(self):
        _, scores = self.rank_with([20.0] * len(self.baseline))
        self.assertEqual(best_index(scores, range(len(scores))), self.control)

    def test_incomplete_control_does_not_promote_an_unfairly_comparable_alternative(self):
        values = [30.0] * len(self.baseline)
        values[self.control] = None
        policy, scores = self.rank_with(values)
        self.assertEqual(scores, self.baseline)
        self.assertIn('fallback', policy.plan_history[-1])

    def test_incomplete_alternative_has_no_numeric_value_or_claim_of_inferiority(self):
        values = [20.0] * len(self.baseline)
        unknown = next(i for i in range(len(values)) if i != self.control)
        values[unknown] = None
        policy, _ = self.rank_with(values)
        self.assertIsNone(policy.plan_history[-1]['plans'][unknown]['value'])

    def test_non_placement_decision_uses_the_unchanged_parent_policy(self):
        policy = OpeningPlanTeacher().bind(self.env)
        snapshot = {**self.snapshot, 'candidates': [{'action': {'type': 'SelectStartingBooster', 'booster_id': 8}}]}
        expected = [(7.1, 'unchanged parent')]
        with patch.object(PaiaReplanTeacher, 'rank', return_value=expected), \
                patch('conditional_plans.opening.compare_openings', side_effect=AssertionError('not placement')):
            self.assertEqual(policy.rank(snapshot), expected)


class OpeningSummaryTests(unittest.TestCase):
    def test_new_colonies_and_remaining_mines_are_distinct_from_upgrades(self):
        _, root = replay_root(4)
        start = copy.deepcopy(root['state'])
        actor = 2
        start['round'] = 1
        start['players'][actor]['structures'] = [{'hex': '-4,-1', 'kind': 'Mine'},
                                               {'hex': '-10,6', 'kind': 'Mine'}]
        end = copy.deepcopy(start)
        end['players'][actor]['structures'] = [{'hex': '-4,-1', 'kind': 'ResearchLab'},
                                             {'hex': '-10,6', 'kind': 'TradingStation'},
                                             {'hex': '-11,4', 'kind': 'Mine'}]
        final = copy.deepcopy(end)
        final['round'] = 2
        summary = opening_summary(final, actor, [{'state': start}, {'state': end}, {'state': final}])
        self.assertEqual(summary['round1_new_colonies'], 1)
        self.assertEqual(summary['round1_mines'], 1)
        self.assertEqual(summary['round1_buildings'], 3)


class OpeningNativeTests(unittest.TestCase):
    def test_complete_opening_matches_independent_native_forecast_and_exposes_actual_income(self):
        from conditional_plans.routes import Plan, acquired
        from current_actions.teacher import CurrentContextTeacher
        from research_plans.teacher import forecast
        from scoring_cache import ranking_scope
        env, snapshot = replay_root(4)
        original = env.snapshot_json()
        report = compare_openings(env, snapshot)
        baseline = PaiaReplanTeacher().bind(env).rank(snapshot)
        first = best_index(baseline, range(len(baseline)))
        actual = next(p for p in report['plans'] if p['first'] == first)
        with ranking_scope():
            expected = forecast(env, snapshot, first, Plan('current-choice'), CurrentContextTeacher(),
                                selector=lambda e, s, scores, goal, done: best_index(scores, range(len(scores))),
                                achieved=acquired)
        self.assertEqual({k: actual[k] for k in expected}, expected)
        self.assertTrue(all(p['complete'] for p in report['plans']))
        for plan in report['plans']:
            summary = plan['diagnostics']
            self.assertEqual(summary['round1_buildings'], len(summary['round1_structures']))
            self.assertEqual(summary['round1_mines'],
                             sum(s['kind'] == 'Mine' for s in summary['round1_structures']))
            self.assertEqual([i['round'] for i in plan['incomes']], [1, 2])
            self.assertTrue(all(i['ore'] >= 0 for i in plan['incomes']))
        self.assertEqual(original, env.snapshot_json())

    def test_every_legal_site_is_considered_and_capped_forecasts_stay_unknown(self):
        env, snapshot = replay_root(4)
        original = env.snapshot_json()
        report = compare_openings(env, snapshot, limit=1)
        self.assertEqual({p['first'] for p in report['plans']}, set(range(len(snapshot['candidates']))))
        self.assertTrue(all(not p['complete'] and p['value'] is None for p in report['plans']))
        self.assertEqual(original, env.snapshot_json())

    def test_existing_modes_remain_unchanged_and_new_mode_is_explicit(self):
        from conditional_plans.evaluate import PLANNING_MODES
        from conditional_plans.teacher import PaiaPlanTeacher
        self.assertIs(PLANNING_MODES['goal-continuation'], PaiaPlanTeacher)
        self.assertIs(PLANNING_MODES['per-action'], PaiaReplanTeacher)
        self.assertIs(PLANNING_MODES['opening'], OpeningPlanTeacher)


if __name__ == '__main__':
    unittest.main()
