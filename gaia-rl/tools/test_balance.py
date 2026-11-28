"""E380 next-round credit:ore balance (teacher_patches.balance_scores)."""
import unittest

import teacher_patches as tp
from four_factions.value import production
from test_prune_convs import snapshot

PA3 = {'type': 'PowerAction', 'id': 3, 'coord': None}
PA4 = {'type': 'PowerAction', 'id': 4, 'coord': None}
PASS = {'type': 'Pass'}
BUILD = {'type': 'Build', 'coord': 'h9'}
CONV = {'type': 'FreeAction', 'kind': 'PowerToCredit', 'count': 1}


def run(snap, top_index=0, others=0.0):
    scores = [(9.0 if i == top_index else others, 'r') for i in range(len(snap['candidates']))]
    out = tp.balance_scores(None, snap, scores)
    return max(range(len(out)), key=lambda i: out[i][0]), out


def income(snap):
    return production(snap['state'], snap['state']['players'][0], include_booster=False)


class Balance(unittest.TestCase):
    def res(self, ore, credits):
        return {'ore': ore, 'credits': credits, 'knowledge': 0, 'qic': 0}

    def test_a_credits_short_lifts_pa4(self):
        snap = snapshot(self.res(10, 0), [], [PASS, PA4])
        inc = income(snap)
        self.assertLess(0 + inc[1], 10 + inc[0])
        best, out = run(snap)
        self.assertEqual(best, 1)
        self.assertIn('balance', out[1][1])

    def test_b_ore_short_lifts_pa3(self):
        snap = snapshot(self.res(0, 30), [], [PASS, PA3])
        inc = income(snap)
        self.assertGreater(30 + inc[1], 2*(0 + inc[0]))
        best, _ = run(snap)
        self.assertEqual(best, 1)

    def test_c_in_band_unchanged(self):
        snap = snapshot(self.res(10, 0), [], [PASS, PA3, PA4])
        inc = income(snap)
        o = 10 + inc[0]
        credits = round(1.5*o) - inc[1]
        snap = snapshot(self.res(10, credits), [], [PASS, PA3, PA4])
        c = credits + inc[1]
        self.assertTrue(o <= c <= 2*o)
        best, _ = run(snap)
        self.assertEqual(best, 0)

    def test_d_build_top_unchanged(self):
        snap = snapshot(self.res(10, 0), ['Mine'], [BUILD, PA4])
        best, _ = run(snap)
        self.assertEqual(best, 0)

    def test_e_round_6_unchanged(self):
        snap = snapshot(self.res(10, 0), [], [PASS, PA4], round=6)
        best, _ = run(snap)
        self.assertEqual(best, 0)

    def test_f_wrong_power_action_not_lifted(self):
        snap = snapshot(self.res(10, 0), [], [PASS, PA3])
        best, _ = run(snap)
        self.assertEqual(best, 0)

    def test_g_free_conversion_never_lifted(self):
        snap = snapshot(self.res(10, 0), [], [PASS, CONV])
        best, _ = run(snap)
        self.assertEqual(best, 0)


if __name__ == '__main__':
    unittest.main()
