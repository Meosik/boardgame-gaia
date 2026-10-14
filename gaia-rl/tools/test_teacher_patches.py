"""symmetric_pass: exact against native passes, and only unpassed action-phase states change."""
import json
import unittest
from unittest import mock

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


class BoosterLookaheadTests(unittest.TestCase):
    def test_booster_decisions_propose_other_boosters_and_flag_the_horizon(self):
        tp.install_booster_lookahead()
        from four_factions.preparation import Policies, PolicyCache, goals_for, best_index
        seen = 0
        for _, snapshot in play(rounds=2):
            state = snapshot['state']
            if not any(tp._booster_choice(c) for c in snapshot['candidates']):
                continue
            from gaia_rl import Environment
            env = Environment.from_state_json(json.dumps(state), 2000)
            fresh = json.loads(env.snapshot_json())
            scores = Policies({}, cache=PolicyCache(), shared_factions=True).rank(env, fresh)
            goals = goals_for(fresh, shared_factions=True)
            control = best_index(scores, range(len(scores)))
            if tp._booster_choice(fresh['candidates'][control]):
                self.assertEqual(tp.decision_horizon(fresh), 2)
                boosters = [g for g in goals if g.name.startswith('booster-')]
                self.assertTrue(boosters and goals[:len(boosters)] == boosters)
                self.assertTrue(all(tp._booster_choice(fresh['candidates'][g.first]) for g in boosters))
                seen += 1
            else:
                self.assertIsNone(tp.decision_horizon(fresh))
        self.assertGreater(seen, 0)


class ResearchFocusTests(unittest.TestCase):
    def order(self, **levels):
        tracks = {t: 0 for t in tp.TRACK_KEYS.values()} | levels
        return sorted(tracks, key=tp._focus_key(tracks))

    def test_navigation_leads_only_until_level_two(self):
        self.assertEqual(self.order(ai=1)[0], 'navigation')
        self.assertEqual(self.order(navigation=1, ai=1)[0], 'navigation')
        after = self.order(navigation=2, ai=1)
        self.assertEqual((after[0], after[-1]), ('ai', 'navigation'))

    def test_a_track_at_level_two_is_the_focus(self):
        self.assertEqual(self.order(navigation=3, economy=2, ai=1)[:2], ['economy', 'navigation'])


class ShipWhenTests(unittest.TestCase):
    def order(self, round_):
        return sorted(('Twilight', 'Eclipse', 'TFMars', 'Rebellion'), key=lambda s: tp._ship_when_key(s, round_))

    def test_ship_order_by_round(self):
        self.assertEqual(self.order(1), ['Rebellion', 'Twilight', 'TFMars', 'Eclipse'])
        self.assertEqual(self.order(2), ['Rebellion', 'Twilight', 'Eclipse', 'TFMars'])
        self.assertEqual(self.order(3), ['Twilight', 'Eclipse', 'Rebellion', 'TFMars'])

    def test_scores_are_handed_out_in_that_order(self):
        snapshot = {'player': 0, 'state': {'round': 1, 'phase': {'ActionPhase': {}}},
                    'candidates': [{'action': {'type': 'ExploreSpaceship', 'ship': 'Eclipse'}},
                                   {'action': {'type': 'ExploreSpaceship', 'ship': 'Rebellion'}},
                                   {'action': {'type': 'Pass', 'booster_id': 1}}]}
        scores = [(5.0, 'a'), (3.0, 'b'), (0.0, 'c')]
        lifted = tp.ship_when_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [3.0, 5.0, 0.0])


class ResearchWhenTests(unittest.TestCase):
    def test_groups_hold_moves_that_differ_only_in_the_track(self):
        def lab(tile, track):
            return {'action': {'type': 'Upgrade', 'coord': '3,-1', 'to': 'ResearchLab',
                               'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': track}}}
        candidates = [{'action': {'type': 'ResearchAdvance', 'track': 'Economy'}},
                      {'action': {'type': 'ResearchAdvance', 'track': 'Science'}},
                      lab(5, 'Terraforming'), lab(5, 'Economy'), lab(10, None), lab(2, 'Economy'),
                      {'action': {'type': 'Pass', 'booster_id': 1}}]
        groups = sorted(tp._when_groups(candidates).values(), key=lambda g: min(g.values()))
        self.assertEqual(groups, [{'Economy': 0, 'Science': 1}, {'Terraforming': 2, 'Economy': 3},
                                  {'Economy': 5}])


class ResearchDefendTests(unittest.TestCase):
    def track(self, new, held, *, kinds=(), structures=(), round_=1, unhurried=None, sure=False, **levels):
        tracks = {t: 0 for t in tp.TRACK_KEYS.values()} | levels
        state = {'round': round_, 'players': [{'faction': 'Taklons', 'research_tracks': tracks,
                                               'structures': list(structures)}]}

        def counts(state, player, contested=True):
            return (new, held) if contested or unhurried is None else unhurried
        with mock.patch.object(tp, '_defend_counts', side_effect=counts), \
                mock.patch.object(tp, '_science_sure', return_value=sure), \
                mock.patch.object(tp, '_in_reach', return_value=dict(enumerate(kinds))):
            return tp.research_defend_track(state, 0)

    def test_navigation_needs_two_new_planets(self):
        self.assertEqual(self.track(2, 0), 'Navigation')
        self.assertEqual(self.track(1, 0), 'Economy')

    def test_two_planets_already_in_reach_mean_economy(self):
        self.assertEqual(self.track(3, 2), 'Economy')

    def test_an_academy_means_economy(self):
        self.assertEqual(self.track(3, 0, structures=[{'kind': 'Academy', 'hex': '0,0'}]), 'Economy')

    def test_gaia_and_economy_branches_are_kept(self):
        self.assertEqual(self.track(0, 0, kinds=('Asteroid',)), 'GaiaProject')
        self.assertIsNone(self.track(0, 0, economy=2))

    def test_without_a_neighbour_economy_comes_before_navigation(self):
        self.assertEqual(self.track(0, 0, unhurried=(2, 0)), 'Economy')
        self.assertEqual(self.track(0, 0, unhurried=(2, 0), science=2), 'Economy')
        self.assertEqual(self.track(0, 0, unhurried=(2, 0), economy=2, round_=3), 'Navigation')
        self.assertIsNone(self.track(0, 0, unhurried=(2, 0), round_=2))

    def test_a_sure_third_federation_means_science_up_to_four(self):
        self.assertEqual(self.track(0, 0, unhurried=(2, 0), sure=True), 'Science')
        self.assertEqual(self.track(0, 0, unhurried=(2, 0), sure=True, science=3, round_=3), 'Science')
        self.assertEqual(self.track(0, 0, unhurried=(2, 0), sure=True, science=4, round_=3), 'Navigation')
        self.assertIsNone(self.track(0, 0, sure=True, round_=2))
        self.assertEqual(self.track(2, 0, sure=True), 'Navigation')

    def test_the_hurried_case_and_the_other_branches_are_round_one_only(self):
        self.assertIsNone(self.track(2, 0, unhurried=(0, 0), round_=2, kinds=('Asteroid',)))

    def test_ring_gap_wraps(self):
        self.assertEqual(tp._ring_gap('Terra', 'Ice'), 1)
        self.assertEqual(tp._ring_gap('Volcanic', 'Desert'), 1)
        self.assertEqual(tp._ring_gap('Terra', 'Swamp'), 3)
        self.assertIsNone(tp._ring_gap('Terra', 'Gaia'))

    def test_groups_chain_within_two_hexes(self):
        groups = tp._groups(['0,0', '2,0', '6,0', '4,0'])
        self.assertEqual(groups, [{'0,0', '2,0', '4,0', '6,0'}])
        self.assertEqual(len(tp._groups(['0,0', '3,0'])), 2)
