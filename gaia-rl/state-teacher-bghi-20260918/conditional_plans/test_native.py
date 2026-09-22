import json
from pathlib import Path
import unittest

from gaia_rl._native import Environment
from current_actions.teacher import CurrentContextTeacher
from conditional_plans.routes import Plan, acquired, next_milestone
from conditional_plans.teacher import select_plan, run_plan


def replay_root(decision):
    data = json.loads((Path(__file__).parent/'fixtures/hadsch130.json').read_text())
    env = Environment(data['seed'], 2000)
    for action in data['actions'][:decision]:
        snapshot = json.loads(env.snapshot_json())
        index = next(i for i,c in enumerate(snapshot['candidates']) if c['action'] == action)
        env.step(snapshot['decision_id'], index)
    return env, json.loads(env.snapshot_json())


class NativeConditionalTests(unittest.TestCase):
    def test_continued_goal_uses_live_native_costs_without_touching_parent(self):
        from unittest.mock import patch
        from conditional_plans.teacher import PaiaPlanTeacher
        from research_plans.teacher import best_index
        env, s = replay_root(16)
        original = env.snapshot_json()
        teacher = PaiaPlanTeacher().bind(env)
        teacher.selected_plan = Plan('PI', institute='-4,-1', repeat_rebellion=True)
        teacher.planning_round = s['state']['round']
        teacher.planning_decision = 0
        with patch.object(teacher, 'evaluate_plans', side_effect=AssertionError('full replan')):
            scores = teacher.rank(s)
        index = best_index(scores, range(len(scores)))
        action = s['candidates'][index]['action']
        self.assertEqual((action['type'], action['coord'], action['to']),
                         ('Upgrade', '-4,-1', 'TradingStation'))
        _, need = next_milestone(s, teacher.selected_plan)
        after = json.loads(env.fork(s['decision_id'], index).snapshot_json())
        for resource in ('ore', 'credits'):
            self.assertEqual(s['state']['players'][2]['resources'][resource]
                             - after['state']['players'][2]['resources'][resource], need[resource])
        self.assertTrue(teacher.plan_history[-1]['continued'])
        self.assertEqual(original, env.snapshot_json())

    def test_pi_route_first_action_is_a_paid_site_specific_station(self):
        env, s = replay_root(16)
        original = env.snapshot_json()
        self.assertEqual(s['player'], 2)
        self.assertFalse(any(c['action'].get('kind') == 'CreditsToQic' for c in s['candidates']))
        plan = Plan('PI', institute='-4,-1', repeat_rebellion=True)
        index = select_plan(env, s, CurrentContextTeacher().rank(s), plan)
        action = s['candidates'][index]['action']
        self.assertEqual(action['type'], 'Upgrade')
        self.assertEqual(action['coord'], '-4,-1')
        self.assertEqual(action['to'], 'TradingStation')
        branch = env.fork(s['decision_id'], index)
        after = json.loads(branch.snapshot_json())
        pred, need = next_milestone(s, plan)
        self.assertTrue(pred(action))
        for resource in ('ore', 'credits'):
            self.assertEqual(s['state']['players'][2]['resources'][resource] -
                             after['state']['players'][2]['resources'][resource], need[resource])
        self.assertEqual(original, env.snapshot_json())

    def test_deployed_gaiaformer_is_not_an_acquired_colony(self):
        env, s = replay_root(133)
        original = env.snapshot_json()
        plan = Plan('Gaia-colony', gaia_coord='-3,-4')
        self.assertEqual(s['state']['board']['hexes']['-3,-4']['planet']['owner'], 2)
        self.assertFalse(acquired(s, 2, plan))
        # At this point another player acts; inspect our milestone without skipping a turn.
        own = {**s, 'player': 2}
        pred, _ = next_milestone(own, plan)
        self.assertTrue(pred({'type': 'Pass'}))
        self.assertFalse(pred({'type': 'Build', 'coord': '-3,-4'}))
        self.assertEqual(original, env.snapshot_json())

    def test_paid_pi_unlocks_qic_and_rebellion_resets_on_real_incomes(self):
        env, s = replay_root(16)
        original = env.snapshot_json()
        plan = Plan('PI-Rebellion', institute='-4,-1', repeat_rebellion=True)
        result = run_plan(env, s, CurrentContextTeacher().rank(s), plan)
        self.assertTrue(result['complete'])
        self.assertEqual([income['round'] for income in result['incomes']], [2, 3])
        uses = [a for a in result['actions'] if a['action']['type'] == 'RebellionGainTechTile']
        self.assertEqual([a['round'] for a in uses], [1, 2])
        pi_index = next(i for i,a in enumerate(result['actions']) if a['action'].get('to') == 'PlanetaryInstitute')
        for i,a in enumerate(result['actions']):
            if a['action'].get('kind') == 'CreditsToQic':
                self.assertGreater(i, pi_index)
                self.assertEqual(a['resources_before']['credits'] - a['resources_after']['credits'], 4*a['action']['count'])
            if a['action']['type'] == 'RebellionGainTechTile':
                self.assertEqual(a['resources_before']['qic'] - a['resources_after']['qic'], 3)
        self.assertEqual(original, env.snapshot_json())

    def test_gaia_forecast_reaches_a_paid_mine_after_a_real_round_transition(self):
        env, s = replay_root(16)
        original = env.snapshot_json()
        result = run_plan(env, s, CurrentContextTeacher().rank(s), Plan('Gaia-colony', gaia_coord='-3,-4'))
        self.assertTrue(result['complete'])
        self.assertTrue(result['goal_acquired'])
        formation = next(a for a in result['actions'] if a['action']['type'] == 'GaiaFormation' and a['action']['coord'] == '-3,-4')
        mine = next(a for a in result['actions'] if a['action']['type'] == 'Build' and a['action']['coord'] == '-3,-4')
        self.assertGreater(mine['round'], formation['round'])
        self.assertEqual(mine['resources_before']['ore'] - mine['resources_after']['ore'], 1)
        self.assertEqual(mine['resources_before']['credits'] - mine['resources_after']['credits'], 2)
        self.assertEqual(original, env.snapshot_json())

    def test_existing_academy_does_not_satisfy_a_missing_pi_pair(self):
        env, s = replay_root(102)
        original = env.snapshot_json()
        plan = Plan('pair', institute='-11,4', academy='Science', academy_coord='-10,6')
        self.assertFalse(acquired(s, 2, plan))
        pred, need = next_milestone({**s, 'player': 2}, plan)
        self.assertTrue(pred({'type': 'Upgrade', 'coord': '-11,4', 'to': 'PlanetaryInstitute'}))
        self.assertEqual(need, {'ore': 4, 'credits': 6})
        self.assertEqual(original, env.snapshot_json())


if __name__ == '__main__':
    unittest.main()
