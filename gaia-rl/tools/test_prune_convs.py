"""E368 conversions-as-payment filter (teacher_patches._prune_convs / prune_indices)."""
import unittest

import teacher_patches as tp


def snapshot(resources, structures, candidates, bowl2=0, bowl3=0):
    player = {'faction': 'Terrans', 'research_tracks': {'terraforming': 0},
              'resources': {**resources, 'power': {'bowl1': 0, 'bowl2': bowl2, 'bowl3': bowl3}},
              'structures': [{'kind': k, 'hex': f'h{i}'} for i, k in enumerate(structures)]}
    state = {'phase': {'ActionPhase': {}}, 'round': 2, 'players': [player], 'board': {'hexes': {}}}
    return {'state': state, 'player': 0, 'candidates': [{'action': a} for a in candidates]}


def conv(kind):
    return {'type': 'FreeAction', 'kind': kind, 'count': 1}


KINDS = ('BurnPower', 'PowerToCredit', 'KnowledgeToCredit', 'OreToCredit', 'PowerToOre', 'PowerToKnowledge',
         'OreToPower')


class PayFilter(unittest.TestCase):
    def blocked_kinds(self, snap):
        out = tp.prune_indices(snap)
        return {c['action'].get('kind') for i, c in enumerate(snap['candidates']) if i in out}

    def test_short_credits_keep_credit_payments_only(self):
        # TS needs 2 ore 3 credits: 2 credits short, covered by spare knowledge/ore. Research (4 knowledge)
        # would need 8 power that is not there, so power→knowledge stays blocked.
        snap = snapshot({'ore': 3, 'credits': 1, 'knowledge': 2, 'qic': 0}, ['Mine'],
                        [conv(k) for k in KINDS] + [{'type': 'Pass'}])
        self.assertEqual(self.blocked_kinds(snap), {'PowerToOre', 'PowerToKnowledge', 'OreToPower'})

    def test_no_shortage_blocks_every_payment(self):
        snap = snapshot({'ore': 9, 'credits': 20, 'knowledge': 9, 'qic': 3}, ['Mine'],
                        [conv(k) for k in KINDS] + [{'type': 'Pass'}])
        self.assertEqual(self.blocked_kinds(snap),
                         {'KnowledgeToCredit', 'OreToCredit', 'PowerToOre', 'PowerToKnowledge', 'OreToPower'})

    def test_short_ore_keeps_power_to_ore(self):
        snap = snapshot({'ore': 0, 'credits': 9, 'knowledge': 9, 'qic': 0}, [],
                        [conv('PowerToOre'), {'type': 'Pass'}], bowl3=3)
        self.assertEqual(self.blocked_kinds(snap), set())

    def test_unaffordable_even_with_conversions_blocks(self):
        snap = snapshot({'ore': 0, 'credits': 0, 'knowledge': 0, 'qic': 0}, [],
                        [conv('PowerToOre'), {'type': 'Pass'}], bowl3=3)
        self.assertEqual(self.blocked_kinds(snap), {'PowerToOre'})

    def test_lone_trading_station_keeps_knowledge_to_credit(self):
        # Codex debate 1/1: a 3-credit station may be legal, a 6-credit one needs 3 knowledge→credit.
        upgrade = {'type': 'Upgrade', 'coord': 'h0', 'to': 'TradingStation', 'tech_tile_choice': None}
        snap = snapshot({'ore': 2, 'credits': 3, 'knowledge': 3, 'qic': 0}, ['Mine'],
                        [conv('KnowledgeToCredit'), upgrade, {'type': 'Pass'}])
        self.assertEqual(self.blocked_kinds(snap), set())

    def test_legal_mine_does_not_hide_gaia_mine_qic(self):
        build = {'type': 'Build', 'coord': 'h9'}
        snap = snapshot({'ore': 9, 'credits': 20, 'knowledge': 0, 'qic': 0}, ['Mine'],
                        [conv('PowerToQic'), build, {'type': 'Pass'}], bowl3=4)
        self.assertEqual(self.blocked_kinds(snap), set())

    def test_never_blocks_everything(self):
        snap = snapshot({'ore': 9, 'credits': 20, 'knowledge': 9, 'qic': 3}, [], [conv('OreToCredit')])
        self.assertEqual(tp.prune_indices(snap), set())


if __name__ == '__main__':
    unittest.main()
