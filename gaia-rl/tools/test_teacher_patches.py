"""symmetric_pass: exact against native passes, and only unpassed action-phase states change."""
import json
import unittest

import fast_teacher
fast_teacher.install()
import budget_teacher
from gaia_rl import Environment
import teacher_patches as tp

SEED = 'geo-quartet-24'   # Taklons, Geodens, Xenos, Terrans


def play(rounds=2):
    """Yield (env, snapshot) for every decision of an easy-level game up to `rounds`."""
    from four_factions.timed import TimedPreparationTeacher
    budget_teacher.install(0)
    budget_teacher.set_horizon(2)
    env = Environment(SEED, 2000)
    teacher = TimedPreparationTeacher(SEED, bgg_openings=True, shared_factions=True)
    teacher.bind(env)
    snapshot = json.loads(env.snapshot_json())
    while not env.is_terminal() and snapshot['state']['round'] <= rounds:
        yield env, snapshot
        decision_id, index = teacher.choose(snapshot)
        before = snapshot
        env.step(decision_id, index)
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, index, snapshot)


class SymmetricPassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = [(None, s) for _, s in play()]

    def test_booster_pass_vp_matches_native_passes(self):
        checked = 0
        for _, snapshot in self.states:
            player = snapshot['state']['players'][snapshot['player']]
            if player['advanced_tech_tiles']:
                continue
            for index, candidate in enumerate(snapshot['candidates']):
                if candidate.get('action', {}).get('type') == 'Pass':
                    env = Environment.from_state_json(json.dumps(snapshot['state']), 2000)
                    fresh = json.loads(env.snapshot_json())
                    self.assertEqual(fresh['candidates'], snapshot['candidates'])
                    env.step(fresh['decision_id'], index)
                    after = json.loads(env.snapshot_json())
                    gained = after['state']['players'][snapshot['player']]['vp']-player['vp']
                    self.assertEqual(tp.booster_pass_vp(snapshot['state'], player), gained)
                    checked += 1
                    break
        self.assertGreater(checked, 4)

    def test_only_unpassed_action_phase_states_gain_the_pass_terms(self):
        from faction_teachers.profiles import profiles
        changed = unchanged = 0
        for _, snapshot in self.states:
            state = snapshot['state']
            for actor, player in enumerate(state['players']):
                home = profiles()[player['faction']].home
                delta = (tp.symmetric_potential(state, actor, home=home)
                         - tp._original(state, actor, home=home))
                if state['round'] >= 1 and not player['passed'] and tp._action_phase(state):
                    expected = tp.booster_pass_vp(state, player)+max(
                        (tp.booster_income_value(b) for b in state['boosters']), default=0)
                    self.assertAlmostEqual(delta, expected)
                    changed += 1
                else:
                    self.assertEqual(delta, 0)
                    unchanged += 1
        self.assertGreater(changed, 0)
        self.assertGreater(unchanged, 0)

    def test_factory_rebinds_every_user_of_potential(self):
        teacher = tp.symmetric_pass(SEED, bgg_openings=True, shared_factions=True)
        import four_factions.preparation as preparation
        import four_factions.teacher as native
        import four_factions.quick as quick
        for module in (preparation, native, quick):
            self.assertIs(module.potential, tp.symmetric_potential)
        self.assertTrue(hasattr(teacher, 'choose'))


if __name__ == '__main__':
    unittest.main()
