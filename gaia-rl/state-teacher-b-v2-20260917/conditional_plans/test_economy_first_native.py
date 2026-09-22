"""Native reviewed-game regressions; unit priorities alone are not strength evidence."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from gaia_rl._native import Environment
from conditional_plans.economy_first import EconomyFirstTeacher
from conditional_plans.opening import OpeningPlanTeacher
from conditional_plans.forecast import forecast_many
from conditional_plans.routes import Plan, acquired
from current_actions.teacher import CurrentContextTeacher
from research_plans.teacher import best_index, research_track
from scoring_cache import ranking_scope


def replay_root(decision):
    data = json.loads((Path(__file__).parent/'fixtures/hadsch113.json').read_text())
    env = Environment(data['seed'], 2000)
    for action in data['actions'][:decision]:
        snapshot = json.loads(env.snapshot_json())
        index = next(i for i, c in enumerate(snapshot['candidates']) if c['action'] == action)
        env.step(snapshot['decision_id'], index)
    return env, json.loads(env.snapshot_json())


class NativeEconomyFirstTests(unittest.TestCase):
    def test_reviewed_native_states_preserve_contextual_non_economy_advances(self):
        for decision in (46, 52, 58, 79):
            env, snapshot = replay_root(decision)
            original = env.snapshot_json()
            teacher = EconomyFirstTeacher().bind(env)
            parent_scores = CurrentContextTeacher().bind(env).rank(snapshot)
            alternatives = [i for i, c in enumerate(snapshot['candidates'])
                            if research_track(snapshot['state'], c['action']) not in (None, 'Economy')]
            preferred = best_index(parent_scores, alternatives)
            self.assertIsNotNone(preferred)
            parent_scores[preferred] = (max(v for v, _ in parent_scores)+1, 'contextual alternative')
            with patch.object(OpeningPlanTeacher, 'rank', return_value=parent_scores) as parent:
                scores = teacher.rank(snapshot)
            parent.assert_called_once_with(snapshot)
            self.assertEqual(scores, parent_scores)
            index = best_index(scores, range(len(scores)))
            action = snapshot['candidates'][index]['action']
            self.assertEqual(index, preferred)
            self.assertNotEqual(research_track(snapshot['state'], action), 'Economy')
            after = json.loads(env.fork(snapshot['decision_id'], index).snapshot_json())
            p = snapshot['state']['players'][snapshot['player']]
            q = after['state']['players'][snapshot['player']]
            self.assertLess(p['research_tracks']['economy'], 4)
            self.assertEqual(q['research_tracks']['economy'], p['research_tracks']['economy'])
            self.assertEqual(sum(q['research_tracks'].values()), sum(p['research_tracks'].values())+1)
            if action['type'] == 'ResearchAdvance':
                self.assertEqual(p['resources']['knowledge']-q['resources']['knowledge'], 4)
            self.assertEqual(original, env.snapshot_json())

    @ranking_scope()
    def test_terminal_horizon_reaches_native_final_vp_not_round_six_income(self):
        env, snapshot = replay_root(79)
        original = env.snapshot_json()
        scores = CurrentContextTeacher().bind(env).rank(snapshot)
        first = best_index(scores, range(len(scores)))
        selector = lambda e, s, ranks, goal, done: best_index(ranks, range(len(ranks)))
        goal = Plan('current-choice')
        def summary(state, actor, frames):
            return {'phase': state['phase'], 'actor': actor}
        results, _ = forecast_many(env, snapshot, [(goal, first)], selector, acquired,
                                   finish_game=True, summarize=summary)
        result = results[0]
        self.assertTrue(result['complete'])
        final_scores = dict(result['diagnostics']['phase']['Ended']['final_scores'])
        self.assertEqual(result['value'], final_scores[snapshot['player']])
        self.assertTrue(any(a['round'] == 6 for a in result['actions']))
        self.assertEqual(original, env.snapshot_json())

    def test_terminal_forecast_cap_still_means_unknown(self):
        env, snapshot = replay_root(79)
        original = env.snapshot_json()
        scores = CurrentContextTeacher().bind(env).rank(snapshot)
        first = best_index(scores, range(len(scores)))
        results, _ = forecast_many(env, snapshot, [(Plan('current-choice'), first)],
            lambda e, s, ranks, goal, done: best_index(ranks, range(len(ranks))), acquired,
            finish_game=True, limit=1)
        self.assertFalse(results[0]['complete'])
        self.assertIsNone(results[0]['value'])
        self.assertEqual(original, env.snapshot_json())


if __name__ == '__main__':
    unittest.main()
