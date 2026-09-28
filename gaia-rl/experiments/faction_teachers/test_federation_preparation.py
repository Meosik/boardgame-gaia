"""Saved native power-building regression; synthetic bound checks are labeled."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time
import unittest
from unittest.mock import Mock, patch

from gaia_rl import Environment
from current_actions.conservation import BLOCKED, PREFIX
from faction_teachers import federation_preparation as building
from faction_teachers.guidance import comparison_variants
from four_factions import preparation as prep
from four_factions.preparation_cache import PolicyCache


class NativeFederationPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((Path(__file__).parent/'fixtures/ambas-federation-preparation.json').read_text())['fixture']
        cls.env = Environment(fixture['seed'], 2000)
        for index in fixture['prefix']:
            s = json.loads(cls.env.snapshot_json())
            cls.env.step(s['decision_id'], index)
        cls.snapshot = json.loads(cls.env.snapshot_json())
        digest = hashlib.sha256(json.dumps(cls.snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert digest == fixture['snapshot_sha256']
        cls.recorded_goal = prep.goal_from_dict(fixture['goal'])
        # A separate structural plan on the SAME native board: the recorded
        # target is now proven forbidden. This test target is not a historical pilot route.
        cls.goal = replace(cls.recorded_goal, name='fixture: legal-site federation',
                           steps=(replace(cls.recorded_goal.steps[0], coord='5,0'),))
        cls.policies = prep.Policies(shared_factions=True, faction_tech_plans=True, cache=PolicyCache())
        cls.scores = cls.policies.rank(cls.env, cls.snapshot)
        cls.first = prep.select_goal(cls.env, cls.snapshot, cls.scores, cls.goal,
                                     cls.policies, time.monotonic()+30)
        cls.funded_env = cls.env.fork(cls.snapshot['decision_id'], cls.first)
        cls.funded = json.loads(cls.funded_env.snapshot_json())
        cls.funded_scores = cls.policies.rank(cls.funded_env, cls.funded)
        cls.second = prep.select_goal(cls.funded_env, cls.funded, cls.funded_scores, cls.goal,
                                      cls.policies, time.monotonic()+30)
        cls.built_state = json.loads(cls.funded_env.preview_state_json(cls.funded['decision_id'], cls.second))

    def tearDown(self):
        self.assertEqual(json.loads(self.env.snapshot_json()), self.snapshot)
        self.assertEqual(json.loads(self.funded_env.snapshot_json()), self.funded)

    def test_recorded_impossible_target_cancels_instead_of_spending_for_power(self):
        self.assertFalse(building.new_federation_site(self.snapshot['state']['players'][3], '3,-2'))
        self.assertFalse(prep.viable(self.snapshot, 3, self.recorded_goal))
        with patch.object(building, 'select_preparation', side_effect=AssertionError('Impossible target')):
            index = prep.select_goal(self.env, self.snapshot, self.scores, self.recorded_goal,
                                     self.policies, time.monotonic()+10)
        self.assertEqual(self.snapshot['candidates'][index]['action']['type'], 'Pass')
        after = json.loads(self.env.fork(self.snapshot['decision_id'], index).snapshot_json())
        remaining = prep.advance_goal(after, 3, self.recorded_goal,
            self.snapshot['candidates'][index]['action'], before=self.snapshot)
        self.assertEqual(remaining.payoff, 'cancelled')

    def test_same_native_root_legacy_and_off_still_pass(self):
        legacy = comparison_variants(self.goal)[0]
        for goal, enabled in ((legacy, True), (self.goal, False)):
            with self.subTest(enabled=enabled):
                pol = prep.Policies(shared_factions=True, faction_tech_plans=enabled)
                index = prep.select_goal(self.env, self.snapshot, self.scores, goal, pol, time.monotonic()+10)
                self.assertEqual(self.snapshot['candidates'][index]['action']['type'], 'Pass')

    def test_paid_funding_unlocks_real_construction_not_an_imaginary_resource(self):
        self.assertEqual(building.unfederated_power(self.snapshot['state']['players'][3]), 6)
        self.assertEqual(self.snapshot['candidates'][self.first]['action'],
                         {'type': 'PowerAction', 'id': 3, 'coord': None})
        before, after = [s['state']['players'][3]['resources'] for s in (self.snapshot, self.funded)]
        self.assertEqual(after['ore']-before['ore'], 2)
        self.assertEqual(before['power']['bowl3']-after['power']['bowl3'], 4)  # native power_action_cost(3)
        self.assertEqual(self.funded['player'], 3)  # All opponents actually passed; no skipped turn.
        self.assertIsNone(building.construction_index(self.env, self.snapshot, self.scores, self.goal, time.monotonic()+10))

    def test_paid_upgrade_increases_power_but_does_not_complete_federation(self):
        action = self.funded['candidates'][self.second]['action']
        self.assertEqual((action['type'], action['coord'], action['to']), ('Upgrade', '5,0', {'Academy': 'Qic'}))
        self.assertEqual(building.unfederated_power(self.built_state['players'][3]), 8)
        before, after = self.funded['state']['players'][3], self.built_state['players'][3]
        self.assertLess(after['resources']['ore'], before['resources']['ore'])
        self.assertLess(after['resources']['credits'], before['resources']['credits'])
        snapshot = {**self.funded, 'state': self.built_state}
        self.assertFalse(prep.achieved(snapshot, 3, self.goal))
        self.assertNotIn('3,-2', after['federated_hexes'])
        self.assertEqual(building.preparation_power(before), 2)
        self.assertEqual(building.preparation_power(after), 4)
        # The paid upgrade triggers an actual opponent charge reaction first.
        branch = self.funded_env.fork(self.funded['decision_id'], self.second)
        reaction = json.loads(branch.snapshot_json())
        accept = next(i for i, c in enumerate(reaction['candidates'])
                      if c['action'] == {'type': 'ChargePower', 'accept': True})
        branch.step(reaction['decision_id'], accept)
        own = json.loads(branch.snapshot_json())
        self.assertEqual(own['player'], 3)
        self.assertTrue(building.needs_power(own))  # The adjacent PI cannot join a new federation.

    def test_native_build_absorbed_by_old_federation_is_not_power_preparation(self):
        index = next(i for i, c in enumerate(self.snapshot['candidates']) if c['action']['type'] == 'Build')
        after = json.loads(self.env.preview_state_json(self.snapshot['decision_id'], index))
        self.assertEqual(building.unfederated_power(after['players'][3]), 6)
        self.assertIn(self.snapshot['candidates'][index]['action']['coord'], after['players'][3]['federated_hexes'])
        scores = [(BLOCKED, PREFIX)]*len(self.scores)
        scores[index] = (1000, 'synthetic preference for the actual native Build')
        self.assertIsNone(building.construction_index(self.env, self.snapshot, scores, self.goal, time.monotonic()+10))

    def test_conservation_is_not_bypassed_and_no_safe_route_is_not_forced(self):
        scores = [(BLOCKED, PREFIX)]*len(self.scores)
        self.assertIsNone(prep.select_goal(self.env, self.snapshot, scores, self.goal,
                                          self.policies, time.monotonic()+10, allow_fallback=False))
        self.assertEqual(scores, [(BLOCKED, PREFIX)]*len(self.scores))

    def test_completed_or_cancelled_plans_keep_existing_fallback(self):
        for goal in (replace(self.goal, steps=()), replace(self.goal, payoff='cancelled')):
            with patch.object(building, 'select_preparation', side_effect=AssertionError('Invalid preparation')):
                index = prep.select_goal(self.env, self.snapshot, self.scores, goal,
                                         self.policies, time.monotonic()+10)
                self.assertEqual(self.snapshot['candidates'][index]['action']['type'], 'Pass')

    def test_preparation_does_not_extend_deadline_or_shallow_horizon(self):
        with self.assertRaises(prep.SearchExpired):
            building.select_preparation(self.env, self.snapshot, self.scores, self.goal,
                                        self.policies, time.monotonic()-1)
        result = prep.rollout(self.env, self.snapshot, self.first, self.goal, self.policies,
                              time.monotonic()+10, decision_depth=1)
        self.assertEqual(result['decisions'], 1)
        self.assertFalse(result['goal_acquired'])
        self.assertEqual(result['end_round'], 5)
        self.assertEqual(building.unfederated_power(result['end_player']), 6)

    def test_preservation_excludes_federating_a_future_targets_neighbor(self):
        # Structural menu tests the cheap filter; no synthetic action is executed.
        snapshot = {**self.snapshot, 'candidates': [
            {'action': {'type': 'FormFederation', 'hexes': ['3,0'], 'satellite_hexes': ['4,0']}},
            {'action': {'type': 'Pass'}}]}
        with patch.object(prep, 'keeps_plan', return_value=True):
            self.assertEqual(prep.select_goal(self.env, snapshot, [(100, 'tempting'), (1, 'wait')],
                self.goal, self.policies, time.monotonic()+10), 1)

    def test_existing_legal_target_federation_precedes_power_preparation(self):
        # Structural controller fixture, not a claim that this action is legal at the native root.
        snapshot = {**self.snapshot, 'candidates': [{'action': {'type': 'FormFederation', 'hexes': ['5,0'], 'satellite_hexes': []}}]}
        with patch.object(prep, 'keeps_plan', return_value=True), \
                patch.object(building, 'select_preparation', side_effect=AssertionError('Unneeded construction')):
            self.assertEqual(prep.select_goal(self.env, snapshot, [(1, 'synthetic')], self.goal,
                                              self.policies, time.monotonic()+10), 0)


class PreparationBoundsTests(unittest.TestCase):
    def setUp(self):
        # Synthetic state for scheduling/guard tests only; no native resource edits.
        self.player = dict(faction='Ambas', tech_tiles=[6], covered_tech_tiles=[],
            structures=[dict(hex='0,0', kind='PlanetaryInstitute'), dict(hex='2,0', kind='ResearchLab')],
            federated_hexes=[])
        self.snapshot = dict(player=0, decision_id=1,
            state=dict(phase={'ActionPhase': {}}, players=[self.player]), candidates=[])
        self.goal = prep.Goal('pilot', 'ordered', target='Ambas',
            sources=('faction-tech-pilot', 'faction-tech-preserve'),
            steps=(prep.Goal('fed', 'federation-race', '0,0'),))

    def test_only_ambas_below_required_power_in_action_phase(self):
        self.assertTrue(building.needs_power(self.snapshot))
        self.player['faction'] = 'Terrans'
        self.assertFalse(building.needs_power(self.snapshot))
        self.player['faction'] = 'Ambas'
        self.player['structures'].append(dict(hex='1,0', kind='Mine'))
        self.assertFalse(building.needs_power(self.snapshot))
        self.player['structures'].pop()
        self.snapshot['state']['phase'] = {'IncomePhase': {}}
        self.assertFalse(building.needs_power(self.snapshot))

    def test_funding_bound_and_opponents_are_not_skipped(self):
        self.snapshot['candidates'] = [{'action': {'type': 'FreeAction'}}]*40
        env, policies = Mock(), Mock()
        after = {**self.snapshot, 'player': 1}
        env.fork.return_value.snapshot_json.return_value = json.dumps(after)
        result = building.select_preparation(env, self.snapshot, [(1, 'eligible')]*40,
                                              self.goal, policies, time.monotonic()+10)
        self.assertIsNone(result)
        self.assertEqual(env.fork.call_count, 32)
        policies.clone.assert_not_called()
        env.preview_state_json.assert_not_called()

    def test_more_power_cannot_erase_required_technology(self):
        self.snapshot['candidates'] = [{'action': {'type': 'Upgrade'}}]
        state = deepcopy(self.snapshot['state'])
        state['players'][0]['covered_tech_tiles'] = [6]
        state['players'][0]['structures'].extend([dict(hex=f'{n},1', kind='Mine') for n in range(3)])
        self.assertGreater(building.unfederated_power(state['players'][0]), 6)
        env = Mock()
        env.preview_state_json.return_value = json.dumps(state)
        self.assertIsNone(building.construction_index(env, self.snapshot, [(1, 'eligible')],
                                                      self.goal, time.monotonic()+10))


if __name__ == '__main__':
    unittest.main()
