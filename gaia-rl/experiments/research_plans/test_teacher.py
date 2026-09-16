import copy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from current_actions.teacher import CurrentContextTeacher, CurrentActionTeacher
from integrated import test_teacher
from research_plans.teacher import (Goal, ResearchPlanTeacher, best_index, forecast,
                                   goal_index, goals_for, reached_horizon, research_track)
from research_plans.value import endpoint_value, final_metric, standing_points


class ResearchPlanTests(unittest.TestCase):
    def setUp(self):
        test_teacher.IntegratedTests.setUp(self)
        self.p['faction'] = 'HadschHallas'
        self.state['phase'] = {'ActionPhase': {'current_player': self.p['player_id']}}
        self.s['candidates'] = [{'action': {'type': 'ResearchAdvance', 'track': track}}
                                for track in ('Economy', 'Navigation', 'GaiaProject', 'Science')]
        self.s['candidates'].append({'action': {'type': 'Pass', 'booster_id': None}})
        self.p['resources']['knowledge'] = 8
        self.scores = [(50-i, 'existing') for i in range(5)]

    def test_foundations_are_alternatives_not_a_forced_order(self):
        names = {g.name for g in goals_for(self.s)}
        self.assertTrue({'current-choice', 'Economy-2', 'Navigation-2', 'GaiaProject-2', 'Science-2'} <= names)
        nav = Goal('nav', (('Navigation', 2),))
        self.assertEqual(goal_index(self.s, self.scores, nav), 1)
        self.p['research_tracks']['navigation'] = 2
        self.assertEqual(goal_index(self.s, self.scores, nav), 0)

    def test_gaia_and_navigation_orders_share_the_same_initial_state(self):
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Transdim'
        before = copy.deepcopy(self.s)
        goals = {g.name: g for g in goals_for(self.s)}
        self.assertEqual(goal_index(self.s, self.scores, goals['Gaia-then-range']), 2)
        self.assertEqual(goal_index(self.s, self.scores, goals['range-then-Gaia']), 1)
        self.assertEqual(before, self.s)

    def test_delay_five_includes_free_tile_research_and_expires_after_income(self):
        self.p['research_tracks']['economy'] = 4
        self.state['research_board']['tech_tile_slots'] = [2, 3, 4, 5, 7, 6, 8, 9, 10]
        self.s['candidates'][1]['action'] = {'type': 'Upgrade', 'tech_tile_choice':
                                            {'kind': 'Standard', 'tile': 7, 'advance_track': None}}
        self.assertEqual(research_track(self.state, self.s['candidates'][1]['action']), 'Economy')
        goal = Goal('wait', defer_until=2)
        self.assertEqual(goal_index(self.s, self.scores, goal), 2)
        self.state['round'] = 2
        self.assertEqual(goal_index(self.s, self.scores, goal), 0)

    def test_unavailable_advanced_target_is_abandoned(self):
        goal = Goal('advanced', (('Navigation', 4),), ('Navigation', 20))
        self.state['research_board']['advanced_tech_tiles'][1] = None
        self.assertEqual(goal_index(self.s, self.scores, goal), 0)
        self.state['research_board']['advanced_tech_tiles'][1] = 20
        self.assertEqual(goal_index(self.s, self.scores, goal), 1)

    def test_advanced_acquisition_must_be_a_native_candidate(self):
        self.p['research_tracks']['navigation'] = 4
        self.state['research_board']['advanced_tech_tiles'][1] = 20
        goal = Goal('advanced', (('Navigation', 4),), ('Navigation', 20))
        self.assertEqual(goal_index(self.s, self.scores, goal), 0)
        self.s['candidates'][3]['action'] = {'type': 'Upgrade', 'tech_tile_choice':
            {'kind': 'Advanced', 'track': 'Navigation', 'covered_tile': 7, 'advance_track': None}}
        self.assertEqual(goal_index(self.s, self.scores, goal), 3)

    def test_available_lost_fleet_advanced_is_also_a_candidate_plan(self):
        self.s['candidates'][3]['action'] = {'type': 'Upgrade', 'tech_tile_choice':
            {'kind': 'LostFleetAdvanced', 'covered_tile': 7, 'advance_track': None}}
        goal = next(g for g in goals_for(self.s) if g.name == 'available-advanced')
        self.assertEqual(goal_index(self.s, self.scores, goal), 3)

    def test_qic_funding_cannot_create_missing_native_conversion(self):
        self.p['explored_ships'] = [1]
        self.p['resources']['qic'] = 1
        self.state['used_spaceship_actions'] = []
        goal = Goal('tech', payoff='RebellionGainTechTile')
        self.assertEqual(goal_index(self.s, self.scores, goal), 0)
        self.s['candidates'][3]['action'] = {'type': 'FreeAction', 'kind': 'CreditsToQic', 'count': 2}
        self.assertEqual(goal_index(self.s, self.scores, goal), 3)
        self.state['used_spaceship_actions'] = [12]
        self.assertEqual(goal_index(self.s, self.scores, goal), 0)

    def test_horizon_waits_for_income_order_and_is_clipped_only_by_actual_end(self):
        self.state['round'] = 3
        self.assertTrue(reached_horizon(self.state, 3))
        self.state['phase'] = {'IncomeOrderPending': {}}
        self.assertFalse(reached_horizon(self.state, 3))
        self.state['round'] = 6
        self.state['phase'] = {'ActionPhase': {}}
        self.assertFalse(reached_horizon(self.state, 7))
        self.state['phase'] = {'Ended': {'final_scores': [[1, 90]]}}
        self.assertTrue(reached_horizon(self.state, 7))

    def test_final_score_is_not_double_counted_with_stock_or_tech_rewards(self):
        self.state['phase'] = {'Ended': {'final_scores': [[1, 90]]}}
        self.assertEqual(endpoint_value(self.state, 1, self.p, self.teacher), 90)

    def test_leaf_prices_are_frozen_and_immediate_advanced_rewards_are_sunk(self):
        root = copy.deepcopy(self.p)
        old = endpoint_value(self.state, 1, root, self.teacher)
        self.p['advanced_tech_tiles'] = [1, 2, 5, 6, 9, 10, 12, 13]
        self.assertEqual(endpoint_value(self.state, 1, root, self.teacher), old)
        self.p['resources']['ore'] += 1
        self.assertAlmostEqual(endpoint_value(self.state, 1, root, self.teacher)-old, 1.5)

    def test_economy_vp_overlay_is_in_tail_but_level_five_has_no_income(self):
        self.p['research_tracks']['economy'] = 4
        self.state['research_board']['economy_research_tile_side'] = 'VictoryPoints'
        old = endpoint_value(self.state, 1, self.p, self.teacher)
        with patch('research_plans.value.income', return_value={'ore': 0, 'credits': 0, 'knowledge': 0}):
            level4 = endpoint_value(self.state, 1, self.p, self.teacher)
            self.p['research_tracks']['economy'] = 5
            level5 = endpoint_value(self.state, 1, self.p, self.teacher)
        self.assertAlmostEqual(level5-level4, 4-.7*5)
        self.assertGreater(old, level4)

    def test_xenos_ranking_is_unchanged_and_never_forecast(self):
        self.p['faction'] = 'Xenos'
        old = CurrentActionTeacher(1).rank(self.s)
        teacher = ResearchPlanTeacher(1)
        with patch('research_plans.teacher.forecast') as run:
            self.assertEqual(teacher.rank(self.s), old)
            run.assert_not_called()

    def test_incomplete_control_preserves_existing_ranks(self):
        teacher = ResearchPlanTeacher(1)
        teacher.env = object()
        expected = CurrentActionTeacher(1).rank(self.s)
        with patch('research_plans.teacher.forecast', return_value={'complete': False, 'value': None}):
            self.assertEqual(teacher.rank(self.s), expected)
        self.assertIn('fallback', teacher.plan_history[-1])

    def test_leaf_comparison_can_keep_control_or_choose_lower_legacy_rank(self):
        teacher = ResearchPlanTeacher(1)
        teacher.env = object()
        before = copy.deepcopy(self.s)
        def run(env, snapshot, first, goal, policy):
            return {'complete': True, 'value': 100 if goal.name == 'Navigation-2' else 90}
        with patch('research_plans.teacher.forecast', side_effect=run):
            scores = teacher.rank(self.s)
        self.assertEqual(best_index(scores, range(len(scores))), 1)
        self.assertTrue(all(math.isfinite(s[0]) for s in scores))
        self.assertEqual(self.s, before)
        self.assertEqual(teacher.plan_history[-1]['selected'], 'Navigation-2')

    def test_immediate_control_can_beat_all_plans_and_ties_do_not_force_a_route(self):
        teacher = ResearchPlanTeacher(1)
        teacher.env = object()
        original = CurrentActionTeacher(1).rank(self.s)
        for other_value in (80, 90):
            def run(env, snapshot, first, goal, policy):
                return {'complete': True, 'value': 90 if goal.name == 'current-choice' else other_value}
            with patch('research_plans.teacher.forecast', side_effect=run):
                scores = teacher.rank(self.s)
            self.assertEqual(best_index(scores, range(len(scores))), best_index(original, range(len(original))))
            self.assertEqual(teacher.plan_history[-1]['selected'], 'current-choice')


class NativeMetricParityTests(unittest.TestCase):
    def test_shared_rust_typescript_fixture_all_36_metrics(self):
        root = Path(__file__).resolve().parents[3]
        fixture = json.loads((root/'gaia-frontend/src/tests/fixtures/finalScoringProgress.json').read_text())
        for index, player in enumerate(fixture['state']['players']):
            for i, condition in enumerate(fixture['conditions']):
                self.assertEqual(final_metric(fixture['state'], player, condition),
                                 fixture['expected'][index][i], (index, condition))


if __name__ == '__main__':
    unittest.main()
