"""formed_mine: BalTaks builds the mine on its own formed Gaia planet before passing (teacher_patches.formed_mine_scores)."""
import copy
import json
import unittest

import teacher_patches as tp
from current_actions.conservation import BLOCKED, PREFIX
from test_prune_convs import snapshot

HEX = '-8,1'
BUILD = {'type': 'Build', 'coord': HEX}
PASS = {'type': 'Pass', 'booster_id': 12}
QIC = {'type': 'FreeAction', 'kind': 'QicToOre', 'count': 1}
RES = {'ore': 0, 'credits': 6, 'knowledge': 0, 'qic': 1}


class FakeFork:
    def __init__(self, snap, children=None):
        self.snap = snap
        self.children = children or {}    # candidate index -> FakeFork

    def snapshot_json(self):
        return json.dumps(self.snap)

    def fork(self, decision_id, index):
        return self.children.get(index, FakeFork(self.snap))


class FakeEnv:
    def __init__(self, after):
        self.after = after

    def fork(self, decision_id, index):
        return FakeFork(self.after)


def make(candidates, faction='BalTaks', structures=()):
    snap = snapshot(RES, [], candidates)
    snap['decision_id'] = 1
    player = snap['state']['players'][0]
    player['faction'] = faction
    player['structures'] = [{'hex': h, 'kind': 'Mine'} for h in structures]
    snap['state']['board']['hexes'] = {
        HEX: {'planet': {'planet_type': 'Transdim', 'is_gaia_formed': True, 'owner': 0}, 'structures': []}}
    return snap


class FormedMine(unittest.TestCase):
    def setUp(self):
        tp._guide['formed_mine'] = True

    def tearDown(self):
        tp._guide.pop('formed_mine', None)

    def scores(self, snap, **special):
        return [special.get(str(i), (1.0 + i, 'r')) for i in range(len(snap['candidates']))]

    def test_1_build_on_top_pass_blocked(self):
        snap = make([PASS, BUILD, QIC])
        out = tp.formed_mine_scores(None, snap, [(9.0, 'r'), (1.0, 'r'), (2.0, 'r')])
        self.assertGreater(out[1][0], 9.0)
        self.assertIn('formed_mine', out[1][1])
        self.assertEqual(out[0][0], BLOCKED)
        self.assertTrue(out[0][1].startswith(PREFIX))

    def test_2_qic_to_ore_lifted_even_if_blocked(self):
        snap = make([PASS, QIC])
        after = copy.deepcopy(snap)
        after['candidates'] = [{'action': BUILD}, {'action': PASS}]
        out = tp.formed_mine_scores(FakeEnv(after), snap, [(9.0, 'r'), (BLOCKED, PREFIX + 'prune')])
        self.assertGreater(out[1][0], 9.0)
        self.assertNotEqual(out[1][0], BLOCKED)
        self.assertIn('QicToOre', out[1][1])
        self.assertEqual(out[0][0], BLOCKED)

    def test_2b_no_build_after_fork_unchanged(self):
        snap = make([PASS, QIC])
        after = copy.deepcopy(snap)
        scores = [(9.0, 'r'), (1.0, 'r')]
        self.assertEqual(tp.formed_mine_scores(FakeEnv(after), snap, scores), scores)

    def test_2c_two_step_chain_lifts_first_conversion(self):
        kc = {'type': 'FreeAction', 'kind': 'KnowledgeToCredit', 'count': 1}
        snap = make([PASS, kc, QIC])
        dead = copy.deepcopy(snap)
        dead['candidates'] = [{'action': PASS}]
        mid = copy.deepcopy(snap)
        mid['candidates'] = [{'action': PASS}, {'action': QIC}]
        done = copy.deepcopy(snap)
        done['candidates'] = [{'action': BUILD}, {'action': PASS}]
        env = FakeFork(snap, {2: FakeFork(dead), 1: FakeFork(mid, {1: FakeFork(done)})})
        out = tp.formed_mine_scores(env, snap, [(9.0, 'r'), (1.0, 'r'), (2.0, 'r')])
        self.assertGreater(out[1][0], 9.0)
        self.assertIn('KnowledgeToCredit -> QicToOre', out[1][1])
        self.assertEqual(out[0][0], BLOCKED)
        self.assertEqual(out[2], (2.0, 'r'))

    def test_3_other_faction_unchanged(self):
        snap = make([PASS, BUILD], faction='Terrans')
        scores = [(9.0, 'r'), (1.0, 'r')]
        self.assertEqual(tp.formed_mine_scores(None, snap, scores), scores)

    def test_4_hex_already_built_unchanged(self):
        snap = make([PASS, BUILD], structures=[HEX])
        scores = [(9.0, 'r'), (1.0, 'r')]
        self.assertEqual(tp.formed_mine_scores(None, snap, scores), scores)
        snap = make([PASS, BUILD])
        snap['state']['board']['hexes'][HEX]['structures'] = [{'kind': 'Mine'}]
        self.assertEqual(tp.formed_mine_scores(None, snap, scores), scores)

    def test_5_flag_off_unchanged(self):
        tp._guide['formed_mine'] = False
        snap = make([PASS, BUILD])
        scores = [(9.0, 'r'), (1.0, 'r')]
        self.assertEqual(tp.formed_mine_scores(None, snap, scores), scores)


if __name__ == '__main__':
    unittest.main()
