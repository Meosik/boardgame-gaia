import json
from pathlib import Path
import unittest

from gaia_rl._native import Environment
from current_actions.teacher import CurrentContextTeacher
from resource_plans.funding import funded_paths
from resource_plans.routes import Route, milestone, routes_for
from resource_plans.teacher import select_route


def replay_root(decision):
    data = json.loads((Path(__file__).parent/'fixtures/xenos75.json').read_text())
    env = Environment(data['seed'], 2000)
    for action in data['actions'][:decision]:
        snapshot = json.loads(env.snapshot_json())
        index = next(i for i, c in enumerate(snapshot['candidates']) if c['action'] == action)
        env.step(snapshot['decision_id'], index)
    return env, json.loads(env.snapshot_json())


class NativeResourcePlanTests(unittest.TestCase):
    def test_academy_can_be_funded_before_it_is_legal_without_credit_conversion(self):
        env, snapshot = replay_root(106)
        original = env.snapshot_json()
        route = Route('academy-Science', academy='Science')
        predicate, need = milestone(snapshot, route)
        self.assertEqual(snapshot['state']['players'][2]['resources']['ore'], 5)
        self.assertFalse(any(predicate(c['action']) for c in snapshot['candidates']))
        self.assertFalse(any(c['action'].get('kind') == 'CreditsToOre' for c in snapshot['candidates']))
        paths, _ = funded_paths(env, snapshot, predicate, need)
        self.assertTrue(paths)
        first = snapshot['candidates'][paths[0]['first']]['action']
        self.assertEqual(first, {'type': 'FreeAction', 'kind': 'BurnPower', 'count': 2})
        self.assertEqual(paths[0]['target']['to'], {'Academy': 'Science'})
        branch = env.fork(snapshot['decision_id'], paths[0]['first'])
        after = json.loads(branch.snapshot_json())
        scores = CurrentContextTeacher().rank(after)
        index = select_route(branch, after, scores, route)
        self.assertEqual(after['candidates'][index]['action'],
                         {'type': 'FreeAction', 'kind': 'PowerToOre', 'count': 1})
        branch.step(after['decision_id'], index)
        funded = json.loads(branch.snapshot_json())
        self.assertEqual(funded['state']['players'][2]['resources']['ore'], 6)
        index = select_route(branch, funded, CurrentContextTeacher().rank(funded), route)
        self.assertTrue(predicate(funded['candidates'][index]['action']))
        branch.step(funded['decision_id'], index)
        built = json.loads(branch.snapshot_json())['state']['players'][2]
        self.assertEqual(built['resources']['ore'], 0)
        self.assertTrue(any(s['kind'] == {'Academy': 'Science'} for s in built['structures']))
        self.assertEqual(original, env.snapshot_json())

    def test_real_federation_tokens_each_get_a_native_first_action(self):
        env, snapshot = replay_root(62)
        original = env.snapshot_json()
        scores = CurrentContextTeacher().rank(snapshot)
        routes = [r for r in routes_for(snapshot, scores) if r.first is not None]
        tokens = [snapshot['candidates'][r.first]['action']['token'] for r in routes]
        self.assertIn({'source': 'Supply', 'kind': 5}, tokens)
        self.assertIn({'source': 'Supply', 'kind': 4}, tokens)
        self.assertTrue(any(t['source'] == 'Spaceship' for t in tokens))
        for route in routes:
            after = json.loads(env.fork(snapshot['decision_id'], route.first).snapshot_json())
            self.assertEqual(len(after['state']['players'][2]['federation_tokens']), 1)
        self.assertEqual(original, env.snapshot_json())

    def test_empty_search_budget_does_not_invent_funding(self):
        env, snapshot = replay_root(106)
        predicate, need = milestone(snapshot, Route('academy', academy='Science'))
        paths, examined = funded_paths(env, snapshot, predicate, need, max_nodes=0)
        self.assertEqual(paths, [])
        self.assertEqual(examined, 0)


if __name__ == '__main__':
    unittest.main()
