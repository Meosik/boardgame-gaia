import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from gaia_rl._native import Environment
from gaia_rl.encoding import FeatureEncoder
from conditional_plans.test_economy_first_native import replay_root
from conditional_plans.economy_first import EconomyFirstTeacher
from current_actions.conservation import blocked
from four_factions import FACTIONS
from four_factions.teacher import NativeFactionTeacher, QuartetTeacher, brainstone_committed, critical_proofs
from current_actions.conservation import identity
from four_factions.value import (HOME, production, materials, power_value, gaia_value,
                                 potential, ROOT)
from four_factions.setup import validate


def initial():
    env = Environment('quartet-pilot-20260913-424', 2000)
    return env, json.loads(env.snapshot_json())


class ValuesTests(unittest.TestCase):
    def test_native_income_oracle_cases(self):
        cases = json.loads((ROOT/'gaia-frontend/src/tests/fixtures/incomeProjection.json').read_text())
        self.assertTrue(cases)
        for case in cases:
            if case['player']['faction'] not in FACTIONS:
                continue
            state = {'research_board': {'economy_research_tile_side': case['side']}}
            self.assertEqual(production(state, case['player']), case['income'])

    def test_concave_resource_potential_is_monotone_at_thresholds(self):
        r = dict(ore=0, credits=0, knowledge=0, qic=0)
        for key in r:
            values = [materials({**r, key: n}) for n in range(35)]
            self.assertTrue(all(b > a for a, b in zip(values, values[1:])))
            slopes = [b-a for a, b in zip(values, values[1:])]
            self.assertTrue(all(b <= a+1e-10 for a, b in zip(slopes, slopes[1:])))

    def test_brainstone_position_is_distinct_and_not_three_tokens(self):
        _, s = initial()
        p = s['state']['players'][2]['resources']['power']
        self.assertEqual(s['state']['players'][2]['faction'], 'Taklons')
        values = [power_value({**p, 'brainstone': location}) for location in ('Area1', 'Area2', 'Area3')]
        self.assertLess(values[0], values[1])
        self.assertLess(values[1], values[2])
        after = copy.deepcopy(s)
        after['state']['players'][2]['resources']['power']['brainstone'] = 'Gaia'
        self.assertTrue(brainstone_committed(s, after, 2))

    def test_terrans_gaia_has_no_reachable_colony_value_without_targets(self):
        _, s = initial()
        state = s['state']
        player = state['players'][3]
        self.assertEqual(player['faction'], 'Terrans')
        for cell in state['board']['hexes'].values():
            if cell['planet'] and cell['planet']['planet_type'] == 'Transdim':
                cell['planet']['owner'] = 0
        self.assertEqual(gaia_value(state, player), 0)
        self.assertTrue(np.isfinite(potential(state, 3)))

    def test_terminal_potential_is_native_vp_not_shaping(self):
        _, s = initial()
        s['state']['phase'] = {'Ended': {'final_scores': [[i, 100+i] for i in range(4)]}}
        for actor in range(4):
            self.assertEqual(potential(s['state'], actor), 100+actor)

    def test_round_six_has_no_invented_qic_terminal_points(self):
        _, s = initial()
        s['state']['round'] = 6
        before = potential(s['state'], 3)
        s['state']['players'][3]['resources']['qic'] += 10
        self.assertEqual(potential(s['state'], 3), before)

    def test_income_booster_can_be_excluded_from_permanent_forecast(self):
        _, s = initial()
        player = s['state']['players'][3]
        player['booster'] = 11
        gross = production(s['state'], player)
        permanent = production(s['state'], player, include_booster=False)
        self.assertEqual(gross[1]-permanent[1], 4)

    def test_historical_cost_map_is_not_widened(self):
        from economy.teacher import HOME as legacy
        self.assertEqual(set(legacy), {'Xenos', 'HadschHallas'})
        self.assertEqual(set(HOME), {'Terrans', 'Taklons'})


class NativeTeacherTests(unittest.TestCase):
    def test_new_faction_native_ranks_are_deterministic_and_immutable(self):
        env, s = initial()
        for _ in range(9):
            if s['state']['players'][s['player']]['faction'] in HOME:
                policy = NativeFactionTeacher().bind(env)
                before = env.snapshot_json()
                ranks = policy.rank(s)
                self.assertEqual(ranks, policy.rank(s))
                self.assertEqual(before, env.snapshot_json())
                self.assertEqual(len(ranks), len(s['candidates']))
                chosen = max(range(len(ranks)), key=lambda i: (ranks[i][0], -i))
                self.assertFalse(blocked(ranks[chosen]))
                FeatureEncoder().encode(s, s['player'])
                env.step(s['decision_id'], chosen)
            else:
                env.step(s['decision_id'], 0)
            s = json.loads(env.snapshot_json())

    def test_stale_snapshot_and_unbound_policy_fail(self):
        env, s = initial()
        while s['state']['players'][s['player']]['faction'] not in HOME:
            env.step(s['decision_id'], 0)
            s = json.loads(env.snapshot_json())
        with self.assertRaises(ValueError):
            NativeFactionTeacher().rank(s)
        policy = NativeFactionTeacher().bind(env)
        env.step(s['decision_id'], 0)
        with self.assertRaises(ValueError):
            policy.rank(s)

    def test_dispatch_retains_hadsch_reference_ranks(self):
        env, s = replay_root(46)
        expected = EconomyFirstTeacher().bind(env).rank(s)
        actual = QuartetTeacher().bind(env).rank(s)
        self.assertEqual(actual, expected)

    def test_rebinding_game_clears_mutable_seat_policies(self):
        env, _ = initial()
        teacher = QuartetTeacher().bind(env)
        teacher.policies[0] = object()
        teacher.bind(env)
        self.assertIn(0, teacher.policies)
        teacher.bind(Environment('new-game'))
        self.assertFalse(teacher.policies)


class ConstraintTests(unittest.TestCase):
    def test_qic_ore_power_chain_retains_its_federation_commitment(self):
        _, snapshot = initial()
        snapshot['player'] = 2
        snapshot['candidates'] = [
            {'action': {'type': 'FreeAction', 'kind': 'OreToPowerBowl3', 'count': 1}},
            {'action': {'type': 'Pass', 'booster_id': 1}}]
        after = copy.deepcopy(snapshot)
        after['decision_id'] += 1
        federation = {'type': 'FormFederation', 'hexes': [], 'satellite_hexes': [],
                      'token': {'source': 'Supply', 'kind': 1}}
        after['candidates'] = [{'action': federation}]
        class FakeEnv:
            def __init__(self, value):
                self.value = value
            def snapshot_json(self):
                return json.dumps(self.value)
            def fork(self, decision, index):
                self_index = 0
                if index != self_index:
                    raise AssertionError('Commitment bypass')
                return FakeEnv(after)
        policy = NativeFactionTeacher().bind(FakeEnv(snapshot))
        policy.commitments = {identity(snapshot): {identity(snapshot['candidates'][0]['action'])},
                              identity(after): {identity(federation)}}
        with patch('four_factions.teacher.potential', return_value=0):
            ranks = policy.rank(snapshot)
        self.assertFalse(blocked(ranks[0]))
        self.assertTrue(blocked(ranks[1]))
        self.assertEqual(policy.commitments[identity(after)], {identity(federation)})

    def test_qic_proof_is_exact_missing_ore_and_only_critical_building(self):
        _, snapshot = initial()
        snapshot['player'] = 3
        snapshot['state']['players'][3]['resources'].update(ore=3, qic=2)
        snapshot['candidates'] = [{'action': {'type': 'FreeAction', 'kind': 'QicToOre', 'count': 1}}]
        after = copy.deepcopy(snapshot)
        after['state']['players'][3]['resources'].update(ore=4, qic=1)
        pi = {'type': 'Upgrade', 'to': 'PlanetaryInstitute', 'coord': '0,0'}
        station = {'type': 'Upgrade', 'to': 'TradingStation', 'coord': '0,0'}
        after['candidates'] = [{'action': pi}, {'action': station}]
        proofs = critical_proofs(None, snapshot, 0, None, after)
        self.assertEqual(proofs, {identity(after): {identity(pi)}})
        snapshot['candidates'][0]['action']['count'] = 2
        after['state']['players'][3]['resources'].update(ore=5, qic=0)
        self.assertFalse(critical_proofs(None, snapshot, 0, None, after))

    def test_forbidden_conversion_is_not_even_previewed(self):
        _, snapshot = initial()
        snapshot['player'] = 2
        snapshot['candidates'] = [
            {'action': {'type': 'FreeAction', 'kind': 'OreToCredit', 'count': 2}},
            {'action': {'type': 'FreeAction', 'kind': 'KnowledgeToCredit', 'count': 1}},
            {'action': {'type': 'Pass', 'booster_id': 1}},
        ]
        class FakeEnv:
            def snapshot_json(self):
                return json.dumps(snapshot)
            def fork(self, decision, index):
                if index != 2:
                    raise AssertionError('A forbidden action was previewed')
                return self
        with patch('four_factions.teacher.potential', return_value=0):
            ranks = NativeFactionTeacher().bind(FakeEnv()).rank(snapshot)
        self.assertTrue(blocked(ranks[0]))
        self.assertTrue(blocked(ranks[1]))
        self.assertFalse(blocked(ranks[2]))


class SplitTests(unittest.TestCase):
    def pools(self):
        return {'training': [{'seed': f'train{i}', 'factions': list(FACTIONS)} for i in range(6)],
                'validation': [{'seed': f'valid{i}', 'factions': list(FACTIONS)} for i in range(2)],
                'evaluation': [{'seed': f'eval{i}', 'factions': list(FACTIONS[i:]+FACTIONS[:i])} for i in range(4)]}

    def test_reject_overlaps_bad_roster_and_seat_imbalance(self):
        pools = self.pools()
        lineups = {s['seed']: s['factions'] for rows in pools.values() for s in rows}
        with patch('four_factions.setup.lineup', side_effect=lineups.__getitem__):
            validate(pools)
            bad = copy.deepcopy(pools)
            bad['validation'][0] = bad['training'][0]
            with self.assertRaises(ValueError):
                validate(bad)
            bad = copy.deepcopy(pools)
            bad['evaluation'][0]['factions'] = list(reversed(FACTIONS))
            with self.assertRaises(ValueError):
                validate(bad)


if __name__ == '__main__':
    unittest.main()
