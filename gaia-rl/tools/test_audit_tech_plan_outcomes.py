import copy
import json
from pathlib import Path
import unittest

from audit_tech_plan_outcomes import summarize


FIXTURE = Path(__file__).parent / 'fixtures' / 'tech-plan-pilot-outcomes.json'


class TechPlanOutcomeTests(unittest.TestCase):
    def test_recorded_23_comparisons_separate_completion_from_success(self):
        fixture = json.loads(FIXTURE.read_text())
        original = copy.deepcopy(fixture)
        result = summarize(fixture['audit_rows'])
        self.assertEqual(result['Terrans']['evaluated_candidates'], 14)
        self.assertEqual(result['Ambas']['evaluated_candidates'], 9)
        for faction, count in [('Terrans', 14), ('Ambas', 9)]:
            self.assertEqual(result[faction]['completed_horizon_comparisons'], count)
            self.assertEqual(result[faction]['goal_acquired_in_forecast'], 0)
            self.assertEqual(result[faction]['selected_decisions'], 0)
        self.assertEqual(result['Terrans']['cancelled_evaluated_candidates'], 0)
        self.assertEqual(result['Ambas']['cancelled_evaluated_candidates'], 3)
        self.assertEqual(fixture, original)

    def test_three_recorded_cancellations_use_remaining_not_initial_goal(self):
        rows = json.loads(FIXTURE.read_text())['audit_rows']
        result = summarize(rows)['Ambas']['candidate_audit']
        self.assertEqual([row['step'] for row in result if row['cancelled']], [46, 46, 67])
        for row in rows:
            for plan in row['audit']['plans']:
                if plan['remaining_goal'].get('payoff') == 'cancelled':
                    self.assertIsNone(plan['goal_spec'].get('payoff'))

    def test_missing_end_state_is_unknown_not_success_or_cancellation(self):
        row = copy.deepcopy(json.loads(FIXTURE.read_text())['audit_rows'][0])
        plan = row['audit']['plans'][0]
        row['audit']['plans'] = [plan]
        plan.pop('remaining_goal')
        plan['complete'] = False
        plan.pop('goal_acquired')
        result = summarize([row])['Terrans']
        self.assertEqual(result['completed_horizon_comparisons'], 0)
        self.assertEqual(result['unknown_outcomes'], 1)
        self.assertIsNone(result['candidate_audit'][0]['cancelled'])
        self.assertIsNone(result['candidate_audit'][0]['goal_acquired_in_forecast'])

    def test_selected_bgg_wrapper_and_action_index_are_resolved(self):
        row = copy.deepcopy(json.loads(FIXTURE.read_text())['audit_rows'][0])
        plan = row['audit']['plans'][0]
        row['audit']['plans'] = [plan, copy.deepcopy(plan)]
        row['audit']['plans'][1]['first'] += 1
        row['audit']['selected'] = 'BGG-R1-example via ' + plan['goal']
        row['audit']['selected_index'] = plan['first']
        result = summarize([row])['Terrans']
        self.assertEqual(result['selected_decisions'], 1)
        self.assertEqual([p['selected'] for p in result['candidate_audit']], [True, False])

    def test_nonpilot_plans_are_not_counted(self):
        row = copy.deepcopy(json.loads(FIXTURE.read_text())['audit_rows'][0])
        for plan in row['audit']['plans']:
            plan['goal_spec']['sources'] = ['B04']
        self.assertEqual(summarize([row]), {})


if __name__ == '__main__':
    unittest.main()
