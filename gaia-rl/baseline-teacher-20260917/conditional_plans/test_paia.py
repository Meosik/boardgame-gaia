import unittest

from conditional_plans import test_teacher as baseline
from conditional_plans.routes import Plan, acquired, plans_for, next_milestone


class PaiaRoutesTests(unittest.TestCase):
    setUp = baseline.ConditionalTests.setUp
    def test_both_factions_get_separate_core_three_federation_candidate(self):
        for faction in ('Xenos', 'HadschHallas'):
            self.p['faction'] = faction
            plans, _ = plans_for(self.s, [(1, ''), (2, '')])
            self.assertTrue(any(getattr(p, 'federation_goal', 0) == 3 for p in plans))

    def test_two_large_buildings_not_spent_together_in_separate_core_route(self):
        self.p['structures'] = [{'hex': '0,0', 'kind': {'Academy': 'Science'}},
                                {'hex': '2,0', 'kind': {'Academy': 'Qic'}}]
        action = {'type': 'FormFederation', 'hexes': ['0,0', '2,0'],
                  'satellite_hexes': [], 'token': {'kind': 1}}
        self.s['candidates'] = [{'action': {'type': 'Pass', 'booster_id': None}}, {'action': action}]
        predicate, _ = next_milestone(self.s, Plan('three', federation_goal=3))
        self.assertFalse(predicate(action))
        # This is a competing route, not a ban in the real menu.
        self.assertEqual(self.s['candidates'][1]['action'], action)

    def test_gaia_asteroid_goal_needs_both_paid_colonies(self):
        self.p['structures'].append({'hex': '1,0', 'kind': 'Mine'})
        plan = Plan('chain', gaia_coord='1,0', asteroid_coord='3,0', immediate_only=True)
        self.assertFalse(acquired(self.s, self.s['player'], plan))
        self.p['structures'].append({'hex': '3,0', 'kind': 'Mine'})
        self.assertTrue(acquired(self.s, self.s['player'], plan))

    def test_immediate_route_does_not_substitute_normal_gaia_or_gaia_two(self):
        self.p['research_tracks']['gaia'] = 1
        self.state['board']['hexes']['1,0']['planet'].update(planet_type='Transdim', owner=None)
        self.s['candidates'].append({'action': {'type': 'GaiaFormation', 'coord': '1,0'}})
        pred, _ = next_milestone(self.s, Plan('instant', gaia_coord='1,0', immediate_only=True))
        self.assertFalse(pred({'type': 'GaiaFormation', 'coord': '1,0'}))
        self.assertFalse(pred({'type': 'ResearchAdvance', 'track': 'GaiaProject'}))

    def test_gaia_goal_cannot_count_a_preexisting_asteroid_as_new_payoff(self):
        self.state['board']['hexes']['1,0']['planet'].update(planet_type='Asteroid', owner=self.s['player'])
        self.p['structures'].append({'hex': '1,0', 'kind': 'Mine'})
        plans, _ = plans_for(self.s, [(1, ''), (2, '')])
        self.assertFalse(any(getattr(p, 'asteroid_coord', None) == '1,0' for p in plans))


class PlanContinuationTests(unittest.TestCase):
    setUp = baseline.ConditionalTests.setUp

    def test_matched_control_replans_without_changing_routes_or_default(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher, PaiaReplanTeacher
        default = PaiaPlanTeacher().bind(object())
        control = PaiaReplanTeacher().bind(object())
        self.assertTrue(default.continue_goals)
        self.assertFalse(control.continue_goals)
        for teacher in (default, control):
            teacher.selected_plan = Plan('PI@0,0', institute='0,0')
            teacher.planning_round = self.state['round']
            teacher.planning_decision = 0
        scores = [(1, ''), (2, '')]
        self.assertEqual(default.plan_routes(self.s, scores), control.plan_routes(self.s, scores))
        self.assertIs(default.evaluate_plans.__func__, control.evaluate_plans.__func__)
        with patch.object(control, 'evaluate_plans', side_effect=RuntimeError('full comparison')):
            with self.assertRaisesRegex(RuntimeError, 'full comparison'):
                control.rank(self.s)

    def test_native_legal_next_milestone_continues_without_full_replanning(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        from research_plans.teacher import best_index
        teacher = PaiaPlanTeacher().bind(object())
        teacher.selected_plan = Plan('PI@0,0', institute='0,0')
        teacher.planning_round = self.state['round']
        teacher.planning_decision = 0
        with patch.object(teacher, 'evaluate_plans', side_effect=AssertionError('unnecessary full replan')):
            scores = teacher.rank(self.s)
        self.assertEqual(best_index(scores, range(len(scores))), 1)
        self.assertTrue(teacher.plan_history[-1]['continued'])

    def test_actual_income_or_completed_goal_replans_instead_of_fixed_opening(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        for complete in (False, True):
            teacher = PaiaPlanTeacher().bind(object())
            teacher.selected_plan = Plan('PI@0,0', institute='0,0')
            teacher.planning_round = self.state['round']-int(not complete)
            if complete:
                self.p['structures'][0]['kind'] = 'PlanetaryInstitute'
            with patch.object(teacher, 'evaluate_plans', side_effect=RuntimeError('replanned')):
                with self.assertRaisesRegex(RuntimeError, 'replanned'):
                    teacher.rank(self.s)

    def test_lost_planet_forces_a_new_comparison(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        teacher = PaiaPlanTeacher().bind(object())
        teacher.selected_plan = Plan('Gaia', gaia_coord='1,0')
        teacher.planning_round = self.state['round']
        self.state['board']['hexes']['1,0']['planet']['owner'] = (self.s['player']+1) % 4
        with patch.object(teacher, 'evaluate_plans', side_effect=RuntimeError('replanned')):
            with self.assertRaisesRegex(RuntimeError, 'replanned'):
                teacher.rank(self.s)

    def test_continuation_cannot_resurrect_forbidden_conversion(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        from current_actions.conservation import blocked
        teacher = PaiaPlanTeacher().bind(object())
        teacher.selected_plan = Plan('PI@0,0', institute='0,0')
        teacher.planning_round = self.state['round']
        teacher.planning_decision = 0
        self.s['candidates'].append({'action': {'type': 'FreeAction', 'kind': 'KnowledgeToCredit'}})
        with patch.object(teacher, 'evaluate_plans', side_effect=AssertionError('unnecessary full replan')):
            scores = teacher.rank(self.s)
        self.assertTrue(blocked(scores[-1]))

    def test_federation_first_index_is_never_reused_in_a_later_snapshot(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        for academy in (None, 'Qic'):
            teacher = PaiaPlanTeacher().bind(object())
            route = Plan('federation-first', first=1, academy=academy)
            with patch.object(teacher, 'plan_routes', return_value=([Plan('current-choice'), route], {})), \
                    patch.object(teacher, 'evaluate_plans', return_value=[
                        {'goal': 'current-choice', 'first': 0, 'value': 1, 'complete': True},
                        {'goal': route.name, 'first': 1, 'value': 2, 'complete': True}]):
                teacher.rank(self.s)
            if academy is None:
                self.assertIsNone(teacher.selected_plan)
            else:
                self.assertEqual(teacher.selected_plan.academy, academy)
                self.assertIsNone(teacher.selected_plan.first)


if __name__ == '__main__':
    unittest.main()
