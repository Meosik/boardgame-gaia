"""A02 scheduling contracts; synthetic utility values are not game-strength evidence."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import a02_round_investment as a02
import build_a02_source as builder


class GraphEnv:
    def __init__(self, graph, key):
        self.graph, self.key = graph, key

    def snapshot_json(self):
        return json.dumps(self.graph[self.key]['snapshot'])

    def fork(self, decision, index):
        if decision != self.graph[self.key]['snapshot']['decision_id']:
            raise AssertionError('stale synthetic decision')
        return GraphEnv(self.graph, self.graph[self.key]['next'][index])


class Policies:
    def __init__(self, memory=None):
        self.memory = deepcopy(memory or {'root': 'preserve'})

    def clone(self):
        return Policies(self.memory)

    def rank(self, env, snapshot):
        self.memory['hypothetical'] = snapshot['decision_id']
        return env.graph[env.key]['scores']


def graph(values, *, investment='Build', blocked=False):
    nodes = {}
    for n, value in enumerate(values):
        player = dict(faction='Terrans', resources={'ore': 10-n, 'credits': 30-n},
                      structures=[{'kind': 'Mine'}] * (2+n), research_tracks={})
        state = dict(round=1, phase={'ActionPhase': {'active_player': 0}},
                     players=[player], value=0)
        actions = [dict(type='Pass', booster_id=10)]
        following = [f'end-{n}']
        scores = [(10.0, 'local pass')]
        if n+1 < len(values):
            actions.append(dict(type=investment, coord=str(n)))
            following.append(f'opponent-{n+1}')
            scores.append((1.0, 'conservation blocked: test' if blocked else 'investment'))
        nodes[f'own-{n}'] = dict(snapshot=dict(decision_id=n, player=0, state=state,
                                              candidates=[{'action': a} for a in actions]),
                                  next=following, scores=scores)
        end = deepcopy(state)
        end.update(round=2, value=value)
        nodes[f'end-{n}'] = dict(snapshot=dict(decision_id=100+n, player=0, state=end,
                                              candidates=[]), next=[], scores=[])
        opponent = deepcopy(state)
        opponent['phase'] = {'ChargePowerPending': {}}
        nodes[f'opponent-{n}'] = dict(snapshot=dict(decision_id=200+n, player=1, state=opponent,
                candidates=[{'action': {'type': 'ChargePower', 'accept': False}}]),
                next=[f'own-{n}'], scores=[(0, 'reaction')])
    return GraphEnv(nodes, 'own-0')


class RoundInvestmentTests(unittest.TestCase):
    def run_graph(self, values, **kwargs):
        env = graph(values, **kwargs)
        snapshot = json.loads(env.snapshot_json())
        publications = []
        deadline = time.monotonic() + 30
        with patch.object(a02.prep, 'leaf_value', side_effect=lambda s, *a: s['state']['value']), \
                patch.object(a02, '_outcome', return_value={'test': True}):
            result = a02.search_round(env, snapshot, Policies(), env.graph[env.key]['scores'],
                                     publications.append, soft_deadline=deadline, hard_deadline=deadline)
        self.assertEqual(json.loads(env.snapshot_json()), snapshot)
        return result, publications

    def test_four_investments_can_beat_pass_without_two_action_quota(self):
        result, publications = self.run_graph([10, 1, 2, 3, 20])
        self.assertEqual(result['index'], 1)
        self.assertEqual(result['maximum_investments_completed'], 4)
        self.assertEqual(len(result['plans']), 5)
        self.assertTrue(result['coverage_complete'])
        self.assertTrue(all(p['end_round'] == 2 for p in result['plans']))
        self.assertTrue(all(len(p['actions']) == 2*len(p['investments'])+1 for p in result['plans']))
        self.assertEqual(publications[0]['index'], 0)

    def test_surplus_credits_do_not_force_more_trading_station_investments(self):
        result, _ = self.run_graph([20, 19, 5, 1], investment='Upgrade')
        self.assertEqual(result['index'], 0)
        self.assertEqual(result['maximum_investments_completed'], 3)

    def test_equal_endpoint_keeps_pass(self):
        result, _ = self.run_graph([10, 10])
        self.assertEqual(result['index'], 0)

    def test_conservation_blocked_investment_is_not_executed(self):
        result, _ = self.run_graph([0, 1000], blocked=True)
        self.assertEqual(len(result['plans']), 1)
        self.assertEqual(result['index'], 0)

    def test_hypothetical_policy_memory_does_not_escape(self):
        result, _ = self.run_graph([0, 20])
        self.assertEqual(result['memory'], {'root': 'preserve'})

    def test_native_transition_cap_is_unknown_not_an_investment_penalty(self):
        with patch.object(a02, 'TRANSITION_LIMIT', 2):
            result, _ = self.run_graph([10, 20, 100])
        self.assertEqual(result['index'], 0)
        self.assertFalse(result['coverage_complete'])
        self.assertTrue(result['incomplete_paths'])
        self.assertTrue(all(p['value'] is None for p in result['incomplete_paths']))

    def test_timeout_before_control_keeps_local_choice(self):
        with patch.object(a02, '_complete', side_effect=a02.prep.SearchExpired()):
            result, _ = self.run_graph([0, 100])
        self.assertEqual(result['index'], 0)
        self.assertEqual(result['plans'], [])
        self.assertFalse(result['coverage_complete'])

    def test_timeout_after_control_does_not_select_unfinished_investment(self):
        original = a02._complete
        calls = 0
        def complete(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise a02.prep.SearchExpired()
            return original(*args, **kwargs)
        with patch.object(a02, '_complete', side_effect=complete):
            result, _ = self.run_graph([10, 100])
        self.assertEqual(result['index'], 0)
        self.assertEqual(len(result['plans']), 1)

    def test_nonfinite_endpoint_is_not_silently_published(self):
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            self.run_graph([float('nan')])

    def test_endpoint_requires_next_round_action_not_income_or_own_pass(self):
        snapshot = json.loads(graph([0]).snapshot_json())
        self.assertFalse(a02.endpoint(snapshot, 1))
        snapshot['state'].update(round=2, phase={'GaiaPhase': {}})
        self.assertFalse(a02.endpoint(snapshot, 1))
        snapshot['state']['phase'] = {'ActionPhase': {}}
        self.assertTrue(a02.endpoint(snapshot, 1))
        snapshot['state'].update(round=6, phase={'Ended': {}})
        self.assertTrue(a02.endpoint(snapshot, 6))

    def test_off_and_non_target_dispatch_exact_original_arguments(self):
        env = graph([0])
        snapshot = json.loads(env.snapshot_json())
        memory, publish = {}, lambda value: None
        for enabled, faction in [('0', 'Terrans'), ('1', 'Xenos')]:
            snapshot['state']['players'][0]['faction'] = faction
            calls = []
            def original(*args, **kwargs):
                calls.append((args, kwargs))
                return 'original'
            with patch.dict(os.environ, {a02.FLAG: enabled}):
                self.assertEqual(a02.dispatch(original, env, snapshot, memory, publish,
                                             soft_deadline=1, hard_deadline=2), 'original')
            self.assertEqual(calls, [((env, snapshot, memory, publish),
                                      dict(soft_deadline=1, hard_deadline=2))])

    def test_existing_bgg_selection_can_keep_remembered_opening(self):
        from bgg_openings.catalog import Buildings
        # The selector itself is the unchanged frozen implementation; exercise its
        # route using a small catalog adapter rather than a new opening preference.
        from types import SimpleNamespace
        opening = SimpleNamespace(label='remembered')
        with patch('bgg_openings.catalog.load_catalog', return_value={'Terrans': (opening,)}), \
                patch('bgg_openings.inventory.building_counts', return_value=Buildings(2, 0, 0, 0, 0)), \
                patch('bgg_openings.planning.select_forecast', side_effect=lambda rows, remembered, plans:
                      (plans[0], opening)):
            env = graph([10, 100])
            snapshot = json.loads(env.snapshot_json())
            deadline = time.monotonic()+30
            with patch.object(a02.prep, 'leaf_value', side_effect=lambda s, *a: s['state']['value']), \
                    patch.object(a02, '_outcome', return_value={}):
                result = a02.search_round(env, snapshot,
                    Policies({'_bgg_targets': {'0': 'remembered'}}), env.graph[env.key]['scores'],
                    lambda r: None, soft_deadline=deadline, hard_deadline=deadline, bgg_openings=True)
            self.assertEqual(result['index'], 0)
            self.assertEqual(result['bgg_opening']['status'], 'kept')

    def test_enabled_nonpass_delegates_without_leaking_preview_memory(self):
        env = graph([0, 10])
        env.graph['own-0']['scores'] = [(0, 'pass'), (10, 'build')]
        snapshot = json.loads(env.snapshot_json())
        memory = {'root': 'preserve'}
        deadline = time.monotonic() + 30
        with patch.dict(os.environ, {a02.FLAG: '1'}), \
                patch.object(a02.prep, 'Policies', side_effect=lambda m, **kw: Policies(m)), \
                patch.object(a02, 'search_round') as search:
            calls = []
            def original(env, snapshot, saved, publish, **kwargs):
                calls.append(deepcopy(saved))
                return 'original'
            result = a02.dispatch(original, env, snapshot, memory, lambda r: None,
                                  soft_deadline=deadline, hard_deadline=deadline)
        self.assertEqual(result, 'original')
        self.assertEqual(calls, [{'root': 'preserve'}])
        search.assert_not_called()

    def test_allocation_never_extends_hard_deadline(self):
        env = graph([0, 10])
        snapshot = json.loads(env.snapshot_json())
        publications = []
        with self.assertRaises(a02.prep.SearchExpired):
            a02.search_round(env, snapshot, Policies(), env.graph['own-0']['scores'],
                             publications.append, soft_deadline=time.monotonic()+30,
                             hard_deadline=time.monotonic()-1,
                             allocation=lambda: time.monotonic()+100)
        self.assertEqual(publications, [])


class BuilderTests(unittest.TestCase):
    def test_builder_relocates_and_hooks_only_disposable_source(self):
        runs = builder.ROOT / 'gaia-rl/runs'
        with tempfile.TemporaryDirectory(prefix='a02-test-', dir=runs) as directory:
            destination = Path(directory)/'nested/source'
            record = builder.build(destination)
            self.assertEqual(record['default_off_flag'], a02.FLAG)
            self.assertIn('search = partial(dispatch, original_search)',
                          (destination/'four_factions/timed.py').read_text())
            self.assertIn(str(builder.ROOT), (destination/'four_factions/value.py').read_text())
            self.assertEqual((destination/a02.__file__.split('/')[-1]).read_bytes(),
                             builder.MODULE.read_bytes())
            with self.assertRaises(FileExistsError):
                builder.build(destination)
        builder.verify_baseline()

    def test_builder_rejects_non_disposable_location(self):
        with self.assertRaises(ValueError):
            builder.build(builder.ROOT/'not-an-a02-run')


if __name__ == '__main__':
    unittest.main()
