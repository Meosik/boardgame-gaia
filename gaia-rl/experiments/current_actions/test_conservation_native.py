import json
from pathlib import Path
import unittest
from unittest.mock import patch

from gaia_rl._native import Environment
from current_actions.conservation import blocked
from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from research_plans.teacher import best_index
from resource_plans.teacher import ResourcePlanTeacher
from resource_plans.funding import funded_paths


def root(decision):
    data = json.loads((Path(__file__).parent/'fixtures/xenos126.json').read_text())
    env = Environment(data['seed'], 2000)
    for action in data['actions'][:decision]:
        snapshot = json.loads(env.snapshot_json())
        i = next(i for i, c in enumerate(snapshot['candidates']) if c['action'] == action)
        env.step(snapshot['decision_id'], i)
    return env, json.loads(env.snapshot_json())


class NativeConservationTests(unittest.TestCase):
    def test_xenos126_station_conversion_is_legal_but_not_allowed_by_teacher_or_funding(self):
        env, s = root(35)
        original = env.snapshot_json()
        indices = [i for i, c in enumerate(s['candidates']) if c['action'].get('kind') == 'QicToOre']
        self.assertTrue(indices)
        for teacher in (CurrentActionTeacher().bind(env), CurrentContextTeacher().bind(env)):
            scores = teacher.rank(s)
            self.assertTrue(all(blocked(scores[i]) for i in indices))
            self.assertNotIn(best_index(scores, range(len(scores))), indices)
        paths, _ = funded_paths(env, s,
            lambda a: a['type'] == 'Upgrade' and a.get('to') == 'TradingStation',
            {'ore': 2, 'credits': 6})
        self.assertFalse(any(p['first'] in indices for p in paths))
        self.assertEqual(env.snapshot_json(), original)

    def test_plan_bonus_cannot_override_the_conversion_prohibition(self):
        env, s = root(35)
        forbidden = next(i for i, c in enumerate(s['candidates']) if c['action'].get('kind') == 'QicToOre')
        passing = next(i for i, c in enumerate(s['candidates']) if c['action']['type'] == 'Pass')
        def result(env, snapshot, scores, route):
            ordinary = route.name == 'current-choice'
            return {'first': passing if ordinary else forbidden, 'complete': True,
                    'value': 1 if ordinary else 99999}
        teacher = ResourcePlanTeacher().bind(env)
        with patch('resource_plans.teacher.run_route', side_effect=result):
            scores = teacher.rank(s)
        self.assertTrue(blocked(scores[forbidden]))
        self.assertEqual(best_index(scores, range(len(scores))), passing)

    def test_native_academy_exception_spends_the_exact_ore_and_cannot_detour(self):
        env, s = root(160)
        original = env.snapshot_json()
        index = next(i for i, c in enumerate(s['candidates']) if c['action'].get('kind') == 'QicToOre')
        teacher = CurrentContextTeacher().bind(env)
        self.assertFalse(blocked(teacher.rank(s)[index]))
        branch = env.fork(s['decision_id'], index)
        after = json.loads(branch.snapshot_json())
        teacher.bind(branch)
        scores = teacher.rank(after)
        eligible = [c['action'] for c, score in zip(after['candidates'], scores) if not blocked(score)]
        self.assertTrue(eligible)
        self.assertTrue(all(a['type'] == 'Upgrade' and isinstance(a.get('to'), dict)
                            and 'Academy' in a['to'] for a in eligible))
        chosen = best_index(scores, range(len(scores)))
        self.assertEqual(after['candidates'][chosen]['action']['tech_tile_choice']['tile'], 4)
        branch.step(after['decision_id'], chosen)
        end = json.loads(branch.snapshot_json())['state']['players'][2]
        self.assertEqual(s['state']['players'][2]['resources']['ore'], 5)
        self.assertEqual(after['state']['players'][2]['resources']['ore'], 6)
        # Native pays six ore first, then the acquired standard tile 4 returns one.
        self.assertEqual(end['resources']['ore'], 1)
        self.assertEqual(end['resources']['credits'], after['state']['players'][2]['resources']['credits'] - 6)
        self.assertEqual(env.snapshot_json(), original)


if __name__ == '__main__':
    unittest.main()
