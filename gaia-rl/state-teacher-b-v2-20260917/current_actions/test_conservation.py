import copy
import unittest

from action_purpose.test_teacher import FakeEnv, action, node
from current_actions.conservation import Conservation, blocked, critical_paths
from research_plans.teacher import best_index
from current_actions.test_teacher import SimpleTeacher


class ConservationTests(unittest.TestCase):
    def scenario(self, target, *, count=1, ore=5):
        convert = {**action('QicToOre'), 'count': count}
        skip = {'type': 'Pass'}
        before = node([convert, skip], [90, 2], ore=ore, credits=6, qic=3)
        after = node([target, skip], [50, 2], ore=ore+count, credits=6, qic=3-count)
        after['decision_id'] = 1
        return before, after, FakeEnv(before, {0: FakeEnv(after)})

    def test_credit_liquidations_blocked_including_batches_and_round_six(self):
        for kind in ('OreToCredit', 'KnowledgeToCredit'):
            for count in (1, 3):
                s = node([{**action(kind), 'count': count}, {'type': 'Pass'}], [90, 2], rnd=6)
                scores = Conservation().protect(None, s, [(90, ''), (2, '')])
                self.assertTrue(blocked(scores[0]))
                self.assertEqual(best_index(scores, range(2)), 1)

    def test_mine_station_lab_and_speculative_plan_do_not_justify_qic(self):
        for target in ({'type': 'Build', 'coord': '0,0'},
                       {'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'},
                       {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab'}):
            s, _, env = self.scenario(target)
            original = copy.deepcopy(s)
            self.assertFalse(critical_paths(env, s, 0))
            self.assertTrue(blocked(Conservation().protect(env, s, [(999, 'plan'), (2, '')])[0]))
            self.assertEqual(original, s)

    def test_exact_missing_ore_enables_academy_and_commits_only_that_followup(self):
        target = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}}
        s, after, env = self.scenario(target)
        guard = Conservation()
        self.assertFalse(blocked(guard.protect(env, s, [(90, ''), (2, '')])[0]))
        # A later plan bonus/pass cannot redirect the ore to ordinary expansion.
        scores = guard.protect(env.branches[0], after, [(50, ''), (999, 'other plan')])
        self.assertEqual(best_index(scores, range(2)), 0)
        self.assertTrue(blocked(scores[1]))
        self.assertEqual(scores, guard.protect(env.branches[0], after, [(50, ''), (999, 'other plan')]))

    def test_excess_batch_and_already_affordable_academy_not_exceptions(self):
        target = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Qic'}}
        for count, ore in ((2, 5), (1, 6)):
            s, _, env = self.scenario(target, count=count, ore=ore)
            self.assertFalse(critical_paths(env, s, 0))
        s, _, env = self.scenario(target)
        s['candidates'].append({'action': target})
        self.assertFalse(critical_paths(env, s, 0))

    def test_pi_exception_and_missing_native_proof(self):
        target = {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'}
        s, _, env = self.scenario(target, ore=3)
        self.assertTrue(critical_paths(env, s, 0))
        self.assertFalse(critical_paths(None, s, 0))
        env.branches[0].snapshot['player'] = 1
        self.assertFalse(critical_paths(env, s, 0))

    def test_power_to_credit_burn_and_xenos_token_recovery_unchanged(self):
        s = node([action(k) for k in ('PowerToCredit', 'BurnPower', 'OreToPowerBowl3')], [1, 2, 3])
        scores = [(1, 'a'), (2, 'b'), (3, 'c')]
        self.assertEqual(Conservation().protect(None, s, scores), scores)

    def test_qic_to_ore_to_credit_chain_is_not_previewed_or_rewarded(self):
        target = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}}
        s, after, env = self.scenario(target)
        after['candidates'].append({'action': action('OreToCredit')})
        after['values'].append(999)
        # No fork for the forbidden second conversion: attempting it fails this test.
        scores = SimpleTeacher().bind(env).rank(s)
        self.assertFalse(blocked(scores[0]))
        self.assertIn('Academy', scores[0][1])

    def test_federation_exception_pays_ore_for_token_then_uses_native_federation(self):
        convert, token, skip = action('QicToOre'), action('OreToPowerBowl3'), {'type': 'Pass'}
        fed = {'type': 'FormFederation', 'hexes': ['0,0'], 'satellite_hexes': ['1,0']}
        before = node([convert, skip], [90, 2], ore=0, qic=2)
        after = node([token, skip], [90, 2], ore=1, qic=1)
        after['decision_id'] = 1
        last = node([fed, skip], [90, 2], ore=0, qic=1)
        last['decision_id'] = 2
        branch = FakeEnv(after, {0: FakeEnv(last)})
        env = FakeEnv(before, {0: branch})
        guard = Conservation()
        self.assertFalse(blocked(guard.protect(env, before, [(90, ''), (2, '')])[0]))
        self.assertTrue(blocked(guard.protect(branch, after, [(90, ''), (999, '')])[1]))
        self.assertTrue(blocked(guard.protect(branch.branches[0], last, [(90, ''), (999, '')])[1]))


if __name__ == '__main__':
    unittest.main()
