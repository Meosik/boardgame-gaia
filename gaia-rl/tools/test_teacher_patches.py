"""symmetric_pass: exact against native passes, and only unpassed action-phase states change."""
import json
import time
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

    def test_colony_cost_with_a_non_ring_home_prices_ring_planets_as_three_steps(self):
        from unittest import mock
        import economy.teacher as economy
        import four_factions.value as value
        state = {'board': {'hexes': {'h': {'planet': {'planet_type': 'Terra'}}}}}
        for faction in ('Moweyds', 'Tinkeroids', 'Darkanians', 'SpaceGiants'):
            player = {'faction': faction, 'structures': [{'hex': 's'}], 'resources': {'qic': 0}}
            with mock.patch.object(economy, 'path_distance', lambda *a: 0), \
                    mock.patch.object(value, 'navigation', lambda p: 1):
                self.assertEqual(tp._colony_cost(state, player, 'h'), (False, 3), faction)

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
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_tokens': ['False']*6 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_shipmine': ['False']*6 + ['False', 'False'],
                    'guide_r1_charge3_lf_more_vm_lf_ts_ships_endgame': ['False']*6 + ['False', 'False']}
        flags += ", tp._guide['byfaction']"
        for factory, want in expected.items():
            code = f"import teacher_patches as tp\ntp.{factory}({SEED!r})\nprint({flags})"
            out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                                 env=env).stdout
            self.assertEqual(out.split(), want, factory)

    def test_menu1_all_factory_turns_on_every_faction_part(self):
        # Subprocess like the test above: the factory rebinds module-level functions for the whole process.
        import os
        import subprocess
        import sys
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join(sys.path)}
        code = ("import teacher_patches as tp\n"
                "tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all('geo-quartet-1050620', "
                "bgg_openings=True, shared_factions=True)\n"
                "print(tp._guide['plan_menu'], tp._guide['menu_first'], tp._guide['resolved_parts'], "
                "tp._guide['weak_factions'], 'opening_res' in tp._faction_parts('Taklons'), "
                "'opening_only' in tp._faction_parts('HadschHallas'))\n"
                "import four_factions.preparation as p\n"
                "outer = p.Policies.rank\n"
                "print(tp.fed_remember_scores in [c.cell_contents for c in outer.__closure__] "
                "and outer._gaia_asteroid_hold and outer._dead_tile)")
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                             env=env).stdout
        # The last word: the federation / token comparisons read the final ranking (outermost recorder, debate 1/1),
        # and gaia_asteroid_hold is installed inside it.
        self.assertEqual(out.split(), ['True', '1', 'True', 'True', 'True', 'True', 'True'])

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

    def test_mj01_corrects_the_track_tables_only_when_on(self):
        levels = {t: 0 for t in tp.TRACK_KEYS.values()}
        firaks, terrans = {'faction': 'Firaks', 'research_tracks': levels}, {'faction': 'Terrans', 'research_tracks': levels}
        self.assertEqual(tp._track_steps_table(firaks), tp.TRACK_STEPS['Firaks'])
        self.assertEqual(tp._faction_tracks(terrans), tp.FACTION_TRACKS['Terrans'])
        self.assertNotIn('economy', tp._track_caps(terrans))
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        self.assertEqual(tp._track_steps_table(firaks)[0], (1, 'economy', 2))   # MJ01-21
        self.assertEqual(tp._track_caps(firaks)['economy'], 2)                  # MJ01-10, every faction
        self.assertEqual(tp._track_caps(firaks)['navigation'], 2)               # TRACK_CAPS kept
        self.assertEqual(tp._track_caps(terrans, table=False), {'economy': 2, 'gaia': 1})
        self.assertNotIn('gaia', tp._faction_tracks(terrans))                    # MJ01-23 replaces T2
        state = {'round': 1, 'players': [dict(terrans, research_tracks=dict(levels, gaia=1))]}
        self.assertNotIn('gaia', [t for t, _ in tp._plan_tracks(state, 0)])

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
                                                        'opening_release', 'tile_prefs'})
        self.assertEqual(tp._faction_parts('Moweyds'), {'track_set'})
        self.assertEqual(tp._faction_parts('Darkanians'), {'track_set', 'track_steps'})
        self.assertEqual(tp._faction_parts('Xenos'), {'niche_tracks'})
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
        self.assertEqual(rows['HadschHallas'], full['HadschHallas'])               # weak_factions off
        tp._guide['weak_factions'] = True
        rows = catalog.load_catalog()
        for faction in tp.WEAK_FACTION_PARTS:
            self.assertEqual({r.label for r in rows[faction]}, set(tp.OPENING_ONLY[faction]), faction)
        self.assertFalse(any('PI' in r.label for r in rows['HadschHallas']))
        self.assertFalse(any(r.label.startswith('1RL') and 'TS' not in r.label for r in rows['Itars']))
        self.assertEqual(rows['Ambas'], full['Ambas'])                             # source_parts off
        tp._guide.update(weak_factions=False, source_parts=True)
        rows = catalog.load_catalog()
        for faction, labels in tp.OPENING_ONLY.items():
            if faction in tp.SOURCE_FACTION_PARTS and 'opening_only' in tp.SOURCE_FACTION_PARTS[faction]:
                self.assertEqual({r.label for r in rows[faction]}, set(labels), faction)   # every label in the table
        self.assertEqual(rows['HadschHallas'], full['HadschHallas'])

    def test_track_steps_src_replaces_the_guide_order(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        player = {'faction': 'Nevlas', 'research_tracks': {'economy': 1, 'science': 1}}
        state = {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player]}
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'Science'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(9.0, 'eco'), (4.0, 'sci')]
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)        # Nevlas has no track_steps
        tp._guide['source_parts'] = True
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [4.0, 9.0])
        player['research_tracks']['science'] = 3
        self.assertIs(tp.track_steps_scores(None, snapshot, scores), scores)        # Science 3 reached
        player.update(faction='Lantids', research_tracks={'economy': 1, 'navigation': 1})
        actions[1] = {'type': 'ResearchAdvance', 'track': 'Navigation'}
        scores = [(4.0, 'eco'), (9.0, 'nav')]
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])   # Economy 2 first
        tp._guide['source_parts'] = False
        self.assertEqual(tp.track_steps_scores(None, snapshot, scores), scores)     # guide order: Navigation 2
        tp._guide['source_tracks'] = True                                            # E59 (ㄱ): the track order alone
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])
        for faction in tp.SOURCE_FACTION_PARTS:
            self.assertEqual(tp._faction_parts(faction) & (tp.SOURCE_FACTION_PARTS[faction] - tp.SOURCE_TRACK_PARTS),
                             set(), faction)                                         # no opening_only, no building_due
        self.assertIn('track_steps_src', tp._faction_parts('Ivits'))
        self.assertNotIn('opening_only', tp._faction_parts('Ambas'))
        tp._guide['source_tracks'] = False

    def test_resolved_parts_order_openings_and_pick_science_by_condition(self):
        tp._guide.update(byfaction=True, faction_guide=True, source_parts=True)   # restored by setUp's cleanup
        self.assertNotIn('opening_res', tp._faction_parts('Terrans'))
        player = {'faction': 'Terrans', 'booster': None, 'structures': [{'kind': 'Mine', 'hex': '0,0'}],
                  'research_tracks': {'economy': 1, 'science': 1}}
        state = {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player], 'board': {'spaceship_tiles': {}},
                 'round_tiles': [{'condition': 'BuildMine'}]*6,
                 'research_board': {'advanced_tech_tiles': [None]*6}}
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        self.assertEqual(tp.guide_opening_labels('Terrans', snapshot), tp.UIQOO_OPENINGS['Terrans'])   # flag off
        tp._guide['resolved_parts'] = True
        self.assertEqual(tp.guide_opening_labels('Terrans', snapshot)[0], '1PI+2M')
        self.assertEqual(tp.guide_opening_labels('Terrans', snapshot)[-1], '1AC+1M')
        self.assertEqual(tp.guide_opening_labels('Taklons', snapshot)[0], '1AC+2M')
        self.assertEqual(tp.guide_opening_labels('Terrans'), tp.UIQOO_OPENINGS['Terrans'])   # no snapshot: guide
        # Darkanians: no terraforming at hand -> academy first; the booster or TF Mars in reach -> institute first.
        player['faction'] = 'Darkanians'
        self.assertEqual(tp.darkanian_terraforming(snapshot), 0)
        self.assertEqual(tp.guide_opening_labels('Darkanians', snapshot)[0], '1AC+1M')
        player['booster'] = tp.TERRAFORM_BOOSTER
        self.assertEqual(tp.guide_opening_labels('Darkanians', snapshot)[0], '1PI+1TS+2M')
        player['booster'] = None
        state['board']['spaceship_tiles'] = {'TFMars': '5,0'}
        self.assertEqual(tp.darkanian_terraforming(snapshot), 0)                                  # 5 away
        state['board']['spaceship_tiles'] = {'TFMars': '2,0'}
        self.assertEqual(tp.darkanian_terraforming(snapshot), 1)
        # science_when: Economy 2 by default, Science when round 5 or 6 scores research steps.
        player['faction'] = 'Ivits'
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'Science'}]
        snapshot['candidates'] = [{'action': a} for a in actions]
        scores = [(4.0, 'eco'), (9.0, 'sci')]
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])   # Economy 2 first
        state['round_tiles'] = [{'condition': 'BuildMine'}]*5 + [{'condition': 'ResearchAdvance'}]
        self.assertEqual(tp.track_steps_scores(None, snapshot, scores), scores)                       # Science first
        # An S/A Advanced tile above Science (LF2-11), or S/A tiles on half the tracks.
        state['round_tiles'] = [{'condition': 'BuildMine'}]*6
        state['research_board']['advanced_tech_tiles'] = [15, 16, 19, 3, 4, 8]       # research step 2 above Science
        self.assertTrue(tp.science_first(state, player))
        state['research_board']['advanced_tech_tiles'] = [15, 16, 19, 3, 4, 21]      # 3 ore: B tier, one S/A on board
        self.assertFalse(tp.science_first(state, player))
        state['research_board']['advanced_tech_tiles'] = [11, 7, 19, 3, 4, 21]       # three S/A tiles
        self.assertTrue(tp.science_first(state, player))
        # Round-1 tech federation (LF token 12 on a ship in reach): Terrans PI+TS first, Xenos the institute.
        player.update(faction='Xenos')
        state['spaceship_boards'] = [{'id': 'Rebellion', 'federation_token': 12}]
        state['board']['spaceship_tiles'] = {'Rebellion': '6,0'}
        self.assertFalse(tp.tech_federation_reachable(snapshot))
        self.assertEqual(tp.guide_opening_labels('Xenos', snapshot)[0], '1RL+5M')
        state['board']['spaceship_tiles'] = {'Rebellion': '1,1'}
        self.assertTrue(tp.tech_federation_reachable(snapshot))
        self.assertEqual(tp.guide_opening_labels('Xenos', snapshot)[0], '1PI+1TS+1M')
        player['faction'] = 'Terrans'
        self.assertEqual(tp.guide_opening_labels('Terrans', snapshot)[0], '1PI+1TS+2M')
        state['spaceship_boards'] = [{'id': 'Rebellion', 'federation_token': 9}]
        self.assertEqual(tp.guide_opening_labels('Terrans', snapshot)[0], '1PI+2M')
        # Itars: the first track follows the opening (institute -> Gaia 1, academy -> Economy 2).
        player.update(faction='Itars', research_tracks={'economy': 1, 'gaia': 0},
                      structures=[{'kind': {'Academy': 'Science'}, 'hex': '0,0'}])
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'GaiaProject'}]
        snapshot['candidates'] = [{'action': a} for a in actions]
        scores = [(4.0, 'eco'), (9.0, 'gaia')]
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])
        player['structures'] = [{'kind': 'PlanetaryInstitute', 'hex': '0,0'}]
        self.assertEqual(tp.track_steps_scores(None, snapshot, scores), scores)
        self.assertIn('building_due', tp._faction_parts('Bescods'))
        self.assertEqual(tp.BUILDING_DUE['Bescods'], ('PlanetaryInstitute', 3))

    def test_building_due_puts_the_institute_first_among_big_buildings(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        player = {'faction': 'Firaks', 'research_tracks': {}, 'structures': [{'kind': 'ResearchLab', 'hex': '0,0'}]}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]}
        actions = [{'type': 'Upgrade', 'coord': '1,0', 'to': 'ResearchLab'},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'},
                   {'type': 'Build', 'coord': '2,0'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(8.0, 'rl'), (5.0, 'pi'), (9.0, 'mine')]
        self.assertIs(tp.building_due_scores(None, snapshot, scores), scores)       # part off
        tp._guide['source_parts'] = True
        self.assertEqual([s[0] for s in tp.building_due_scores(None, snapshot, scores)], [5.0, 8.0, 9.0])
        state['round'] = 1
        self.assertIs(tp.building_due_scores(None, snapshot, scores), scores)       # before the due round
        state['round'] = 2
        player['structures'].append({'kind': 'PlanetaryInstitute', 'hex': '3,0'})
        self.assertIs(tp.building_due_scores(None, snapshot, scores), scores)       # already built
        player.update(faction='Itars', structures=[])
        self.assertIs(tp.building_due_scores(None, snapshot, scores), scores)       # Itars due round 3
        state['round'] = 3
        self.assertEqual([s[0] for s in tp.building_due_scores(None, snapshot, scores)], [5.0, 8.0, 9.0])

    def test_weak_faction_parts_are_on_only_with_their_flag(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        self.assertNotIn('opening_only', tp._faction_parts('HadschHallas'))
        self.assertNotIn('building_limits', tp._faction_parts('HadschHallas'))
        tp._guide['weak_factions'] = True
        self.assertTrue({'opening_only', 'building_limits'} <= tp._faction_parts('HadschHallas'))
        self.assertIn('opening_only', tp._faction_parts('Itars'))
        self.assertIn('opening_only', tp._faction_parts('Firaks'))
        self.assertNotIn('opening_only', tp._faction_parts('Terrans'))

    def test_resolved_parts_qic_academy_and_rebellion_institute_exception(self):
        import bgg_openings.fixed as fixed
        saved_targets, saved_kind = dict(fixed.TARGETS), fixed.target_kind
        self.addCleanup(lambda: (fixed.TARGETS.clear(), fixed.TARGETS.update(saved_targets)))
        self.addCleanup(setattr, fixed, 'target_kind', saved_kind)
        tp._guide.update(byfaction=True, faction_guide=True, source_parts=True)   # restored by setUp's cleanup
        tp.install_fixed_academy()
        self.assertEqual(tp.academy_target('BalTaks'), 'Science')
        self.assertEqual(fixed.target_kind('BalTaks'), {'Academy': 'Science'})
        tp._guide['resolved_parts'] = True
        self.assertEqual(tp.academy_target('BalTaks'), 'Qic')
        self.assertEqual(fixed.target_kind('BalTaks'), {'Academy': 'Qic'})
        self.assertEqual(fixed.target_kind('Xenos'), {'Academy': 'Science'})
        self.assertEqual(fixed.target_kind('Terrans'), 'PlanetaryInstitute')
        # HadschHallas: no institute in rounds 1-2 unless the Rebellion is ours to reach and no rival (explored,
        # 3 QIC) can press its 3-QIC action now.
        player = {'faction': 'HadschHallas', 'research_tracks': {}, 'structures': [{'kind': 'Mine', 'hex': '0,0'}],
                  'explored_ships': [], 'resources': {'qic': 1}}
        rival = {'faction': 'Terrans', 'structures': [{'kind': 'Mine', 'hex': '8,0'}], 'explored_ships': [],
                 'resources': {'qic': 3}}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player, rival],
                 'board': {'spaceship_tiles': {}}}
        actions = [{'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(4.0, 'ac'), (9.0, 'pi')]
        self.assertFalse(tp.rebellion_reachable(snapshot))
        self.assertEqual([s[0] for s in tp.building_limits_scores(None, snapshot, scores)], [9.0, 4.0])
        state['board']['spaceship_tiles'] = {'Rebellion': '2,0'}
        self.assertTrue(tp.rebellion_reachable(snapshot))                           # rival not explored
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # exception: institute allowed
        rival['explored_ships'] = [tp.REBELLION]                                    # explored and 3 QIC: a rival
        self.assertFalse(tp.rebellion_reachable(snapshot))
        rival['resources']['qic'] = 2                                               # explored but short of QIC
        self.assertTrue(tp.rebellion_reachable(snapshot))
        state['board']['spaceship_tiles'] = {'Rebellion': '6,0'}                   # out of range, not explored
        self.assertFalse(tp.rebellion_reachable(snapshot))
        player['explored_ships'] = [tp.REBELLION]                                   # already on the ship
        self.assertTrue(tp.rebellion_reachable(snapshot))
        player['explored_ships'] = []
        tp._guide['resolved_parts'] = False
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # no building_limits without a flag

    def test_hadsch_hallas_first_token_is_six_credits_and_the_replay_is_compared_first(self):
        tp._guide.update(byfaction=True, faction_guide=True, source_parts=True, resolved_parts=True)   # setUp restores
        player = {'faction': 'HadschHallas', 'structures': [{'kind': 'Mine', 'hex': '0,0'}],
                  'federation_tokens': [], 'gray_federation_tokens': []}
        state = {'round': 3, 'phase': {'ActionPhase': {}}, 'players': [player]}
        fed = {'type': 'FormFederation', 'hexes': ['0,0', '1,0'], 'satellite_hexes': []}
        actions = [{**fed, 'token': {'source': 'Supply', 'kind': 1}},
                   {**fed, 'token': {'source': 'Supply', 'kind': 5}},
                   {**fed, 'hexes': ['0,0', '2,0'], 'token': {'source': 'Supply', 'kind': 1}},
                   {'type': 'Build', 'coord': '3,0'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(9.0, 'vp12'), (6.0, 'credits6'), (8.0, 'other hexes'), (7.0, 'mine')]
        lifted = tp.fed_token_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [6.0, 9.0, 8.0, 7.0])              # same hexes: the 6-credit token
        self.assertIn('fed_token_credits', lifted[1][1])
        player['federation_tokens'] = [5]
        self.assertIs(tp.fed_token_scores(None, snapshot, scores), scores)          # first federation only
        player['federation_tokens'] = []
        tp._guide['resolved_parts'] = False
        self.assertIs(tp.fed_token_scores(None, snapshot, scores), scores)          # part off
        tp._guide['resolved_parts'] = True
        # replay_first: the institute built, a legal replay in the remembered ranking -> compared first.
        actions = [{'type': 'TwilightReplayFederationToken', 'token_kind': 5}, {'type': 'Build', 'coord': '3,0'}]
        snapshot['candidates'] = [{'action': a} for a in actions]
        scores = [(2.0, 'replay'), (9.0, 'mine')]
        tp.fed_remember_scores(None, snapshot, scores)
        self.assertIsNone(tp.replay_first_goal(snapshot))                           # no institute yet
        player['structures'].append({'kind': 'PlanetaryInstitute', 'hex': '1,0'})
        goal = tp.replay_first_goal(snapshot)
        self.assertEqual((goal.family, goal.first), ('root', 0))
        player['faction'] = 'Terrans'
        self.assertIsNone(tp.replay_first_goal(snapshot))                           # HadschHallas only

    def test_itars_academy_kind_and_hadsch_hallas_track_by_neighbour(self):
        tp._guide.update(byfaction=True, faction_guide=True, source_parts=True, resolved_parts=True)   # setUp restores
        player = {'faction': 'Itars', 'research_tracks': {}, 'structures': [{'kind': 'TradingStation', 'hex': '0,0'}]}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]}
        actions = [{'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Qic'}},
                   {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'}},
                   {'type': 'Build', 'coord': '2,0'}]
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': a} for a in actions]}
        scores = [(9.0, 'qic ac'), (5.0, 'science ac'), (7.0, 'mine')]
        lifted = tp.academy_kind_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [7.0, 5.0, 9.0])                   # the mine leads, not the QIC academy
        self.assertIn('academy_kind', lifted[2][1])
        scores = [(5.0, 'qic ac'), (9.0, 'science ac'), (7.0, 'mine')]
        self.assertIs(tp.academy_kind_scores(None, snapshot, scores), scores)       # Science academy already best
        player['faction'] = 'BalTaks'
        scores = [(9.0, 'qic ac'), (5.0, 'science ac'), (7.0, 'mine')]
        self.assertIs(tp.academy_kind_scores(None, snapshot, scores), scores)       # no such rule for BalTaks
        # HadschHallas rounds 1-2: Navigation 2 with a rival within two hexes, Economy 2 otherwise.
        player.update(faction='HadschHallas', research_tracks={'economy': 0, 'navigation': 0},
                      structures=[{'kind': 'Mine', 'hex': '0,0'}])
        rival = {'faction': 'Terrans', 'structures': [{'kind': 'Mine', 'hex': '5,0'}]}
        state['players'].append(rival)
        actions = [{'type': 'ResearchAdvance', 'track': 'Economy'}, {'type': 'ResearchAdvance', 'track': 'Navigation'}]
        snapshot['candidates'] = [{'action': a} for a in actions]
        scores = [(4.0, 'eco'), (9.0, 'nav')]
        self.assertFalse(tp.rival_adjacent(state, 0))
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])   # Economy 2
        rival['structures'] = [{'kind': 'Mine', 'hex': '2,0'}]
        self.assertTrue(tp.rival_adjacent(state, 0))
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [4.0, 9.0])   # Navigation 2 already best
        scores = [(9.0, 'eco'), (4.0, 'nav')]
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [4.0, 9.0])   # Navigation 2
        state['round'] = 3
        self.assertEqual([s[0] for s in tp.track_steps_scores(None, snapshot, scores)], [9.0, 4.0])   # from round 3 the guide's Economy 2

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

    def test_endgame_prices_value_the_round_six_stock_at_the_final_scoring_rates(self):
        import copy
        import guide_value as gv
        from faction_teachers.profiles import profiles
        snapshot = next(s for _, s in play(rounds=1) if s['state']['round'] == 1)
        state = copy.deepcopy(snapshot['state'])
        state['round'] = 6                                             # horizon 0: the last round
        player = state['players'][0]
        player['resources'].update(ore=4, credits=5, knowledge=3, qic=9)
        player['research_tracks'].update(economy=3, ai=5)
        home = profiles()[player['faction']].home
        before = tp.guide_potential(state, 0, home=home)
        self.assertEqual(tp.endgame_stock_vp(player), 4 + 4*(1+3))   # 12/3 and levels 3 + 3,4,5
        tp._guide['endgame_prices'] = True                             # restored by setUp
        after = tp.guide_potential(state, 0, home=home)
        guide = gv.research_value(state, player) + gv.materials(state, player['resources']) + gv.power_value(state, player)
        self.assertAlmostEqual(before - after, guide - 20)
        self.assertGreater(before - after, 30)                         # 9 QIC alone were 42 VP
        # Earlier rounds keep the guide prices.
        state['round'] = 5
        tp._guide['endgame_prices'] = False
        before = tp.guide_potential(state, 0, home=home)
        tp._guide['endgame_prices'] = True
        self.assertEqual(tp.guide_potential(state, 0, home=home), before)

    def test_ship_adjacent_mine_leads_the_entry_that_pays_range_qic(self):
        empty = {'planet': None, 'structures': [], 'satellites': []}
        board = {'hexes': {f'{q},{r}': dict(empty) for q in range(-6, 9) for r in range(-6, 9)},
                 'spaceship_tiles': {'Twilight': '4,0'}}
        board['hexes']['0,0'] = {**empty, 'structures': [{'kind': 'Mine', 'owner': 0}]}
        desert = {'planet_type': 'Desert', 'owner': None, 'is_gaia_formed': False}          # Xenos home
        board['hexes']['3,0'] = {**empty, 'planet': dict(desert)}                            # next to the ship
        board['hexes']['3,1'] = {**empty, 'planet': {**desert, 'planet_type': 'Terra'}}      # 2 steps from Desert
        board['hexes']['4,-1'] = {**empty, 'planet': {**desert, 'planet_type': 'Gaia'}}      # 1 QIC to colonize
        player = {'player_id': 0, 'faction': 'Xenos', 'research_tracks': {'navigation': 0}, 'tech_tiles': [],
                  'covered_tech_tiles': [], 'structures': [{'kind': 'Mine', 'hex': '0,0'}]}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player], 'board': board}
        snapshot = {'player': 0, 'state': state,
                    'candidates': [{'action': {'type': 'ExploreSpaceship', 'ship': 'Twilight'}},   # 2 QIC
                                   {'action': {'type': 'Build', 'coord': '3,0'}},                 # 1 QIC, home
                                   {'action': {'type': 'Build', 'coord': '3,1'}},                 # 2 steps
                                   {'action': {'type': 'Build', 'coord': '4,-1'}},                # Gaia
                                   {'action': {'type': 'Pass'}}]}
        scores = [(9.0, 'ship'), (5.0, 'home'), (7.0, 'terra'), (8.0, 'gaia'), (2.0, 'pass')]
        self.assertIs(tp.ship_adjacent_mine_scores(None, snapshot, scores), scores)   # part off
        tp._guide['ship_adjacent_mine'] = True                                          # restored by setUp
        lifted = tp.ship_adjacent_mine_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [5.0, 9.0, 7.0, 8.0, 2.0])
        self.assertIn('ship_adjacent_mine', lifted[1][1])
        # The mine already leads: untouched.
        leads = [(4.0, 'ship'), (5.0, 'home'), (7.0, 'terra'), (8.0, 'gaia'), (2.0, 'pass')]
        self.assertIs(tp.ship_adjacent_mine_scores(None, snapshot, leads), leads)
        # The entry pays no QIC (ship next to our mine): nothing to save.
        board['spaceship_tiles']['Twilight'] = '1,0'
        self.assertIs(tp.ship_adjacent_mine_scores(None, snapshot, scores), scores)
        # Only the one-step ring planet next to the ship counts; it must not cost more QIC than the entry
        # (ship at distance 5: 2 QIC; the planet beyond it at distance 6: 3 QIC).
        board['spaceship_tiles']['Twilight'] = '5,0'
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '6,0'}}
        board['hexes']['6,0'] = {**empty, 'planet': dict(desert)}
        self.assertIs(tp.ship_adjacent_mine_scores(None, snapshot, scores), scores)
        snapshot['candidates'][1] = {'action': {'type': 'Build', 'coord': '4,0'}}           # distance 4: 2 QIC
        board['hexes']['4,0'] = {**empty, 'planet': dict(desert)}
        self.assertEqual([s[0] for s in tp.ship_adjacent_mine_scores(None, snapshot, scores)],
                         [5.0, 9.0, 7.0, 8.0, 2.0])
        self.assertEqual(tp._ring_steps('Desert', desert), 0)
        self.assertEqual(tp._ring_steps('Desert', {'planet_type': 'Swamp'}), 1)
        self.assertIsNone(tp._ring_steps('Desert', {'planet_type': 'Gaia'}))

    def _race_state(self, me, rival, rival_green=True):
        levels = lambda sci: {'terraforming': 0, 'navigation': 0, 'ai': 0, 'gaia': 0, 'economy': 0, 'science': sci}
        rich = {'ore': 6, 'credits': 6, 'knowledge': 4, 'qic': 0}
        return {'round': 5, 'phase': {'ActionPhase': {}},
                'players': [{'faction': 'Xenos', 'research_tracks': levels(me), 'federation_tokens': [4],
                             'resources': dict(rich), 'structures': [{'kind': 'TradingStation', 'hex': '0,0'}]},
                            {'faction': 'Terrans', 'research_tracks': levels(rival),
                             'federation_tokens': [3] if rival_green else [], 'resources': dict(rich),
                             'structures': [{'kind': 'ResearchLab', 'hex': '5,5'}]}]}

    def test_race_reads_level_five_and_rival_tokens(self):
        self.assertEqual(tp._race(self._race_state(4, 4), 0, 'Science'), 'contested')
        self.assertEqual(tp._race(self._race_state(3, 4), 0, 'Science'), 'lost')
        self.assertEqual(tp._race(self._race_state(4, 5), 0, 'Science'), 'lost')
        self.assertIsNone(tp._race(self._race_state(4, 4, rival_green=False), 0, 'Science'))
        self.assertIsNone(tp._race(self._race_state(4, 2), 0, 'Science'))
        # A rival that cannot pay soon is no threat (user: count the rival's resources).
        poor = self._race_state(0, 0)
        poor['players'][0]['research_tracks']['economy'] = 3
        poor['players'][1]['research_tracks']['economy'] = 4                     # Economy race, rival Science 0
        poor['players'][1]['resources'].update(knowledge=0, ore=0, credits=0)
        self.assertIsNone(tp._race(poor, 0, 'Economy'))                         # 0 knowledge, no Science income
        self.assertIsNone(tp._race(poor, 0, 'Economy', 'advanced'))             # no upgrade it can pay
        poor['players'][1]['research_tracks']['science'] = 2
        poor['players'][1]['resources']['knowledge'] = 2
        self.assertEqual(tp._race(poor, 0, 'Economy'), 'lost')                  # 2 now + 2 next income
        self.assertEqual(tp._race(self._race_state(3, 4), 0, 'Science', 'advanced'), 'lost')
        # Advanced tiles come by other ways too: Twilight's free lab, the Itars' Gaia phase, Space Giants' institute.
        rival = poor['players'][1]
        rival['structures'] = [{'kind': 'TradingStation', 'hex': '5,5'}]
        rival['explored_ships'] = [0]
        rival['resources']['ore'] = 2
        self.assertTrue(tp._rival_ready(rival, 'advanced'))                    # Twilight lab
        rival['explored_ships'] = []
        self.assertFalse(tp._rival_ready(rival, 'advanced'))
        rival.update(faction='Itars', structures=[{'kind': 'PlanetaryInstitute', 'hex': '5,5'}])
        rival['resources']['power'] = {'gaia_forming': 4}
        self.assertTrue(tp._rival_ready(rival, 'advanced'))
        rival.update(faction='SpaceGiants', pi_ability_used=False)
        rival['resources']['power'] = {}
        self.assertTrue(tp._rival_ready(rival, 'advanced'))
        rival['pi_ability_used'] = True
        self.assertFalse(tp._rival_ready(rival, 'advanced'))

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
        # Science 5 replaces the level-4 income (9 knowledge once vs 4 a round): from round 4 only.
        state['players'][1]['federation_tokens'] = [3]
        state['round'] = 3
        self.assertEqual([s[0] for s in tp.track_race_scores(None, snapshot, scores)], [6.0, 2.0, 4.0, 9.0])
        self.assertTrue(tp._level5_pays({'round': 4}, 'Science'))
        self.assertFalse(tp._level5_pays({'round': 4}, 'Economy'))              # Economy from round 5
        self.assertTrue(tp._level5_pays({'round': 5}, 'Economy'))
        self.assertTrue(tp._level5_pays({'round': 2}, 'Terraforming'))

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

    def test_tile_prefs_follow_the_guide_tiles(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        player = {'faction': 'HadschHallas', 'research_tracks': {}}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]}
        up = lambda tile, track=None: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                                       'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': track}}
        snapshot = {'player': 0, 'state': state,
                    'candidates': [{'action': up(3)}, {'action': up(2)}, {'action': up(5)}, {'action': {'type': 'Pass'}}]}
        scores = [(9.0, 't3'), (4.0, 't2'), (6.0, 't5'), (1.0, 'pass')]
        lifted = tp.tile_prefs_scores(None, snapshot, scores)
        self.assertEqual([s[0] for s in lifted], [4.0, 9.0, 6.0, 1.0])          # prefers 2 over the 4-credit tile 3
        player['faction'] = 'Ambas'                                             # avoids 2 only
        scores = [(4.0, 't3'), (9.0, 't2'), (6.0, 't5'), (1.0, 'pass')]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 6.0, 9.0, 1.0])
        player['faction'] = 'Geodens'                                           # 10 early, 9 from round 4
        snapshot['candidates'][1] = {'action': up(9)}
        snapshot['candidates'][2] = {'action': up(10)}
        scores = [(9.0, 't3'), (4.0, 't9'), (6.0, 't10'), (1.0, 'pass')]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [6.0, 4.0, 9.0, 1.0])
        state['round'] = 4
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 9.0, 6.0, 1.0])
        player['faction'] = 'Terrans'                                           # no table entry: untouched
        self.assertIs(tp.tile_prefs_scores(None, snapshot, scores), scores)
        # Scope (091): Itars' list is for the institute's Gaia-phase tile only — lab tiles stay the search's.
        player['faction'] = 'Itars'
        snapshot['candidates'] = [{'action': up(5)}, {'action': up(6)}, {'action': {'type': 'Pass'}}]
        scores = [(9.0, 't5'), (4.0, 't6'), (1.0, 'pass')]
        self.assertIs(tp.tile_prefs_scores(None, snapshot, scores), scores)
        ability = lambda tile: {'type': 'ItarsGaiaTechTile', 'tile': tile, 'track': 'GaiaProject'}
        snapshot['candidates'] = [{'action': ability(5)}, {'action': ability(6)}, {'action': {'type': 'Pass'}}]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 9.0, 1.0])
        # Bescods' big-building tile comes with the institute or academy, not the first lab.
        player['faction'] = 'Bescods'
        snapshot['candidates'] = [{'action': up(2)}, {'action': up(6)}, {'action': {'type': 'Pass'}}]
        self.assertIs(tp.tile_prefs_scores(None, snapshot, scores), scores)
        big = lambda tile: {**up(tile), 'to': {'Academy': 'Science'}}
        snapshot['candidates'] = [{'action': big(2)}, {'action': big(6)}, {'action': {'type': 'Pass'}}]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 9.0, 1.0])

    def test_all_factory_artifact_needs_four_tokens_left_and_moweyds_institute_needs_tech_federation(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        player = {'faction': 'Xenos', 'resources': {'power': {'bowl1': 2, 'bowl2': 4, 'bowl3': 3}}}
        snapshot = {'player': 0, 'state': {'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'ExamineArtifact', 'artifact': 3}}, {'action': {'type': 'Pass'}}]}
        scores = [(9.0, 'art'), (2.0, 'pass')]
        self.assertEqual([s[0] for s in tp.artifact_tokens_scores(None, snapshot, scores)], [2.0, 9.0])  # 9-6 = 3 left
        player['resources']['power']['bowl1'] = 3                                                       # 4 left
        self.assertIs(tp.artifact_tokens_scores(None, snapshot, scores), scores)
        player['faction'] = 'Itars'
        self.assertEqual([s[0] for s in tp.artifact_tokens_scores(None, snapshot, scores)], [2.0, 9.0])
        self.assertIn('opening_res', tp._faction_parts('Moweyds'))
        self.assertEqual(tp.TECH_FEDERATION_OPENINGS['Moweyds'][0], '1PI+1TS')
        self.assertEqual(tp.LOST_FLEET_OPENINGS['Moweyds'][0], '1RL+4M')

    def test_all_factory_b19_nevlas_tile_and_taklons_power_order(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        self.assertIn('tile_prefs', tp._faction_parts('Nevlas'))
        player = {'faction': 'Nevlas', 'research_tracks': {}}
        state = {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player],
                 'research_board': {'tech_tile_slots': [6, 5, 8, 10, 9, 3, 4, 7, 2]}}            # 10 under Gaia
        up = lambda tile: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                           'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': None}}
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': up(10)}, {'action': up(3)}]}
        scores = [(9.0, 't10'), (4.0, 't3')]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 9.0])  # B19-S60
        player['faction'] = 'Taklons'
        power = lambda pid, **k: {'action': {'type': 'PowerAction', 'id': pid, **k}}
        snapshot = {'player': 0, 'state': state, 'candidates': [power(5), power(6, coord='2,0'), {'action': {'type': 'Pass'}}]}
        scores = [(9.0, 'k2'), (6.0, 'tf1'), (1.0, 'pass')]
        self.assertEqual([s[0] for s in tp.power_prefs_scores(None, snapshot, scores)], [6.0, 9.0, 1.0])  # 1 TF first
        scores = [(1.0, 'k2'), (6.0, 'tf1'), (9.0, 'pass')]
        self.assertIs(tp.power_prefs_scores(None, snapshot, scores), scores)                              # not a power move

    @staticmethod
    def far_start_snapshot(boosters=(), transdim=0):
        cell = lambda planet=None, owner=None, structures=(): {
            'planet': {'planet_type': planet, 'owner': None} if planet else None, 'structures': list(structures)}
        hexes = {'0,0': cell('Volcanic'), '1,0': cell('Desert'), '3,0': cell('Terra', structures=[{'owner': 1}]),
                 '4,0': cell('Volcanic'), '0,1': cell('Transdim' if transdim >= 1 else None),
                 '-1,0': cell('Transdim' if transdim >= 2 else None)}
        me = {'player_id': 0, 'faction': 'Geodens', 'structures': [{'hex': '-9,0'}], 'tech_tiles': [], 'covered_tech_tiles': [],
              'research_tracks': {'navigation': 0}}
        other = {'player_id': 1, 'faction': 'Terrans', 'structures': [{}]*9}
        state = {'round': 0, 'phase': {'Setup': {}}, 'players': [me, other], 'boosters': list(boosters),
                 'board': {'hexes': hexes}}
        place = lambda coord: {'action': {'type': 'PlaceStartingStructure', 'coord': coord}}
        return {'state': state, 'player': 0, 'candidates': [place('0,0'), place('4,0')]}

    def test_far_start_blocked_unless_cheap_mine_next_to_opponent_or_instant_gaia(self):
        from current_actions.conservation import blocked
        snapshot = self.far_start_snapshot()
        scores = [(5.0, 'far'), (4.0, 'near')]
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))     # gate off: unchanged
        tp._guide['mj01'] = True                                             # restored by setUp's cleanup
        # 1,0 is Desert, one step from Geodens' Volcanic, in reach 1 of the start and 2 hexes from the opponent at 3,0.
        self.assertEqual(tp.guide_r1_scores(snapshot, scores), scores)
        snapshot['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'   # three steps: not cheap
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))
        instant = self.far_start_snapshot(boosters=(5, 8), transdim=2)
        instant['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'
        self.assertEqual(tp.guide_r1_scores(instant, scores), scores)         # booster 5, two Transdim, no easy site
        instant['state']['board']['hexes']['-1,0']['planet'] = None           # one Transdim only
        self.assertTrue(blocked(tp.guide_r1_scores(instant, scores)[0]))
        instant['state']['board']['hexes']['-1,0']['planet'] = {'planet_type': 'Transdim', 'owner': None}
        instant['state']['boosters'] = [8]
        self.assertTrue(blocked(tp.guide_r1_scores(instant, scores)[0]))      # booster 5 not in the supply

    def test_all_factory_far_start_allowed_when_more_cheap_planets_within_base_reach_than_near_start(self):
        from current_actions.conservation import blocked
        snapshot = self.far_start_snapshot()
        hexes = snapshot['state']['board']['hexes']
        hexes['1,0']['planet']['planet_type'] = 'Ice'                       # no cheap-mine exception for the far start
        planet = lambda kind: {'planet': {'planet_type': kind, 'owner': None}, 'structures': []}
        hexes['5,0'] = planet('Desert')                                     # near start 4,0: room 1
        for coord in ('0,-1', '-1,1', '0,2'):
            hexes[coord] = planet('Volcanic')                               # far start 0,0: 2 within reach 1, 0,2 is 2 away
        scores = [(5.0, 'far'), (4.0, 'near')]
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))   # gate off: as before
        tp._guide['mj01'] = True
        self.assertEqual(tp.expansion_room(snapshot['state'], 0, '0,0'), 2)
        self.assertEqual(tp.expansion_room(snapshot['state'], 0, '4,0'), 1)
        self.assertEqual(tp.guide_r1_scores(snapshot, scores), scores)
        hexes['-1,1']['planet']['planet_type'] = 'Gaia'                     # not counted: room 1 == near room 1
        self.assertEqual(tp.expansion_room(snapshot['state'], 0, '0,0'), 1)
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))
        hexes['-1,1']['planet']['planet_type'] = 'Transdim'                 # not counted either
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))
        hexes['-1,1']['planet']['planet_type'] = 'Ice'                      # not cheap
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))

    def test_all_factory_expansion_room_counts_one_qic_landing_and_its_follow_ups(self):
        tp._guide['mj01'] = True
        snapshot = self.far_start_snapshot()
        state, hexes = snapshot['state'], snapshot['state']['board']['hexes']
        hexes['1,0']['planet']['planet_type'] = 'Ice'
        planet = lambda kind: {'planet': {'planet_type': kind, 'owner': None}, 'structures': []}
        hexes['0,2'], hexes['0,-2'] = planet('Volcanic'), planet('Volcanic')    # base 1, 2 away: one QIC lands on either
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 0)                 # no QIC: out of reach
        state['players'][0]['resources'] = {'qic': 1}
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 1)                 # two separate far planets: one landing, not two
        hexes['0,3'] = planet('Volcanic')                                       # next to 0,2: landing there, one follow-up
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 2)
        hexes['0,4'] = planet('Ice')                                            # not cheap: not a follow-up
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 2)
        hexes['0,5'] = planet('Volcanic')                                       # 3 from 0,2: not within base of the landing
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 2)
        state['players'][0]['resources'] = {'qic': 0}
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 0)

    def test_all_factory_expansion_room_ambas_base_reach_is_navigation_2(self):
        from faction_teachers.profiles import profiles
        tp._guide['mj01'] = True
        snapshot = self.far_start_snapshot()
        state, hexes = snapshot['state'], snapshot['state']['board']['hexes']
        state['players'][0]['faction'] = 'Ambas'
        home = profiles()['Ambas'].home
        hexes['4,0']['planet']['planet_type'] = 'Transdim'
        hexes['1,0']['planet']['planet_type'] = home
        hexes['0,2'] = {'planet': {'planet_type': home, 'owner': None}, 'structures': []}
        self.assertEqual(tp._base_reach(state['players'][0]), 2)
        self.assertEqual(tp.expansion_room(state, 0, '0,0'), 2)                 # 0,2 is 2 away: inside the base reach
        state['players'][0]['faction'] = 'Geodens'
        self.assertEqual(tp._base_reach(state['players'][0]), 1)                # others keep their current reach

    @staticmethod
    def ambas_nav2_snapshot(faction='Ambas', navigation=1, rnd=1):
        player = {'faction': faction, 'structures': [], 'research_tracks': {'navigation': navigation}}
        state = {'round': rnd, 'phase': {'ActionPhase': {}}, 'players': [player]}
        research = lambda track: {'action': {'type': 'ResearchAdvance', 'track': track}}
        return {'player': 0, 'state': state,
                'candidates': [research('Science'), research('Navigation'), {'action': {'type': 'Pass'}}]}

    def test_all_factory_ambas_navigation_2_leads_research_in_the_rl4m_and_ts6m_plans_only(self):
        from bgg_openings.catalog import parse_buildings
        scores = [(9.0, 'science'), (5.0, 'nav'), (1.0, 'pass')]
        plan = parse_buildings('1RL+4M')
        snapshot = self.ambas_nav2_snapshot()
        self.assertIs(tp.ambas_nav2_scores(snapshot, scores, plan), scores)         # gate off
        tp._guide['mj01'] = True
        self.assertEqual([s[0] for s in tp.ambas_nav2_scores(snapshot, scores, plan)], [5.0, 9.0, 1.0])
        self.assertEqual([s[0] for s in tp.ambas_nav2_scores(snapshot, scores, parse_buildings('1TS+6M'))], [5.0, 9.0, 1.0])
        self.assertIs(tp.ambas_nav2_scores(snapshot, scores, parse_buildings('1AC+2M')), scores)     # academy route
        self.assertIs(tp.ambas_nav2_scores(snapshot, scores, parse_buildings('1RL+1TS+2M')), scores)
        self.assertIs(tp.ambas_nav2_scores(self.ambas_nav2_snapshot(navigation=2), scores, plan), scores)
        self.assertIs(tp.ambas_nav2_scores(self.ambas_nav2_snapshot(rnd=2), scores, plan), scores)
        self.assertIs(tp.ambas_nav2_scores(self.ambas_nav2_snapshot(faction='Gleens'), scores, plan), scores)

    def test_all_factory_booster5_worth_income_only_unless_faction_rides_gaia_track(self):
        import guide_value as gv
        state = {'round': 0}
        player = {'faction': 'Ambas', 'research_tracks': {'gaia': 0}}
        full = gv.booster_value(state, 5)
        self.assertEqual(tp._booster_value(state, player, 5), full)          # gate off
        tp._guide['mj01'] = True
        self.assertNotIn('gaia', tp._faction_tracks(player))
        income = gv.to_vp(dict(state, round=1), tp.BOOSTER5_INCOME_ONLY)
        self.assertEqual(tp._booster_value(state, player, 5), income)
        self.assertLess(income, full)
        self.assertEqual(tp._booster_value(state, player, 8), gv.booster_value(state, 8))
        player['research_tracks']['gaia'] = 1
        self.assertEqual(tp._booster_value(state, player, 5), full)
        self.assertIn('gaia', tp._faction_tracks({'faction': 'SpaceGiants'}))
        self.assertEqual(tp._booster_value(state, {'faction': 'SpaceGiants', 'research_tracks': {'gaia': 0}}, 5), full)

    def test_all_factory_instant_gaia_spot_needs_two_transdim_and_at_most_one_easy_site(self):
        tp._guide['mj01'] = True
        snapshot = self.far_start_snapshot(boosters=(5,), transdim=2)         # 1,0 Desert: one easy site
        state, hexes = snapshot['state'], snapshot['state']['board']['hexes']
        self.assertTrue(tp.instant_gaia_spot(state, 0, ['0,0']))
        hexes['0,-1'] = {'planet': {'planet_type': 'Ice', 'owner': None}, 'structures': []}    # three steps: not cheap
        self.assertTrue(tp.instant_gaia_spot(state, 0, ['0,0']))
        hexes['0,-1']['planet']['planet_type'] = 'Desert'                      # second easy site
        self.assertFalse(tp.instant_gaia_spot(state, 0, ['0,0']))
        self.assertFalse(tp.instant_gaia_spot(state, 0, ['4,0']))              # measured from another spot: no Transdim in reach
        hexes['0,-1']['planet'] = None
        hexes['-1,0']['planet'] = None
        self.assertFalse(tp.instant_gaia_spot(state, 0, ['0,0']))              # one Transdim

    def test_all_factory_booster5_first_and_booster9_second_with_two_transdim_and_little_expansion(self):
        snapshot = self.far_start_snapshot(boosters=(5, 8, 9), transdim=2)
        snapshot['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'
        snapshot['state']['players'][0]['structures'] = [{'hex': '0,0', 'owner': 0}]
        snapshot['candidates'] = [{'action': {'type': 'SelectStartingBooster', 'booster_id': b}} for b in (8, 9, 5)]
        scores = [(9.0, 'b8'), (6.0, 'b9'), (4.0, 'b5')]
        self.assertIs(tp.start_booster5_scores(None, snapshot, scores), scores)   # gate off
        tp._guide['mj01'] = True
        self.assertEqual([s[0] for s in tp.start_booster5_scores(None, snapshot, scores)], [4.0, 6.0, 9.0])
        snapshot['candidates'] = [{'action': {'type': 'SelectStartingBooster', 'booster_id': b}} for b in (9, 8, 5)]
        scores = [(9.0, 'b9'), (6.0, 'b8'), (4.0, 'b5')]
        self.assertEqual([s[0] for s in tp.start_booster5_scores(None, snapshot, scores)], [6.0, 4.0, 9.0])
        snapshot['candidates'] = [{'action': {'type': 'SelectStartingBooster', 'booster_id': b}} for b in (8, 5)]
        scores = [(9.0, 'b8'), (4.0, 'b5')]
        self.assertEqual([s[0] for s in tp.start_booster5_scores(None, snapshot, scores)], [4.0, 9.0])   # no booster 9
        hexes = snapshot['state']['board']['hexes']
        hexes['-1,0']['planet'] = None
        self.assertIs(tp.start_booster5_scores(None, snapshot, scores), scores)   # one Transdim: unchanged
        hexes['-1,0']['planet'] = {'planet_type': 'Transdim', 'owner': None}
        hexes['1,0']['planet']['planet_type'] = 'Desert'
        hexes['0,-1'] = {'planet': {'planet_type': 'Desert', 'owner': None}, 'structures': []}
        self.assertIs(tp.start_booster5_scores(None, snapshot, scores), scores)   # two easy sites: unchanged

    def test_all_factory_bescods_lab_openings_and_no_round1_academy(self):
        self.assertNotIn('opening_res', tp._faction_parts('Bescods'))
        self.assertNotIn('building_limits', tp._faction_parts('Bescods'))
        tp._guide['mj01'] = True
        self.assertIn('building_limits', tp._faction_parts('Bescods'))
        self.assertEqual(tp.guide_opening_labels('Bescods', {})[:2], ('1RL+1TS+2M', '1RL+2M'))
        self.assertNotIn('1AC+2M', tp.guide_opening_labels('Bescods', {}))
        player = {'faction': 'Bescods'}
        up = lambda to: {'type': 'Upgrade', 'coord': '0,0', 'to': to}
        snapshot = {'player': 0, 'state': {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': up({'Academy': 'Science'})}, {'action': up('ResearchLab')}]}
        scores = [(9.0, 'ac'), (4.0, 'rl')]
        self.assertEqual([s[0] for s in tp.building_limits_scores(None, snapshot, scores)], [4.0, 9.0])
        snapshot['state']['round'] = 2
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)

    def test_all_factory_knowledge_to_credit_blocked_when_better_options_exist(self):
        from current_actions.conservation import blocked
        free = lambda kind, count=2: {'action': {'type': 'FreeAction', 'kind': kind, 'count': count}}
        player = {'faction': 'Geodens'}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]}
        snapshot = {'player': 0, 'state': state, 'candidates': [free('KnowledgeToCredit'), {'action': {'type': 'Pass'}}]}
        scores = [(5.0, 'k2c'), (1.0, 'pass')]
        tp._guide['mj01'] = True
        self.assertEqual(tp.knowledge_to_credit_scores(None, snapshot, scores), scores)   # nothing better open
        snapshot['candidates'].append({'action': {'type': 'ResearchAdvance', 'track': 'Economy'}})
        self.assertTrue(blocked(tp.knowledge_to_credit_scores(None, snapshot, scores + [(2.0, 'r')])[0]))
        snapshot['candidates'][2] = free('PowerToCredit', 1)
        self.assertFalse(blocked(tp.knowledge_to_credit_scores(None, snapshot, scores + [(2.0, 'p')])[0]))  # count differs
        snapshot['candidates'][2] = free('OreToCredit', 2)
        self.assertTrue(blocked(tp.knowledge_to_credit_scores(None, snapshot, scores + [(2.0, 'o')])[0]))
        tp._guide['mj01'] = False                                                       # gate off: unchanged
        self.assertFalse(blocked(tp.knowledge_to_credit_scores(None, snapshot, scores + [(2.0, 'o')])[0]))

    def test_all_factory_sh11_gaia_vp_tile_not_first_and_gaia1_for_asteroid(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        player = {'faction': 'Gleens', 'research_tracks': {'navigation': 1}, 'tech_tiles': [], 'covered_tech_tiles': []}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]}
        up = lambda tile: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                           'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': None}}
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': up(8)}, {'action': up(2)}]}
        scores = [(9.0, 't8'), (4.0, 't2')]
        self.assertEqual([s[0] for s in tp.range_tile_scores(None, snapshot, scores)], [4.0, 9.0])
        player['tech_tiles'] = [5]                                              # not the first tile any more
        self.assertIs(tp.range_tile_scores(None, snapshot, scores), scores)
        # Round 3, first tile, 12 = 9, 8 = 8, 2 = 4: both avoidances hold, tile 2 leads (debate 1/1).
        player['tech_tiles'], state['round'] = [], 3
        snapshot['candidates'] = [{'action': up(12)}, {'action': up(8)}, {'action': up(2)}]
        scores = [(9.0, 't12'), (8.0, 't8'), (4.0, 't2')]
        self.assertEqual([s[0] for s in tp.range_tile_scores(None, snapshot, scores)], [4.0, 8.0, 9.0])
        state['round'] = 2
        xenos = {'faction': 'Taklons', 'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()}}
        self.assertEqual(tp._track_caps(xenos, table=False)['gaia'], 1)        # Gaia only for the former
        giants = {'faction': 'SpaceGiants', 'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()}}
        self.assertNotIn('gaia', tp._track_caps(giants, table=False))          # Gaia forming is their track (MJ01-13)
        original = tp._reach_targets
        try:
            tp._reach_targets = lambda state, player, types: [('3,3', {'planet_type': 'Asteroid'}, 0, 0)]
            lone = dict(xenos, structures=[{'kind': 'Mine', 'hex': '0,0'}], gaiaformers_total=0)
            self.assertTrue(tp._asteroid_gaia({'players': [lone]}, lone))
            self.assertFalse(tp._asteroid_gaia({'players': [lone]}, dict(lone, gaiaformers_total=1)))
            # No Asteroid in reach now, but booster 5 forms a reachable Transdim planet with an Asteroid next to it (user).
            tp._reach_targets = lambda state, player, types: (
                [('2,0', {'planet_type': 'Transdim'}, 0, 0)] if types == ('Transdim',) else [])
            import economy.teacher as et
            distance = et.path_distance
            et.path_distance = lambda state, starts, coord: 3          # Transdim → Asteroid 3 hexes
            board = {'hexes': {'4,0': {'planet': {'planet_type': 'Asteroid', 'owner': None}, 'structures': []}}}
            later = dict(lone, booster=5, research_tracks=dict(lone['research_tracks'], navigation=1),
                         tech_tiles=[], covered_tech_tiles=[], resources={'qic': 1})
            try:
                self.assertTrue(tp._asteroid_gaia({'players': [later], 'board': board}, later))   # range 1 + 1 QIC
                self.assertFalse(tp._asteroid_gaia({'players': [later], 'board': board}, dict(later, resources={'qic': 0})))
                self.assertFalse(tp._asteroid_gaia({'players': [later], 'board': board}, dict(later, booster=1)))
            finally:
                et.path_distance = distance
        finally:
            tp._reach_targets = original

    def test_all_factory_plan_cost_sums_the_upgrade_chain_and_counts_power_conversions(self):
        from four_factions.preparation import Goal
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        player = {'faction': 'Xenos', 'player_id': 0, 'research_tracks': {}, 'structures': [{'kind': 'Mine', 'hex': '0,0'}],
                  'resources': {'ore': 0, 'credits': 0, 'knowledge': 0, 'qic': 0,
                                'power': {'bowl1': 0, 'bowl2': 0, 'bowl3': 0}}}
        state = {'board': {'hexes': {'0,0': {'structures': []}}}, 'players': [player]}
        snapshot = {'player': 0, 'state': state}
        cost, after = tp._upgrade_chain_cost(snapshot, player, Goal('PI@0,0', 'upgrade', '0,0', 'PlanetaryInstitute'))
        self.assertEqual(cost, {'ore': 6, 'credits': 12})                       # TS 2+6 (no neighbour) + PI 4+6
        self.assertEqual(after['structures'][0]['kind'], 'PlanetaryInstitute')
        # Firaks lab → downgrade → lab from a trading station: both labs paid (debate 1/1).
        firaks = dict(player, faction='Firaks', structures=[{'kind': 'TradingStation', 'hex': '0,0'}])
        state['players'] = [firaks]
        lab = Goal('ResearchLab@0,0', 'upgrade', '0,0', 'ResearchLab')
        cycle = Goal('Firaks-lab-downgrade-rebuild@0,0', 'ordered',
                     steps=(lab, Goal('FiraksDowngradeResearchLab@0,0', 'faction-action', '0,0', 'FiraksDowngradeResearchLab'), lab))
        self.assertEqual(tp._plan_cost(snapshot, cycle), {'ore': 6, 'credits': 10})
        state['players'] = [player]
        originals = tp._menu_multi_step, tp._plan_cost, tp._plan_budget
        try:
            tp._menu_multi_step = lambda snapshot, goal: True
            tp._plan_cost = lambda snapshot, goal: {'knowledge': 4}
            tp._plan_budget = lambda state, player: {'knowledge': 2}
            nevlas = dict(player, faction='Nevlas', resources=dict(player['resources'], power={'bowl1': 0, 'bowl2': 0, 'bowl3': 2}))
            state['players'] = [nevlas]
            self.assertTrue(tp.plan_affordable(snapshot, None))                    # 2 short, 2 tokens to the Gaia area
            nevlas['faction'] = 'Xenos'
            self.assertFalse(tp.plan_affordable(snapshot, None))                   # 8 power needed, 2 held
            # Nevlas institute: 1 ore short = 3 power = 2 tokens at 2 power each (debate 1/1).
            tp._plan_cost = lambda snapshot, goal: {'ore': 1}
            tp._plan_budget = lambda state, player: {'ore': 0}
            nevlas.update(faction='Nevlas', structures=[{'kind': 'PlanetaryInstitute', 'hex': '0,0'}])
            self.assertTrue(tp.plan_affordable(snapshot, None))
            nevlas['structures'] = [{'kind': 'Mine', 'hex': '0,0'}]
            self.assertFalse(tp.plan_affordable(snapshot, None))                   # no institute: 3 tokens needed
            # Mixed shortfall with the institute: ore 2 tokens + credit 1 token = 3 > 2 (odd remainders lost).
            tp._plan_cost = lambda snapshot, goal: {'ore': 1, 'credits': 1}
            tp._plan_budget = lambda state, player: {}
            nevlas['structures'] = [{'kind': 'PlanetaryInstitute', 'hex': '0,0'}]
            self.assertFalse(tp.plan_affordable(snapshot, None))
        finally:
            tp._menu_multi_step, tp._plan_cost, tp._plan_budget = originals
        # Public check (debate 1/1): Firaks with the lab standing, 'downgrade → lab' is two pending steps and the
        # rebuild (3 ore, 5 credits) is checked against the budget.
        firaks = dict(player, faction='Firaks', structures=[{'kind': 'ResearchLab', 'hex': '0,0'}],
                      resources=dict(player['resources'], ore=1, credits=1))
        state['players'] = [firaks]
        rebuild = Goal('Firaks-lab-downgrade-rebuild@0,0', 'ordered', steps=(
            Goal('FiraksDowngradeResearchLab@0,0', 'faction-action', '0,0', 'FiraksDowngradeResearchLab'), lab))
        family, budget = tp._menu_family, tp._plan_budget
        try:
            tp._menu_family = lambda snapshot, goal: 'ability'
            tp._plan_budget = lambda state, player: {'ore': 1, 'credits': 1}
            self.assertEqual(tp._pending_steps(snapshot, rebuild), 2)
            self.assertFalse(tp.plan_affordable(snapshot, rebuild))
            tp._plan_budget = lambda state, player: {'ore': 3, 'credits': 5}
            self.assertTrue(tp.plan_affordable(snapshot, rebuild))
        finally:
            tp._menu_family, tp._plan_budget = family, budget

    def test_all_factory_range_tile_early_only_and_stops_navigation(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        player = {'faction': 'Gleens', 'research_tracks': {'navigation': 1}, 'tech_tiles': [], 'covered_tech_tiles': []}
        state = {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player]}
        up = lambda tile: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                           'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': None}}
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': up(5)}, {'action': up(12)}]}
        scores = [(9.0, 't5'), (4.0, 't12')]
        self.assertEqual([s[0] for s in tp.range_tile_scores(None, snapshot, scores)], [4.0, 9.0])
        state['round'] = 3
        scores = [(4.0, 't5'), (9.0, 't12')]
        self.assertEqual([s[0] for s in tp.range_tile_scores(None, snapshot, scores)], [9.0, 4.0])
        self.assertNotIn('navigation', tp._track_caps(player, table=False))
        player['tech_tiles'] = [12]
        self.assertEqual(tp._track_caps(player, table=False)['navigation'], 1)

    def test_all_factory_tfmars_instant_gaia_needs_entry_free_action_power_and_former(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup
        levels = {t: 0 for t in tp.TRACK_KEYS.values()}
        player = {'faction': 'Taklons', 'research_tracks': levels, 'explored_ships': [2],
                  'gaiaformers_total': 1, 'gaiaformers_deployed': 0, 'gaiaformers_in_gaia_area': 0,
                  'resources': {'power': {'bowl1': 2, 'bowl2': 2, 'bowl3': 2}, 'spent_gaia_formers': 0}}
        state = {'round': 2, 'used_spaceship_actions': [], 'players': [player]}
        self.assertTrue(tp._tfmars_gaia_ready(state, player))
        self.assertIn(('gaia', 1), tp._plan_tracks(state, 0))                  # Taklons Gaia 1 once on T F Mars
        state['used_spaceship_actions'] = [6]
        self.assertFalse(tp._tfmars_gaia_ready(state, player))
        state['used_spaceship_actions'] = []
        player['gaiaformers_total'] = 0
        self.assertFalse(tp._tfmars_gaia_ready(state, player))
        player['explored_ships'] = []
        self.assertNotIn('gaia', [t for t, _ in tp._plan_tracks(state, 0)])
        # Payable as the engine counts it (debate 1/1): a Brainstone in area III, Nevlas' institute half cost.
        player.update(explored_ships=[2], gaiaformers_total=1)
        player['resources']['power'] = {'bowl1': 3, 'bowl2': 2, 'bowl3': 0, 'brainstone': 'Area3'}
        self.assertTrue(tp._tfmars_gaia_ready(state, player))
        player['resources']['power'] = {'bowl1': 3, 'bowl2': 2, 'bowl3': 1}
        self.assertFalse(tp._tfmars_gaia_ready(state, player))
        player.update(faction='Nevlas', structures=[{'kind': 'PlanetaryInstitute', 'hex': '0,0'}])
        self.assertTrue(tp._tfmars_gaia_ready(state, player))
        self.assertEqual(tp._tfmars_tokens(player), 1)

    def _asteroid_hold(self, faction, rnd=1, mj01=True, transdim=True):
        from current_actions.conservation import blocked
        tp._guide['mj01'] = mj01                           # restored by setUp's cleanup
        hexes = {'0,0': {'planet': {'planet_type': 'Asteroid', 'is_gaia_formed': False}},
                 '1,0': {'planet': {'planet_type': 'Red', 'is_gaia_formed': False}}}
        state = {'round': rnd, 'phase': {'ActionPhase': {}}, 'board': {'hexes': hexes},
                 'players': [{'faction': faction}]}
        snapshot = {'player': 0, 'state': state, 'candidates': [
            {'action': {'type': 'Build', 'coord': '0,0'}}, {'action': {'type': 'Build', 'coord': '1,0'}}]}
        scores = [(5.0, 'asteroid'), (4.0, 'red')]
        with mock.patch.object(tp, '_reach_targets', return_value=[('2,0', {}, 0, 0)] if transdim else []):
            out = tp.gaia_asteroid_hold_scores(None, snapshot, scores)
        return scores, out, blocked

    def test_gaia_asteroid_hold_blocks_the_asteroid_build_while_a_transdim_planet_is_in_reach(self):
        scores, out, blocked = self._asteroid_hold('Itars')
        self.assertTrue(blocked(out[0]))
        self.assertEqual(out[1], scores[1])
        self.assertEqual(scores[0], (5.0, 'asteroid'))     # input untouched

    def test_gaia_asteroid_hold_leaves_scores_without_transdim_late_rounds_other_factions_and_no_mj01(self):
        for kwargs in ({'faction': 'Itars', 'transdim': False}, {'faction': 'Itars', 'rnd': 4},
                       {'faction': 'Geodens'}, {'faction': 'Itars', 'mj01': False}):
            scores, out, _ = self._asteroid_hold(**kwargs)
            self.assertEqual(out, scores, kwargs)

    def test_gaia_riders_are_the_factions_with_a_gaia_guide_track(self):
        self.assertEqual(tp.GAIA_RIDERS, {'Xenos', 'Terrans', 'Gleens', 'Itars', 'Firaks', 'BalTaks'})

    def _dead_tile(self, faction, structures=(), tracks=None, mj01=True):
        tp._guide['mj01'] = mj01                           # restored by setUp's cleanup
        player = {'faction': faction, 'structures': list(structures), 'research_tracks': tracks or {}}
        state = {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player],
                 'research_board': {'tech_tile_slots': [10, 3, 6, 5, 2, 7, 9, 8, 4]}}
        up = lambda tile: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                           'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': None}}
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': up(3)}, {'action': up(5)}]}
        scores = [(9.0, 'tile3'), (4.0, 'tile5')]
        return scores, tp.dead_tile_scores(None, snapshot, scores)

    def test_dead_tile_baltaks_navigation_tile_yields_before_the_institute(self):
        scores, out = self._dead_tile('BalTaks')
        self.assertGreater(out[1][0], out[0][0])
        self.assertEqual((out[1][0], out[0][0]), (9.0, 4.0))
        self.assertIn('dead_tile', out[1][1])

    def test_dead_tile_any_faction_with_the_column_track_at_5_is_swapped(self):
        scores, out = self._dead_tile('Geodens', tracks={'navigation': 5})
        self.assertGreater(out[1][0], out[0][0])

    def test_dead_tile_leaves_live_columns_institute_and_no_mj01_alone(self):
        for kwargs in ({'faction': 'BalTaks', 'structures': [{'kind': 'PlanetaryInstitute', 'hex': '0,0'}]},
                       {'faction': 'Geodens', 'tracks': {'navigation': 4}}, {'faction': 'BalTaks', 'mj01': False}):
            scores, out = self._dead_tile(**kwargs)
            self.assertEqual(out, scores, kwargs)

    def test_all_factory_taklons_charge4_tile_unless_under_gaia_and_xenos_ai_late(self):
        tp._guide['mj01'] = True                           # restored by setUp's cleanup (ALL_FACTION_PARTS on)
        player = {'faction': 'Taklons', 'research_tracks': {}}
        state = {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player],
                 'research_board': {'tech_tile_slots': [6, 10, 8, 2, 9, 3, 4, 7, 5]}}
        up = lambda tile: {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                           'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': None}}
        snapshot = {'player': 0, 'state': state, 'candidates': [{'action': up(3)}, {'action': up(10)}, {'action': up(5)}]}
        scores = [(9.0, 't3'), (4.0, 't10'), (6.0, 't5')]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [4.0, 9.0, 6.0])  # charge-4 leads
        state['research_board']['tech_tile_slots'] = [6, 5, 8, 10, 9, 3, 4, 7, 2]                       # 10 under Gaia
        scores = [(9.0, 't3'), (8.0, 't10'), (6.0, 't5')]
        self.assertEqual([s[0] for s in tp.tile_prefs_scores(None, snapshot, scores)], [6.0, 8.0, 9.0])  # K2: tile 5
        xenos = {'faction': 'Xenos', 'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()}}
        research = lambda track: {'action': {'type': 'ResearchAdvance', 'track': track}}
        snap = {'player': 0, 'state': {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [xenos],
                                       'research_board': {'advanced_tech_tiles': [1, 2, 3, 5, 6, 9]}},
                'candidates': [research('ArtificialIntelligence'), research('Navigation')]}
        lifted = tp.track_set_scores(None, snap, [(9.0, 'ai'), (5.0, 'nav')])
        self.assertEqual([s[0] for s in lifted], [5.0, 9.0])                  # AI late
        snap['state']['research_board']['advanced_tech_tiles'][2] = 11          # X4: a good tile on AI
        self.assertEqual([s[0] for s in tp.track_set_scores(None, snap, [(9.0, 'ai'), (5.0, 'nav')])], [9.0, 5.0])

    def test_niche_tracks_for_hadsch_hallas_and_xenos(self):
        tp._guide.update(byfaction=True, faction_guide=True)   # restored by setUp's cleanup
        lv = lambda **k: {**{t: 0 for t in tp.TRACK_KEYS.values()}, **k}
        me = {'faction': 'HadschHallas', 'research_tracks': lv(economy=2)}
        rival = {'faction': 'Geodens', 'research_tracks': lv(terraforming=3, gaia=0, ai=1)}
        state = {'round': 3, 'phase': {'ActionPhase': {}}, 'players': [me, rival]}
        research = lambda t: {'action': {'type': 'ResearchAdvance', 'track': t}}
        snapshot = {'player': 0, 'state': state,
                    'candidates': [research('Economy'), research('Terraforming'), research('GaiaProject')]}
        scores = [(9.0, 'eco'), (6.0, 'tf'), (2.0, 'gaia')]
        self.assertEqual([s[0] for s in tp.niche_tracks_scores(None, snapshot, scores)], [2.0, 6.0, 9.0])
        me['research_tracks'] = lv(economy=1)                                  # before Economy 2 / Navigation 2
        self.assertIs(tp.niche_tracks_scores(None, snapshot, scores), scores)
        me.update(faction='Xenos', research_tracks=lv())                        # no Gaia faction: Gaia leads
        self.assertEqual([s[0] for s in tp.niche_tracks_scores(None, snapshot, scores)], [2.0, 6.0, 9.0])
        rival['faction'] = 'Terrans'                                            # a Gaia faction plays: untouched
        self.assertIs(tp.niche_tracks_scores(None, snapshot, scores), scores)

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
        player['faction'] = 'HadschHallas'
        state['round'] = 2
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # weak_factions off
        tp._guide['weak_factions'] = True
        self.assertEqual([s[0] for s in tp.building_limits_scores(None, snapshot, scores)], [4.0, 7.0, 9.0])
        state['round'] = 3
        self.assertIs(tp.building_limits_scores(None, snapshot, scores), scores)   # institute from round 3

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

    @staticmethod
    def track_plan_state(rival='Taklons'):
        empty = {'planet': None, 'structures': [], 'satellites': []}
        hexes = {f'{q},{r}': dict(empty) for q in range(-4, 5) for r in range(-4, 5)}
        hexes['0,0'] = {**empty, 'planet': {'planet_type': 'Terra', 'owner': 0, 'is_gaia_formed': False},
                        'structures': [{'kind': 'Mine', 'owner': 0}]}
        hexes['2,0'] = {**empty, 'planet': {'planet_type': 'Desert', 'owner': None, 'is_gaia_formed': False}}
        hexes['0,1'] = {**empty, 'planet': {'planet_type': 'Transdim', 'owner': None, 'is_gaia_formed': False}}
        terrans = {'faction': 'Terrans', 'player_id': 0, 'passed': False,
                   'research_tracks': {'terraforming': 0, 'navigation': 0, 'ai': 0, 'gaia': 1, 'economy': 0, 'science': 0},
                   'resources': {'ore': 4, 'credits': 10, 'knowledge': 4, 'qic': 0, 'spent_gaia_formers': 0,
                                 'power': {'bowl1': 4, 'bowl2': 4, 'bowl3': 0, 'gaia_forming': 0}},
                   'structures': [{'kind': 'Mine', 'hex': '0,0'}], 'tech_tiles': [], 'covered_tech_tiles': [],
                   'booster': None, 'artifacts': [],
                   'gaiaformers_total': 1, 'gaiaformers_deployed': 0, 'gaiaformers_in_gaia_area': 0}
        other = {'faction': rival, 'player_id': 1, 'structures': [], 'research_tracks': {'navigation': 0},
                 'tech_tiles': [], 'covered_tech_tiles': [], 'resources': {'qic': 0}}
        return {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [terrans, other], 'board': {'hexes': hexes},
                'research_board': {'economy_research_tile_side': 'Power', 'advanced_tech_tiles': [0]*6}}

    def test_track_plans_follow_the_faction_tracks_and_open_colonies(self):
        state = self.track_plan_state()
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        self.assertEqual(tp.track_plan_goals(snapshot), [])                           # part off
        tp._guide['track_plans'] = True                                               # restored by setUp's cleanup
        # Terrans without a Gaia rival (T2): Navigation 2 → Science 4 → Economy; Navigation 2 reaches 2,0.
        self.assertEqual(tp._plan_tracks(state, 0), [('navigation', 2), ('science', 2), ('economy', 2)])
        plans = tp.track_plan_goals(snapshot)
        names = [p.name for p in plans]
        self.assertEqual(names[:3], ['track-plan-Navigation-2>colony@2,0', 'track-plan-Science-2', 'track-plan-Economy-2'])
        self.assertEqual([s.family for s in plans[0].steps], ['research', 'colony'])
        self.assertEqual((plans[0].steps[0].target, plans[0].steps[0].level, plans[0].steps[1].coord), ('Navigation', 2, '2,0'))
        # Off the guide list only with a colony: AI 1's QIC reaches 2,0, the free former takes the transdim 0,1;
        # Terraforming 1 opens nothing (same ore per step) and gets no plan.
        self.assertIn('track-plan-ArtificialIntelligence-1>colony@2,0', names)
        self.assertIn('track-plan-GaiaProject-2>colony@0,1', names)
        self.assertFalse(any('Terraforming' in n for n in names))
        self.assertTrue(all(p.family == 'ordered' and 'track_plans' in p.sources for p in plans))
        # With a Gaia rival the Gaia plan follows Navigation (T2); a cap closes a track (BalTaks AI 4).
        rival = self.track_plan_state(rival='BalTaks')
        self.assertEqual(tp._plan_tracks(rival, 0)[1], ('gaia', 2))
        self.assertEqual(tp.track_plan_goals({'player': 0, 'state': rival, 'candidates': []})[1].name,
                         'track-plan-GaiaProject-2>colony@0,1')
        state['players'][0]['faction'] = 'BalTaks'
        state['players'][0]['research_tracks']['ai'] = 4
        self.assertNotIn('ai', [t for t, _ in tp._plan_tracks(state, 0)])
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('gaia', 4))                  # TRACK_STEPS round target leads
        state['round'] = 6
        self.assertEqual(tp.track_plan_goals(snapshot), [])                           # round 6 is free

    def test_round_tile_lead_moves_the_goals_the_tile_scores_to_the_front(self):
        from four_factions.preparation import Goal
        state = self.track_plan_state()
        player = state['players'][0]
        player['structures'] = [{'kind': 'Mine', 'hex': '0,0'}, {'kind': 'TradingStation', 'hex': '1,0'}]
        state['board']['hexes']['1,0'] = {**state['board']['hexes']['1,0'],
                                          'planet': {'planet_type': 'Terra', 'owner': 0, 'is_gaia_formed': False}}
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        goals = [Goal('Economy-2', 'research', target='Economy', level=2),
                 Goal('Science@0,0', 'upgrade', '0,0', 'Science'), Goal('Science@1,0', 'upgrade', '1,0', 'Science'),
                 Goal('PlanetaryInstitute@1,0', 'upgrade', '1,0', 'PlanetaryInstitute'),
                 Goal('colony@2,0', 'colony', '2,0'), Goal('colony@3,0', 'colony', '3,0'),
                 Goal('three-federations-separate-cores', 'federations')]
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        tile = lambda condition: [{'condition': condition, 'vp_per_unit': 2}]*6
        state['round_tiles'] = tile('UpgradeTradingStation')
        self.assertIs(tp.round_tile_lead_goals(snapshot, goals), goals)             # part off
        tp._guide['round_tile_lead'] = True                                          # restored by setUp's cleanup
        first = lambda: [g.name for g in tp.round_tile_lead_goals(snapshot, goals)[:2]]
        self.assertEqual(first(), ['Science@0,0', 'Economy-2'])                      # the mine's upgrade leads
        state['round_tiles'] = tile('UpgradeResearchLab')
        self.assertEqual(first(), ['Science@1,0', 'Economy-2'])
        state['round_tiles'] = tile('UpgradeLargeBuilding')
        self.assertEqual(first(), ['PlanetaryInstitute@1,0', 'Economy-2'])
        state['round_tiles'] = tile('ResearchAdvance')
        self.assertEqual(first(), ['Economy-2', 'Science@0,0'])
        state['round_tiles'] = tile('BuildMineOnGaia')
        self.assertEqual(first(), ['colony@3,0', 'Economy-2'])
        state['round_tiles'] = tile('BuildMineOnNewPlanetType')
        self.assertEqual(first(), ['colony@2,0', 'colony@3,0'])                      # Desert and Gaia are new, Terra is not
        state['round_tiles'] = tile('TerraformingStep')
        self.assertEqual(first(), ['colony@2,0', 'Economy-2'])                       # Terra → Desert takes steps, Gaia none
        state['round_tiles'] = tile('FormFederation')
        self.assertEqual(first(), ['three-federations-separate-cores', 'Economy-2'])
        state['round_tiles'] = tile('BuildMine')
        self.assertEqual(first(), ['colony@2,0', 'colony@3,0'])
        state['round'] = 7                                                           # no tile: untouched
        self.assertIs(tp.round_tile_lead_goals(snapshot, goals), goals)

    def test_task_dedup_drops_a_regenerated_remembered_plan_without_the_menu(self):
        """E90, A arm: goals_for proposes the remembered plan again; search inserts it at goals[0] too. The wrapped
        scoring_pairs (called right after) drops the later copy from search's own list; a same-name plan with other
        steps stays; the roots list drops what goals / pairs hold; other interleave calls pass through."""
        import four_factions.preparation as p
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families', 'scoring_pairs'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        step_a, step_b = Goal('colony@2,0', 'colony', '2,0'), Goal('colony@3,0', 'colony', '3,0')
        remembered = Goal('track-plan-Economy-2', 'ordered', steps=(Goal('Economy-2', 'research'), step_a))
        other = Goal('track-plan-Economy-2', 'ordered', steps=(Goal('Economy-2', 'research'), step_b))
        again = Goal('track-plan-Economy-2', 'ordered', steps=(Goal('Economy-2', 'research'), step_a))
        root1 = Goal('root-1', 'root', first=1)
        p.goals_for = lambda snapshot, **kwargs: [again, other]
        p.interleave_families = lambda items, family: list(items)
        p.scoring_pairs = lambda snapshot, scores, goals: [root1, remembered]
        tp.install_task_dedup()
        tp.install_task_dedup()                                                      # installs once
        self.assertTrue(p.scoring_pairs._task_dedup_outer)
        goals = p.interleave_families(p.goals_for({}), lambda g: g.family)
        goals.insert(0, remembered)                                                  # as search does
        paired = p.scoring_pairs({}, [], goals)
        self.assertEqual(goals, [remembered, other])                                 # in place
        self.assertEqual(paired, [root1])
        roots = [root1, Goal('root-2', 'root', first=2)]
        self.assertEqual([g.name for g in p.interleave_families(roots, None)], ['root-2'])
        self.assertEqual(p.interleave_families(roots, None), roots)                  # consumed: next call untouched
        self.assertEqual(p.interleave_families([3, 1], None), [3, 1])

    def _exec_dedup(self, mj01, goals_in, pairs_out=()):
        """goals_for -> insert nothing -> scoring_pairs, with the mj01 gate on or off; returns (goals, paired)."""
        import four_factions.preparation as p
        for name in ('goals_for', 'interleave_families', 'scoring_pairs'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(tp._guide.__setitem__, 'mj01', tp._guide['mj01'])
        tp._guide['mj01'] = mj01
        snapshot = {'state': {'players': {0: {'faction': 'Terrans'}}}, 'player': 0}
        p.goals_for = lambda snapshot, **kwargs: list(goals_in)
        p.interleave_families = lambda items, family: list(items)
        p.scoring_pairs = lambda snapshot, scores, goals: list(pairs_out)
        tp.install_task_dedup()
        goals = p.goals_for(snapshot)
        paired = p.scoring_pairs(snapshot, [], goals)
        return goals, paired

    def test_task_dedup_execution_key_with_the_gate_on(self):
        """ships_menu1_all: plans that differ only by name / sources are one comparison (the first stays); a different
        steps / first / family keeps both; the B19 source flag steers viable(), so it stays in the key."""
        from four_factions.preparation import Goal
        step = Goal('colony@2,0', 'colony', '2,0')
        a = Goal('BGG-R1-1RL+2M', 'sequence', steps=(step,), sources=('x',))
        b = Goal('BalTaks-former-QIC-then-expand', 'sequence', steps=(Goal('other-name', 'colony', '2,0'),), sources=('y',))
        goals, _ = self._exec_dedup(True, [a, b])
        self.assertEqual(goals, [a])
        c = Goal('c', 'sequence', steps=(Goal('colony@3,0', 'colony', '3,0'),))
        d = Goal('d', 'sequence', steps=(step,), first=4)
        goals, _ = self._exec_dedup(True, [a, c, d])
        self.assertEqual(goals, [a, c, d])
        goals, _ = self._exec_dedup(True, [a, Goal('e', 'sequence', steps=(step,), sources=('B19',))])
        self.assertEqual(len(goals), 2)
        goals, paired = self._exec_dedup(True, [a], pairs_out=[b, d])           # the pairs drop what goals hold
        self.assertEqual(paired, [d])

    def test_task_dedup_name_only_difference_stays_with_the_gate_off(self):
        from four_factions.preparation import Goal
        step = Goal('colony@2,0', 'colony', '2,0')
        a = Goal('one', 'sequence', steps=(step,), sources=('x',))
        b = Goal('two', 'sequence', steps=(step,), sources=('y',))
        goals, paired = self._exec_dedup(False, [a, b], pairs_out=[Goal('three', 'sequence', steps=(step,))])
        self.assertEqual(goals, [a, b])
        self.assertEqual(len(paired), 1)

    def _setup_tasks(self, mj01, kind='PlaceStartingStructure', places=5, plans=3):
        """The comparison set search builds for a decision with `places` candidates, wrapped as in the all factory."""
        import four_factions.preparation as p
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families', 'scoring_pairs'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(tp._guide.__setitem__, 'mj01', tp._guide['mj01'])
        self.addCleanup(lambda saved=list(budget_teacher.budget_hooks): budget_teacher.budget_hooks.__setitem__(slice(None), saved))
        tp._guide['mj01'] = mj01
        tp.install_setup_places()
        tp.install_setup_places()                                                    # once
        self.assertEqual(budget_teacher.budget_hooks.count(tp.setup_places_budget), 1)
        snapshot = {'state': {'players': {0: {'faction': 'Terrans'}}}, 'player': 0,
                    'candidates': [{'action': {'type': kind, 'coord': f'{i},0'}} for i in range(places)]}
        scores = [(10.0-i, f's{i}') for i in range(places)]
        plan_goals = [Goal(f'plan-{n}', 'sequence', steps=(Goal(f'colony@{n},0', 'colony', f'{n},0'),)) for n in range(plans)]
        p.goals_for = lambda snapshot, **kwargs: list(plan_goals)
        p.interleave_families = lambda items, family: list(items)
        p.scoring_pairs = lambda snapshot, scores, goals: []
        tp.install_task_dedup()
        goals = p.interleave_families(p.goals_for(snapshot), lambda g: g.family)
        paired = p.scoring_pairs(snapshot, scores, goals)
        roots = [Goal(f'root-{i}', 'root', first=i) for i in range(1, places)]
        tasks = [Goal('current-choice', first=0), *goals, *p.interleave_families(roots, lambda g: g.family), *paired]
        return snapshot, scores, tasks

    def test_setup_places_every_open_place_is_one_comparison_with_the_gate_on(self):
        snapshot, scores, tasks = self._setup_tasks(True)
        budget = budget_teacher.budget_for(snapshot, scores, 4)
        self.assertEqual(budget, 5)                                                  # max(spec 4, 5 places)
        self.assertEqual(budget_teacher.budget_for(snapshot, scores, 8), 8)
        self.assertEqual(len(tasks), 5)
        self.assertEqual([t.first for t in tasks], [0, 1, 2, 3, 4])                  # control + root-1..4, no repeated place
        from current_actions.conservation import BLOCKED, PREFIX
        scores[3] = (BLOCKED, PREFIX+'blocked')
        self.assertEqual(budget_teacher.budget_for(snapshot, scores, 2), 4)          # blocked places are not counted

    def test_setup_places_other_decisions_and_gate_off_are_unchanged(self):
        snapshot, scores, tasks = self._setup_tasks(True, kind='Upgrade')
        self.assertEqual(budget_teacher.budget_for(snapshot, scores, 4), 4)
        self.assertEqual([t.name for t in tasks][:4], ['current-choice', 'plan-0', 'plan-1', 'plan-2'])
        snapshot, scores, tasks = self._setup_tasks(False)
        self.assertEqual(budget_teacher.budget_for(snapshot, scores, 4), 4)
        self.assertEqual(len(tasks), 1+3+4)                                          # the plans stay with the gate off

    def test_setup_places_keeps_ordered_plans_whose_first_move_is_not_predictable(self):
        import four_factions.preparation as p
        from four_factions.preparation import Goal
        snapshot, scores, tasks = self._setup_tasks(True, plans=0)
        ordered = Goal('track-plan', 'ordered', steps=(Goal('Economy-2', 'research'),))
        p.goals_for = lambda snapshot, **kwargs: [ordered, Goal('x', 'sequence', steps=(Goal('c', 'colony', '1,0'),))]
        goals = p.goals_for(snapshot)
        p.scoring_pairs(snapshot, scores, goals)
        self.assertEqual(goals, [ordered])

    def _bgg_wrapped(self, mj01):
        import bgg_openings.planning as planning
        self.addCleanup(setattr, planning, 'goals', planning.goals)
        self.addCleanup(setattr, planning, 'select_forecast', planning.select_forecast)
        self.addCleanup(tp._guide.__setitem__, 'mj01', tp._guide['mj01'])
        self.addCleanup(tp._bgg_setup.__setitem__, 0, tp._bgg_setup[0])
        tp._guide['mj01'] = mj01
        sentinel = ['original-goals']
        planning.goals = lambda snapshot, remembered=None: sentinel
        planning.select_forecast = lambda rows, remembered, comparisons: 'original-forecast'
        tp.install_setup_no_bgg()
        tp.install_setup_no_bgg()                                                    # wraps once
        self.assertFalse(hasattr(planning.goals.__wrapped__, '_setup_no_bgg'))
        return planning, sentinel

    def test_setup_no_bgg_blocks_goals_and_forecast_only_at_a_setup_placement(self):
        planning, sentinel = self._bgg_wrapped(True)
        setup = {'state': {'players': {0: {'faction': 'Terrans'}}}, 'player': 0,
                 'candidates': [{'action': {'type': 'PlaceStartingStructure'}}]}
        other = {**setup, 'candidates': [{'action': {'type': 'Upgrade'}}]}
        self.assertEqual(planning.goals(setup, None), [])
        self.assertIsNone(planning.select_forecast((), None, []))
        self.assertIs(planning.goals(other, None), sentinel)                          # the flag is reset by every goals call
        self.assertEqual(planning.select_forecast((), None, []), 'original-forecast')
        planning.goals(setup)
        planning.goals(other)
        self.assertEqual(planning.select_forecast((), None, []), 'original-forecast')
        planning, sentinel = self._bgg_wrapped(False)                                 # gate off: always the original
        self.assertIs(planning.goals(setup, None), sentinel)
        self.assertEqual(planning.select_forecast((), None, []), 'original-forecast')

    def test_setup_placement_real_planned_tasks_have_no_bgg_goal_and_compare_every_place(self):
        import budget_teacher
        import four_factions.preparation as p
        import parallel_search
        from four_factions.preparation import Policies, PolicyCache
        from current_actions.conservation import blocked
        for name in ('goals_for', 'interleave_families', 'scoring_pairs'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(lambda saved=list(budget_teacher.budget_hooks): budget_teacher.budget_hooks.__setitem__(slice(None), saved))
        tp._guide['mj01'] = True
        self.addCleanup(tp._guide.__setitem__, 'mj01', False)
        import bgg_openings.planning as planning
        self.addCleanup(setattr, planning, 'goals', planning.goals)
        self.addCleanup(setattr, planning, 'select_forecast', planning.select_forecast)
        tp.install_setup_places()
        tp.install_setup_no_bgg()
        tp.install_task_dedup()
        env = Environment(SEED, 2000)
        snapshot = json.loads(env.snapshot_json())
        self.assertTrue(any(c['action']['type'] == 'PlaceStartingStructure' for c in snapshot['candidates']))
        policies = Policies({}, cache=PolicyCache(), shared_factions=True)
        scores = policies.rank(env, snapshot)
        tasks, _ = parallel_search._planned_tasks(env, snapshot, {}, scores, policies,
                                                  {'bgg_openings': True, 'shared_factions': True})
        self.assertFalse([t for t in tasks if t.family == 'bgg-opening'])
        firsts = {t.first for t in tasks if t.first is not None}
        open_places = {i for i, c in enumerate(snapshot['candidates'])
                       if c['action']['type'] == 'PlaceStartingStructure' and not blocked(scores[i])}
        self.assertGreater(len(open_places), 1)
        self.assertLessEqual(open_places, firsts)

    def start_snapshot_two_placed(self, mine):
        """far_start_snapshot where the actor already placed the structures at `mine`."""
        snapshot = self.far_start_snapshot()
        snapshot['state']['players'][0]['structures'] = [{'hex': c} for c in mine]
        return snapshot

    def test_all_factory_first_start_is_never_blocked_for_being_far(self):
        from current_actions.conservation import blocked
        scores = [(5.0, 'far'), (4.0, 'near')]
        snapshot = self.start_snapshot_two_placed([])
        snapshot['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'      # no far-start exception
        self.assertTrue(blocked(tp.guide_r1_scores(snapshot, scores)[0]))                # gate off: blocked as before
        tp._guide['mj01'] = True
        self.assertEqual(tp.guide_r1_scores(snapshot, scores), scores)                   # nothing placed yet: free

    def test_all_factory_second_start_is_free_once_the_first_is_near_and_blocked_while_it_is_far(self):
        from current_actions.conservation import blocked
        scores = [(5.0, 'far'), (4.0, 'near')]
        tp._guide['mj01'] = True
        far_first = self.start_snapshot_two_placed(['-9,0'])
        far_first['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'
        self.assertTrue(blocked(tp.guide_r1_scores(far_first, scores)[0]))               # first start far: second must be near
        near_first = self.start_snapshot_two_placed(['4,0'])                              # 4,0 is 1 from the opponent at 3,0
        near_first['state']['board']['hexes']['1,0']['planet']['planet_type'] = 'Ice'
        self.assertEqual(tp.guide_r1_scores(near_first, scores), scores)                 # one near start is enough
        tp._guide['mj01'] = False
        self.assertTrue(blocked(tp.guide_r1_scores(near_first, scores)[0]))              # gate off: unchanged

    def test_plan_menu_orders_the_front_by_the_faction_row(self):
        from four_factions.preparation import Goal
        for faction, row in tp.FACTION_MENU.items():
            self.assertEqual(sorted(row), sorted(tp.MENU_DEFAULT), faction)        # every row names each family once
        state = self.track_plan_state()
        state['round_tiles'] = [{'condition': 'BuildMineOnGaia', 'vp_per_unit': 3}]*6
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources'].update(ore=12, qic=1, knowledge=8)         # the Desert plan is affordable (E86 ㄱ; Navigation 0→2 = 8 knowledge)
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        bare = Goal('Navigation-2', 'research', target='Navigation', level=2)
        plan = Goal('track-plan-Navigation-2>colony@2,0', 'ordered', steps=(bare, Goal('colony@2,0', 'colony', '2,0')))
        ability = Goal('Terrans-x', 'ordered', steps=(Goal('a', 'faction-action', target='X'),))
        goals = [bare, Goal('Science@0,0', 'upgrade', '0,0', 'Science'), Goal('colony@3,0', 'colony', '3,0'), ability]
        fed = Goal('federation-7', 'root', first=7)
        self.assertIs(tp.plan_menu_goals(snapshot, goals), goals)                   # part off
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        with mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                mock.patch.object(tp, 'fed_compare_goal', return_value=fed), \
                mock.patch.object(tp, 'token_compare_goal', return_value=None):
            menu = tp.plan_menu_goals(snapshot, goals)
            # Default row: tile (the Gaia colony) → federation → (no token) → track; the bare Navigation-2 dropped.
            self.assertEqual([g.name for g in menu[:3]], ['colony@3,0', 'federation-7', plan.name])
            self.assertEqual({g.name for g in menu[3:]}, {'Science@0,0', 'Terrans-x'})
            self.assertEqual({id(g) for g in menu[:3]}, tp._menu_front)
            state['players'][0]['faction'] = 'Itars'
            ability2 = Goal('Itars-PI@0,0-Gaia-tech@0,1', 'ordered', steps=(Goal('a', 'faction-action', target='X'),))
            goals[3] = ability2
            menu = tp.plan_menu_goals(snapshot, goals)                              # Itars row: tile → ability → federation
            self.assertEqual([g.name for g in menu[:3]], ['colony@3,0', ability2.name, 'federation-7'])
            state['round'] = 6
            del state['round_tiles']
            menu = tp.plan_menu_goals(snapshot, goals)                              # no tile: ability → federation → track
            self.assertEqual([g.name for g in menu[:3]], [ability2.name, 'federation-7', plan.name])

    def test_plan_menu_first_slots_follow_guide_menu_first(self):
        """E89 (ㄷ) B': _guide['menu_first'] = 1 puts one goal in front; the default 3 is unchanged."""
        from four_factions.preparation import Goal
        state = self.track_plan_state()
        state['round_tiles'] = [{'condition': 'BuildMineOnGaia', 'vp_per_unit': 3}]*6
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        goals = [Goal('colony@3,0', 'colony', '3,0'), Goal('Science@0,0', 'upgrade', '0,0', 'Science')]
        fed = Goal('federation-7', 'root', first=7)
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        with mock.patch.object(tp, 'track_plan_goals', return_value=[]), \
                mock.patch.object(tp, 'fed_compare_goal', return_value=fed), \
                mock.patch.object(tp, 'token_compare_goal', return_value=None):
            for first, expected in ((3, 2), (1, 1)):
                tp._guide['menu_first'] = first
                menu = tp.plan_menu_goals(snapshot, goals)
                self.assertEqual(len(tp._menu_slots), expected, first)
                self.assertEqual(len(tp._menu_front), expected, first)
                self.assertEqual(menu[0].name, 'colony@3,0')

    def test_install_plan_menu_spreads_the_front_over_the_three_task_lists(self):
        """E82 (ㄱ): search compares control, goals[0], roots[0], paired[0], goals[1], ... — in 102 the menu's second
        slot entered at position 3 (federation ×2–23 per faction) and the third never (four comparisons). The front
        now opens the goals, roots and scoring-pair lists, so its three slots are compared at positions 1, 2, 3."""
        import four_factions.preparation as p
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families', 'scoring_pairs', 'search'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(setattr, p.Policies, 'rank', p.Policies.rank)
        state = self.track_plan_state()
        state['round_tiles'] = [{'condition': 'BuildMineOnGaia', 'vp_per_unit': 3}]*6
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources'].update(ore=12, qic=1, knowledge=8)         # the Desert plan is affordable (E86 ㄱ; Navigation 0→2 = 8 knowledge)
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        tile, other = Goal('colony@3,0', 'colony', '3,0'), Goal('Science@0,0', 'upgrade', '0,0', 'Science')
        fed = Goal('federation-7', 'root', first=7)
        plan = Goal('track-plan-Navigation-2>colony@2,0', 'ordered',
                    steps=(Goal('Navigation-2', 'research', target='Navigation', level=2), Goal('colony@2,0', 'colony', '2,0')))
        roots = [Goal('root-2', 'root', first=2), Goal('root-5', 'root', first=5)]
        p.goals_for = lambda snapshot, **kwargs: [tile, other]
        p.scoring_pairs = lambda snapshot, scores, goals: [Goal(f'tile-action-1-then-{g.name}', g.family, first=1)
                                                           for g in goals if g.family == 'colony']
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        tp.install_plan_menu()
        tp.install_plan_menu()                                                       # installs once
        with mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                mock.patch.object(tp, 'fed_compare_goal', return_value=fed), \
                mock.patch.object(tp, 'token_compare_goal', return_value=None):
            proposals = p.goals_for(snapshot)
        self.assertEqual([g.name for g in proposals], ['colony@3,0', 'federation-7', plan.name, 'Science@0,0'])
        goals = p.interleave_families(proposals, lambda g: g.family)
        self.assertEqual([g.name for g in goals], ['colony@3,0', 'Science@0,0'])  # slot 1 leads; slots 2–3 wait
        self.assertEqual([g.name for g in p.interleave_families(roots, lambda g: g.first)],
                         ['federation-7', 'root-2', 'root-5'])                       # slot 2 opens the roots
        # quick.py (candidate indices) and source_paths.py (cores) call the same name: untouched, as is an empty list.
        self.assertEqual(p.interleave_families([3, 1, 2], lambda i: i % 2), [3, 2, 1])   # the plain round-robin
        self.assertEqual(p.interleave_families([other], lambda g: g.family), [other])
        self.assertEqual(p.interleave_families([], lambda g: g.first), [])
        paired = p.scoring_pairs(snapshot, [], goals)
        self.assertEqual([g.name for g in paired], [plan.name, 'tile-action-1-then-colony@3,0'])  # slot 3 opens the pairs
        # Part off: nothing is inserted anywhere.
        tp._guide['plan_menu'] = False
        self.assertEqual(p.goals_for(snapshot), [tile, other])
        self.assertEqual(p.interleave_families(roots, lambda g: g.first), roots)
        self.assertEqual([g.name for g in p.scoring_pairs(snapshot, [], [tile])], ['tile-action-1-then-colony@3,0'])

    def _menu_task_fixture(self, with_fed):
        """plan_menu installed over fake proposals; returns (snapshot, scores, memory, goals) where `plan` is the track
        plan (menu slot 3 with a federation goal, slot 2 without one) and the memory remembers it (lab 103, E90)."""
        import four_factions.preparation as p
        from dataclasses import asdict
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families', 'scoring_pairs', 'search'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(setattr, p.Policies, 'rank', p.Policies.rank)
        state = self.track_plan_state()
        state['round_tiles'] = [{'condition': 'BuildMineOnGaia', 'vp_per_unit': 3}]*6
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources'].update(ore=12, qic=1, knowledge=8)
        state['phase'] = {'ActionPhase': {}}
        snapshot = {'player': 0, 'state': state, 'decision_id': 'd', 'steps': 0,
                    'candidates': [{'action': {'type': t}} for t in ('Pass', 'Build', 'Research', 'Power')]}
        scores = [(4.0, ''), (3.0, ''), (2.0, ''), (1.0, '')]
        tile, other = Goal('colony@3,0', 'colony', '3,0'), Goal('Science@0,0', 'upgrade', '0,0', 'Science')
        fed = Goal('federation-7', 'root', first=3) if with_fed else None
        plan = Goal('track-plan-Navigation-2>colony@2,0', 'ordered',
                    steps=(Goal('Navigation-2', 'research', target='Navigation', level=2), Goal('colony@2,0', 'colony', '2,0')))
        p.goals_for = lambda snapshot, **kwargs: [tile, other]
        p.scoring_pairs = lambda snapshot, scores, goals: [Goal(f'tile-action-1-then-{g.name}', g.family, first=1)
                                                           for g in goals if g.family == 'colony']
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        tp.install_task_dedup()  # as the ships factory does before plan_menu (two dedup layers, lab 104a)
        tp.install_plan_menu()
        memory = {'_plans': {'0': asdict(plan)}}
        return snapshot, scores, memory, (tile, other, fed, plan)

    def _assert_plan_once_and_next_candidate_kept(self, with_fed):
        import four_factions.preparation as p
        import parallel_search
        snapshot, scores, memory, (tile, other, fed, plan) = self._menu_task_fixture(with_fed)
        policies = mock.Mock(memory=memory, delta_factions=())
        with mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                mock.patch.object(tp, 'fed_compare_goal', return_value=fed), \
                mock.patch.object(tp, 'token_compare_goal', return_value=None), \
                mock.patch.object(p, 'viable', return_value=True), mock.patch.object(p, 'achieved', return_value=False):
            tasks, _ = parallel_search._planned_tasks(None, snapshot, memory, scores, policies, {})
            names = [g.name for g in tasks]
            self.assertEqual(names.count(plan.name), 1)
            self.assertEqual(len(names), len(set(names)))
            # cap60 compares four distinct plans: control, the remembered plan, and the next roots / pairs entries in
            # place of the dropped copy (the copy is removed from its own list, so that list's next entry moves up).
            self.assertEqual(names[0], 'current-choice')
            self.assertEqual(names[1], plan.name)
            self.assertIn('federation-7' if with_fed else 'root-1', names[:4])
            self.assertIn('tile-action-1-then-colony@3,0', names[:4])
            self.assertIn('colony@3,0', names)
            # The sequential search rolls out the same list in the same order.
            rolled = []
            def rollout(env, snap, first, goal, *args, **kwargs):
                rolled.append(goal.name)
                return {'complete': True, 'value': 1.0, 'actions': [], 'decisions': 1}
            with mock.patch.object(p, 'rollout', rollout), mock.patch.object(p, 'select_goal', lambda *a, **k: 1), \
                    mock.patch.object(p.Policies, 'rank', lambda self, env, snap: scores):
                result = p.search(None, snapshot, json.loads(json.dumps(memory)), lambda r: None,
                                  soft_deadline=time.monotonic()+1e6, hard_deadline=time.monotonic()+1e6)
            self.assertEqual(rolled, names)
            self.assertEqual(result['planned_comparisons'], len(names))
            self.assertEqual(len({json.dumps(r['goal_spec'], sort_keys=True) for r in result['plans']}), len(names))

    def test_a_remembered_plan_that_is_menu_slot_3_is_compared_once_and_pushes_nothing_out(self):
        self._assert_plan_once_and_next_candidate_kept(with_fed=True)

    def test_a_remembered_plan_that_is_menu_slot_2_is_compared_once_and_pushes_nothing_out(self):
        self._assert_plan_once_and_next_candidate_kept(with_fed=False)

    def test_plan_menu_drops_a_multi_step_plan_the_next_income_cannot_pay(self):
        """E86 (ㄱ): a track / ability plan whose pending steps cost more than held + next income is not generated;
        one the next income pays stays (known-bad 8: the institute plan is not forced into the same round)."""
        from four_factions.preparation import Goal
        state = self.track_plan_state()
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources']['knowledge'] = 8
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        research = Goal('Navigation-2', 'research', target='Navigation', level=2)
        plan = Goal('track-plan-Navigation-2>colony@3,0', 'ordered', steps=(research, Goal('colony@3,0', 'colony', '3,0')))
        # 8 knowledge (0→2) + a Gaia mine three hexes away at range 2: 1 ore, 2 credits, 1 range QIC + 1 Gaia QIC.
        self.assertEqual(tp._plan_cost(snapshot, plan), {'knowledge': 8, 'ore': 1, 'credits': 2, 'qic': 2})
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        with mock.patch.object(tp._value, 'production', return_value=[0]*7):        # held only: 0 QIC
            self.assertFalse(tp.plan_affordable(snapshot, plan))
            self.assertTrue(tp.plan_affordable(snapshot, research))                 # a single step is never dropped
            self.assertTrue(tp.plan_affordable(snapshot, Goal('federation-7', 'root', first=7)))
            ability = Goal('Terrans-PI@0,0-x', 'ordered', steps=(Goal('TradingStation@0,0', 'upgrade', '0,0', 'TradingStation'),
                                                                 Goal('Build@3,0', 'faction-action', '3,0', 'Build')))
            self.assertEqual(tp._plan_cost(snapshot, ability), {'ore': 3, 'credits': 8, 'qic': 2})
            self.assertFalse(tp.plan_affordable(snapshot, ability))
            with mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                    mock.patch.object(tp, 'fed_compare_goal', return_value=None), \
                    mock.patch.object(tp, 'token_compare_goal', return_value=None):
                self.assertNotIn(plan.name, [g.name for g in tp.plan_menu_goals(snapshot, [ability])])
                self.assertNotIn(ability.name, [g.name for g in tp.plan_menu_goals(snapshot, [ability])])
        with mock.patch.object(tp._value, 'production', return_value=[0, 0, 0, 2, 0, 0, 0]):   # next income: 2 QIC
            self.assertTrue(tp.plan_affordable(snapshot, plan))
            self.assertTrue(tp.plan_affordable(snapshot, ability))
            with mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                    mock.patch.object(tp, 'fed_compare_goal', return_value=None), \
                    mock.patch.object(tp, 'token_compare_goal', return_value=None):
                self.assertEqual([g.name for g in tp.plan_menu_goals(snapshot, [ability])], [plan.name, ability.name])
        # An achieved first step costs nothing more: the remaining colony alone, paid by the QIC held.
        state['players'][0]['research_tracks']['navigation'] = 2
        state['players'][0]['resources']['qic'] = 2
        with mock.patch.object(tp._value, 'production', return_value=[0]*7):
            self.assertEqual(tp._plan_cost(snapshot, plan), {'ore': 1, 'credits': 2, 'qic': 2})   # range 2: 1 + Gaia 1
            self.assertTrue(tp.plan_affordable(snapshot, plan))                     # one pending step: not covered

    def test_plan_cost_counts_steps_in_order(self):
        """Debate on E88: research effects reach the later mines, research costs 4 knowledge per level, AI grants QIC."""
        from four_factions.preparation import Goal
        state = self.track_plan_state()
        state['players'][0]['resources'].update(ore=12, credits=10, knowledge=8, qic=0)
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        nav = Goal('Navigation-2', 'research', target='Navigation', level=2)
        mine = Goal('colony@2,0', 'colony', '2,0')
        plan = Goal('track-plan-Navigation-2>colony@2,0', 'ordered', steps=(nav, mine))
        # (a) The Desert hex is two away: range 1 needs 1 QIC, range 2 (after Navigation 2) none.
        self.assertEqual(tp._mine_cost(state, state['players'][0], '2,0')['qic'], 1)
        cost = tp._plan_cost(snapshot, plan)
        self.assertEqual((cost['knowledge'], cost['qic']), (8, 0))
        with mock.patch.object(tp._value, 'production', return_value=[0]*7):
            self.assertTrue(tp.plan_affordable(snapshot, plan))                     # held 0 QIC suffices only in order
        # (b) 0→2 on one step is 8 knowledge; two steps on one track are not counted twice.
        self.assertEqual(tp._plan_cost(snapshot, nav), {'knowledge': 8})
        two = Goal('two', 'ordered', steps=(Goal('Navigation-1', 'research', target='Navigation', level=1), nav))
        self.assertEqual(tp._plan_cost(snapshot, two), {'knowledge': 8})
        state['players'][0]['research_tracks']['navigation'] = 1
        self.assertEqual(tp._plan_cost(snapshot, nav), {'knowledge': 4})
        state['players'][0]['research_tracks']['navigation'] = 0
        # The AI track's QIC (1 + 1 for levels 1–2) is credited against the later QIC costs.
        ai = Goal('ArtificialIntelligence-2', 'research', target='ArtificialIntelligence', level=2)
        self.assertEqual(tp._plan_cost(snapshot, Goal('ai', 'ordered', steps=(ai, mine))),
                         {'knowledge': 8, 'qic': 1-2, 'ore': cost['ore'], 'credits': cost['credits']})

    def test_plan_menu_keeps_the_research_of_a_dropped_plan(self):
        """Debate on E88: the bare research goal returns to the pool when its only covering plan is unaffordable."""
        from four_factions.preparation import Goal
        state = self.track_plan_state()
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources']['knowledge'] = 8
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        research = Goal('Navigation-2', 'research', target='Navigation', level=2)
        plan = Goal('track-plan-Navigation-2>colony@3,0', 'ordered', steps=(research, Goal('colony@3,0', 'colony', '3,0')))
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        with mock.patch.object(tp._value, 'production', return_value=[0]*7), \
                mock.patch.object(tp, 'track_plan_goals', return_value=[plan]), \
                mock.patch.object(tp, 'fed_compare_goal', return_value=None), \
                mock.patch.object(tp, 'token_compare_goal', return_value=None):
            self.assertFalse(tp.plan_affordable(snapshot, plan))
            names = [g.name for g in tp.plan_menu_goals(snapshot, [])]               # the wrapper already removed it
            self.assertEqual(names, ['Navigation-2'])
            self.assertEqual([g.name for g in tp.plan_menu_goals(snapshot, [research])], ['Navigation-2'])   # no duplicate

    def test_plan_menu_forgets_a_remembered_plan_the_budget_cannot_pay(self):
        """E86 (ㄱ): the remembered plan is dropped from the memory search gets when its steps are unaffordable."""
        import four_factions.preparation as p
        from dataclasses import asdict
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families', 'scoring_pairs', 'search'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        self.addCleanup(setattr, p.Policies, 'rank', p.Policies.rank)
        state = self.track_plan_state()
        state['board']['hexes']['3,0'] = {**state['board']['hexes']['3,0'],
                                          'planet': {'planet_type': 'Gaia', 'owner': None, 'is_gaia_formed': False}}
        state['players'][0]['resources']['knowledge'] = 8
        snapshot = {'player': 0, 'state': state, 'candidates': []}
        plan = Goal('track-plan-Navigation-2>colony@3,0', 'ordered', steps=(
            Goal('Navigation-2', 'research', target='Navigation', level=2), Goal('colony@3,0', 'colony', '3,0')))
        memory = {'_plans': {'0': asdict(plan), '1': {'name': 'other'}}, 'x': 1}
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        with mock.patch.object(tp._value, 'production', return_value=[0]*7):
            kept, forgot = tp.forget_unaffordable_plan(snapshot, memory)
            self.assertEqual((kept['_plans'], kept['x'], forgot), ({'1': {'name': 'other'}}, 1, plan.name))
            self.assertIn('0', memory['_plans'])                                     # the caller's memory is untouched
            self.assertEqual(tp.forget_unaffordable_plan(snapshot, {}), ({}, None))
            seen = []
            p.search = lambda env, snapshot, memory, publish, **kw: seen.append(memory) or {'plans': [], 'index': 0}
            tp.install_plan_menu()
            result = p.search(None, snapshot, memory, lambda r: None)
            self.assertEqual((result['menu_forgot'], list(seen[0]['_plans'])), (plan.name, ['1']))
        with mock.patch.object(tp._value, 'production', return_value=[0, 0, 0, 2, 0, 0, 0]):
            self.assertEqual(tp.forget_unaffordable_plan(snapshot, memory), (memory, None))
            result = p.search(None, snapshot, memory, lambda r: None)
            self.assertNotIn('menu_forgot', result)
            self.assertIs(seen[1], memory)

    def test_menu_track_steps_absorb_science_when_and_research_when_land(self):
        """E86 (ㄴ): under plan_menu the track plans' first entry follows science_when (Nevlas, Ivits) and, with no
        faction round target pending, research_when_land (no land in reach → Navigation; safe land → Economy)."""
        state = self.track_plan_state()
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('navigation', 2))         # part off: the guide order (T2)
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        self.assertEqual(tp._land_counts(state, state['players'][0]), (1, 0))      # the transdim 0,1 in reach, safe
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('economy', 2))             # safe land: Economy to the sweet spot
        state['players'][0]['research_tracks']['economy'] = 2
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('navigation', 2))         # at the sweet spot: guide order
        state['players'][0]['research_tracks']['economy'] = 0
        state['board']['hexes']['0,1']['planet'] = None
        self.assertEqual(tp._land_counts(state, state['players'][0]), (0, 0))
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('navigation', 2))         # no land: range first
        state['players'][0]['research_tracks']['navigation'] = 5
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('terraforming', 1))       # Navigation full: Terraforming
        state['round'] = 4                                                           # LAND_ROUNDS are 1-3
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('science', 2))
        state['round'] = 2
        state['players'][0]['faction'] = 'Nevlas'
        state['players'][0]['research_tracks']['navigation'] = 0
        tp._guide['resolved_parts'] = True                                           # science_when is a resolved part
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('economy', 2))             # no reason for Science: Economy 2
        state['round_tiles'] = [{'condition': 'BuildMine'}]*4 + [{'condition': 'ResearchAdvance'}]*2
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('science', 3))             # round 5 tile pays research: Science 3

    def test_menu_track_steps_put_geodens_terraforming_and_navigation_first_from_round_2(self):
        """E97: under plan_menu Geodens' track plans lead with Terraforming 3, then Navigation 2, from round 2."""
        state = self.track_plan_state()
        state['players'][0]['faction'] = 'Geodens'
        state['round'] = 2
        tp._guide['plan_menu'] = True                                                # restored by setUp's cleanup
        self.assertEqual(tp._plan_tracks(state, 0)[:2], [('terraforming', 3), ('navigation', 2)])
        state['players'][0]['research_tracks']['terraforming'] = 3
        self.assertEqual(tp._plan_tracks(state, 0)[0], ('navigation', 2))
        state['round'] = 1
        state['players'][0]['research_tracks']['terraforming'] = 0
        self.assertNotEqual(tp._plan_tracks(state, 0)[0], ('terraforming', 3))   # round 1: Economy/Science start

    def test_menu_tie_goes_to_the_proposed_plan_and_remembers_it(self):
        """E74: 101 pair-002 step 114 — Geodens-new-type tied current-choice at 265.89 and lost the tie."""
        spec = {'name': 'Geodens-new-type@-3,-1', 'family': 'ordered', 'first': 3, 'steps': ()}
        plans = [{'goal': 'current-choice', 'family': 'current', 'first': 3, 'complete': True, 'value': 265.89},
                 {'goal': 'root-7', 'family': 'root', 'first': 7, 'complete': True, 'value': 265.89},
                 {'goal': 'federation-2', 'family': 'root', 'first': 2, 'complete': True, 'value': 230.42},
                 {'goal': 'Geodens-new-type@-3,-1', 'family': 'ordered', 'first': 3, 'complete': True,
                  'value': 265.89, 'goal_spec': spec}]
        memory = {}
        result = {'index': 3, 'selected': 'current-choice', 'plans': plans, 'memory': memory}
        tp.menu_tie_break({'player': 2}, result)
        self.assertEqual((result['index'], result['selected']), (3, 'menu-tie Geodens-new-type@-3,-1'))
        self.assertEqual(result['menu_tie'], {'replaced': 'current-choice', 'replaced_index': 3})
        self.assertEqual(memory['_plans']['2'], {**spec, 'first': None})
        tp.menu_tie_break({'player': 2}, result)                                     # idempotent
        self.assertEqual(result['selected'], 'menu-tie Geodens-new-type@-3,-1')
        # A plan that wins outright (value_max already played it) or loses is left alone.
        for value, selected in ((270.0, 'value-max Geodens-new-type@-3,-1'), (260.0, 'current-choice')):
            plans[3]['value'] = value
            result = {'index': 3, 'selected': selected, 'plans': plans, 'memory': {}}
            tp.menu_tie_break({'player': 2}, result)
            self.assertEqual(result['selected'], selected)
            self.assertNotIn('menu_tie', result)

    def test_menu_tie_goes_to_a_federation_or_flip_proposal_without_remembering_it(self):
        """review-code-d60b9b0: federation-N / flip-N share family 'root' with the ranking's root-N moves but are
        menu proposals; a tie with current-choice goes to them, and a root-N tie never counts as a proposal."""
        for name in ('federation-2', 'flip-2'):
            plans = [{'goal': 'current-choice', 'family': 'current', 'first': 3, 'complete': True, 'value': 265.89},
                     {'goal': name, 'family': 'root', 'first': 2, 'complete': True, 'value': 265.89,
                      'goal_spec': {'name': name, 'family': 'root', 'first': 2, 'steps': ()}}]
            memory = {}
            result = {'index': 3, 'selected': 'current-choice', 'plans': plans, 'memory': memory}
            tp.menu_tie_break({'player': 2}, result)
            self.assertEqual((result['index'], result['selected']), (2, f'menu-tie {name}'))
            self.assertEqual(result['menu_tie'], {'replaced': 'current-choice', 'replaced_index': 3})
            self.assertEqual(memory, {})                                                  # single move, not remembered
        plans = [{'goal': 'current-choice', 'family': 'current', 'first': 3, 'complete': True, 'value': 265.89},
                 {'goal': 'root-7', 'family': 'root', 'first': 7, 'complete': True, 'value': 265.89}]
        result = {'index': 3, 'selected': 'current-choice', 'plans': plans, 'memory': {}}
        tp.menu_tie_break({'player': 2}, result)
        self.assertEqual((result['index'], result['selected']), (3, 'current-choice'))
        self.assertNotIn('menu_tie', result)

    def test_install_track_plans_puts_plans_first_and_drops_the_bare_research_goal(self):
        import four_factions.preparation as p
        from four_factions.preparation import Goal
        for name in ('goals_for', 'interleave_families'):
            self.addCleanup(setattr, p, name, getattr(p, name))
        bare = Goal('Navigation-2', 'research', target='Navigation', level=2)
        p.goals_for = lambda snapshot, **kwargs: [bare, 'other-goal']
        plan = Goal('track-plan-Navigation-2>colony@2,0', 'ordered', steps=(bare, Goal('colony@2,0', 'colony', '2,0')))
        plans = [plan, Goal('track-plan-Science-2', 'ordered', steps=(Goal('Science-2', 'research', target='Science', level=2),)),
                 Goal('track-plan-Economy-2', 'ordered', steps=(Goal('Economy-2', 'research', target='Economy', level=2),))]
        with mock.patch.object(tp, 'track_plan_goals', return_value=[]):
            tp.install_track_plans()
            tp.install_track_plans()                                                  # installs once
            self.assertEqual(p.goals_for({}), [bare, 'other-goal'])                   # no plans: unchanged
        with mock.patch.object(tp, 'track_plan_goals', return_value=plans):
            self.assertEqual(p.goals_for({}), [*plans, 'other-goal'])                 # the covered bare goal dropped
        second = Goal('track-plan-Navigation-2>colony@3,0', 'ordered', steps=(bare, Goal('colony@3,0', 'colony', '3,0')))
        order = p.interleave_families([Goal('a', 'colony'), plans[0], second, *plans[1:], Goal('b', 'colony')],
                                      lambda g: g.family)
        # TRACK_PLANS_FIRST ahead, one plan per track: the second Navigation colony waits with the rest.
        self.assertEqual([g.name for g in order[:2]], [plans[0].name, plans[1].name])
        self.assertEqual({g.name for g in order[2:]}, {'a', 'b', second.name, plans[2].name})
        self.assertFalse(getattr(p.rollout, '_track_plans', False))                  # the horizon is untouched
