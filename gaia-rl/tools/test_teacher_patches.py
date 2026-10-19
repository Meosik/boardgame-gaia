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


class OpeningBudgetTests(unittest.TestCase):
    """opening_budget keeps the ore and credits the round-1 target's upgrades still cost (B14 §4,
    IR01: academy first, the mine last and only with 1 ore 1 credit to spare)."""
    def setUp(self):
        self.saved = dict(tp._guide)
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def test_chain_costs_count_only_the_upgrades_still_owed(self):
        from bgg_openings.catalog import parse_buildings as b
        self.assertEqual(tp.chain_costs(b('2M'), b('1AC+2M'), 'Geodens'), (11, 17))
        self.assertEqual(tp.chain_costs(b('2M'), b('1AC+2M'), 'Geodens', ts_credits=3), (11, 14))
        self.assertEqual(tp.chain_costs(b('1TS+2M'), b('1AC+2M'), 'Geodens'), (9, 11))
        self.assertEqual(tp.chain_costs(b('1RL+2M'), b('1AC+2M'), 'Geodens'), (6, 6))
        self.assertEqual(tp.chain_costs(b('1AC+2M'), b('1AC+2M'), 'Geodens'), (0, 0))
        self.assertEqual(tp.chain_costs(b('3M'), b('1RL+5M'), 'Xenos'), (5, 11))   # mines deferred
        self.assertEqual(tp.chain_costs(b('2M'), b('1PI+1TS+2M'), 'Geodens'), (8, 18))
        self.assertIsNone(tp.chain_costs(b('1PI+2M'), b('1AC+2M'), 'Terrans'))

    @staticmethod
    def snapshot(ore, credits, structures, candidates, qic=0, bowl3=0):
        player = {'faction': 'Geodens', 'resources': {'ore': ore, 'credits': credits, 'knowledge': 3,
                                                       'qic': qic, 'power': {'bowl3': bowl3}},
                  'structures': structures}
        return {'state': {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player],
                          'board': {'hexes': {}}},
                'player': 0, 'decision_id': 'd', 'candidates': [{'action': a} for a in candidates]}

    class Env:
        """fork(decision, i) returns the i-th prepared snapshot."""
        def __init__(self, after):
            self.after = after

        def fork(self, decision_id, index):
            text = json.dumps(self.after[index])
            return type('Fork', (), {'snapshot_json': staticmethod(lambda: text)})()

    def test_moves_that_break_the_budget_are_blocked_chain_upgrades_and_free_moves_are_not(self):
        from bgg_openings.catalog import parse_buildings
        from current_actions.conservation import blocked
        lab = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'ResearchLab', 'hex': '1,0'}]
        academy = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': {'Academy': 'Science'}, 'hex': '1,0'}]
        three = lab+[{'kind': 'Mine', 'hex': '2,0'}]
        before = self.snapshot(6, 15, lab, [
            {'type': 'Build', 'coord': '2,0'},
            {'type': 'Upgrade', 'coord': '1,0', 'to': {'Academy': 'Science'}},
            {'type': 'ResearchAdvance', 'track': 'Science'},
            {'type': 'PowerAction', 'id': 6, 'coord': '2,0'},
            {'type': 'FreeAction', 'kind': 'QicToOre', 'count': 1},
            {'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'},
            {'type': 'Pass', 'booster_id': 1}])
        after = [self.snapshot(5, 13, three, []),                      # the mine: 5 < 6 owed
                 self.snapshot(0, 9, academy, []),                      # the academy itself
                 self.snapshot(6, 15, lab, []),                         # research: nothing spent
                 self.snapshot(4, 15, three, []),                       # terraform + mine
                 self.snapshot(7, 15, lab, []),                         # funding
                 self.snapshot(4, 9, [{'kind': 'TradingStation', 'hex': '0,0'}, lab[1]], []),
                 self.snapshot(6, 15, lab, [])]
        scores = [(10.0, 'mine'), (9.0, 'academy'), (8.0, 'research'), (7.0, 'power'),
                  (6.0, 'qic'), (5.0, 'second ts'), (1.0, 'pass')]
        target = parse_buildings('1AC+2M')
        masked = tp.opening_budget_scores(self.Env(after), before, scores, target, float('inf'))
        self.assertEqual([blocked(s) for s in masked], [True, False, False, True, False, True, False])
        self.assertIn('6 ore 6 credits', masked[0][1])
        # With ore to spare the mine stays: 8 - 1 = 7 >= 6.
        roomy = self.snapshot(8, 15, lab, [{'type': 'Build', 'coord': '2,0'}])
        masked = tp.opening_budget_scores(self.Env([self.snapshot(7, 13, three, [])]), roomy,
                                          scores[:1], target, float('inf'))
        self.assertFalse(blocked(masked[0]))
        # A QIC (1 → 1 ore) and bowl-III power (3 → 1 ore, 1 → 1 credit) count as payment: after
        # the mine 5 ore + 1 QIC pays the academy (066 p003 paid it with QIC→ore)...
        funded = self.snapshot(6, 15, lab, [{'type': 'Build', 'coord': '2,0'},
                                            {'type': 'PowerAction', 'id': 2, 'coord': '2,0'}], qic=1)
        after = [self.snapshot(5, 13, three, [], qic=1), self.snapshot(5, 13, three, [], qic=0)]
        masked = tp.opening_budget_scores(self.Env(after), funded, scores[:2], target, float('inf'))
        self.assertEqual([blocked(s) for s in masked], [False, True])   # ...spending the QIC does not
        powered = self.snapshot(6, 15, lab, [{'type': 'Build', 'coord': '2,0'}], bowl3=3)
        masked = tp.opening_budget_scores(self.Env([self.snapshot(5, 13, three, [], bowl3=3)]),
                                          powered, scores[:1], target, float('inf'))
        self.assertFalse(blocked(masked[0]))
        # Credits: 7 owed 6 after a 6-credit TS... power left after the ore gap pays credits too.
        tight = self.snapshot(6, 9, lab, [{'type': 'Build', 'coord': '2,0'}], bowl3=3)
        masked = tp.opening_budget_scores(self.Env([self.snapshot(5, 7, three, [], bowl3=3)]),
                                          tight, scores[:1], target, float('inf'))
        self.assertFalse(blocked(masked[0]))          # 5 ore + 3 power → 6 ore, 7 credits >= 6
        masked = tp.opening_budget_scores(self.Env([self.snapshot(5, 5, three, [], bowl3=3)]),
                                          tight, scores[:1], target, float('inf'))
        self.assertTrue(blocked(masked[0]))           # power used for ore, 5 credits < 6
        # Target reached, or not round 1: untouched.
        done = self.snapshot(0, 9, academy, [{'type': 'Build', 'coord': '2,0'}])
        one = scores[:1]
        self.assertIs(tp.opening_budget_scores(self.Env([]), done, one, target, float('inf')), one)
        before['state']['round'] = 2
        self.assertIs(tp.opening_budget_scores(self.Env(after), before, scores, target, float('inf')),
                      scores)

    def test_the_first_chain_step_mine_to_trading_station_is_never_budgeted(self):
        # 067/068 p001: Geodens 9 ore, 1 QIC, no bowl-III power, target 1AC+2M. After the 2-ore TS
        # the lab and academy still owe 9 ore 11 credits, more than 7 ore + 1 QIC — but the TS is
        # the chain's own first step, so it must stay open; only the new mine is budgeted.
        from bgg_openings.catalog import parse_buildings
        from current_actions.conservation import blocked
        mines = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'Mine', 'hex': '1,0'}]
        ts = [{'kind': 'TradingStation', 'hex': '0,0'}, mines[1]]
        before = self.snapshot(9, 15, mines, [
            {'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'},
            {'type': 'Build', 'coord': '2,0'}], qic=1)
        after = [self.snapshot(7, 9, ts, [], qic=1),
                 self.snapshot(8, 13, mines+[{'kind': 'Mine', 'hex': '2,0'}], [], qic=1)]
        masked = tp.opening_budget_scores(self.Env(after), before, [(10.0, 'ts'), (9.0, 'mine')],
                                          parse_buildings('1AC+2M'), float('inf'))
        self.assertEqual([blocked(s) for s in masked], [False, True])
        self.assertIn('11 ore', masked[1][1])

    def test_budget_guard_blocks_nothing_while_the_chain_cannot_be_paid(self):
        # 068 p001 Taklons: 7 ore, 1 QIC, no bowl-III power against TS 2 + RL 3 + AC 6 = 11 ore.
        from bgg_openings.catalog import parse_buildings
        from current_actions.conservation import blocked
        mines = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'Mine', 'hex': '1,0'}]
        before = self.snapshot(7, 15, mines, [{'type': 'Build', 'coord': '2,0'}], qic=1)
        after = [self.snapshot(6, 13, mines+[{'kind': 'Mine', 'hex': '2,0'}], [], qic=1)]
        scores = [(9.0, 'mine')]
        target = parse_buildings('1AC+2M')
        masked = tp.opening_budget_scores(self.Env(after), before, scores, target, float('inf'))
        self.assertTrue(blocked(masked[0]))                       # without the guard: reserved anyway
        tp._guide['budget_guard'] = True
        self.assertIs(tp.opening_budget_scores(self.Env(after), before, scores, target, float('inf')), scores)
        # 7 ore + 1 QIC + 9 power/3 = 11 ore and 20 credits >= 17 pay the chain: the mine is budgeted again.
        payable = self.snapshot(7, 20, mines, [{'type': 'Build', 'coord': '2,0'}], qic=1, bowl3=9)
        masked = tp.opening_budget_scores(self.Env([self.snapshot(6, 18, mines+[{'kind': 'Mine', 'hex': '2,0'}], [], qic=1, bowl3=9)]),
                                          payable, scores, target, float('inf'))
        self.assertTrue(blocked(masked[0]))

    def test_opening_release_hands_round_one_back_once_the_upgrades_are_built(self):
        import bgg_openings.planning as planning
        from bgg_openings.catalog import parse_buildings
        saved = planning.select_action
        self.addCleanup(setattr, planning, 'select_action', saved)
        planning.select_action = lambda env, snapshot, scores, target, policies, deadline: 0
        tp.install_opening_release()
        academy = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': {'Academy': 'Science'}, 'hex': '1,0'}]
        lab = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'ResearchLab', 'hex': '1,0'}]
        candidates = [{'type': 'Build', 'coord': '2,0'}, {'type': 'ExploreSpaceship', 'ship': 'Eclipse'}]
        scores = [(15.9, 'mine'), (17.1, 'ship')]
        target = parse_buildings('1AC+2M')
        done = self.snapshot(3, 9, academy, candidates)
        self.assertEqual(planning.select_action(None, done, scores, target, None, float('inf')), 1)
        owing = self.snapshot(6, 15, lab, candidates)
        self.assertEqual(planning.select_action(None, owing, scores, target, None, float('inf')), 0)

    def test_tile_track_reads_the_chosen_track_or_the_slot(self):
        state = {'round': 1, 'phase': {'ActionPhase': {}},
                 'research_board': {'tech_tile_slots': [9, 7, 8, 6, 4, 2, 3, 10, 5]},
                 'players': [{'faction': 'Geodens', 'tech_tiles': []}]}
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 4, 'advance_track': None}), 'Economy')
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 2, 'advance_track': None}), 'Science')
        self.assertIsNone(tp._tile_track(state, {'kind': 'Standard', 'tile': 10, 'advance_track': None}))
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 10, 'advance_track': 'Economy'}), 'Economy')

    def test_opt_in_factories_set_only_their_flags(self):
        # Built in subprocesses: a factory rebinds module-level functions for the whole process, which
        # would leak into the tests that run after this one. The flags are the opt-in parts that stay
        # after the 2026-10-19 pruning (stack-parts.md B); the base factory sets none of them.
        import os
        import subprocess
        import sys
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)}
        flags = "tp._guide['former_use'], tp._guide['opening_budget'], tp._guide['budget_guard'], " \
                "tp._guide['opening_release'], tp._guide['academy_economy'], tp._guide['research_when_land'], " \
                "tp._guide['track_income']"
        expected = {'guide_r1_charge3_lf_more_vm_lf_ts_ships': ['False']*6 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_former': ['True'] + ['False']*5 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_budget': ['False', 'True'] + ['False']*4 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_land': ['False']*5 + ['True', 'False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_income': ['False']*6 + ['sweet', 'False'],
                    # byfaction: the wrappers are installed, the module flags stay off, the table decides.
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction': ['False']*6 + ['False', 'True'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_byfaction_guide': ['False']*6 + ['False', 'True'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_fed': ['False']*6 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_tokens': ['False']*6 + ['False', 'False']}
        flags += ", tp._guide['byfaction']"
        for factory, want in expected.items():
            code = f"import teacher_patches as tp\ntp.{factory}({SEED!r})\nprint({flags})"
            out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                                 env=env).stdout
            self.assertEqual(out.split(), want, factory)

    def test_faction_parts_come_from_the_tables(self):
        # Base stack: only the faction parts of BASE_FACTION_PARTS; a faction not in the table has none.
        self.assertEqual(tp._faction_parts('Xenos'), set())
        self.assertEqual(tp._faction_parts('HadschHallas'), set())
        self.assertEqual(tp._faction_parts('Geodens'), {'geodens_guide', 'geodens_two_incomes', 'geodens_r1_research'})
        self.assertEqual(tp._faction_parts('Terrans'), {'terrans_gaia_late', 'track_income'})   # E18
        self.assertEqual(tp._faction_parts('Taklons'), {'brainstone_ships', 'taklons_pi_token'})
        self.assertTrue(tp._early_terrans_gaia({'round': 2, 'players': [{'faction': 'Terrans'}]}, 0))
        self.assertFalse(tp._early_terrans_gaia({'round': 2, 'players': [{'faction': 'Xenos'}]}, 0))
        # ships_byfaction adds the measured candidates and nothing for the others.
        tp._guide['byfaction'] = True                      # restored by setUp's cleanup
        self.assertEqual(tp._faction_parts('Terrans'), {'terrans_gaia_late', 'track_income'})
        self.assertEqual(tp._faction_parts('Geodens') - tp.BASE_FACTION_PARTS['Geodens'], {'former_use'})
        self.assertEqual(tp._faction_parts('Taklons') - tp.BASE_FACTION_PARTS['Taklons'],
                         {'opening_budget', 'budget_guard', 'opening_release'})
        self.assertEqual(tp._faction_parts('Xenos'), set())
        self.assertFalse(tp._part({'faction': 'Taklons'}, 'track_income'))
        for faction in ('Gleens', 'Ambas', 'Itars', 'Nevlas', 'Firaks', 'BalTaks', 'Ivits', 'Bescods', 'Lantids', 'HadschHallas'):
            self.assertEqual(tp._faction_parts(faction), {'track_set'}, faction)
        self.assertNotIn('track_set', tp._faction_parts('Terrans'))

    def test_track_set_orders_research_onto_the_faction_tracks_unless_a_rule_chose(self):
        tp._guide['byfaction'] = True                      # restored by setUp's cleanup
        player = {'faction': 'Gleens', 'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()}}
        snapshot = {'player': 0, 'state': {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'ResearchAdvance', 'track': 'Economy'}},
                                   {'action': {'type': 'ResearchAdvance', 'track': 'Navigation'}},
                                   {'action': {'type': 'Build', 'coord': '0,0'}}]}
        lifted = tp.track_set_scores(None, snapshot, [(5.0, 'a'), (3.0, 'b'), (9.0, 'c')])
        self.assertEqual([s[0] for s in lifted], [3.0, 5.0, 9.0])          # Gleens: Navigation over Economy, the mine untouched
        self.assertIn('track_set', lifted[1][1])
        lifted = tp.track_set_scores(None, snapshot, [(5.0, 'a; research when: Economy now'), (3.0, 'b'), (9.0, 'c')])
        self.assertEqual([s[0] for s in lifted], [5.0, 3.0, 9.0])          # a situational rule chose: untouched
        snapshot['state']['round'] = 6
        scores = [(5.0, 'a'), (3.0, 'b'), (9.0, 'c')]
        self.assertIs(tp.track_set_scores(None, snapshot, scores), scores)   # round 6 is free
        snapshot['state']['round'] = 2
        player['faction'] = 'Xenos'
        self.assertIs(tp.track_set_scores(None, snapshot, scores), scores)   # not a track_set faction
        tp._guide['byfaction'] = False
        player['faction'] = 'Gleens'
        self.assertIs(tp.track_set_scores(None, snapshot, scores), scores)   # base stack: off

    def test_faction_guide_parts_are_on_only_with_the_guide_flag(self):
        tp._guide['byfaction'] = True                      # restored by setUp's cleanup
        self.assertEqual(tp._faction_parts('BalTaks'), {'track_set'})
        self.assertEqual(tp._faction_parts('Moweyds'), set())
        tp._guide['faction_guide'] = True
        self.assertEqual(tp._faction_parts('BalTaks'), {'track_set', 'track_steps', 'track_caps', 'building_limits',
                                                        'opening_only', 'fixed_academy', 'opening_budget', 'budget_guard',
                                                        'opening_release'})
        self.assertEqual(tp._faction_parts('Moweyds'), {'track_set'})
        self.assertEqual(tp._faction_parts('Darkanians'), {'track_set', 'track_steps'})
        self.assertEqual(tp._faction_parts('Xenos'), set())
        self.assertEqual(tp._faction_parts('Terrans'), {'terrans_gaia_late', 'track_income'})
        for faction in tp.GUIDE_FACTION_PARTS:
            self.assertIn(faction, tp.FACTION_TRACKS, faction)
            for _, track, _ in tp.TRACK_STEPS.get(faction, ()):
                self.assertIn(track, tp.TRACK_NAMES)
        for faction, caps in tp.TRACK_CAPS.items():
            self.assertTrue(set(caps) <= set(tp.TRACK_NAMES), faction)

    def test_opening_only_cuts_the_baltaks_catalog_to_the_academy_openings(self):
        import bgg_openings.catalog as catalog
        import bgg_openings.planning as planning
        saved = catalog.load_catalog, planning.load_catalog
        self.addCleanup(lambda: (setattr(catalog, 'load_catalog', saved[0]),
                                 setattr(planning, 'load_catalog', saved[1])))
        tp.install_opening_only()
        full = saved[0]()
        self.assertEqual(catalog.load_catalog()['BalTaks'], full['BalTaks'])      # part off: unchanged
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        rows = catalog.load_catalog()
        self.assertEqual([r.label for r in rows['BalTaks']], ['1AC+1M', '1AC+2M'])
        self.assertEqual(rows['Taklons'], full['Taklons'])
        self.assertIs(planning.load_catalog, catalog.load_catalog)

    def test_fixed_academy_wraps_rank_for_the_faction_with_the_part_in_round_one(self):
        import bgg_openings.fixed as fixed
        import four_factions.preparation as p
        saved_rank, saved_targets = p.Policies.rank, dict(fixed.TARGETS)
        self.addCleanup(setattr, p.Policies, 'rank', saved_rank)
        self.addCleanup(lambda: (fixed.TARGETS.clear(), fixed.TARGETS.update(saved_targets)))
        calls = []
        p.Policies.rank = lambda self, env, snapshot: [(1.0, 'x')]
        with mock.patch.object(fixed, 'enforce', lambda env, snap, scores, memory: (calls.append(1) or [(2.0, 'y')], {})):
            tp.install_fixed_academy()
            self.assertEqual(fixed.TARGETS['BalTaks'], 'Science')
            self.assertEqual(fixed.target_kind('BalTaks'), {'Academy': 'Science'})
            policies = mock.Mock(memory={})
            snapshot = {'player': 0, 'state': {'round': 1, 'phase': {'ActionPhase': {}},
                                               'players': [{'faction': 'BalTaks'}]}}
            self.assertEqual(p.Policies.rank(policies, None, snapshot), [(1.0, 'x')])   # part off
            tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
            self.assertEqual(p.Policies.rank(policies, None, snapshot), [(2.0, 'y')])
            snapshot['state']['round'] = 2
            self.assertEqual(p.Policies.rank(policies, None, snapshot), [(1.0, 'x')])   # round 1 only
            snapshot['state'].update(round=1, players=[{'faction': 'Taklons'}])
            self.assertEqual(p.Policies.rank(policies, None, snapshot), [(1.0, 'x')])   # no part
        self.assertEqual(len(calls), 1)

    def test_value_max_keeps_only_catalog_labels_as_the_saved_target(self):
        def run(faction, target):
            snapshot = {'player': 1, 'state': {'players': [{'faction': 'Xenos'}, {'faction': faction}]}}
            result = {'index': 0, 'selected': 'x', 'memory': {},
                      'plans': [{'complete': True, 'value': 5.0, 'first': 3, 'goal': f'BGG-R1-{target}',
                                 'family': 'bgg-opening', 'goal_spec': {'target': target}}]}
            tp._value_max(snapshot, result)
            self.assertEqual(result['index'], 3)
            return result['memory'].get('_bgg_targets', {})
        self.assertEqual(run('BalTaks', '1AC+1M'), {'1': '1AC+1M'})
        self.assertEqual(run('Moweyds', '1RL+4M'), {})      # Lost Fleet: no BGG table, nothing saved

    def test_fed_cluster_moves_the_mine_next_to_our_unfederated_buildings(self):
        player = {'faction': 'Terrans', 'research_tracks': {},
                  'structures': [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'Mine', 'hex': '5,5'}],
                  'federated_hexes': ['5,5']}
        empty = {'planet': None, 'structures': [], 'satellites': []}
        board = {'hexes': {f'{q},{r}': dict(empty) for q in range(-6, 8) for r in range(-6, 8)},
                 'spaceship_tiles': {}}
        snapshot = {'player': 0, 'state': {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player],
                                           'board': board},
                    'candidates': [{'action': {'type': 'Build', 'coord': '3,0'}},     # far
                                   {'action': {'type': 'Build', 'coord': '1,0'}},     # next to 0,0
                                   {'action': {'type': 'Build', 'coord': '5,6'}},     # next to a federated mine only
                                   {'action': {'type': 'Pass'}}]}
        scores = [(9.0, 'far'), (5.0, 'near'), (7.0, 'fed'), (8.0, 'pass')]
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)   # part off
        tp._guide['fed'] = True                                                 # restored by setUp's cleanup
        lifted = tp.fed_cluster_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [5.0, 9.0, 7.0, 8.0])
        self.assertIn('fed_cluster', lifted[1][1])
        snapshot['state']['round'] = 6
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)   # round 6 is free
        snapshot['state']['round'] = 2
        best_near = [(5.0, 'far'), (9.0, 'near'), (7.0, 'fed'), (8.0, 'pass')]
        self.assertIs(tp.fed_cluster_scores(None, snapshot, best_near), best_near)
        # No adjacent mine: distance 2 (one satellite) is the nearest and leads over distance 3.
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '2,0'}}
        lifted = tp.fed_cluster_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [5.0, 9.0, 7.0, 8.0])
        # Distance 2 but the hex between (2,0 and 0,0 share only 1,0) is a planet: no satellite can
        # link it, not near.
        board['hexes']['1,0'] = {**empty, 'planet': {'planet_type': 'Terra', 'owner': None}}
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)
        board['hexes']['1,0'] = dict(empty)
        self.assertEqual([s[0] for s in tp.fed_cluster_scores(None, snapshot, scores)], [5.0, 9.0, 7.0, 8.0])
        # Nearest at distance 3 or more: nothing near, untouched.
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '0,4'}}
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)
        # A mine next to a federation joins it, and a building next to a federation seeds none.
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '5,4'}}      # next to federated 5,5
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)
        player['structures'].append({'kind': 'Mine', 'hex': '4,5'})                  # next to the federation
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '3,5'}}      # next to 4,5 only
        self.assertIs(tp.fed_cluster_scores(None, snapshot, scores), scores)

    def test_fed_cluster_prefers_a_mine_that_bridges_two_groups(self):
        tp._guide['fed'] = True                                                 # restored by setUp's cleanup
        empty = {'planet': None, 'structures': [], 'satellites': []}
        board = {'hexes': {f'{q},{r}': dict(empty) for q in range(-6, 9) for r in range(-6, 9)},
                 'spaceship_tiles': {}}
        player = {'faction': 'Xenos', 'research_tracks': {}, 'federated_hexes': [],
                  'structures': [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'Mine', 'hex': '4,0'}]}
        state = {'round': 3, 'phase': {'ActionPhase': {}}, 'players': [player], 'board': board}
        # Linking 0,0 and 4,0 takes 3 satellites; a mine on 2,0 leaves 2 (one each side): -1.
        link = tp._link_costs(state, ['0,0', '4,0'], set())
        self.assertEqual((link('2,0'), link('1,0'), link('0,3')), (-1, -1, 2))
        snapshot = {'player': 0, 'state': state,
                    'candidates': [{'action': {'type': 'Build', 'coord': '0,3'}},
                                   {'action': {'type': 'Build', 'coord': '2,0'}},
                                   {'action': {'type': 'Build', 'coord': '1,0'}}]}
        lifted = tp.fed_cluster_scores(None, snapshot, [(9.0, 'far'), (6.0, 'bridge'), (5.0, 'next')])
        self.assertEqual([s[0] for s in lifted], [6.0, 9.0, 5.0])
        self.assertIn('satellites -1', lifted[1][1])

    def _race_state(self, me, rival, rival_green=True):
        levels = lambda sci: {'terraforming': 0, 'navigation': 0, 'ai': 0, 'gaia': 0, 'economy': 0, 'science': sci}
        return {'round': 5, 'phase': {'ActionPhase': {}},
                'players': [{'faction': 'Xenos', 'research_tracks': levels(me), 'federation_tokens': [4]},
                            {'faction': 'Terrans', 'research_tracks': levels(rival),
                             'federation_tokens': [3] if rival_green else []}]}

    def test_race_reads_level_five_and_rival_tokens(self):
        self.assertEqual(tp._race(self._race_state(4, 4), 0, 'Science'), 'contested')
        self.assertEqual(tp._race(self._race_state(3, 4), 0, 'Science'), 'lost')
        self.assertEqual(tp._race(self._race_state(4, 5), 0, 'Science'), 'lost')
        self.assertIsNone(tp._race(self._race_state(4, 4, rival_green=False), 0, 'Science'))
        self.assertIsNone(tp._race(self._race_state(4, 2), 0, 'Science'))

    def test_track_race_leads_the_contested_level_five_and_advanced_tile(self):
        state = self._race_state(4, 4)
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'Science'},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': 3, 'advance_track': None}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Advanced', 'track': 'Science', 'covered_tile': 3,
                                         'advance_track': None}}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(6.0, 'eco'), (2.0, 'sci5'), (9.0, 'std'), (4.0, 'adv')]
        self.assertIs(tp.track_race_scores(None, snapshot, scores), scores)    # part off
        tp._guide['tokens'] = True                                              # restored by setUp's cleanup
        lifted = tp.track_race_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [2.0, 6.0, 4.0, 9.0])
        state['players'][1]['federation_tokens'] = []                           # rival cannot flip: no race
        self.assertEqual([s[0] for s in tp.track_race_scores(None, snapshot, scores)], [6.0, 2.0, 9.0, 4.0])

    def test_token_goals_compare_a_flip_and_drop_lost_races(self):
        from four_factions.preparation import Goal
        import four_factions.preparation as p
        saved = p.goals_for
        self.addCleanup(setattr, p, 'goals_for', saved)
        lost5 = Goal('Science-5', 'research', target='Science', level=5)
        keep5 = Goal('Economy-5', 'research', target='Economy', level=5)
        lost_adv = Goal('advanced-9', 'advanced', target='Science', tile=9)
        p.goals_for = lambda snapshot, **kwargs: [lost5, keep5, lost_adv]
        tp.install_token_goals()
        state = self._race_state(3, 4)                    # Science lost: rival at 4 with a token, we are at 3
        state['players'][0]['research_tracks']['economy'] = 4
        snapshot = {'player': 0, 'state': state,
                    'candidates': [{'action': {'type': 'Pass'}},
                                   {'action': {'type': 'ResearchAdvance', 'track': 'Economy'}}]}
        tp.fed_remember_scores(None, snapshot, [(0.0, 'pass'), (-3.0, 'eco5')])
        self.assertEqual(p.goals_for(snapshot), [lost5, keep5, lost_adv])     # parts off
        tp._guide['tokens'] = True                                              # restored by setUp's cleanup
        goals = p.goals_for(snapshot)
        self.assertEqual((goals[0].name, goals[0].first), ('flip-1', 1))       # Economy 4 -> 5 flips the token
        self.assertEqual(goals[1:], [keep5])

    def test_fed_compare_puts_the_best_federation_first_in_goals(self):
        import four_factions.preparation as p
        saved = p.goals_for
        self.addCleanup(setattr, p, 'goals_for', saved)
        p.goals_for = lambda snapshot, **kwargs: ['other-goal']
        tp.install_fed_compare()
        sats = lambda n: [f'{i},9' for i in range(n)]
        snapshot = {'player': 0, 'state': {'round': 6, 'phase': {'ActionPhase': {}}, 'players': [{'faction': 'Xenos'}]},
                    'candidates': [{'action': {'type': 'Pass'}},
                                   {'action': {'type': 'FormFederation', 'satellite_hexes': sats(6)}},
                                   {'action': {'type': 'FormFederation', 'satellite_hexes': sats(3)}},
                                   {'action': {'type': 'FormFederation', 'satellite_hexes': sats(1)}}]}
        scores = [(0.0, 'pass'), (-16.0, 'f6'), (-16.0, 'f3'), (-20.0, 'f1')]
        tp.fed_remember_scores(None, snapshot, scores)
        self.assertEqual(p.goals_for(snapshot), ['other-goal'])                # part off
        tp._guide['fed'] = True                                                 # restored by setUp's cleanup
        goals = p.goals_for(snapshot)
        self.assertEqual((goals[0].family, goals[0].first), ('root', 2))       # best score, fewer satellites on a tie
        self.assertEqual(goals[1:], ['other-goal'])
        other = dict(snapshot)                                                  # another snapshot: no ranking kept
        self.assertEqual(p.goals_for(other), ['other-goal'])

    def test_track_caps_close_a_guide_track_at_its_level(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        levels = {t: 0 for t in tp.TRACK_KEYS.values()}
        levels['navigation'] = 4
        player = {'faction': 'Gleens', 'research_tracks': levels}
        snapshot = {'player': 0, 'state': {'round': 3, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'ResearchAdvance', 'track': 'Navigation'}},
                                   {'action': {'type': 'ResearchAdvance', 'track': 'GaiaProject'}}]}
        lifted = tp.track_set_scores(None, snapshot, [(5.0, 'nav'), (3.0, 'gaia')])
        self.assertEqual([s[0] for s in lifted], [3.0, 5.0])     # Navigation 4 is the end: Gaia leads
        levels['navigation'] = 3
        scores = [(5.0, 'nav'), (3.0, 'gaia')]
        self.assertEqual(tp.track_set_scores(None, snapshot, scores), scores)
        tp._guide['faction_guide'] = False
        levels['navigation'] = 4
        self.assertEqual(tp.track_set_scores(None, snapshot, scores), scores)   # caps off: both on-guide

    def test_track_steps_lead_research_until_the_guide_level(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        levels = {t: 0 for t in tp.TRACK_KEYS.values()}
        levels['gaia'] = 1
        player = {'faction': 'BalTaks', 'research_tracks': levels}
        state = {'round': 1, 'phase': {'ActionPhase': {}},
                 'research_board': {'tech_tile_slots': [9, 7, 8, 6, 4, 2, 3, 10, 5]}, 'players': [player]}
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'GaiaProject'},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'Economy'}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'GaiaProject'}},
                   {'type': 'Build', 'coord': '2,0'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(6.0, 'eco'), (2.0, 'gaia'), (20.0, 'tile-eco'), (19.0, 'tile-gaia'), (30.0, 'mine')]
        lifted = tp.track_steps_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [2.0, 6.0, 19.0, 20.0, 30.0])   # swaps only, the mine untouched
        self.assertIn('track_steps', lifted[1][1])
        levels['gaia'] = 4
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)    # level reached
        levels['gaia'] = 1
        state['round'] = 6
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)    # round 6 is free
        # Bescods: the round-2 entry waits for round 2; Science 2 leads in round 1.
        state['round'] = 1
        player['faction'] = 'Bescods'
        snapshot['candidates'] = [{'action': {'type': 'ResearchAdvance', 'track': t}}
                                  for t in ('Economy', 'Science', 'Navigation')]
        lifted = tp.track_steps_scores(None, snapshot, [(6.0, 'eco'), (2.0, 'sci'), (1.0, 'nav')])
        self.assertEqual([s[0] for s in lifted], [2.0, 6.0, 1.0])
        levels['science'] = 2
        scores = [(6.0, 'eco'), (2.0, 'sci'), (1.0, 'nav')]
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)    # Economy waits for round 2
        tp._guide['faction_guide'] = False
        levels['science'] = 0
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)    # byfaction alone: off

    def test_building_limits_swap_the_limited_upgrade_away(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        player = {'faction': 'Firaks', 'research_tracks': {}}
        state = {'round': 4, 'phase': {'ActionPhase': {}}, 'players': [player]}
        actions = [{'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'},
                   {'type': 'Build', 'coord': '2,0'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(9.0, 'ac'), (4.0, 'pi'), (7.0, 'mine')]
        lifted = tp.building_limits_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [7.0, 4.0, 9.0])
        self.assertIn('building_limits', lifted[2][1])
        player['faction'] = 'Ambas'
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # Ambas: academy allowed
        state['round'] = 2
        scores = [(4.0, 'ac'), (9.0, 'pi'), (7.0, 'mine')]
        self.assertEqual([s[0] for s in tp.building_limits_scores(None, snapshot, scores)], [4.0, 7.0, 9.0])
        state['round'] = 3
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # Ambas institute from round 3
        player['faction'] = 'BalTaks'
        state['round'] = 6
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # BalTaks round 6 tier

    def test_academy_economy_leads_research_and_the_tile_track_until_economy_two(self):
        state = {'round': 2, 'phase': {'ActionPhase': {}},
                 'research_board': {'tech_tile_slots': [9, 7, 8, 6, 4, 2, 3, 10, 5]},
                 'players': [{'faction': 'Taklons', 'research_tracks': {'economy': 0, 'science': 1},
                              'structures': [{'kind': 'Mine', 'hex': '0,0'}, {'kind': {'Academy': 'Science'}, 'hex': '1,0'}]}]}
        actions = [{'type': 'ResearchAdvance', 'track': 'Science'}, {'type': 'ResearchAdvance', 'track': 'Economy'},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'Science'}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'Economy'}},
                   {'type': 'Build', 'coord': '2,0'}]
        scores = [(6.7, 'sci'), (0.0, 'eco'), (20.0, 'tile-sci'), (19.0, 'tile-eco'), (30.0, 'mine')]
        snapshot = {'state': state, 'player': 0, 'candidates': [{'action': a} for a in actions]}
        lifted = tp.academy_economy_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [0.0, 6.7, 19.0, 20.0, 30.0])   # swaps only, the mine untouched
        self.assertIn('research when', lifted[1][1])
        state['players'][0]['research_tracks']['economy'] = 2
        self.assertIs(tp.academy_economy_scores(None, snapshot, scores), scores)
        state['players'][0]['research_tracks']['economy'] = 0
        state['players'][0]['faction'] = 'BalTaks'
        self.assertIs(tp.academy_economy_scores(None, snapshot, scores), scores)
        # No academy yet: only the tile of the upgrade that builds one is steered.
        state['players'][0]['faction'] = 'Geodens'
        state['players'][0]['structures'] = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'ResearchLab', 'hex': '1,0'}]
        building = [{'type': 'Upgrade', 'coord': '1,0', 'to': {'Academy': 'Science'},
                     'tech_tile_choice': {'kind': 'Standard', 'tile': 2, 'advance_track': None}},
                    {'type': 'Upgrade', 'coord': '1,0', 'to': {'Academy': 'Science'},
                     'tech_tile_choice': {'kind': 'Standard', 'tile': 4, 'advance_track': None}}]
        snapshot['candidates'] = [{'action': a} for a in actions[:2]+building]
        building.append({'type': 'Upgrade', 'coord': '1,0', 'to': {'Academy': 'Science'},
                         'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'Economy'}})
        building.append({'type': 'Upgrade', 'coord': '1,0', 'to': {'Academy': 'Science'},
                         'tech_tile_choice': {'kind': 'Standard', 'tile': 10, 'advance_track': 'Science'}})
        snapshot['candidates'] = [{'action': a} for a in actions[:2]+building]
        lifted = tp.academy_economy_scores(None, snapshot, [(6.7, 'sci'), (0.0, 'eco'), (31.2, 'tile-2'),
                                                           (30.5, 'tile-4'), (29.0, 'tile-10-eco'), (30.0, 'tile-10-sci')])
        # Research is not steered before the academy exists; which tile is taken is not steered either
        # (tile 2 vs tile 4 stay); among one tile's track variants Economy leads (tile 10: 30.0 <-> 29.0).
        self.assertEqual([s[0] for s in lifted], [6.7, 0.0, 31.2, 30.5, 30.0, 29.0])

    def test_track_income_sweet_counts_economy_to_two_and_science_on_guide_tracks(self):
        from four_factions.value import INCOME
        state = {'research_board': {'economy_research_tile_side': 'Power'}}
        economy = INCOME['economy']['Power']
        player = {'faction': 'Xenos', 'research_tracks': {'economy': 3, 'science': 2}}
        excess = tp._track_income_excess(state, player)
        expected = [a-b+c for a, b, c in zip(economy[3], economy[2], INCOME['science'][2])]
        self.assertEqual(excess, expected)                        # Economy above 2 and all Science uncounted
        player['research_tracks']['economy'] = 2
        self.assertEqual(tp._track_income_excess(state, player), INCOME['science'][2])
        player['faction'] = 'Taklons'                             # Science is a Taklons guide track
        self.assertEqual(tp._track_income_excess(state, player), [0]*7)
        player['faction'] = 'Terrans'                             # Terrans: Economy counted to 4 (PG18-T20)
        player['research_tracks']['economy'] = 4
        self.assertEqual(tp._track_income_excess(state, player), INCOME['science'][2])
        player['faction'] = 'Geodens'                             # Geodens: to 3 (B14-03)
        self.assertEqual(tp._track_income_excess(state, player),
                         [a-b+c for a, b, c in zip(economy[4], economy[3], INCOME['science'][2])])
        player['faction'] = 'HadschHallas'                        # Economy first: counted at every level
        player['research_tracks']['economy'] = 4
        self.assertEqual(tp._track_income_excess(state, player), [0]*7)
        self.assertTrue(any(INCOME['science'][2]))                # the table rows used above are not empty
        self.assertTrue(any(a != b for a, b in zip(economy[3], economy[2])))

    def test_research_when_land_leads_range_without_land_and_economy_when_safe(self):
        state = {'round': 2, 'phase': {'ActionPhase': {}},
                 'players': [{'faction': 'Terrans', 'research_tracks': {'economy': 0}}]}
        actions = [{'type': 'ResearchAdvance', 'track': 'ArtificialIntelligence'},
                   {'type': 'ResearchAdvance', 'track': 'Navigation'},
                   {'type': 'ResearchAdvance', 'track': 'Economy'},
                   {'type': 'ResearchAdvance', 'track': 'Terraforming'},
                   {'type': 'Build', 'coord': '2,0'}]
        scores = [(4.7, 'ai'), (3.7, 'nav'), (0.0, 'eco'), (5.3, 'tf'), (30.0, 'mine')]
        snapshot = {'state': state, 'player': 0, 'candidates': [{'action': a} for a in actions]}
        with mock.patch.object(tp, '_land_counts', return_value=(0, 0)):
            lifted = tp.research_when_land_scores(None, snapshot, scores)
            self.assertEqual([s[0] for s in lifted], [4.7, 5.3, 0.0, 3.7, 30.0])   # Navigation takes the best research score
            self.assertIn('no land', lifted[1][1])
            snapshot['candidates'] = [{'action': a} for a in actions if a.get('track') != 'Navigation']
            lifted = tp.research_when_land_scores(None, snapshot, scores[:1]+scores[2:])
            self.assertEqual([s[0] for s in lifted], [4.7, 0.0, 5.3, 30.0])        # no Navigation offered: Terraforming already best
        snapshot['candidates'] = [{'action': a} for a in actions]
        with mock.patch.object(tp, '_land_counts', return_value=(5, 0)):
            lifted = tp.research_when_land_scores(None, snapshot, scores)
            self.assertEqual([s[0] for s in lifted], [4.7, 3.7, 5.3, 0.0, 30.0])   # safe land: Economy leads
            self.assertIn('land safe', lifted[2][1])
            state['players'][0]['research_tracks']['economy'] = 2
            self.assertIs(tp.research_when_land_scores(None, snapshot, scores), scores)
            state['players'][0]['research_tracks']['economy'] = 0
        with mock.patch.object(tp, '_land_counts', return_value=(5, 2)):
            self.assertIs(tp.research_when_land_scores(None, snapshot, scores), scores)   # contested: untouched
        state['round'] = 4
        with mock.patch.object(tp, '_land_counts', return_value=(0, 0)):
            self.assertIs(tp.research_when_land_scores(None, snapshot, scores), scores)   # rounds 1-3 only

    def test_ship_entries_and_ship_upgrades_are_not_budgeted(self):
        # User (2026-10-17): a ship entered with range QIC can make the chain cheaper — Twilight's
        # lab for 3 power + 2 ore instead of 3 ore 5 credits. The entry is never blocked and the
        # ship's upgrade counts as a chain step like any Upgrade; the owed sum is recomputed after it.
        from bgg_openings.catalog import parse_buildings
        from current_actions.conservation import blocked
        ts = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'TradingStation', 'hex': '1,0'}]
        lab = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'ResearchLab', 'hex': '1,0'}]
        before = self.snapshot(8, 13, ts, [
            {'type': 'ExploreSpaceship', 'ship': 'Rebellion'},
            {'type': 'TwilightFreeResearchLab', 'coord': '1,0'},
            {'type': 'Build', 'coord': '2,0'}], qic=1, bowl3=3)
        after = [self.snapshot(8, 13, ts, [], qic=0, bowl3=3),           # entry: the range QIC
                 self.snapshot(6, 13, lab, [], qic=1, bowl3=0),          # 2 ore + 3 power, lab reached
                 self.snapshot(7, 11, ts+[{'kind': 'Mine', 'hex': '2,0'}], [], qic=1, bowl3=3)]
        scores = [(9.0, 'rebellion'), (8.0, 'twilight lab'), (7.0, 'mine')]
        masked = tp.opening_budget_scores(self.Env(after), before, scores, parse_buildings('1AC+2M'),
                                          float('inf'))
        # The mine: 7 ore + 1 QIC + 1 (3 power) = 9 ore, 11 credits against RL 3/5 + AC 6/6: it pays.
        self.assertEqual([blocked(s) for s in masked], [False, False, False])
        after[2] = self.snapshot(6, 11, ts+[{'kind': 'Mine', 'hex': '2,0'}], [], qic=1, bowl3=3)
        masked = tp.opening_budget_scores(self.Env(after), before, scores, parse_buildings('1AC+2M'),
                                          float('inf'))
        self.assertEqual([blocked(s) for s in masked], [False, False, True])
        self.assertIn('9 ore 11 credits', masked[2][1])

    def test_install_wraps_select_action_once(self):
        import bgg_openings.planning as planning
        original = planning.select_action
        self.addCleanup(setattr, planning, 'select_action', original)
        tp.install_opening_budget()
        tp.install_opening_budget()
        self.assertTrue(planning.select_action._opening_budget)
        self.assertIs(planning.select_action.__wrapped__, getattr(original, '__wrapped__', original))
        self.assertTrue(tp._guide['opening_budget'])
