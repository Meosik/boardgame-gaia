import unittest

from conditional_plans.test_native import replay_root
from conditional_plans.routes import Plan, acquired
from conditional_plans.teacher import select_plan
from conditional_plans.forecast import forecast_many
from current_actions.teacher import CurrentContextTeacher
from research_plans.teacher import forecast
from scoring_cache import ranking_scope


class SharedForecastTests(unittest.TestCase):
    @ranking_scope()
    def test_shared_and_independent_native_paths_match_exactly(self):
        env, s = replay_root(16)
        original = env.snapshot_json()
        policy = CurrentContextTeacher().bind(env)
        scores = policy.rank(s)
        plans = [Plan('PI', institute='-4,-1', repeat_rebellion=True),
                 Plan('same-PI', institute='-4,-1', repeat_rebellion=True),
                 Plan('Gaia', gaia_coord='-3,-4')]
        tasks = [(p, select_plan(env, s, scores, p)) for p in plans]
        expected = [forecast(env, s, i, p, CurrentContextTeacher(),
                            selector=select_plan, achieved=acquired) for p, i in tasks]
        actual, stats = forecast_many(env, s, tasks, select_plan, acquired)
        self.assertEqual(expected, actual)
        self.assertLess(stats['native_prefix_steps'], stats['independent_prefix_steps'])
        self.assertLess(stats['income_reconstructions'], len(tasks))
        self.assertEqual(original, env.snapshot_json())

    def test_limit_does_not_turn_unknown_into_a_numeric_losing_score(self):
        env, s = replay_root(16)
        scores = CurrentContextTeacher().bind(env).rank(s)
        plan = Plan('PI', institute='-4,-1')
        tasks = [(plan, select_plan(env, s, scores, plan))]*2
        expected = forecast(env, s, tasks[0][1], plan, CurrentContextTeacher(), limit=1,
                            selector=select_plan, achieved=acquired)
        actual, stats = forecast_many(env, s, tasks, select_plan, acquired, limit=1)
        self.assertEqual(actual, [expected, expected])
        self.assertIsNone(actual[0]['value'])
        self.assertEqual(stats['native_prefix_steps'], 1)


if __name__ == '__main__':
    unittest.main()
