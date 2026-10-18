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


class LeechWhenTests(unittest.TestCase):
    def test_answer_by_cost_and_round(self):
        self.assertIsNone(tp._leech_when(0, 1))
        self.assertEqual([tp._leech_when(1, r) for r in (1, 5, 6)], [True, True, None])
        self.assertEqual([tp._leech_when(2, r) for r in (3, 4, 5)], [True, True, None])
        self.assertEqual([tp._leech_when(3, r) for r in (1, 6)], [False, False])


class NotYetTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(tp._guide)
        tp._guide.update(dict.fromkeys(tp.WHEN_NOT_YET, True))
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def player(self, *, tokens=9, knowledge=0, faction='Terrans', mines=2):
        return {'faction': faction, 'structures': [{'kind': 'Mine', 'hex': f'{i},0'} for i in range(mines)],
                'resources': {'knowledge': knowledge, 'power': {'bowl1': tokens, 'bowl2': 0, 'bowl3': 0}}}

    def held(self, action, round_=1, **player):
        return tp._not_yet({'round': round_}, self.player(**player), action) is not None

    def test_resource_artifact_only_in_round_one_with_three_tokens_left(self):
        artifact = {'type': 'ExamineArtifact', 'artifact': 6}
        self.assertFalse(self.held(artifact))
        self.assertTrue(self.held(artifact, tokens=8))
        self.assertTrue(self.held(artifact, round_=2))
        self.assertFalse(self.held({'type': 'ExamineArtifact', 'artifact': 12}, round_=2))

    def test_taklons_institute_waits_for_round_four(self):
        upgrade = {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'}
        self.assertTrue(self.held(upgrade, round_=3, faction='Taklons'))
        self.assertFalse(self.held(upgrade, round_=4, faction='Taklons'))
        self.assertFalse(self.held(upgrade, round_=1))

    def test_twilight_range_needs_knowledge_left_over(self):
        move = {'type': 'TwilightRangeBuild', 'coord': '0,0'}
        self.assertEqual([self.held(move, knowledge=k) for k in (3, 4, 5, 8)], [False, True, False, True])

    def test_the_last_mine_is_kept_when_an_asteroid_is_in_reach(self):
        build = {'type': 'Build', 'coord': '0,0'}
        with mock.patch.object(tp, '_in_reach', return_value={'1,1': 'Asteroid'}):
            self.assertTrue(self.held(build, mines=7))
            self.assertFalse(self.held(build, mines=6))
        with mock.patch.object(tp, '_in_reach', return_value={}):
            self.assertFalse(self.held(build, mines=7))

    def test_academy_kind_by_round(self):
        kinds = [tp._academy_kind({'round': r}, {'explored_ships': []}) for r in (1, 3, 4, 5)]
        self.assertEqual(kinds, ['Science', 'Science', None, 'Qic'])
        self.assertEqual(tp._academy_kind({'round': 2}, {'explored_ships': ['Rebellion']}), 'Qic')


class BurnAndFormerTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(tp._guide)
        tp._guide.update(burn_when=True, terrans_former=True)
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def burn_held(self, bowl3, count=2, used=()):
        player = {'faction': 'Terrans', 'resources': {'power': {'bowl1': 0, 'bowl2': 4, 'bowl3': bowl3}}}
        action = {'type': 'FreeAction', 'kind': 'BurnPower', 'count': count}
        return tp._not_yet({'round': 1, 'used_power_actions': list(used)}, player, action) is not None

    def test_burn_only_when_it_pays_for_a_power_action(self):
        self.assertFalse(self.burn_held(2))                      # 2 + 2 reaches the 4-power actions
        self.assertTrue(self.burn_held(2, used=(3, 4, 5, 6, 7)))
        self.assertTrue(self.burn_held(7))                        # every action is affordable already

    def test_terrans_former_waits_for_a_transdim_planet(self):
        state = {'round': 1, 'board': {'hexes': {'1,1': {'planet': {'planet_type': 'Asteroid', 'is_gaia_formed': False}}}}}
        player = {'faction': 'Terrans', 'structures': [], 'resources': {}}
        build = {'type': 'Build', 'coord': '1,1'}
        with mock.patch.object(tp, '_gaia_room', return_value=1):
            with mock.patch.object(tp, '_in_reach', return_value={'2,2': 'Transdim'}):
                self.assertIsNotNone(tp._not_yet(state, player, build))
                self.assertIsNone(tp._not_yet(state, {**player, 'faction': 'Xenos'}, build))
            with mock.patch.object(tp, '_in_reach', return_value={}):
                self.assertIsNone(tp._not_yet(state, player, build))


class TechWhenTests(unittest.TestCase):
    def snapshot(self, *, faction='Terrans', tiles=(), structures=(), gaia=1, round_=1):
        tracks = {t: 0 for t in tp.TRACK_KEYS.values()} | {'gaia': gaia}
        player = {'faction': faction, 'tech_tiles': list(tiles), 'structures': list(structures),
                  'research_tracks': tracks}

        def lab(tile, kind='Standard'):
            return {'action': {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                               'tech_tile_choice': {'kind': kind, 'tile': tile, 'advance_track': None}}}
        candidates = [lab(5), lab(10), lab(8), lab(7), {'action': {'type': 'Pass', 'booster_id': 1}}]
        return {'player': 0, 'state': {'round': round_, 'phase': {'ActionPhase': {}}, 'players': [player]},
                'candidates': candidates}

    def top_tile(self, knowledge=0, **kwargs):
        snapshot = self.snapshot(**kwargs)
        scores = [(9.0, 'a'), (8.0, 'b'), (7.0, 'c'), (10.0, 'd'), (0.0, 'e')]
        with mock.patch.object(tp._value, 'production', return_value=[0, 0, knowledge, 0, 0, 0, 0]):
            lifted = tp.tech_when_scores(None, snapshot, scores)
        best = max(range(4), key=lambda i: lifted[i][0])
        return snapshot['candidates'][best]['action']['tech_tile_choice']['tile']

    def test_first_tile(self):
        self.assertEqual(self.top_tile(), 10)
        self.assertEqual(self.top_tile(faction='Geodens'), 10)             # B18-03 first tiles

    def test_later_tiles(self):
        self.assertEqual(self.top_tile(faction='Geodens', tiles=(2,), knowledge=3), 5)  # tile 7 held back only
        self.assertEqual(self.top_tile(faction='Geodens', tiles=(2,)), 5)  # tile 7 held back, next best
        self.assertEqual(self.top_tile(faction='Geodens', tiles=(2,), round_=6), 7)
        self.assertEqual(self.top_tile(faction='Geodens', tiles=(2,), gaia=3), 5)   # no Gaia-mine rule (LF2-08)

    def test_second_tile_is_one_to_cover(self):
        saved = dict(tp._guide)
        self.addCleanup(lambda: tp._guide.update(saved))
        tp._guide['cover_tile'] = True
        snapshot = self.snapshot(faction='Geodens', tiles=(10,))
        snapshot['candidates'].insert(0, {'action': {'type': 'Upgrade', 'coord': '0,0', 'to': 'ResearchLab',
                                                     'tech_tile_choice': {'kind': 'Standard', 'tile': 13,
                                                                          'advance_track': None}}})
        scores = [(1.0, 'z'), (9.0, 'a'), (8.0, 'b'), (7.0, 'c'), (10.0, 'd'), (0.0, 'e')]
        with mock.patch.object(tp._value, 'production', return_value=[0]*7):
            lifted = tp.tech_when_scores(None, snapshot, scores)
        self.assertEqual(max(range(5), key=lambda i: lifted[i][0]), 0)

    def test_gaia_tile_for_terrans(self):
        saved = dict(tp._guide)
        self.addCleanup(lambda: tp._guide.update(saved))
        tp._guide['gaia_tile'] = True
        self.assertEqual(self.top_tile(tiles=(10,)), 8)
        self.assertEqual(self.top_tile(faction='Geodens', tiles=(2,)), 5)


class GuideMoreTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(tp._guide)
        tp._guide.update(dict.fromkeys(tp.GUIDE_MORE, True))
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def player(self, **resources):
        return {'player_id': 0, 'faction': 'Geodens', 'federated_hexes': ['1,1'], 'federation_tokens': [],
                'structures': [{'hex': '1,1', 'kind': 'Mine'}, {'hex': '2,2', 'kind': 'TradingStation'}],
                'resources': {'ore': 4, 'credits': 6, 'knowledge': 0, 'qic': 1} | resources}

    def held(self, action, round_=2, **resources):
        return tp._not_yet_more({'round': round_}, self.player(**resources), action) is not None

    def test_holds(self):
        self.assertTrue(self.held({'type': 'Upgrade', 'coord': '1,1', 'to': 'TradingStation'}))
        self.assertFalse(self.held({'type': 'Upgrade', 'coord': '3,3', 'to': 'TradingStation'}))
        self.assertTrue(self.held({'type': 'Upgrade', 'coord': '3,3', 'to': 'TradingStation'}, credits=10))
        self.assertTrue(self.held({'type': 'PowerAction', 'id': 1}, knowledge=0))
        self.assertFalse(self.held({'type': 'PowerAction', 'id': 1}, knowledge=5))
        self.assertTrue(self.held({'type': 'TFMarsTechBonus'}, round_=3))
        self.assertFalse(self.held({'type': 'TFMarsTechBonus'}, round_=4))
        self.assertTrue(self.held({'type': 'RebellionCreditsAndQic'}, qic=1))
        self.assertFalse(self.held({'type': 'RebellionCreditsAndQic'}, qic=2))

    def test_leech_lf_early_rounds(self):
        self.assertTrue(tp._leech_when(3, 1))
        self.assertIsNone(tp._leech_when(3, 2, keep_ship=True))
        self.assertFalse(tp._leech_when(3, 3))

    def test_federation_token_and_pass_booster(self):
        def fed(kind):
            return {'action': {'type': 'FormFederation', 'hexes': ['2,2'], 'satellite_hexes': [],
                               'token': {'source': 'Supply', 'kind': kind}}}
        snapshot = {'player': 0, 'state': {'round': 3, 'phase': {'ActionPhase': {}},
                                           'players': [self.player()]},
                    'candidates': [fed(3), fed(8), fed(5), {'action': {'type': 'Pass', 'booster_id': 1}},
                                   {'action': {'type': 'Pass', 'booster_id': 3}}]}
        scores = [(9.0, 'a'), (7.0, 'b'), (8.0, 'c'), (1.0, 'd'), (2.0, 'e')]
        with mock.patch.object(tp, '_booster_vp', side_effect=lambda s, p, b: {1: 6, 3: 1}[b]):
            lifted = tp.guide_more_scores(None, snapshot, scores)
        self.assertEqual(max(range(3), key=lambda i: lifted[i][0]), 1)      # 8 VP 8 credits
        self.assertGreater(lifted[3][0], lifted[4][0])                      # 6-VP pass booster


class GuideRestTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(tp._guide)
        tp._guide.update(dict.fromkeys(tp.GUIDE_REST, True))
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def player(self, mines=2, knowledge=0):
        structures = [{'hex': f'{i},0', 'kind': 'Mine'} for i in range(mines)] + [{'hex': '9,9', 'kind': 'TradingStation'}]
        return {'player_id': 0, 'faction': 'Geodens', 'structures': structures, 'federation_tokens': [],
                'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()},
                'resources': {'ore': 4, 'credits': 6, 'knowledge': knowledge, 'qic': 1}}

    def held(self, action, round_=2, **player):
        return tp._not_yet_more({'round': round_}, self.player(**player), action) is not None

    def test_no_mines_kept_or_even_knowledge(self):
        self.assertNotIn('mines_kept', tp.GUIDE_REST)       # dropped (B2-05 unclear)
        self.assertFalse(self.held({'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'}))
        lab = {'type': 'Upgrade', 'coord': '9,9', 'to': 'ResearchLab'}
        self.assertFalse(self.held(lab, knowledge=1))        # no even-knowledge rule (removed)

    def test_contested_order(self):
        tracks = {t: 0 for t in tp.TRACK_KEYS.values()} | {'ai': 4}
        players = [{**self.player(), 'research_tracks': tracks, 'passed': False}, {'passed': False}]
        snapshot = {'player': 0, 'decision_id': 1, 'state': {'round': 3, 'phase': {'ActionPhase': {}}, 'players': players},
                    'candidates': [{'action': {'type': 'PowerAction', 'id': 3}},
                                   {'action': {'type': 'ResearchAdvance', 'track': 'ArtificialIntelligence'}},
                                   {'action': {'type': 'Pass', 'booster_id': 1}}]}
        scores = [(5.0, 'a'), (3.0, 'b'), (0.0, 'c')]
        lifted = tp._guide_rest(None, snapshot, scores, list(scores), [0, 1, 2],
                                {i: c['action'] for i, c in enumerate(snapshot['candidates'])})
        self.assertGreater(lifted[1][0], lifted[0][0])


class GuideFinalTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(tp._guide)
        tp._guide.update(dict.fromkeys(tp.GUIDE_FINAL, True))
        self.addCleanup(lambda: tp._guide.update(self.saved))

    def test_holds(self):
        state = {'round': 5, 'board': {'hexes': {'1,1': {'planet': {'planet_type': 'Asteroid', 'is_gaia_formed': False}}}}}
        player = {'faction': 'Taklons', 'booster': 6, 'structures': [], 'resources': {}}
        self.assertIsNone(tp._not_yet_more(state, player, {'type': 'Build', 'coord': '1,1'}))
        self.assertIsNotNone(tp._not_yet_more(state, player, {'type': 'ExploreSpaceship', 'ship': 'Twilight'}))
        self.assertIsNone(tp._not_yet_more({**state, 'round': 4}, player, {'type': 'ExploreSpaceship', 'ship': 'Twilight'}))

    def test_former_booster_not_taken_with_an_asteroid_ahead(self):
        player = {'player_id': 0, 'faction': 'Geodens', 'structures': [], 'tech_tiles': [],
                  'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()},
                  'resources': {'ore': 1, 'credits': 1, 'knowledge': 0, 'qic': 0}}
        snapshot = {'player': 0, 'state': {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'Pass', 'booster_id': 6}},
                                   {'action': {'type': 'Pass', 'booster_id': 9}}]}
        scores = [(2.0, 'a'), (1.0, 'b')]
        with mock.patch.object(tp, '_idle_formers', return_value=1), \
                mock.patch.object(tp, '_in_reach', return_value={'1,1': 'Asteroid'}), \
                mock.patch.object(tp, '_booster_vp', return_value=0):
            lifted = tp.guide_more_scores(None, snapshot, scores)
        self.assertGreater(lifted[1][0], lifted[0][0])

    def test_track_set_orders_research_unless_a_rule_chose(self):
        player = {'player_id': 0, 'faction': 'Geodens', 'structures': [], 'tech_tiles': [],
                  'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()},
                  'resources': {'ore': 1, 'credits': 1, 'knowledge': 4, 'qic': 0}}
        snapshot = {'player': 0, 'state': {'round': 2, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'ResearchAdvance', 'track': 'Science'}},
                                   {'action': {'type': 'ResearchAdvance', 'track': 'Terraforming'}}]}
        lifted = tp.guide_more_scores(None, snapshot, [(5.0, 'a'), (3.0, 'b')])
        self.assertGreater(lifted[1][0], lifted[0][0])
        lifted = tp.guide_more_scores(None, snapshot, [(5.0, 'a; research when: Science now'), (3.0, 'b')])
        self.assertGreater(lifted[0][0], lifted[1][0])
        terrans = {**player, 'faction': 'Terrans'}
        self.assertEqual(tp._faction_tracks({}, terrans), ('navigation', 'gaia', 'economy'))
        mission = {'final_scoring_tiles': [{'condition': 'MostPlanetTypes'}]}
        self.assertIn('terraforming', tp._faction_tracks(mission, terrans))

    def test_faction_holds(self):
        hexes = {'1,1': {'planet': {'planet_type': 'Desert'}}, '0,0': {'planet': {'planet_type': 'Oxide'}}}
        state = {'round': 2, 'board': {'hexes': hexes}, 'used_power_actions': []}
        power = {'bowl1': 0, 'bowl2': 0, 'bowl3': 7, 'brainstone': None}

        def player(faction, *kinds):
            return {'faction': faction, 'structures': [{'hex': '0,0', 'kind': k} for k in kinds],
                    'resources': {'power': power}}
        fed = {'type': 'FormFederation', 'hexes': []}
        self.assertIsNotNone(tp._faction_hold(state, player('Xenos', 'Mine'), fed))
        self.assertIsNone(tp._faction_hold(state, player('Xenos', 'PlanetaryInstitute'), fed))
        pi = {'type': 'Upgrade', 'coord': '0,0', 'to': 'PlanetaryInstitute'}
        self.assertIsNotNone(tp._faction_hold(state, player('Xenos', 'TradingStation'), pi))
        build = {'type': 'Build', 'coord': '1,1'}
        self.assertIsNotNone(tp._faction_hold(state, player('Geodens', 'Mine'), build))
        self.assertIsNone(tp._faction_hold(state, player('Geodens', 'PlanetaryInstitute'), build))
        free = {'type': 'FreeAction', 'kind': 'PowerToCredit', 'count': 1}
        self.assertIsNotNone(tp._faction_hold(state, player('Terrans', 'Mine'), free))

    def test_round1_mine_and_lab_before_passing(self):
        player = {'player_id': 0, 'faction': 'Terrans', 'tech_tiles': [],
                  'structures': [{'hex': '0,0', 'kind': 'Mine'}, {'hex': '1,0', 'kind': 'TradingStation'}],
                  'research_tracks': {t: 0 for t in tp.TRACK_KEYS.values()},
                  'resources': {'ore': 1, 'credits': 1, 'knowledge': 0, 'qic': 0}}
        snapshot = {'player': 0, 'state': {'round': 1, 'phase': {'ActionPhase': {}}, 'players': [player]},
                    'candidates': [{'action': {'type': 'Build', 'coord': '2,0'}},
                                   {'action': {'type': 'Upgrade', 'coord': '1,0', 'to': 'ResearchLab'}},
                                   {'action': {'type': 'Pass', 'booster_id': 1}}]}
        with mock.patch.object(tp, '_booster_vp', return_value=0):
            lifted = tp.guide_more_scores(None, snapshot, [(-1.0, 'a'), (-2.0, 'b'), (0.0, 'c')])
        self.assertGreater(lifted[0][0], lifted[2][0])
        self.assertGreater(lifted[1][0], lifted[2][0])

    def test_ship_numbers_and_gaia_both(self):
        player = {'explored_ships': [1, 2], 'research_tracks': {'gaia': 0}, 'booster': 9,
                  'gaiaformers_total': 0, 'gaiaformers_deployed': 0, 'gaiaformers_in_gaia_area': 0,
                  'resources': {'spent_gaia_formers': 0}}
        self.assertTrue(tp._explored(player, 'Rebellion'))
        self.assertFalse(tp._explored(player, 'Eclipse'))
        state = {'used_spaceship_actions': []}
        self.assertTrue(tp._gaia_both(state, player, ['Transdim', 'Asteroid']))      # TF Mars + new former
        self.assertFalse(tp._gaia_both(state, player, ['Transdim']))
        self.assertFalse(tp._gaia_both({'used_spaceship_actions': [6]}, player, ['Transdim', 'Asteroid']))
        booster = {**player, 'explored_ships': [], 'booster': 5}
        self.assertTrue(tp._gaia_both(state, booster, ['Transdim', 'Asteroid']))

    def test_mine_tile_without_mines_in_hand(self):
        tracks = {t: 0 for t in tp.TRACK_KEYS.values()}
        full = {'structures': [{'kind': 'Mine', 'hex': f'{i},0'} for i in range(8)], 'research_tracks': tracks}
        self.assertTrue(tp._tech_held_back({'round': 3}, 11, full))
        self.assertFalse(tp._tech_held_back({'round': 3}, 11, {**full, 'structures': full['structures'][:7]}))
        player = {**full, 'faction': 'Geodens', 'resources': {}}
        state = {'round': 3, 'spaceship_boards': []}
        for action in ({'type': 'ExamineArtifact', 'artifact': 12},
                       {'type': 'RebellionGainTechTile', 'tile': 11, 'track': 'Economy'},
                       {'type': 'FormFederation', 'hexes': [], 'token': {'source': 'Supply', 'kind': 14}}):
            self.assertIsNotNone(tp._not_yet_more(state, player, action))
            self.assertIsNone(tp._not_yet_more(state, {**player, 'structures': full['structures'][:7]}, action))


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


class OpeningLabelTests(unittest.TestCase):
    """guide_label_forecast keeps the guide's opening under its own label (lab 064 follow-up)."""
    def setUp(self):
        from bgg_openings.catalog import load_catalog
        self.rows = load_catalog()['Geodens']
        self.saved = dict(tp._guide)
        tp._guide.update(geodens_b14=True, sheden_r1=False)
        self.addCleanup(lambda: tp._guide.update(self.saved))

    @staticmethod
    def forecast(name, target, counts, value, family='bgg-opening'):
        buildings = dict(mine=counts[0], trading_station=counts[1], research_lab=counts[2],
                         planetary_institute=counts[3], academy=counts[4])
        return {'goal': name, 'goal_spec': {'family': family, 'target': target}, 'family': family,
                'first': 0, 'complete': True, 'value': value, 'r1_buildings': buildings}

    def test_academy_plan_that_stopped_at_the_lab_keeps_its_label(self):
        from bgg_openings.planning import select_forecast as original
        lab = self.forecast('BGG-R1-1AC+2M', '1AC+2M', (2, 0, 1, 0, 0), 264.1)
        pi = self.forecast('Geodens-PI@1,-2', None, (3, 0, 0, 1, 0), 280.6, family='colony')
        _, opening = original(self.rows, None, [lab, pi])
        self.assertEqual(opening.label, '1PI+3M')        # the frozen rule: the reached inventory
        plan, opening = tp.guide_label_forecast(original, self.rows, None, [lab, pi])
        self.assertEqual((plan['goal'], opening.label), ('BGG-R1-1AC+2M', '1AC+2M'))

    def test_remembered_guide_label_first_then_the_guide_order(self):
        from bgg_openings.planning import select_forecast as original
        second = self.forecast('BGG-R1-1RL+1TS+2M', '1RL+1TS+2M', (2, 1, 1, 0, 0), 300.0)
        first = self.forecast('BGG-R1-1AC+2M', '1AC+2M', (2, 0, 1, 0, 0), 250.0)
        _, opening = tp.guide_label_forecast(original, self.rows, None, [second, first])
        self.assertEqual(opening.label, '1AC+2M')
        _, opening = tp.guide_label_forecast(original, self.rows, '1RL+1TS+2M', [second, first])
        self.assertEqual(opening.label, '1RL+1TS+2M')

    def test_a_forecast_that_left_the_road_to_the_label_falls_back_to_the_reached_inventory(self):
        # Lab 065: Xenos 1RL+5M was kept while its rollout ended at 1RL+1TS+3M (a second upgrade
        # chain), so the teacher chased a mine it could not build. The label now needs a forecast
        # that can still grow into it; otherwise the frozen rule remembers what was reached.
        from bgg_openings.catalog import load_catalog
        from bgg_openings.planning import select_forecast as original
        xenos = load_catalog()['Xenos']
        astray = self.forecast('BGG-R1-1RL+5M', '1RL+5M', (3, 1, 1, 0, 0), 228.8)
        _, opening = tp.guide_label_forecast(original, xenos, '1RL+5M', [astray, astray])
        self.assertEqual(opening.label, '1RL+1TS+3M')          # what the unpatched teacher remembers
        self.assertEqual(opening.label, original(xenos, '1RL+5M', [astray, astray])[1].label)
        on_the_way = self.forecast('BGG-R1-1RL+5M', '1RL+5M', (4, 0, 1, 0, 0), 228.8)
        _, opening = tp.guide_label_forecast(original, xenos, '1RL+5M', [on_the_way])
        self.assertEqual(opening.label, '1RL+5M')              # one mine short: still on the road
        too_many = self.forecast('BGG-R1-1AC+2M', '1AC+2M', (3, 0, 1, 0, 0), 250.0)
        _, opening = tp.guide_label_forecast(original, self.rows, None, [too_many])
        self.assertEqual(opening.label, '1RL+3M')              # more mines than the label: reached shape

    def test_without_a_guide_goal_or_a_guide_order_the_original_decides(self):
        from bgg_openings.planning import select_forecast as original
        pi = self.forecast('Geodens-PI@1,-2', None, (3, 0, 0, 1, 0), 280.6, family='colony')
        _, opening = tp.guide_label_forecast(original, self.rows, None, [pi])
        self.assertEqual(opening.label, '1PI+3M')
        tp._guide['geodens_b14'] = False
        lab = self.forecast('BGG-R1-1AC+2M', '1AC+2M', (2, 0, 1, 0, 0), 264.1)
        _, opening = tp.guide_label_forecast(original, self.rows, None, [lab])
        self.assertEqual(opening.label, '1RL+2M')


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

    def test_geodens_b14_first_tile_on_economy_and_no_early_gaia(self):
        from current_actions.conservation import blocked
        state = {'round': 1, 'phase': {'ActionPhase': {}},
                 'research_board': {'tech_tile_slots': [9, 7, 8, 6, 4, 2, 3, 10, 5]},
                 'players': [{'faction': 'Geodens', 'tech_tiles': []}]}
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 4, 'advance_track': None}), 'Economy')
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 2, 'advance_track': None}), 'Science')
        self.assertIsNone(tp._tile_track(state, {'kind': 'Standard', 'tile': 10, 'advance_track': None}))
        self.assertEqual(tp._tile_track(state, {'kind': 'Standard', 'tile': 10, 'advance_track': 'Economy'}), 'Economy')

        def lab(tile, track):
            return {'type': 'Upgrade', 'coord': '-3,0', 'to': 'ResearchLab',
                    'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': track}}
        actions = [lab(5, 'GaiaProject'), lab(5, 'Economy'), lab(10, 'Economy'), lab(4, None),
                   lab(10, 'GaiaProject'), {'type': 'ResearchAdvance', 'track': 'GaiaProject'},
                   {'type': 'ResearchAdvance', 'track': 'Economy'}]
        scores = [(22.0, 'a'), (20.8, 'b'), (19.5, 'c'), (18.0, 'd'), (20.6, 'e'), (6.4, 'f'), (0.0, 'g')]
        snapshot = {'state': state, 'player': 0, 'candidates': [{'action': a} for a in actions]}
        lifted = tp.geodens_b14_tech_scores(None, snapshot, scores)
        best = max(range(len(lifted)), key=lambda i: lifted[i][0])
        self.assertEqual(best, 2)                                 # the 4-charge tile on Economy leads the lab
        self.assertEqual(lifted[2][0], 20.8)                      # with the group's best non-Gaia score
        self.assertLess(lifted[0][0], -900)                       # tile 5 + Gaia and the Gaia research pushed down
        self.assertLess(lifted[4][0], -900)
        self.assertLess(lifted[5][0], -900)
        self.assertEqual(lifted[6], scores[6])                    # other research untouched
        self.assertFalse(any(blocked(s) for s in lifted))
        state['players'][0]['faction'] = 'Terrans'
        self.assertIs(tp.geodens_b14_tech_scores(None, snapshot, scores), scores)

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

    def test_label_value_picks_the_best_completed_guide_opening(self):
        from bgg_openings.catalog import Opening
        rows = (Opening('Geodens', '1AC+2M', 123, 146, 4, 6), Opening('Geodens', '1PI+1TS+2M', 100, 140, 4, 7))
        plans = [{'goal_spec': {'family': 'bgg-opening', 'target': '1AC+2M'}, 'complete': True, 'value': 279.8,
                  'r1_buildings': {'mine': 2, 'trading_station': 0, 'research_lab': 0, 'planetary_institute': 0, 'academy': 1}},
                 {'goal_spec': {'family': 'bgg-opening', 'target': '1PI+1TS+2M'}, 'complete': True, 'value': 339.7,
                  'r1_buildings': {'mine': 2, 'trading_station': 1, 'research_lab': 0, 'planetary_institute': 1, 'academy': 0}}]
        with mock.patch.object(tp, 'guide_opening_labels', return_value=('1AC+2M', '1PI+1TS+2M')):
            original = lambda rows, remembered, comparisons: None
            plan, opening = tp.guide_label_forecast(original, rows, '1AC+2M', plans)
            self.assertEqual(opening.label, '1AC+2M')                  # guide order, as before
            tp._guide['label_value'] = True
            plan, opening = tp.guide_label_forecast(original, rows, '1AC+2M', plans)
            self.assertEqual(opening.label, '1PI+1TS+2M')              # the better completed guide opening
            plans[1]['value'] = 279.8
            plan, opening = tp.guide_label_forecast(original, rows, '1AC+2M', plans)
            self.assertEqual(opening.label, '1AC+2M')                  # tie: the remembered, guide-first label

    def test_ships_fix_label_factory_installs_the_forecast_hook(self):
        # Lab 072: the factory set label_value without install_opening_label(), so the hook that reads
        # the flag was never on planning.select_forecast and the B arm played the A arm's code.
        # Built in a subprocess: the factory rebinds module-level functions for the whole process,
        # which would leak into the tests that run after this one.
        import subprocess
        import sys
        code = ("import teacher_patches as tp, bgg_openings.planning as p\n"
                "tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_fix_label(%r)\n"
                "print(getattr(p.select_forecast, '_opening_label', False), tp._guide['label_value'])" % SEED)
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.split(), ['True', 'True'])

    def test_ships_label_value_and_fix_noacademy_factories_set_their_flags(self):
        # Labs 077 and 078 (built in subprocesses, see the test above).
        import subprocess
        import sys
        code = ("import teacher_patches as tp, bgg_openings.planning as p\n"
                "tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_label_value(%r)\n"
                "print(getattr(p.select_forecast, '_opening_label', False), tp._guide['label_value'],"
                " tp._guide['opening_budget'], tp._guide['academy_economy'])" % SEED)
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.split(), ['True', 'True', 'False', 'False'])
        code = ("import teacher_patches as tp, bgg_openings.planning as p\n"
                "tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_fix_noacademy(%r)\n"
                "print(tp._guide['opening_budget'], tp._guide['budget_guard'], tp._guide['opening_release'],"
                " tp._guide['geodens_b14_tech'], tp._guide['academy_economy'], tp._guide['former_use'],"
                " tp._guide['instant_forming'], getattr(p.select_forecast, '_opening_label', False))" % SEED)
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True).stdout
        self.assertEqual(out.split(), ['True', 'True', 'True', 'True', 'False', 'False', 'False', 'False'])

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
