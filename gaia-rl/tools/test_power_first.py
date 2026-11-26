"""E368 power action first (teacher_patches.power_first_scores)."""
import unittest

import teacher_patches as tp
from test_prune_convs import snapshot

PA3 = {'type': 'PowerAction', 'id': 3, 'coord': None}
PA5 = {'type': 'PowerAction', 'id': 5, 'coord': None}
PASS = {'type': 'Pass'}
BUILD = {'type': 'Build', 'coord': 'h9'}
UPGRADE = {'type': 'Upgrade', 'coord': 'h0', 'to': 'TradingStation', 'tech_tile_choice': None}
OTHER = {'type': 'FreeAction', 'kind': 'BurnPower', 'count': 1}


def run(snap, top_index, others=0.0):
    """Top candidate gets 9, the rest `others`; returns the index with the highest score after the patch."""
    scores = [(9.0 if i == top_index else others, 'r') for i in range(len(snap['candidates']))]
    out = tp.power_first_scores(None, snap, scores)
    return max(range(len(out)), key=lambda i: out[i][0]), out


class PowerFirst(unittest.TestCase):
    def test_a_ore_power_action_swaps_with_pass(self):
        # A mine is 1 ore short; id 3 gives 2 ore.
        snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, [], [PASS, PA3])
        best, out = run(snap, 0)
        self.assertEqual(best, 1)
        self.assertEqual(out[0][0], 0.0)
        self.assertIn('power_first', out[1][1])

    def test_b_without_power_action_unchanged(self):
        snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, [], [PASS, OTHER])
        best, _ = run(snap, 0)
        self.assertEqual(best, 0)

    def test_c_progressing_top_unchanged(self):
        for top in (BUILD, UPGRADE):
            snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, ['Mine'], [top, PA3])
            best, _ = run(snap, 0)
            self.assertEqual(best, 0, top['type'])

    def test_d_knowledge_for_research(self):
        snap = snapshot({'ore': 9, 'credits': 20, 'knowledge': 2, 'qic': 0}, [], [PASS, PA5])
        best, _ = run(snap, 0)
        self.assertEqual(best, 1)

    def test_e_shortfall_too_big_unchanged(self):
        # Only a lab is left to pay for (8 mines, 4 stations), 3 ore short; id 3 gives 2.
        snap = snapshot({'ore': 0, 'credits': 20, 'knowledge': 9, 'qic': 0}, ['Mine']*8 + ['TradingStation']*4,
                        [PASS, PA3])
        best, _ = run(snap, 0)
        self.assertEqual(best, 0)

    def test_tied_top_candidates_power_action_strictly_first(self):
        snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, [], [PASS, OTHER, PA3])
        scores = [(9.0, 'r'), (9.0, 'r'), (0.0, 'r')]
        out = tp.power_first_scores(None, snap, scores)
        self.assertIn('power_first', out[2][1])
        for j in (0, 1):
            self.assertGreater(out[2][0], out[j][0])

    def test_blocked_power_action_ignored(self):
        snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, [], [PASS, PA3])
        from current_actions.conservation import BLOCKED, PREFIX
        scores = [(9.0, 'r'), (BLOCKED, PREFIX+'pruned')]
        self.assertEqual(tp.power_first_scores(None, snap, scores), scores)


if __name__ == '__main__':
    unittest.main()
