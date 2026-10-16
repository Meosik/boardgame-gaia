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
