"""fed_absorb / fed_prep / nav_good (teacher_patches, factory ..._formedmine_fednav, E383)."""
import unittest
from unittest import mock

import teacher_patches as tp

FLAGS = ('fed_absorb', 'fed_prep', 'nav_good')


def planet(owner=None):
    return {'planet_type': 'Terra', 'is_gaia_formed': False, 'owner': owner}


def state_with(hexes, players=None):
    return {'board': {'hexes': hexes}, 'players': players or [], 'round': 2}


class FlagCase(unittest.TestCase):
    def setUp(self):
        self.saved = {k: tp._guide.get(k) for k in FLAGS}

    def tearDown(self):
        for k, v in self.saved.items():
            if v is None:
                tp._guide.pop(k, None)
            else:
                tp._guide[k] = v


class ComingMines(FlagCase):
    def test_1_empty_own_planet_returned(self):
        state = state_with({'0,0': {'planet': planet(1), 'structures': []}})
        out = tp._coming_mines(state, {'player_id': 1}, set())
        self.assertEqual(out, [{'hex': '0,0', 'kind': 'Mine'}])

    def test_2_next_to_federated_hex_not_returned(self):
        near = tp._hex_neighbors('5,5')[0]
        state = state_with({near: {'planet': planet(1), 'structures': []}})
        self.assertEqual(tp._coming_mines(state, {'player_id': 1}, {'5,5'}), [])

    def test_3_federated_hex_itself_not_returned(self):
        state = state_with({'5,5': {'planet': planet(1), 'structures': []}})
        self.assertEqual(tp._coming_mines(state, {'player_id': 1}, {'5,5'}), [])

    def test_4_other_owner_or_structure_not_returned(self):
        state = state_with({
            '0,0': {'planet': planet(0), 'structures': []},
            '3,0': {'planet': planet(1), 'structures': [{'kind': 'Mine'}]},
            '6,0': {'planet': planet(None), 'structures': []},
            '9,0': {'structures': []}})
        self.assertEqual(tp._coming_mines(state, {'player_id': 1}, set()), [])


class FederationProgress(FlagCase):
    def progress(self, absorb, hexes, federated=()):
        player = {'player_id': 1, 'faction': 'X', 'federated_hexes': list(federated),
                  'structures': [{'hex': '0,0', 'kind': 'Mine'}]}
        tp._guide['fed_absorb'] = absorb
        with mock.patch('guide_value.to_vp', lambda state, charges: charges), \
                mock.patch.object(tp, '_part', lambda p, name: False):
            return tp.federation_progress(state_with(hexes), player)

    def test_1_linking_coming_mine_raises_value(self):
        hexes = {'2,0': {'planet': planet(1), 'structures': []}}
        off, on = self.progress(False, hexes), self.progress(True, hexes)
        self.assertGreater(on, off)

    def test_2_coming_mine_touching_federation_adds_nothing(self):
        # the federated hex is far from our mine at 0,0; the planet beside it is excluded
        fed = '9,9'
        near = tp._hex_neighbors(fed)[0]
        hexes = {near: {'planet': planet(1), 'structures': []}}
        off = self.progress(False, hexes, [fed])
        on = self.progress(True, hexes, [fed])
        self.assertEqual(on, off)

    def test_3_far_coming_mine_forms_own_group(self):
        hexes = {'8,0': {'planet': planet(1), 'structures': []}}
        self.assertEqual(self.progress(True, hexes), self.progress(False, hexes))


class FedPrepOrder(unittest.TestCase):
    def setUp(self):
        self.snap = {'candidates': [{'action': {'type': 'Pass'}}, {'action': {'type': 'FormFederation'}}]}
        self.now, self.prep = 'NOW', ['P1', 'P2']

    def tearDown(self):
        tp._fed_scores.pop(id(self.snap), None)

    def test_1_top_is_federation(self):
        tp._fed_scores[id(self.snap)] = [(1.0, 'r'), (5.0, 'r')]
        self.assertEqual(tp._fed_prep_order(self.snap, self.now, self.prep), ['P1', 'P2', 'NOW'])

    def test_2_top_not_federation(self):
        tp._fed_scores[id(self.snap)] = [(9.0, 'r'), (5.0, 'r')]
        self.assertEqual(tp._fed_prep_order(self.snap, self.now, self.prep), ['NOW', 'P1', 'P2'])

    def test_3_empty_prep(self):
        tp._fed_scores[id(self.snap)] = [(1.0, 'r'), (5.0, 'r')]
        self.assertEqual(tp._fed_prep_order(self.snap, self.now, []), ['NOW'])

    def test_4_scores_missing(self):
        self.assertEqual(tp._fed_prep_order(self.snap, self.now, self.prep), ['NOW'])


def fake_range_qic(state, player, target, bonus=0, starts=None):
    return 1 if player['research_tracks']['navigation'] < 2 else 0


def ship_state(shuttles=1, explored=()):
    player = {'research_tracks': {'navigation': 1}, 'resources': {'qic': 0},
              'exploration_shuttles_available': shuttles, 'explored_ships': list(explored)}
    state = {'board': {'spaceship_tiles': {'Twilight': '1,1'}}, 'players': [player]}
    return state, player


class OpenedShips(unittest.TestCase):
    def run_ships(self, **kw):
        state, player = ship_state(**kw)
        with mock.patch('economy.teacher.range_qic', fake_range_qic):
            return tp._opened_ships(state, player, 2)

    def test_1_no_shuttle(self):
        self.assertEqual(self.run_ships(shuttles=0), [])

    def test_2_ship_in_range_after_step(self):
        self.assertEqual(self.run_ships(), ['Twilight'])

    def test_3_explored_excluded(self):
        self.assertEqual(self.run_ships(explored=[0]), [])

    def test_4_already_in_range_excluded(self):
        state, player = ship_state()
        with mock.patch('economy.teacher.range_qic', lambda s, p, t, **k: 0):
            self.assertEqual(tp._opened_ships(state, player, 2), [])


NAV_RANGE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4}
NAV_DIST = {'1,0': 1, '2,0': 2, '3,0': 4, '4,0': 2}      # coord -> distance
NAV_TYPE = {'1,0': 'Good', '2,0': 'Good', '3,0': 'Good', '4,0': 'Bad'}


def dist_range_qic(state, player, coord, bonus=0, starts=None):
    return max(0, (NAV_DIST[coord] - NAV_RANGE[player['research_tracks']['navigation']] + 1) // 2)


class NavGood(FlagCase):
    def opened(self, flag, qic=1):
        tp._guide['nav_good'] = flag
        hexes = {c: {'planet': {'planet_type': t}} for c, t in NAV_TYPE.items()}
        player = {'faction': 'X', 'research_tracks': {'navigation': 1}, 'resources': {'qic': qic}}
        state = state_with(hexes)

        def targets(st, p, types):      # in reach with the QIC the player holds
            return [(c, hexes[c]['planet'], 0) for c in hexes if dist_range_qic(st, p, c) <= p['resources']['qic']]
        with mock.patch.object(tp._value, 'targets', targets), \
                mock.patch('economy.teacher.range_qic', dist_range_qic), \
                mock.patch.object(tp, '_fed_plan_usable', lambda st, p, pl, gaia_planned=False: pl['planet_type'] == 'Good'), \
                mock.patch.object(tp, '_colony_cost', lambda st, p, c: (True, 0)):
            return tp._opened_colonies(state, player, 'navigation', 2)

    def test_1_needs_qic_now_none_after(self):
        # nav 1 to 2, 1 QIC held: distance 2 (QIC 1 now, 0 after) in; distance 4 (still QIC 1) out;
        # distance 1 (already in range) out; the bad planet at distance 2 out
        self.assertEqual(self.opened(True), ['2,0'])

    def test_2_held_qic_does_not_matter(self):
        self.assertEqual(self.opened(True, qic=0), ['2,0'])

    def test_3_without_flag_old_reach_difference(self):
        # old: reach(after) - reach(player) with the held QIC: distance 4 (QIC 1 at level 2) newly reachable
        self.assertEqual(self.opened(False), ['3,0'])


class GoodByCost(unittest.TestCase):
    def setUp(self):
        self.saved = tp._guide.get('good_by_cost')

    def tearDown(self):
        if self.saved is None:
            tp._guide.pop('good_by_cost', None)
        else:
            tp._guide['good_by_cost'] = self.saved

    def usable(self, flag, level, steps):
        tp._guide['good_by_cost'] = flag
        player = {'research_tracks': {'terraforming': level}}
        with mock.patch.object(tp, '_terraform_steps', lambda st, p, kind: steps):
            return tp._fed_plan_usable({}, player, {'planet_type': 'Desert'})

    def test_1_level0(self):
        self.assertTrue(self.usable(True, 0, 1))
        self.assertFalse(self.usable(True, 0, 2))

    def test_2_level2(self):
        self.assertTrue(self.usable(True, 2, 1))     # 2 ore
        self.assertFalse(self.usable(True, 2, 2))    # 4 ore

    def test_3_level3(self):
        self.assertTrue(self.usable(True, 3, 3))     # 3 ore
        self.assertFalse(self.usable(True, 2, 3))

    def test_4_flag_off_level3(self):
        self.assertFalse(self.usable(False, 3, 2))
        self.assertTrue(self.usable(False, 3, 1))

    def test_5_steps_none(self):
        self.assertFalse(self.usable(True, 3, None))


class Factory(unittest.TestCase):
    def test_factory_exists(self):
        self.assertTrue(callable(
            tp.guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier_prune_fedplan_balance_formedmine_fednav))


if __name__ == '__main__':
    unittest.main()
