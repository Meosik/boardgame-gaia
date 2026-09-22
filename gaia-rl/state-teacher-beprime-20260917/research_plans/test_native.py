import json
from pathlib import Path
import unittest

from gaia_rl._native import Environment
from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from research_plans.teacher import Goal, forecast, goal_index


class NativePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((Path(__file__).parent/'fixtures/hadsch_income_timing.json').read_text())
        cls.seed, cls.prefix = data['seed'], data['actions']
        cls.env = Environment(data['seed'], 2000)
        for action in data['actions']:
            s = json.loads(cls.env.snapshot_json())
            index = next(i for i, c in enumerate(s['candidates']) if c['action'] == action)
            cls.env.step(s['decision_id'], index)
        cls.snapshot = json.loads(cls.env.snapshot_json())

    def test_early_forecast_stops_after_exactly_two_verified_incomes(self):
        env = Environment(self.seed, 2000)
        for action in self.prefix[:35]:
            snapshot = json.loads(env.snapshot_json())
            index = next(i for i, c in enumerate(snapshot['candidates']) if c['action'] == action)
            env.step(snapshot['decision_id'], index)
        original = env.snapshot_json()
        snapshot = json.loads(original)
        self.assertEqual(snapshot['player'], 2)
        self.assertEqual(snapshot['state']['round'], 1)
        first = next(i for i, c in enumerate(snapshot['candidates']) if c['action'] ==
                     {'type': 'ResearchAdvance', 'track': 'Economy'})
        result = forecast(env, snapshot, first, Goal('budgeted', (('Economy', 2),)), CurrentContextTeacher())
        self.assertTrue(result['complete'])
        self.assertEqual(result['round'], 3)
        self.assertEqual([income['round'] for income in result['incomes']], [2, 3])
        self.assertEqual(original, env.snapshot_json())

    def test_first_research_pays_knowledge_and_green_token_once(self):
        original = self.env.snapshot_json()
        s = self.snapshot
        index = next(i for i, c in enumerate(s['candidates']) if c['action'] ==
                     {'type': 'ResearchAdvance', 'track': 'Economy'})
        after = json.loads(self.env.fork(s['decision_id'], index).snapshot_json())['state']['players'][2]
        before = s['state']['players'][2]
        self.assertEqual(before['research_tracks']['economy'], 4)
        self.assertEqual(after['research_tracks']['economy'], 5)
        self.assertEqual(before['resources']['knowledge']-after['resources']['knowledge'], 4)
        self.assertEqual(len(before['federation_tokens'])-len(after['federation_tokens']), 1)
        self.assertEqual(after['resources']['ore']-before['resources']['ore'], 3)
        self.assertEqual(after['resources']['credits']-before['resources']['credits'], 6)
        self.assertEqual(original, self.env.snapshot_json())

    def test_now_and_wait_reach_same_real_endpoint_without_mutating_parent(self):
        original = self.env.snapshot_json()
        scores = CurrentActionTeacher(1).bind(self.env).rank(self.snapshot)
        results = []
        for goal in (Goal('now'), Goal('wait', defer_until=6)):
            first = goal_index(self.snapshot, scores, goal)
            result = forecast(self.env, self.snapshot, first, goal, CurrentContextTeacher())
            self.assertTrue(result['complete'])
            self.assertEqual(result['round'], 6)
            self.assertTrue(result['incomes'])
            self.assertTrue(all(min(row[side].values()) >= 0 for row in result['actions']
                                for side in ('resources_before', 'resources_after')))
            self.assertEqual(original, self.env.snapshot_json())
            results.append(result)
        now, wait = results
        self.assertEqual(now['actions'][0]['tracks_after']['economy'], 5)
        self.assertTrue(all(row['tracks_after']['economy'] == 4 for row in wait['actions'] if row['round'] == 5))
        # Regression fixture only, not a claim that waiting is always the better plan.
        self.assertGreater(wait['value'], now['value'])

    def test_budget_exhaustion_has_no_invented_value_or_extra_step(self):
        original = self.env.snapshot_json()
        result = forecast(self.env, self.snapshot, 0, Goal('bounded'), CurrentContextTeacher(), limit=1)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['value'])
        self.assertEqual(result['decisions'], 1)
        self.assertEqual(len(result['actions']), 1)
        self.assertEqual(original, self.env.snapshot_json())


if __name__ == '__main__':
    unittest.main()
