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


class GeodensGuideTests(unittest.TestCase):
    def test_geodens_proposals_put_cheap_new_types_first_and_leave_others_alone(self):
        from faction_teachers.paths import goals as tree_goals
        checked = 0
        for _, snapshot in play(rounds=3):
            state = snapshot['state']
            player = state['players'][snapshot['player']]
            if 'ActionPhase' not in state['phase']:
                continue
            original = tree_goals(snapshot)
            ordered = tp.geodens_goals(snapshot, original)
            if player['faction'] != 'Geodens':
                self.assertIs(ordered, original)
                continue
            self.assertTrue(set(original) <= set(ordered))
            costs = [tp._colony_cost(state, player, tp._target_coord(g)) for g in ordered if tp._target_coord(g)]
            self.assertEqual(costs, sorted(costs))
            checked += 1
        self.assertGreater(checked, 0)

    def test_only_geodens_rollouts_use_the_second_income_boundary(self):
        import four_factions.preparation as preparation
        states = {s['state']['players'][s['player']]['faction']: s for _, s in play(rounds=1)}
        budget_teacher.set_horizon(1)
        tp.install_geodens_guide()
        seen = {}
        configured = preparation.reached_horizon

        def fake(env, snapshot, *args, **kwargs):
            seen[snapshot['state']['players'][snapshot['player']]['faction']] = preparation.reached_horizon
            return {}
        preparation.rollout.__wrapped__, original = fake, preparation.rollout.__wrapped__
        try:
            for faction, snapshot in states.items():
                preparation.rollout(None, snapshot)
        finally:
            preparation.rollout.__wrapped__ = original
        self.assertIs(seen['Geodens'], configured.__wrapped__)
        self.assertIs(seen['Taklons'], configured)
        self.assertIs(preparation.reached_horizon, configured)


class CalibratedValueTests(unittest.TestCase):
    def test_unit_weights_reproduce_the_symmetric_potential(self):
        import json
        import tempfile
        from extract_dataset import potential_terms, pass_terms
        from faction_teachers.profiles import profiles
        states = [s for _, s in play(rounds=2) if 'ActionPhase' in s['state']['phase']]
        keys = set()
        for snapshot in states:
            for i, p in enumerate(snapshot['state']['players']):
                keys |= set(potential_terms(snapshot['state'], i, profiles()[p['faction']].home))
                keys |= set(pass_terms(snapshot['state'], i))
        with tempfile.NamedTemporaryFile('w', suffix='.json') as weights:
            json.dump({'rounds': {str(r): dict.fromkeys(keys, 1.0) for r in range(1, 7)}}, weights)
            weights.flush()
            tp.install_calibrated_value(weights.name)
        for snapshot in states:
            for i, p in enumerate(snapshot['state']['players']):
                home = profiles()[p['faction']].home
                self.assertAlmostEqual(tp.calibrated_potential(snapshot['state'], i, home=home),
                                       tp.symmetric_potential(snapshot['state'], i, home=home), places=9)


class FamilyRotationTests(unittest.TestCase):
    def test_rotation_keeps_every_goal_and_varies_the_first_family(self):
        from four_factions.preparation import goals_for, interleave_families
        firsts, checked = set(), 0
        for _, snapshot in play(rounds=3):
            if 'ActionPhase' not in snapshot['state']['phase']:
                continue
            original = goals_for(snapshot, shared_factions=True)
            rotated = tp.rotate_families(snapshot, original)
            self.assertCountEqual(rotated, original)
            faction = snapshot['state']['players'][snapshot['player']]['faction']
            if faction == 'Geodens':
                self.assertEqual(rotated, original)
            elif rotated:
                firsts.add(interleave_families(rotated, lambda g: g.family)[0].family)
                checked += 1
        self.assertGreater(checked, 10)
        self.assertGreater(len(firsts), 2)
