import copy
import json
from pathlib import Path
import unittest

from bgg_openings.fixed import TARGETS, MISSED_TARGET_COST, completed, boundary_loss, enforce
from current_actions.conservation import blocked
from four_factions.preparation import Policies
from research_plans.teacher import best_index


class FakeEnv:
    def __init__(self, snapshot, children=None):
        self.snapshot = snapshot
        self.children = children or {}

    def snapshot_json(self):
        return json.dumps(self.snapshot)

    def fork(self, decision, index):
        assert decision == self.snapshot['decision_id']
        return self.children[index]

    def preview_state_json(self, decision, index):
        return json.dumps(self.fork(decision, index).snapshot['state'])


def node(actions, *, faction='Xenos', rnd=2, power=0):
    player = {'faction': faction, 'structures': [], 'resources': {
        'ore': 2, 'credits': 2, 'knowledge': 0, 'qic': 0,
        'power': {'bowl1': 0, 'bowl2': 4, 'bowl3': power}}}
    return {'decision_id': 0, 'player': 0, 'state': {
        'round': rnd, 'phase': {'ActionPhase': {}}, 'players': [player]},
        'candidates': [{'action': a} for a in actions]}


class FixedTests(unittest.TestCase):
    def test_exact_science_academy_and_minimum_mines_not_forced_pass(self):
        for faction, target in TARGETS.items():
            core = {'Academy': target} if target == 'Science' else target
            p = {'faction': faction, 'structures': [{'kind': core}, {'kind': 'Mine'}, {'kind': 'Mine'}]}
            self.assertTrue(completed(p))
            p['structures'].append({'kind': 'Mine'})
            self.assertTrue(completed(p))
            if target == 'Science':
                p['structures'][0]['kind'] = {'Academy': 'Qic'}
                self.assertFalse(completed(p))

    def test_miss_cost_is_once_at_round_boundary_not_native_vp(self):
        s = node([], rnd=1)['state']
        s['players'][0]['vp'] = 10
        before = copy.deepcopy(s)
        after = {**s, 'round': 2}
        self.assertEqual(boundary_loss(s, after, 0), MISSED_TARGET_COST)
        self.assertEqual(boundary_loss(s, s, 0), 0)
        self.assertEqual(boundary_loss(after, {**after, 'round': 3}, 0), 0)
        self.assertEqual(s, before)

    def test_idle_burn_blocked_even_if_delta_is_large_and_r6_unchanged(self):
        burn = {'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1}
        passing = {'type': 'Pass'}
        s = node([burn, passing])
        after = node([passing], power=1)
        env = FakeEnv(s, {0: FakeEnv(after)})
        result, _ = enforce(env, s, [(100, 'delta'), (0, 'pass')], {})
        self.assertTrue(blocked(result[0]))
        self.assertEqual(best_index(result, range(2)), 1)
        s['state']['round'] = 6
        result, _ = enforce(env, s, [(100, 'delta'), (0, 'pass')], {})
        self.assertFalse(blocked(result[0]))

    def test_minimum_burn_has_verified_spend_and_cannot_then_pass(self):
        burns = [{'type': 'FreeAction', 'kind': 'BurnPower', 'count': n} for n in (1, 2)]
        passing = {'type': 'Pass'}
        spend = {'type': 'PowerAction', 'id': 3}
        s = node([*burns, passing], power=3)
        a = node([spend, passing], power=4)
        b = node([spend, passing], power=5)
        end = node([passing], power=0)
        ea, eb = FakeEnv(a, {0: FakeEnv(end)}), FakeEnv(b, {0: FakeEnv(end)})
        env = FakeEnv(s, {0: ea, 1: eb})
        memory = {}
        result, _ = enforce(env, s, [(5, ''), (10, ''), (0, '')], memory)
        self.assertFalse(blocked(result[0]))
        self.assertTrue(blocked(result[1]))
        result, audit = enforce(ea, a, [(-5, ''), (100, '')], memory)
        self.assertEqual(best_index(result, range(2)), 0)
        self.assertEqual(audit['mode'], 'verified-burn-spend')

    def test_completed_opening_keeps_further_profitable_actions(self):
        s = node([{'type': 'ResearchAdvance', 'track': 'Navigation'}, {'type': 'Pass'}], rnd=1)
        s['state']['players'][0]['structures'] = [
            {'kind': {'Academy': 'Science'}}, {'kind': 'Mine'}, {'kind': 'Mine'}]
        result, audit = enforce(FakeEnv(s), s, [(3, 'research'), (0, 'pass')], {})
        self.assertEqual(best_index(result, range(2)), 0)
        self.assertTrue(audit['completed'])

    def test_unfunded_core_does_not_spend_its_ore_on_an_unrelated_mine(self):
        s = node([{'type': 'Build', 'coord': '1,0'}, {'type': 'Pass'}], rnd=1)
        p = s['state']['players'][0]
        p['structures'] = [{'hex': '0,0', 'kind': 'ResearchLab'}]
        p['resources'].update(ore=1, credits=10)
        after = copy.deepcopy(s)
        after['state']['players'][0]['structures'].append({'hex': '1,0', 'kind': 'Mine'})
        after['state']['players'][0]['resources'].update(ore=0, credits=8)
        env = FakeEnv(s, {0: FakeEnv(after), 1: FakeEnv(s)})
        result, audit = enforce(env, s, [(999, 'mine'), (0, 'pass')], {})
        self.assertTrue(blocked(result[0]))
        self.assertEqual(audit['mode'], 'no-funded-progress-found')

    def test_factory_enables_only_explicit_new_config_not_old_sessions(self):
        from coaching.server import teacher_factory
        config = {'seed': 'test', 'delta_factions': []}
        self.assertFalse(teacher_factory(config)([], {}).fixed_openings)
        self.assertTrue(teacher_factory({**config, 'fixed_openings': True})([], {}).fixed_openings)


class NativeFixedTests(unittest.TestCase):
    def test_burn_conversion_qic_chain_completes_core_without_cash_detour(self):
        from gaia_rl import Environment
        data = json.loads((Path(__file__).parent/'fixtures/burn-core-funding.json').read_text())
        env = Environment(data['seed'], 2000)
        for action in data['actions']:
            s = json.loads(env.snapshot_json())
            env.step(s['decision_id'], next(i for i, c in enumerate(s['candidates']) if c == action))
        actor = json.loads(env.snapshot_json())['player']
        policy = Policies(fixed_openings=True, delta_factions=('HadschHallas', 'Taklons'))
        actions = []
        for _ in range(4):
            s = json.loads(env.snapshot_json())
            scores = policy.rank(env, s)
            i = best_index(scores, range(len(scores)))
            actions.append(s['candidates'][i]['action'])
            env.step(s['decision_id'], i)
        self.assertEqual([a.get('kind') for a in actions[:3]], ['BurnPower', 'PowerToOre', 'QicToOre'])
        self.assertEqual([a['count'] for a in actions[:3]], [1, 1, 1])
        self.assertEqual(actions[-1]['to'], {'Academy': 'Science'})
        self.assertTrue(policy.fixed_audit['next_mine_funded'])
        for _ in range(64):
            s = json.loads(env.snapshot_json())
            if s['player'] == actor and 'ActionPhase' in s['state']['phase']:
                break
            i = next((i for i, c in enumerate(s['candidates']) if c['action']['type'] == 'Pass'), 0)
            env.step(s['decision_id'], i)
        scores = policy.rank(env, s)
        i = best_index(scores, range(len(scores)))
        mines = sum(v['kind'] == 'Mine' for v in s['state']['players'][actor]['structures'])
        env.step(s['decision_id'], i)
        end_player = json.loads(env.snapshot_json())['state']['players'][actor]
        # A native booster build is also a paid mine; do not require the plain
        # Build spelling instead of checking the actual approved outcome.
        self.assertEqual(sum(v['kind'] == 'Mine' for v in end_player['structures']), mines+1)
        self.assertTrue(completed(end_player))

    def test_last_mine_cost_is_preserved_by_actual_academy_technology_choice(self):
        from gaia_rl import Environment
        data = json.loads((Path(__file__).parent/'fixtures/last-mine-budget.json').read_text())
        env = Environment(data['seed'], 2000)
        seen = set()
        for n, action in enumerate(data['actions']):
            s = json.loads(env.snapshot_json())
            if n in (45, 49):
                policy = Policies(fixed_openings=True, delta_factions=('HadschHallas', 'Taklons'))
                scores = policy.rank(env, s)
                index = best_index(scores, range(len(scores)))
                self.assertTrue(policy.fixed_audit['next_mine_funded'])
                chosen = s['candidates'][index]['action']
                self.assertEqual(chosen['to'], {'Academy': 'Science'})
                branch = env.fork(s['decision_id'], index)
                actor = s['player']
                # Native legality proof only: skip other players, not a match result.
                for _ in range(64):
                    after = json.loads(branch.snapshot_json())
                    if after['player'] == actor and 'ActionPhase' in after['state']['phase']:
                        break
                    passing = next((j for j, c in enumerate(after['candidates'])
                                    if c['action']['type'] == 'Pass'), 0)
                    branch.step(after['decision_id'], passing)
                else:
                    self.fail('No next actor turn in native proof')
                ranks = policy.rank(branch, after)
                mine = best_index(ranks, range(len(ranks)))
                self.assertEqual(after['candidates'][mine]['action']['type'], 'Build')
                branch.step(after['decision_id'], mine)
                self.assertTrue(completed(json.loads(branch.snapshot_json())['state']['players'][actor]))
                self.assertEqual(json.loads(env.snapshot_json()), s)
                seen.add(n)
            env.step(s['decision_id'], next(i for i, c in enumerate(s['candidates']) if c == action))
        self.assertEqual(seen, {45, 49})

    def test_expired_reserve_still_prioritizes_a_real_core_upgrade(self):
        import time
        from four_factions.quick import fallback
        from four_factions.test_preparation import root
        env, s = root()
        result = fallback(env, s, {}, deadline=time.monotonic()-1, fixed_openings=True)
        self.assertEqual(s['candidates'][result['index']]['action']['type'], 'Upgrade')
        self.assertEqual(result['fixed_opening']['target'], 'PlanetaryInstitute')

    def test_recorded_preparation_instead_of_pass_and_minimum_qic(self):
        from gaia_rl import Environment
        data = json.loads((Path(__file__).parent/'fixtures/coached-r1.json').read_text())
        env = Environment(data['seed'], 2000)
        expected = {57: ('PowerAction', None), 65: ('ResearchAdvance', None),
                    69: ('FreeAction', 'QicToOre')}
        checked = set()
        for n, action in enumerate(data['actions']):
            s = json.loads(env.snapshot_json())
            if n in expected:
                original = env.snapshot_json()
                policy = Policies(fixed_openings=True, delta_factions=('HadschHallas', 'Taklons'))
                ranks = policy.rank(env, s)
                index = best_index(ranks, range(len(ranks)))
                chosen = s['candidates'][index]['action']
                self.assertEqual((chosen['type'], chosen.get('kind')), expected[n])
                if n == 69:
                    self.assertEqual(chosen['count'], 1)
                self.assertEqual(env.snapshot_json(), original)
                checked.add(n)
            index = next(i for i, c in enumerate(s['candidates']) if c == action)
            env.step(s['decision_id'], index)
        self.assertEqual(checked, set(expected))

    def test_native_fixed_core_is_prioritized_over_pass_without_changing_menu(self):
        from four_factions.test_preparation import root
        env, s = root()
        original = env.snapshot_json()
        policy = Policies(fixed_openings=True)
        scores = policy.rank(env, s)
        index = best_index(scores, range(len(scores)))
        self.assertEqual(s['candidates'][index]['action']['type'], 'Upgrade')
        self.assertEqual(policy.fixed_audit['target'], 'PlanetaryInstitute')
        self.assertEqual(env.snapshot_json(), original)
        self.assertTrue(policy.clone().fixed_openings)


if __name__ == '__main__':
    unittest.main()
