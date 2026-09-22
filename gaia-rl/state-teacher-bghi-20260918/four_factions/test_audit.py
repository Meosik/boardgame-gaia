import copy
import json
import unittest

from current_actions.conservation import BLOCKED, PREFIX
from four_factions.audit import capture_decision
from four_factions.teacher import QuartetTeacher


def snapshot():
    return {'decision_id': 12, 'player': 0, 'state': {
        'round': 2, 'players': [{'faction': 'HadschHallas'}]},
        'candidates': [{'action': {'type': 'Pass', 'booster_id': 1}},
                       {'action': {'type': 'ResearchAdvance', 'track': 'Economy'}}]}


class DecisionAuditTests(unittest.TestCase):
    def test_native_candidate_limit_is_copied_without_inventing_missing_evidence(self):
        s = snapshot()
        self.assertIsNone(capture_decision(s, [(1, 'a'), (2, 'b')], [])['candidate_generation'])
        s['candidate_generation'] = {'federation_limit_hits': 1,
                                     'federation_limit_reasons': ['search work']}
        result = capture_decision(s, [(1, 'a'), (2, 'b')], [])
        result['candidate_generation']['federation_limit_reasons'].clear()
        self.assertEqual(s['candidate_generation']['federation_limit_reasons'], ['search work'])

    def test_preserves_alternatives_without_calling_forecasts_actual_results(self):
        s = snapshot()
        scores = [(2.0, 'pass'), (3.0, 'paid research')]
        plans = [{'selected': 'research', 'plans': [
            {'goal': 'research', 'first': 1, 'complete': True, 'value': 42,
             'goal_acquired': True, 'actions': [{'action': {'type': 'Build'}}]},
            {'goal': 'academy', 'first': 0, 'complete': False, 'value': None}]}]
        original = copy.deepcopy((s, scores, plans))
        result = capture_decision(s, scores, plans)
        self.assertEqual(result['selected_index'], 1)
        self.assertEqual(len(result['candidate_scores']), 2)
        self.assertEqual(result['forecast_audits'], plans)
        self.assertTrue(result['predictions_are_not_observed_outcomes'])
        self.assertIsNone(result['forecast_audits'][0]['plans'][1]['value'])
        json.dumps(result, allow_nan=False)
        result['forecast_audits'][0]['plans'][0]['actions'].clear()
        self.assertEqual((s, scores, plans), original)

    def test_eligibility_and_ties_match_existing_teacher_choice(self):
        s = snapshot()
        scores = [(100, PREFIX+'blocked'), (1, 'eligible')]
        result = capture_decision(s, scores, [])
        self.assertEqual(result['selected_index'], 1)
        self.assertFalse(result['candidate_scores'][0]['eligible'])
        self.assertEqual(capture_decision(s, [(2, 'a'), (2, 'b')], [])['selected_index'], 0)

    def test_bad_or_all_blocked_ranks_fail_instead_of_inventing_a_choice(self):
        for scores in ([(1, 'a')], [(float('nan'), 'a'), (1, 'b')],
                       [(BLOCKED, PREFIX+'a'), (BLOCKED, PREFIX+'b')]):
            with self.assertRaises(ValueError):
                capture_decision(snapshot(), scores, [])

    def test_dispatch_captures_only_this_decisions_plans_without_changing_ranks(self):
        class Policy:
            def __init__(self):
                self.plan_history = [{'decision_id': 11, 'selected': 'old'}]

            def rank(self, s):
                self.plan_history.append({'decision_id': s['decision_id'], 'selected': 'new'})
                return [(0, 'pass'), (1, 'research')]

        env = object()
        teacher = QuartetTeacher().bind(env)
        teacher.policies[0] = Policy()
        s = snapshot()
        self.assertEqual(teacher.choose(s), (12, 1))
        self.assertEqual(teacher.last_scores, [(0, 'pass'), (1, 'research')])
        self.assertEqual(teacher.last_audit['forecast_audits'],
                         [{'decision_id': 12, 'selected': 'new'}])
        teacher.bind(object())
        self.assertIsNone(teacher.last_audit)


if __name__ == '__main__':
    unittest.main()
