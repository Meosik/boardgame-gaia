import copy
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from scoring_cache import decision_scope, memoized, ranking_scope, shared_rank, uncached
from current_actions.teacher import CurrentContextTeacher
from economy.teacher import construction_cost, origins, path_distance
from economy.test_teacher import fixture, line_board


class CacheTests(unittest.TestCase):
    def test_scope_reuses_results_but_returns_independent_values(self):
        calls = []

        @memoized('test', lambda value: value)
        def compute(state, value):
            calls.append(value)
            return [value]

        state = {}
        compute(state, 1)
        compute(state, 1)
        with decision_scope(state) as cache:
            compute(state, 1).append('not cached')
            self.assertEqual(compute(state, 1), [1])
            self.assertEqual(cache.hits, 1)
        self.assertFalse(cache.entries)
        self.assertEqual(calls, [1, 1, 1])

    def test_nested_states_exceptions_and_uncached_mode_are_isolated(self):
        calls = []

        @memoized('test', lambda: ())
        def compute(state):
            calls.append(state['value'])
            return state['value']

        first, second = {'value': 1}, {'value': 2}
        with decision_scope(first):
            self.assertEqual(compute(first), 1)
            with self.assertRaisesRegex(ValueError, 'probe'):
                with decision_scope(second):
                    self.assertEqual(compute(second), 2)
                    raise ValueError('probe')
            self.assertEqual(compute(first), 1)
            self.assertEqual(compute(second), 2)
            with uncached():
                self.assertEqual(compute(first), 1)
        self.assertEqual(calls, [1, 2, 2, 1])

    def test_decision_cache_is_bounded_and_does_not_cache_exceptions(self):
        calls = []

        @memoized('test', lambda value: value)
        def compute(state, value):
            calls.append(value)
            if value < 0:
                raise ValueError('negative')
            return value

        state = {}
        with decision_scope(state, max_entries=2) as cache:
            for value in (0, 1, 2, 2):
                self.assertEqual(compute(state, value), value)
            self.assertEqual(len(cache.entries), 2)
            for _ in range(2):
                with self.assertRaises(ValueError):
                    compute(state, -1)
        self.assertEqual(calls, [0, 1, 2, 2, -1, -1])

    def test_shared_scores_key_full_snapshot_and_copy_returned_list(self):
        snapshot = {'state': {'round': 1}, 'player': 0,
                    'candidates': [{'action': {'type': 'Pass'}}]}
        calls = []

        def rank():
            calls.append(1)
            return [(1.25, 'same reason')]

        with ranking_scope() as cache:
            shared_rank(snapshot, rank)[0] = (999, 'changed by caller')
            self.assertEqual(shared_rank(copy.deepcopy(snapshot), rank), [(1.25, 'same reason')])
            for field, value in (('player', 1), ('state', {'round': 2}),
                                 ('candidates', [{'action': {'type': 'Build'}}])):
                shared_rank({**snapshot, field: value}, rank)
            self.assertEqual(cache.hits, 1)
            with uncached():
                shared_rank(snapshot, rank)
        self.assertEqual(len(calls), 5)
        self.assertFalse(cache.entries)
        with ranking_scope():
            shared_rank(snapshot, rank)
        self.assertEqual(len(calls), 6)

    def test_shared_cache_has_entry_and_byte_limits(self):
        with ranking_scope(max_entries=2, max_bytes=4096) as cache:
            for i in range(4):
                self.assertEqual(shared_rank({'i': i}, lambda: [(i, 'score')]), [(i, 'score')])
            self.assertLessEqual(len(cache.entries), 2)
            self.assertLessEqual(cache.bytes_used, 4096)
        with ranking_scope(max_bytes=1) as cache:
            shared_rank({'i': 1}, lambda: [(1, 'score')])
            self.assertFalse(cache.entries)


class GeometryCacheTests(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.player = fixture()
        self.state = self.snapshot['state']
        line_board(self.state)

    def test_geometry_hits_and_no_stale_board_after_scope(self):
        with decision_scope(self.state) as cache:
            self.assertEqual(origins(self.state, self.player), ['0,0'])
            origins(self.state, self.player).append('6,0')
            self.assertEqual(origins(self.state, self.player), ['0,0'])
            self.assertEqual(path_distance(self.state, ['0,0'], '4,0'), 4)
            self.assertEqual(path_distance(self.state, iter(['0,0']), '4,0'), 4)
            self.assertGreaterEqual(cache.hits, 2)
        self.state['board']['hexes']['0,0']['structures'] = []
        self.state['board']['hexes']['4,0']['structures'] = [{'owner': 1, 'kind': 'Mine'}]
        with decision_scope(self.state):
            self.assertEqual(origins(self.state, self.player), ['4,0'])

    def test_cost_cache_tracks_prospective_navigation_terraforming_and_tiles(self):
        self.state['board']['hexes']['4,0']['planet']['planet_type'] = 'Oxide'
        action = {'type': 'Build', 'coord': '4,0'}
        players = [copy.deepcopy(self.player) for _ in range(5)]
        players[1]['research_tracks']['navigation'] = 4
        players[2]['research_tracks']['terraforming'] = 3
        players[3]['tech_tiles'] = [12]
        players[4]['tech_tiles'], players[4]['covered_tech_tiles'] = [12], [12]
        expected = [construction_cost(self.state, player, action) for player in players]
        with decision_scope(self.state) as cache:
            for player, cost in zip(players, expected):
                self.assertEqual(construction_cost(self.state, player, action), cost)
                actual = construction_cost(self.state, player, action)
                with self.assertRaises(FrozenInstanceError):
                    actual.ore = 999
                self.assertEqual(construction_cost(self.state, player, action), cost)
            self.assertGreater(cache.hits, 0)

    def test_research_key_includes_prospective_player_and_candidate(self):
        teacher = CurrentContextTeacher()

        def score(instance, state, player, track):
            return player['resources']['ore'] + (10 if instance._candidate.get('type') == 'Upgrade' else 0)

        with patch('action_purpose.costs.CorrectedContextTeacher.research', score):
            with decision_scope(self.state) as cache:
                teacher._candidate = {'type': 'ResearchAdvance'}
                first = teacher.research(self.state, self.player, 'Navigation')
                self.assertEqual(teacher.research(self.state, self.player, 'Navigation'), first)
                teacher._candidate = {'type': 'Upgrade'}
                self.assertEqual(teacher.research(self.state, self.player, 'Navigation'), first+10)
                player = copy.deepcopy(self.player)
                player['resources']['ore'] += 1
                self.assertEqual(teacher.research(self.state, player, 'Navigation'), first+11)
                self.assertEqual(cache.hits, 1)


if __name__ == '__main__':
    unittest.main()
