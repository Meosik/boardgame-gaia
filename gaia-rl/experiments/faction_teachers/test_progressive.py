"""Scheduler tests use synthetic values; native depth tests use a saved branch."""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from gaia_rl import Environment
from faction_teachers.clock import completed_values
from faction_teachers.guidance import comparison_variants
from faction_teachers.progressive import progressive_search
from four_factions import preparation as prep


class ProgressiveTests(unittest.TestCase):
    def setUp(self):
        self.control = prep.Goal('current-choice', first=0)
        self.existing = prep.Goal('pilot', 'ordered', first=1, sources=('faction-tech-pilot',))
        self.preserve = comparison_variants(self.existing)[1]
        self.other = prep.Goal('other', 'root', first=2)
        self.started, self.published = [], []
        self.result = dict(plans=[], index=0, selected='local-baseline', coverage_complete=False)

    def run_search(self, forecast, *, depths=(1, 2), tasks=None, deadline=None, allocation=None):
        def rollout(env, snapshot, first, goal, policies, deadline, *, decision_depth, **kwargs):
            self.started.append((decision_depth, goal.name))
            return forecast(decision_depth, goal)

        def publish_depth(rows, depth):
            winner = max((r for r in rows if r['complete']), key=lambda r: r['value'])
            self.result.update(plans=rows, index=winner['first'], selected=winner['goal'], comparison_depth=depth)
            self.published.append(deepcopy(self.result))
            return winner

        end = deadline if deadline is not None else time.monotonic() + 10
        with patch('faction_teachers.progressive.DEPTHS', depths), \
                patch.object(prep, 'rollout', side_effect=rollout):
            return progressive_search(None, {}, [], tasks or [self.other, self.existing, self.preserve],
                self.control, prep.Policies(), self.result, publish_depth, lambda: None,
                soft_deadline=end, hard_deadline=end, allocation=allocation)

    @staticmethod
    def complete(value, full=False):
        return dict(complete=True, value=value, actions=[], full_horizon_reached=full)

    def test_core_paths_before_other_candidates_and_before_deepening(self):
        self.run_search(lambda d, g: self.complete(1))
        self.assertEqual(self.started[:4], [(1, g.name) for g in
                                           (self.control, self.existing, self.preserve, self.other)])
        self.assertEqual(self.started[4][0], 2)
        self.assertEqual(self.result['unsearched_comparisons'], 0)

    def test_only_same_depth_values_reach_selection_and_clock(self):
        def forecast(depth, goal):
            if depth == 1:
                return self.complete(100 if goal == self.preserve else 10)
            return self.complete(-200 if goal == self.preserve else -100)
        result = self.run_search(forecast)
        self.assertEqual(result['comparison_depth'], 2)
        self.assertNotEqual(result['selected'], self.preserve.name)
        self.assertEqual(max(completed_values(result).values()), -100)
        for receipt in self.published:
            self.assertEqual({r['comparison_depth'] for r in receipt['plans']}, {receipt['comparison_depth']})

    def test_deeper_winner_cannot_publish_without_deeper_control(self):
        def forecast(depth, goal):
            if depth == 2 and goal == self.control:
                raise prep.SearchExpired()
            return self.complete(1000 if depth == 2 else 20 if goal == self.preserve else 10)
        result = self.run_search(forecast)
        self.assertEqual(result['comparison_depth'], 1)
        self.assertEqual(result['selected'], self.preserve.name)
        self.assertFalse(result['comparison_stages'][-1]['published'])
        self.assertEqual(result['comparison_stages'][-1]['plans'][0]['value'], 1000)
        self.assertEqual(max(completed_values(result).values()), 20)

    def test_incomplete_incumbent_retains_shallower_comparison(self):
        def forecast(depth, goal):
            if depth == 2 and goal == self.preserve:
                return dict(complete=False, value=None)
            return self.complete(20 if goal == self.preserve else 10)
        result = self.run_search(forecast)
        self.assertEqual(result['comparison_depth'], 1)
        self.assertEqual(result['selected'], self.preserve.name)
        self.assertIn('anchor incomplete', result['stop_reason'])

    def test_incomplete_alternative_is_unknown_and_not_selected(self):
        result = self.run_search(lambda d, g: dict(complete=False, value=None) if g == self.preserve
                                 else self.complete(5))
        self.assertFalse(result['coverage_complete'])
        self.assertNotEqual(result['selected'], self.preserve.name)
        self.assertIsNone(next(r for r in result['plans'] if r['goal'] == self.preserve.name)['value'])

    def test_full_horizon_stops_without_repeating_finished_routes(self):
        result = self.run_search(lambda d, g: self.complete(1, full=True))
        self.assertEqual(len(self.started), 4)
        self.assertTrue(result['coverage_complete'])
        self.assertEqual(len(result['comparison_stages']), 1)

    def test_early_full_horizon_reused_at_the_same_current_cutoff(self):
        self.run_search(lambda d, g: self.complete(1, full=(g == self.control or d == 2)))
        self.assertEqual(self.started.count((1, self.control.name)), 1)
        self.assertNotIn((2, self.control.name), self.started)
        self.assertTrue(self.result['coverage_complete'])
        self.assertEqual({r['comparison_depth'] for r in self.result['plans']}, {2})

    def test_cached_first_action_and_exact_duplicate_goal(self):
        goal = prep.Goal('select-once', 'ordered', sources=('faction-tech-pilot',))
        with patch.object(prep, 'select_goal', return_value=1) as select:
            self.run_search(lambda d, g: self.complete(1), tasks=[goal, goal])
        select.assert_called_once()
        self.assertEqual(self.result['planned_comparisons'], 2)

    def test_ties_keep_previous_incumbent(self):
        result = self.run_search(lambda d, g: self.complete(20 if d == 2 or g == self.preserve else 10))
        self.assertEqual(result['selected'], self.preserve.name)

    def test_no_extra_time_or_forecast_after_deadline(self):
        self.run_search(lambda d, g: self.fail('Forecast after deadline'), deadline=time.monotonic()-1)
        self.assertEqual(self.started, [])
        self.assertEqual(self.result['selected'], 'local-baseline')

    def test_live_allocation_stop_keeps_completed_shallow_choice(self):
        def allocation():
            return time.monotonic() + (1 if len(self.started) < 4 else -1)
        self.run_search(lambda d, g: self.complete(1), allocation=allocation)
        self.assertEqual(len(self.started), 4)
        self.assertEqual(self.result['comparison_depth'], 1)

    def test_clock_rejects_stale_depth_but_legacy_receipts_still_work(self):
        rows = [dict(complete=True, first=0, value=900, comparison_depth=1),
                dict(complete=True, first=1, value=10, comparison_depth=2)]
        self.assertEqual(completed_values(dict(plans=rows, comparison_depth=2)), {1: 10})
        self.assertEqual(completed_values(dict(plans=rows)), {0: 900, 1: 10})


class NativeDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((Path(__file__).parent/'fixtures/ambas-plan-cancellation.json').read_text())['fixture']
        cls.env = Environment(fixture['seed'], 2000)
        for index in fixture['prefix']:
            snapshot = json.loads(cls.env.snapshot_json())
            cls.env.step(snapshot['decision_id'], index)
        cls.snapshot = json.loads(cls.env.snapshot_json())
        cls.first = fixture['destructive_index']
        cls.goal = prep.Goal('current-choice', first=cls.first)

    def test_one_native_transition_without_ranking_an_opponent(self):
        with patch.object(prep.Policies, 'rank', side_effect=AssertionError('Exceeded depth 1')):
            result = prep.rollout(self.env, self.snapshot, self.first, self.goal,
                prep.Policies(shared_factions=True, faction_tech_plans=True),
                time.monotonic()+10, decision_depth=1)
        after = json.loads(self.env.fork(self.snapshot['decision_id'], self.first).snapshot_json())
        actor = self.snapshot['player']
        expected = prep.leaf_value(after, actor, self.snapshot['state']['players'][actor])
        self.assertEqual(result['value'], expected)
        self.assertEqual(result['decisions'], 1)
        self.assertFalse(result['full_horizon_reached'])
        self.assertEqual(json.loads(self.env.snapshot_json()), self.snapshot)

    def test_legacy_rollout_shape_and_early_boundary_are_preserved(self):
        with patch.object(prep, 'reached_horizon', return_value=True):
            old = prep.rollout(self.env, self.snapshot, self.first, self.goal,
                              prep.Policies(), time.monotonic()+10)
            new = prep.rollout(self.env, self.snapshot, self.first, self.goal,
                              prep.Policies(), time.monotonic()+10, decision_depth=8)
        self.assertTrue(new.pop('full_horizon_reached'))
        self.assertEqual(old, new)
        self.assertEqual(json.loads(self.env.snapshot_json()), self.snapshot)

    def test_depth_must_remain_within_legacy_limit(self):
        for depth in (0, -1, 193):
            with self.assertRaises(ValueError):
                prep.rollout(self.env, self.snapshot, self.first, self.goal,
                             prep.Policies(), time.monotonic()+10, decision_depth=depth)


if __name__ == '__main__':
    unittest.main()
