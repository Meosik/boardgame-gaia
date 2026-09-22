import copy
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from action_purpose.costs import construction_cost, CorrectedContextTeacher, expansion_gain
from action_purpose.teacher import PurposeTeacher, conversion_loss, ship_followup
from economy.test_teacher import fixture, line_board
from research_context.teacher import advance
from gaia_rl._native import Environment


def action(kind):
    return {'type': 'FreeAction', 'kind': kind, 'count': 1}


def node(actions, values, ore=4, knowledge=4, credits=3, qic=1, power=(2, 4, 0), rnd=3):
    p = {'player_id': 0, 'faction': 'HadschHallas', 'resources': {
        'ore': ore, 'credits': credits, 'knowledge': knowledge, 'qic': qic,
        'power': dict(zip(('bowl1', 'bowl2', 'bowl3'), power))}}
    return {'player': 0, 'decision_id': 0, 'candidates': [{'action': a} for a in actions],
            'values': values, 'state': {'phase': {'ActionPhase': {'active_player': 0}}, 'round': rnd, 'players': [p]}}


class FakeEnv:
    def __init__(self, snapshot, branches=None):
        self.snapshot = snapshot
        self.branches = branches or {}
    def fork(self, decision, index):
        assert decision == self.snapshot['decision_id']
        return self.branches[index]
    def snapshot_json(self):
        return json.dumps(self.snapshot)


class SimpleTeacher(PurposeTeacher):
    def base_rank(self, snapshot):
        return [(v, 'base') for v in snapshot['values']]


class PurposeTests(unittest.TestCase):
    def test_unproductive_burn_is_below_pass(self):
        burn, skip = action('BurnPower'), {'type': 'Pass'}
        before = node([burn, skip], [58, 2])
        after = node([skip], [2], power=(2, 2, 1))
        t = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        self.assertLess(t.rank(before)[0][0], 2)

    def test_burn_enabling_power_action_is_preferred_to_pass(self):
        burn, skip, spend = action('BurnPower'), {'type': 'Pass'}, {'type': 'PowerAction', 'id': 3}
        before = node([burn, skip], [58, 2], power=(2, 3, 2))
        after = node([spend, skip], [60, 2], power=(2, 1, 3))
        t = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        result = t.rank(before)
        self.assertGreater(result[0][0], result[1][0])
        self.assertIn('PowerAction', result[0][1])

    def test_already_available_action_does_not_justify_conversion(self):
        free, build, skip = action('KnowledgeToCredit'), {'type': 'Build', 'coord': '1,0'}, {'type': 'Pass'}
        before = node([free, build, skip], [58, 50, 2])
        after = node([build, skip], [60, 2], knowledge=3, credits=4)
        t = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        self.assertLess(t.rank(before)[0][0], 2)

    def test_liquidation_allowed_only_with_verified_use_and_accounts_for_lost_research(self):
        free, build, skip = action('OreToCredit'), {'type': 'Build', 'coord': '1,0'}, {'type': 'Pass'}
        before = node([free, skip], [58, 2], credits=1)
        after = node([build, skip], [50, 2], ore=3, credits=2)
        t = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        self.assertGreater(t.rank(before)[0][0], 2)
        p = before['state']['players'][0]
        q = copy.deepcopy(p);q['resources'].update(knowledge=3, credits=2)
        loss = conversion_loss(p, q, [action('KnowledgeToCredit')], 3)
        self.assertGreater(loss, conversion_loss(p, q, [action('KnowledgeToCredit')], 6))

    def test_qic_credit_chain_is_charged_for_net_qic_loss(self):
        first, second, skip = action('QicToOre'), action('OreToCredit'), {'type': 'Pass'}
        build = {'type': 'Build', 'coord': '1,0'}
        before = node([first, skip], [-10, 2], credits=1)
        middle = node([second, skip], [-10, 2], ore=5, credits=1, qic=0)
        after = node([build, skip], [50, 2], credits=2, qic=0)
        env = FakeEnv(before, {0: FakeEnv(middle, {0: FakeEnv(after)})})
        t = SimpleTeacher().bind(env)
        result = t.rank(before)
        self.assertGreater(result[0][0], 2)
        self.assertEqual(before['state']['players'][0]['resources']['qic'], 1)
        self.assertEqual(t.preview_count, 2)

    def test_better_funded_action_beats_conversion_route(self):
        free, mine, skip = action('OreToCredit'), {'type': 'Build', 'coord': '1,0'}, {'type': 'Pass'}
        before = node([free, mine, skip], [58, 65, 2])
        after = node([{'type': 'Upgrade', 'coord': '2,0'}], [50], ore=3, credits=4)
        t = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        scores = t.rank(before)
        self.assertGreater(scores[1][0], scores[0][0])

    def test_xenos_power_recovery_exception_is_preserved(self):
        s = node([action('OreToPowerBowl3'), {'type': 'Pass'}], [58, 2])
        s['state']['players'][0]['faction'] = 'Xenos'
        t = SimpleTeacher().bind(FakeEnv(s))
        self.assertEqual(t.rank(s)[0][0], 58)
        self.assertEqual(t.preview_count, 0)

    def test_pass_penalty_requires_productive_action_not_stock(self):
        t = SimpleTeacher(2)
        s = node([{'type': 'Pass'}], [2], knowledge=15, ore=15, credits=30)
        self.assertEqual(t.rank(s)[0][0], 2)
        s = node([{'type': 'Pass'}, {'type': 'ResearchAdvance', 'track': 'Economy'}], [2, 45])
        self.assertLess(t.rank(s)[0][0], 2)

    def test_no_imaginary_opponent_followup(self):
        s = node([action('OreToCredit'), {'type': 'Pass'}], [58, 2])
        after = node([{'type': 'Build'}], [99]);after['player'] = 1
        t = SimpleTeacher().bind(FakeEnv(s, {0: FakeEnv(after)}))
        self.assertEqual(t.rank(s)[0][0], -12)


class CostAndOrderTests(unittest.TestCase):
    def setUp(self):
        self.s, self.p = fixture();self.state = self.s['state'];line_board(self.state)
        self.s['player'] = self.p['player_id']
        self.p['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
        self.p['resources'].update(ore=8, credits=10, knowledge=8, qic=0)
        self.p['research_tracks'] = {k: 0 for k in self.p['research_tracks']}
        self.p['tech_tiles'] = [];self.p['covered_tech_tiles'] = []
        self.state['round'] = 2

    def test_corrected_natural_gaia_requires_entry_plus_range(self):
        self.state['board']['hexes']['3,0']['planet']['planet_type'] = 'Gaia'
        cost = construction_cost(self.state, self.p, {'type': 'Build', 'coord': '3,0'})
        self.assertEqual(cost.qic, 2)

    def test_gaia_forecast_does_not_pretend_entry_is_free(self):
        for q in (1, 3, 4):self.state['board']['hexes'][f'{q},0']['planet']['owner'] = 2
        self.state['board']['hexes']['2,0']['planet']['planet_type'] = 'Gaia'
        self.p['research_tracks']['navigation'] = 1
        self.assertEqual(expansion_gain(self.state, self.p, advance(self.p, 'Navigation')), 0)
        self.p['resources']['qic'] = 1
        self.assertGreater(expansion_gain(self.state, self.p, advance(self.p, 'Navigation')), 0)

    def test_research_bonus_requires_reduced_fundable_cost(self):
        self.p['research_tracks']['terraforming'] = 1
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Swamp'
        self.s['candidates'] = [{'action': {'type': 'ResearchAdvance', 'track': 'Terraforming'}}]
        scores = [(40, 'base')]
        PurposeTeacher(3).adjust_research_order(self.s, scores)
        self.assertGreater(scores[0][0], 40)
        self.p['resources']['credits'] = 0
        scores = [(40, 'base')]
        PurposeTeacher(3).adjust_research_order(self.s, scores)
        self.assertEqual(scores[0][0], 40)

    def test_ship_followup_checks_actual_shared_slot_ids(self):
        self.p['resources']['qic'] = 3
        self.state['research_board']['tech_tiles'] = [4]
        self.state['used_spaceship_actions'] = []
        self.assertGreater(ship_followup(self.state, self.p, 'Rebellion')[0], 0)
        self.state['used_spaceship_actions'] = [12]
        self.assertEqual(ship_followup(self.state, self.p, 'Rebellion')[0], 0)
        self.state['used_spaceship_actions'] = []
        self.p['resources']['qic'] = 2
        self.assertEqual(ship_followup(self.state, self.p, 'Rebellion')[0], 0)

    def test_eclipse_followup_does_not_require_a_former(self):
        self.state['spaceship_boards'].append({'id': 'Eclipse', 'tech_tiles': []}) if not any(b['id']=='Eclipse' for b in self.state['spaceship_boards']) else None
        self.state['board']['hexes']['1,0']['planet']['planet_type'] = 'Asteroid'
        self.state['used_spaceship_actions'] = []
        self.p['gaiaformers_total'] = 0
        self.assertGreater(ship_followup(self.state, self.p, 'Eclipse')[0], 0)
        self.state['used_spaceship_actions'] = [9]
        self.assertEqual(ship_followup(self.state, self.p, 'Eclipse')[0], 0)

    def test_native_fork_keeps_snapshot_unchanged(self):
        env = Environment('research-context-20260911-fresh-10', 2000)
        before = env.snapshot_json();s = json.loads(before)
        a = env.fork(s['decision_id'], 0)
        self.assertEqual(before, env.snapshot_json())
        self.assertNotEqual(json.loads(a.snapshot_json())['decision_id'], s['decision_id'])


if __name__ == '__main__':unittest.main()
