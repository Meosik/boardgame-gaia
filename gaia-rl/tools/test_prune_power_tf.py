"""E368 terraforming power-action filter (teacher_patches._prune_power_tf / prune_indices)."""
import unittest
from unittest import mock

import teacher_patches as tp

# Terrans (home Terra): Terra 0 steps, Oxide 1, Volcanic 2 (RING order).
PLANETS = {'own': 'Terra', 'one': 'Oxide', 'two': 'Volcanic', 'gaia': 'Gaia'}


def snapshot(candidates, terraforming=0, faction='Terrans'):
    player = {'faction': faction, 'research_tracks': {'terraforming': terraforming, 'economy': 0, 'science': 0},
              'resources': {'ore': 0, 'credits': 0, 'knowledge': 0, 'qic': 0,
                            'power': {'bowl1': 0, 'bowl2': 0, 'bowl3': 0}},
              'structures': [{'kind': 'Mine', 'hex': 'home'}],
              'booster': None, 'tech_tiles': [], 'covered_tech_tiles': [], 'artifacts': []}
    hexes = {name: {'planet': {'planet_type': kind}} for name, kind in PLANETS.items()}
    state = {'phase': {'ActionPhase': {}}, 'round': 2, 'players': [player], 'board': {'hexes': hexes},
             'research_board': {'economy_research_tile_side': 'Power'}}
    return {'state': state, 'player': 0, 'candidates': [{'action': a} for a in candidates]}


def pa(id, coord):
    return {'type': 'PowerAction', 'id': id, 'coord': coord}


class PowerTf(unittest.TestCase):
    def setUp(self):
        self.distance = 0
        patches = [mock.patch('economy.teacher.path_distance', lambda state, starts, coord: self.distance),
                   mock.patch('four_factions.value.navigation', lambda player: 0)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def verdict(self, action, **kw):
        snap = snapshot([action], **kw)
        return tp._prune_power_tf(snap['state'], snap['state']['players'][0], action)

    def test_exact_fit_kept(self):
        for distance in (0, 1):    # qic 0 and 1
            self.distance = distance
            self.assertFalse(self.verdict(pa(6, 'one')), distance)
            self.assertFalse(self.verdict(pa(2, 'two')), distance)

    def test_two_qic_blocked(self):
        self.distance = 3    # (3-0+1)//2 = 2
        self.assertTrue(self.verdict(pa(6, 'one')))
        self.assertTrue(self.verdict(pa(2, 'two')))

    def test_own_colour_blocked(self):
        self.assertTrue(self.verdict(pa(6, 'own')))
        self.assertTrue(self.verdict(pa(2, 'own')))

    def test_wasted_spade_blocked(self):
        self.assertTrue(self.verdict(pa(2, 'one')))
        self.assertTrue(self.verdict(pa(2, 'one'), terraforming=3))

    def test_buying_extra_spade_needs_terraforming_3(self):
        self.assertTrue(self.verdict(pa(6, 'two'), terraforming=0))
        self.assertTrue(self.verdict(pa(6, 'two'), terraforming=2))
        self.assertFalse(self.verdict(pa(6, 'two'), terraforming=3))

    def test_off_ring_blocked_exact_fit_kept(self):
        self.assertTrue(self.verdict(pa(6, 'gaia')))
        snap = snapshot([pa(6, 'gaia'), pa(6, 'one')])
        self.assertEqual(tp.prune_indices(snap), {0})

    def test_not_a_terraforming_power_action(self):
        self.assertIsNone(self.verdict(pa(3, None)))
        self.assertIsNone(self.verdict(pa(6, None)))
        self.assertIsNone(self.verdict({'type': 'Build', 'coord': 'one'}))

    def test_blocked_candidates_pruned(self):
        snap = snapshot([pa(6, 'one'), pa(2, 'one'), {'type': 'Pass'}])
        self.assertEqual(tp.prune_indices(snap), {1})

    def test_family_restored_when_all_blocked(self):
        snap = snapshot([pa(6, 'own'), pa(2, 'one'), {'type': 'Pass'}])
        self.assertEqual(tp.prune_indices(snap), set())


if __name__ == '__main__':
    unittest.main()
