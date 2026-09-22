import copy
import unittest
from unittest.mock import patch

from current_actions.teacher import CurrentActionTeacher
from integrated import test_teacher
from research_plans.teacher import best_index
from conditional_plans.teacher import HadschPlanTeacher, run_plan, select_plan
from conditional_plans.routes import Plan, acquired, plans_for, next_milestone


class ConditionalTests(unittest.TestCase):
    def setUp(self):
        test_teacher.IntegratedTests.setUp(self)
        self.p['faction'] = 'HadschHallas'
        self.p['structures'] = [{'hex': '0,0', 'kind': 'TradingStation'},
                                {'hex': '2,0', 'kind': 'ResearchLab'}]
        self.state['phase'] = {'ActionPhase': {'current_player': self.s['player']}}
        self.s['candidates'] = [
            {'action': {'type': 'Pass', 'booster_id': None}},
            {'action': {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute', 'tech_tile_choice': None}},
        ]

    def test_pi_is_offered_before_research_is_legal(self):
        routes, _ = plans_for(self.s, [(1, ''), (2, '')])
        self.assertTrue(any(r.institute == '0,0' for r in routes))
        self.assertTrue({'current-choice', 'expand', 'academy-Science'} <= {r.name for r in routes})

    def test_both_pi_and_alternatives_can_win_without_a_faction_bonus(self):
        for preferred in ('current-choice', 'PI@0,0'):
            teacher = HadschPlanTeacher().bind(object())
            with patch('conditional_plans.teacher.run_plan', side_effect=lambda e,s,v,r: {
                    'first': int(r.name == 'PI@0,0'), 'complete': True,
                    'value': 101 if r.name == preferred else 90}):
                scores = teacher.rank(self.s)
            self.assertEqual(teacher.plan_history[-1]['selected'], preferred)
            self.assertEqual(best_index(scores, range(len(scores))), int(preferred == 'PI@0,0'))

    def test_incomplete_control_preserves_ranks_and_unknown_has_no_value(self):
        teacher = HadschPlanTeacher().bind(object())
        with patch('conditional_plans.teacher.run_plan', return_value={'first': 0, 'complete': False, 'value': None}):
            self.assertEqual(teacher.rank(self.s), CurrentActionTeacher(1).rank(self.s))

    def test_xenos_is_unchanged_and_setup_does_not_plan(self):
        self.p['faction'] = 'Xenos'
        with patch('conditional_plans.teacher.run_plan') as run:
            self.assertEqual(HadschPlanTeacher().rank(self.s), CurrentActionTeacher(1).rank(self.s))
            run.assert_not_called()
        self.p['faction'] = 'HadschHallas'
        self.state['phase'] = {'Setup': {}}
        with patch('conditional_plans.teacher.run_plan') as run:
            self.assertEqual(HadschPlanTeacher().rank(self.s), CurrentActionTeacher(1).rank(self.s))
            run.assert_not_called()

    def test_pi_milestone_pays_exact_coordinate_prerequisite(self):
        self.p['structures'][0]['kind'] = 'Mine'
        pred, need = next_milestone(self.s, Plan('pi', institute='0,0'))
        self.assertTrue(pred({'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'}))
        self.assertFalse(pred({'type': 'Upgrade', 'coord': '2,0', 'to': 'TradingStation'}))
        self.assertEqual(need, {'ore': 2, 'credits': 6})
        self.p['structures'][0]['kind'] = 'TradingStation'
        pred, need = next_milestone(self.s, Plan('pi', institute='0,0'))
        self.assertTrue(pred(self.s['candidates'][1]['action']))
        self.assertEqual(need, {'ore': 4, 'credits': 6})

    def test_pi_already_elsewhere_does_not_try_to_build_a_second(self):
        self.p['structures'][1]['kind'] = 'PlanetaryInstitute'
        pred, need = next_milestone(self.s, Plan('pi', institute='0,0'))
        self.assertFalse(pred(self.s['candidates'][1]['action']))
        self.assertEqual(need, {})

    def test_distance_pair_uses_distinct_sites_and_both_orders(self):
        self.state['final_scoring_tiles'] = [{'condition': 'GreatestDistancePiAcademy'}]
        routes, sampling = plans_for(self.s, [(1, ''), (2, '')])
        pairs = [r for r in routes if r.institute and r.academy_coord]
        self.assertTrue(pairs)
        self.assertEqual({r.academy_first for r in pairs}, {True, False})
        self.assertTrue(all(r.institute != r.academy_coord for r in pairs))
        self.assertIn('pair_targets_total', sampling)

    def test_pair_not_completed_by_pi_alone_or_other_academy_type(self):
        route = Plan('pair', institute='0,0', academy='Science', academy_coord='2,0')
        self.p['structures'][0]['kind'] = 'PlanetaryInstitute'
        self.assertFalse(acquired(self.s, self.s['player'], route))
        self.p['structures'][1]['kind'] = {'Academy': 'Qic'}
        self.assertFalse(acquired(self.s, self.s['player'], route))
        self.p['structures'][1]['kind'] = {'Academy': 'Science'}
        self.assertTrue(acquired(self.s, self.s['player'], route))

    def test_rebellion_plan_keeps_preparing_pi_when_this_round_action_is_taken(self):
        self.state['used_spaceship_actions'] = [12]
        route = Plan('pi-rebellion', institute='0,0', repeat_rebellion=True)
        pred, need = next_milestone(self.s, route)
        self.assertTrue(pred(self.s['candidates'][1]['action']))
        self.assertEqual(need, {'ore': 4, 'credits': 6})
        self.p['structures'][0]['kind'] = 'PlanetaryInstitute'
        self.assertFalse(acquired(self.s, self.s['player'], route))

    def test_gaia_goal_is_colonization_not_just_sending_a_gaiaformer(self):
        cell = self.state['board']['hexes']['1,0']
        cell['planet'].update(planet_type='Transdim', owner=self.s['player'], is_gaia_formed=False)
        route = Plan('gaia', gaia_coord='1,0')
        self.assertFalse(acquired(self.s, self.s['player'], route))
        pred, _ = next_milestone(self.s, route)
        self.assertTrue(pred({'type': 'Pass'}))
        cell['planet']['is_gaia_formed'] = True
        pred, need = next_milestone(self.s, route)
        self.assertTrue(pred({'type': 'Build', 'coord': '1,0'}))
        self.assertEqual(need['ore'], 1)
        self.assertEqual(need['credits'], 2)
        self.p['structures'].append({'hex': '1,0', 'kind': 'Mine'})
        self.assertTrue(acquired(self.s, self.s['player'], route))

    def test_rival_taken_gaia_target_is_not_counted_or_pursued(self):
        cell = self.state['board']['hexes']['1,0']
        cell['planet'].update(planet_type='Transdim', owner=3, is_gaia_formed=True)
        route = Plan('gaia', gaia_coord='1,0')
        pred, need = next_milestone(self.s, route)
        self.assertFalse(pred({'type': 'Build', 'coord': '1,0'}))
        self.assertEqual(need, {})
        self.assertFalse(acquired(self.s, self.s['player'], route))

    def test_legal_special_gaia_does_not_force_unneeded_research(self):
        self.state['board']['hexes']['1,0']['planet'].update(planet_type='Transdim', owner=None)
        action = {'type': 'RoundBoosterImmediateGaiaFormation', 'coord': '1,0'}
        self.s['candidates'].append({'action': action})
        pred, need = next_milestone(self.s, Plan('gaia', gaia_coord='1,0'))
        self.assertTrue(pred(action))
        self.assertEqual(need, {})

    def test_forecast_only_pi_and_gaia_do_not_mutate_parent_or_award_intentions(self):
        before = copy.deepcopy(self.s)
        plans_for(self.s, [(1, ''), (2, '')])
        self.assertEqual(before, self.s)


if __name__ == '__main__':
    unittest.main()
