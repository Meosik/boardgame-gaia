"""E369 standard tech tile pruning (teacher_patches._tile_class / _prune_tile / prune_indices)."""
import unittest
from unittest import mock

import teacher_patches as tp

SLOTS = [2, 3, 4, 10, 6, 7, 5, 8, 9]    # 0-5 on-track (Terra, Nav, AI, Gaia, Eco, Sci), 6-8 middle row


def make_state(faction, slots=None, rnd=2, labs=0, navigation=2, tracks=None):
    levels = {'navigation': navigation, 'economy': 0, 'science': 0, 'terraforming': 0, 'gaia': 0, 'ai': 0}
    levels.update(tracks or {})
    structures = [{'kind': 'Mine', 'hex': 'home'}] + [{'kind': 'ResearchLab', 'hex': 'lab%d' % i} for i in range(labs)]
    player = {'faction': faction, 'research_tracks': levels,
              'resources': {'ore': 0, 'credits': 0, 'knowledge': 0, 'qic': 0,
                            'power': {'bowl1': 0, 'bowl2': 0, 'bowl3': 0}},
              'structures': structures, 'booster': None, 'tech_tiles': [], 'covered_tech_tiles': [], 'artifacts': []}
    state = {'phase': {'ActionPhase': {}}, 'round': rnd, 'players': [player], 'board': {'hexes': {}},
             'research_board': {'tech_tile_slots': list(SLOTS if slots is None else slots)}}
    return state, player


def upgrade(tile, track, coord='x'):
    return {'type': 'Upgrade', 'coord': coord, 'to': 'ResearchLab',
            'tech_tile_choice': {'kind': 'Standard', 'tile': tile, 'advance_track': track}}


class PruneTile(unittest.TestCase):
    def test_taklons_charge4_under_gaia(self):
        state, player = make_state('Taklons')
        self.assertEqual(tp._tile_class(state, player, 10), 'avoid')
        state, player = make_state('Taklons', slots=[2, 3, 4, 9, 6, 7, 10, 8, 5])
        self.assertEqual(tp._tile_class(state, player, 10), 'good')

    def test_geodens_tile9_late(self):
        for rnd, want in ((3, 'later'), (4, 'good')):
            state, player = make_state('Geodens', slots=[2, 3, 4, 10, 6, 7, 5, 8, 9], rnd=rnd)
            self.assertEqual(tp._tile_class(state, player, 9), want, rnd)

    def test_bescods_tile3_by_labs(self):
        for labs, want in ((0, 'avoid'), (1, 'ok')):
            state, player = make_state('Bescods', labs=labs)
            self.assertEqual(tp._tile_class(state, player, 3), want, labs)
        state, player = make_state('Bescods', labs=2)
        self.assertEqual(tp._tile_class(state, player, 2), 'good')

    def test_ambas_navigation_tile(self):
        state, player = make_state('Ambas', rnd=1, navigation=0)
        self.assertEqual(tp._tile_class(state, player, 12), 'good')
        state, player = make_state('Ambas', rnd=3, navigation=0)
        self.assertEqual(tp._tile_class(state, player, 12), 'avoid')
        self.assertEqual(tp._tile_class(state, player, 13), 'good')

    def test_prune_tile_tier_by_track(self):
        state, player = make_state('Taklons')    # plan: navigation + economy (first two below cap)
        self.assertEqual(tp._prune_tile(state, player, upgrade(5, 'Economy')), 0)
        self.assertEqual(tp._prune_tile(state, player, upgrade(5, 'Terraforming')), 1)
        self.assertIsNone(tp._prune_tile(state, player, {'type': 'Upgrade', 'coord': 'x'}))

    def run_indices(self, state, candidates):
        snap = {'state': state, 'player': 0, 'candidates': [{'action': a} for a in candidates]}
        with mock.patch.object(tp, '_prune_mine', lambda *a: None), \
                mock.patch.object(tp, '_prune_power_tf', lambda *a: None), \
                mock.patch.object(tp, '_prune_feds', lambda *a: set()), \
                mock.patch.object(tp, '_prune_convs', lambda *a: set()):
            return tp.prune_indices(snap)

    def test_indices_block_worse_tiers(self):
        state, _ = make_state('Taklons')
        got = self.run_indices(state, [upgrade(5, 'Economy'), upgrade(5, 'Terraforming'), upgrade(8, 'Economy')])
        self.assertEqual(got, {1, 2})

    def test_indices_same_tier_keeps_all(self):
        state, _ = make_state('Taklons')
        got = self.run_indices(state, [upgrade(5, 'Terraforming', 'x'), upgrade(5, 'Terraforming', 'y')])
        self.assertEqual(got, set())


if __name__ == '__main__':
    unittest.main()
