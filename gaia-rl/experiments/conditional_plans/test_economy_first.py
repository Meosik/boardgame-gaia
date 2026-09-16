import copy
import unittest
from unittest.mock import patch

from conditional_plans.economy_first import (
    EconomyFirstTeacher, compare_five, select_timing, timing_winner,
)
from conditional_plans.opening import OpeningPlanTeacher
from conditional_plans.routes import Plan
from conditional_plans import test_teacher as baseline
from current_actions.conservation import BLOCKED, PREFIX
from current_actions.teacher import CurrentActionTeacher
from research_plans.teacher import best_index


class EconomyFirstTests(unittest.TestCase):
    setUp = baseline.ConditionalTests.setUp

    def research_menu(self, level):
        self.p['research_tracks']['economy'] = level
        self.p['resources']['knowledge'] = 8
        self.s['candidates'] = [{'action': action} for action in (
            {'type': 'ResearchAdvance', 'track': 'Terraforming'},
            {'type': 'ResearchAdvance', 'track': 'Economy'},
            {'type': 'Pass', 'booster_id': None},
            {'type': 'ResearchAdvance', 'track': 'Science'},
        )]
        return [(30, 'terraform'), (10, 'economy'), (0, 'pass'), (20, 'science')]

    def test_low_economy_preserves_contextual_choices_in_every_round(self):
        for level in range(4):
            for rnd in range(1, 7):
                for preferred in (0, 1, 3):
                    with self.subTest(level=level, round=rnd, preferred=preferred):
                        scores = self.research_menu(level)
                        scores[preferred] = (100, 'contextual winner')
                        self.state['round'] = rnd
                        before = copy.deepcopy(self.s)
                        teacher = EconomyFirstTeacher().bind(object())
                        with patch.object(OpeningPlanTeacher, 'rank', return_value=scores) as parent, \
                                patch.object(CurrentActionTeacher, 'rank', return_value=scores), \
                                patch('conditional_plans.economy_first.compare_five',
                                      side_effect=AssertionError('not Economy5')):
                            result = teacher.rank(self.s)
                        parent.assert_called_once_with(self.s)
                        self.assertEqual(result, scores)
                        self.assertEqual(best_index(result, range(len(result))), preferred)
                        self.assertEqual(self.s, before)
                        self.assertEqual(teacher.plan_history, [])

    def test_last_round_other_track_race_is_not_replaced_by_economy_catchup(self):
        scores = self.research_menu(1)
        self.state['round'] = 6
        self.p['research_tracks'].update(gaia=4, ai=4)
        self.p['resources'].update(credits=26, ore=6, knowledge=5, qic=3)
        self.s['candidates'][0]['action']['track'] = 'GaiaProject'
        self.s['candidates'][3]['action']['track'] = 'ArtificialIntelligence'
        other = next(p for p in self.state['players'] if p['player_id'] != self.s['player'])
        other['research_tracks']['economy'] = 5
        before = copy.deepcopy(self.s)
        teacher = EconomyFirstTeacher().bind(object())
        with patch.object(OpeningPlanTeacher, 'rank', return_value=scores) as parent, \
                patch.object(CurrentActionTeacher, 'rank', return_value=scores):
            result = teacher.rank(self.s)
        parent.assert_called_once_with(self.s)
        self.assertEqual(result, scores)
        self.assertEqual(best_index(result, range(len(result))), 0)
        self.assertEqual(self.s, before)

    def test_focus_ends_at_four_without_blocking_other_research(self):
        scores = self.research_menu(4)
        teacher = EconomyFirstTeacher().bind(object())
        with patch.object(OpeningPlanTeacher, 'rank', return_value=scores) as parent:
            self.assertEqual(teacher.rank(self.s), scores)
        parent.assert_called_once()

    def test_other_factions_and_setup_keep_the_parent_policy(self):
        scores = self.research_menu(2)
        for faction, phase in (('Xenos', {'ActionPhase': {}}), ('HadschHallas', {'Setup': {}})):
            self.p['faction'], self.state['phase'] = faction, phase
            teacher = EconomyFirstTeacher().bind(object())
            with patch.object(OpeningPlanTeacher, 'rank', return_value=scores):
                self.assertEqual(teacher.rank(self.s), scores)

    def test_contextual_conservation_is_preserved_below_four(self):
        scores = self.research_menu(2)
        scores[0] = (BLOCKED, PREFIX+'test restriction')
        teacher = EconomyFirstTeacher().bind(object())
        with patch.object(OpeningPlanTeacher, 'rank', return_value=scores), \
                patch.object(CurrentActionTeacher, 'rank', return_value=scores):
            result = teacher.rank(self.s)
        self.assertEqual(result, scores)

    def test_delay_filters_only_economy_five_not_science_five(self):
        scores = self.research_menu(4)
        self.p['research_tracks']['science'] = 4
        scores[1], scores[3] = (100, 'economy'), (90, 'science')
        goal = Plan('later', targets=(('Economy', 5),), defer_until=6)
        self.assertEqual(select_timing(None, self.s, scores, goal, False), 3)
        self.state['round'] = 6
        self.assertEqual(select_timing(None, self.s, scores, goal, False), 1)

    def test_taken_top_abandons_wait_goal_without_fictitious_funding(self):
        scores = self.research_menu(4)
        self.s['candidates'][1]['action'] = {'type': 'FreeAction', 'kind': 'PowerToKnowledge', 'count': 1}
        other = next(p for p in self.state['players'] if p['player_id'] != self.s['player'])
        other['research_tracks']['economy'] = 5
        goal = Plan('later', targets=(('Economy', 5),), defer_until=6)
        self.assertEqual(select_timing(None, self.s, scores, goal, False), 0)

    def test_terminal_comparison_reuses_shared_forecast_with_original_limit(self):
        scores = self.research_menu(4)
        scores[1] = (100, 'economy')
        with patch('conditional_plans.economy_first.forecast_many', return_value=(
                [{'complete': True, 'value': value} for value in (100, 101, 102)], {})) as forecast:
            plans, _ = compare_five(object(), self.s, scores, 1)
        self.assertEqual(len(plans), 3)
        self.assertTrue(forecast.call_args.kwargs['finish_game'])
        self.assertNotIn('limit', forecast.call_args.kwargs)
        self.assertEqual(timing_winner(plans)['defer_until'], 6)

    def test_incomplete_control_is_unknown_and_preserves_original_action(self):
        plans = [{'complete': False, 'value': None, 'defer_until': 0},
                 {'complete': True, 'value': 150, 'defer_until': 6}]
        self.assertIsNone(timing_winner(plans))

    def test_immediate_payoff_can_win_and_equal_scores_prefer_later_income(self):
        plans = [{'complete': True, 'value': 151, 'defer_until': 0},
                 {'complete': True, 'value': 150, 'defer_until': 6},
                 {'complete': False, 'value': None, 'defer_until': 5}]
        self.assertIs(timing_winner(plans), plans[0])
        plans[0]['value'] = 150
        self.assertIs(timing_winner(plans), plans[1])

    def test_timing_selection_changes_only_the_selected_native_rank(self):
        scores = self.research_menu(4)
        scores[1] = (100, 'economy')
        for values, expected in (((150, 160), 0), ((160, 150), 1), ((None, 160), 1)):
            plans = [{'goal': 'now', 'first': 1, 'defer_until': 0,
                      'complete': values[0] is not None, 'value': values[0]},
                     {'goal': 'later', 'first': 0, 'defer_until': 6,
                      'complete': True, 'value': values[1]}]
            teacher = EconomyFirstTeacher().bind(object())
            original = copy.deepcopy(self.s)
            with patch.object(OpeningPlanTeacher, 'rank', return_value=scores), \
                    patch('conditional_plans.economy_first.compare_five', return_value=(plans, {})):
                result = teacher.rank(self.s)
            self.assertEqual(best_index(result, range(len(result))), expected)
            for i, score in enumerate(scores):
                if i != expected:
                    self.assertEqual(result[i], score)
            self.assertEqual(self.s, original)

    def test_last_round_keeps_parent_and_round_five_has_one_delay(self):
        scores = self.research_menu(4)
        scores[1] = (100, 'economy')
        self.state['round'] = 5
        with patch('conditional_plans.economy_first.forecast_many',
                   return_value=([{'complete': True, 'value': 100}]*2, {})) as forecast:
            plans, _ = compare_five(None, self.s, scores, 1)
        self.assertEqual([p['defer_until'] for p in plans], [0, 6])
        self.assertEqual(len(forecast.call_args.args[2]), 2)
        self.state['round'] = 6
        with patch.object(OpeningPlanTeacher, 'rank', return_value=scores), \
                patch('conditional_plans.economy_first.compare_five', side_effect=AssertionError('R6 delay')):
            self.assertEqual(EconomyFirstTeacher().bind(object()).rank(self.s), scores)

    def test_mode_is_explicit_and_historical_modes_stay_unchanged(self):
        from conditional_plans.evaluate import PLANNING_MODES
        from conditional_plans.teacher import PaiaPlanTeacher, PaiaReplanTeacher
        self.assertIs(PLANNING_MODES['economy-first'], EconomyFirstTeacher)
        self.assertIs(PLANNING_MODES['opening'], OpeningPlanTeacher)
        self.assertIs(PLANNING_MODES['per-action'], PaiaReplanTeacher)
        self.assertIs(PLANNING_MODES['goal-continuation'], PaiaPlanTeacher)


if __name__ == '__main__':
    unittest.main()
