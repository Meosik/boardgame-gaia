import copy
import unittest
from unittest.mock import patch

from current_actions.teacher import CurrentActionTeacher
from integrated import test_teacher
from research_plans.teacher import best_index
from resource_plans.teacher import ResourcePlanTeacher, wait_for_funding
from resource_plans.routes import Route, routes_for, milestone, achieved


class ResourcePlanTests(unittest.TestCase):
    def setUp(self):
        test_teacher.IntegratedTests.setUp(self)
        self.p['faction'] = 'Xenos'
        self.state['phase'] = {'ActionPhase': {'current_player': self.s['player']}}
        self.s['candidates'] = [{'action': {'type': 'Pass', 'booster_id': None}},
                                {'action': {'type': 'Upgrade', 'coord': '0,0',
                                            'to': {'Academy': 'Science'}, 'tech_tile_choice': None}}]

    def test_construction_roots_offer_competing_plans_without_legal_research(self):
        names = {r.name for r in routes_for(self.s, [(1, ''), (2, '')])}
        self.assertTrue({'current-choice', 'academy-Science', 'academy-Qic',
                         'Navigation-2', 'expand'} <= names)

    def test_academy_is_a_candidate_not_a_faction_requirement(self):
        teacher = ResourcePlanTeacher().bind(object())
        old = CurrentActionTeacher(1).rank(self.s)
        with patch('resource_plans.teacher.run_route', side_effect=lambda env, s, scores, route:
                   {'first': 0 if route.name == 'current-choice' else 1,
                    'complete': True, 'value': 100 if route.name == 'current-choice' else 90}):
            ranks = teacher.rank(self.s)
        self.assertEqual(best_index(ranks, range(len(ranks))), 0)
        self.assertEqual(teacher.plan_history[-1]['selected'], 'current-choice')
        self.assertNotEqual(best_index(old, range(len(old))), 0)

    def test_same_faction_changes_choice_with_forecast_outcome(self):
        teacher = ResourcePlanTeacher().bind(object())
        with patch('resource_plans.teacher.run_route', side_effect=lambda env, s, scores, route:
                   {'first': 1 if route.name == 'academy-Science' else 0,
                    'complete': True, 'value': 101 if route.name == 'academy-Science' else 90}):
            ranks = teacher.rank(self.s)
        self.assertEqual(best_index(ranks, range(len(ranks))), 1)
        self.assertEqual(teacher.plan_history[-1]['selected'], 'academy-Science')

    def test_incomplete_control_preserves_all_existing_scores(self):
        teacher = ResourcePlanTeacher().bind(object())
        expected = CurrentActionTeacher(1).rank(self.s)
        with patch('resource_plans.teacher.run_route', return_value={
                'first': 0, 'complete': False, 'value': None}):
            self.assertEqual(teacher.rank(self.s), expected)

    def test_hadsch_remains_the_existing_control(self):
        self.p['faction'] = 'HadschHallas'
        with patch('resource_plans.teacher.run_route') as run:
            self.assertEqual(ResourcePlanTeacher().rank(self.s), CurrentActionTeacher(1).rank(self.s))
            run.assert_not_called()

    def test_academy_prerequisite_changes_with_actual_buildings(self):
        route = Route('academy', academy='Science')
        predicate, need = milestone(self.s, route)
        self.assertTrue(predicate(self.s['candidates'][1]['action']))
        self.assertEqual(need, {'ore': 6, 'credits': 6})
        self.p['structures'][0]['kind'] = 'TradingStation'
        predicate, need = milestone(self.s, route)
        self.assertFalse(predicate(self.s['candidates'][1]['action']))
        self.assertTrue(predicate({'type': 'Upgrade', 'to': 'ResearchLab'}))
        self.assertEqual(need, {'ore': 3, 'credits': 5})

    def test_acquisition_is_from_actual_state_not_intended_action(self):
        route = Route('academy', academy='Science')
        self.assertFalse(achieved(self.s, self.s['player'], route))
        self.p['structures'][0]['kind'] = {'Academy': 'Qic'}
        self.assertFalse(achieved(self.s, self.s['player'], route))
        self.p['structures'][0]['kind'] = {'Academy': 'Science'}
        self.assertTrue(achieved(self.s, self.s['player'], route))

    def test_rival_taken_ship_action_does_not_force_entry(self):
        self.state['used_spaceship_actions'] = [12]
        route = Route('rebellion', ship='Rebellion', payoff='RebellionGainTechTile')
        predicate, _ = milestone(self.s, route)
        self.assertFalse(predicate({'type': 'ExploreSpaceship', 'ship': 'Rebellion'}))
        route = Route('range-then-tech', (('Navigation', 2),), payoff='RebellionGainTechTile', lab_first=True)
        predicate, _ = milestone(self.s, route)
        self.assertFalse(predicate({'type': 'ResearchAdvance', 'track': 'Navigation'}))

    def test_finished_lab_research_route_does_not_rebuild_a_consumed_lab(self):
        self.p['structures'][0]['kind'] = {'Academy': 'Science'}
        self.p['research_tracks']['navigation'] = 2
        route = Route('lab-first', (('Navigation', 2),), lab_first=True)
        predicate, _ = milestone(self.s, route)
        self.assertFalse(predicate({'type': 'Upgrade', 'to': 'TradingStation'}))

    def test_ship_and_supply_token_choices_are_separate_candidates(self):
        base = {'type': 'FormFederation', 'hexes': ['0,0'], 'satellite_hexes': []}
        for token in ({'Supply': 5}, {'Supply': 4}, {'Spaceship': 'TFMars'}):
            self.s['candidates'].append({'action': {**base, 'token': token}})
        before = copy.deepcopy(self.s)
        routes = [r for r in routes_for(self.s, [(1, '')]*5) if r.first is not None]
        self.assertEqual({r.first for r in routes}, {2, 3, 4})
        self.assertEqual(before, self.s)

    def test_remote_station_does_not_assume_the_neighbor_discount(self):
        self.p['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
        _, need = milestone(self.s, Route('academy', academy='Science'))
        self.assertEqual(need['credits'], 6)
        self.state['board']['hexes']['1,0']['structures'] = [{'owner': 2, 'kind': 'Mine'}]
        _, need = milestone(self.s, Route('academy', academy='Science'))
        self.assertEqual(need['credits'], 3)

    def test_reservation_is_only_a_fundable_candidate_not_a_fixed_ratio(self):
        self.p['resources'].update(ore=5, credits=30)
        before = copy.deepcopy(self.s)
        self.assertEqual(wait_for_funding(self.s, [(1, ''), (2, '')], {'ore': 6, 'credits': 6}), 0)
        self.assertIsNone(wait_for_funding(self.s, [(1, ''), (2, '')], {'ore': 20, 'credits': 6}))
        self.assertEqual(before, self.s)
        self.state['round'] = 6
        self.assertIsNone(wait_for_funding(self.s, [(1, ''), (2, '')], {'ore': 6, 'credits': 6}))

    def test_existing_gaia_and_advanced_payoffs_are_not_lost(self):
        predicate, _ = milestone(self.s, Route('gaia', payoff='GaiaFormation'))
        self.assertTrue(predicate({'type': 'GaiaFormation', 'coord': '1,0'}))
        predicate, _ = milestone(self.s, Route('advanced', payoff='AdvancedTechnology'))
        self.assertTrue(predicate({'type': 'Upgrade', 'tech_tile_choice':
                                  {'kind': 'LostFleetAdvanced', 'covered_tile': 7}}))

    def test_federation_continuations_compare_academy_costs_not_just_stock(self):
        self.s['candidates'].append({'action': {'type': 'FormFederation', 'token': {'source': 'Supply', 'kind': 5}}})
        routes = [r for r in routes_for(self.s, [(1, '')]*3) if r.first == 2]
        self.assertTrue(any(r.academy == 'Science' for r in routes))
        self.assertTrue(any(r.academy == 'Qic' for r in routes))
        self.assertTrue(any(r.academy is None for r in routes))


if __name__ == '__main__':
    unittest.main()
