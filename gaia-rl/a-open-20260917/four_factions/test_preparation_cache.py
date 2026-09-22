import json
import time
import unittest
from unittest.mock import patch

from current_actions.conservation import blocked, identity
from four_factions.preparation import Goal, Policies, rollout, search, select_goal
from four_factions.preparation_cache import PolicyCache
from four_factions.test_preparation import root


class PolicyCacheTests(unittest.TestCase):
    def test_cache_does_not_survive_into_another_real_search(self):
        env, snapshot = root()
        for _ in range(2):
            with patch('four_factions.preparation.rollout', return_value={
                    'complete': False, 'value': None, 'actions': []}):
                result = search(env, snapshot, {}, lambda value: None,
                                soft_deadline=time.monotonic()+10, hard_deadline=time.monotonic()+20)
            self.assertEqual(result['policy_cache']['hits'], 0)
            self.assertEqual(result['policy_cache']['misses'], 1)

    def test_values_are_detached_and_limits_do_not_change_results(self):
        cache = PolicyCache(max_entries=1, max_bytes=10000)
        scores, memory = [(2.0, 'allowed')], {'next': ['critical']}
        cache.put('one', scores, memory)
        scores[0] = (-1, 'mutated')
        memory['next'].clear()
        got, saved = cache.get('one')
        self.assertEqual(got, [(2.0, 'allowed')])
        self.assertEqual(saved, {'next': ['critical']})
        got.clear(); saved['next'].clear()
        self.assertEqual(cache.get('one'), ([(2.0, 'allowed')], {'next': ['critical']}))
        cache.put('two', [(3.0, 'other')], {})
        self.assertIsNone(cache.get('two'))
        self.assertEqual(cache.stats()['entries'], 1)
        tiny = PolicyCache(max_bytes=1)
        tiny.put('one', [(2.0, 'allowed')], {})
        self.assertIsNone(tiny.get('one'))
        self.assertEqual(tiny.stats()['bytes_used'], 0)
        disabled = PolicyCache(max_entries=0)
        disabled.put('one', [(2.0, 'allowed')], {})
        self.assertIsNone(disabled.get('one'))

    def test_exact_native_ranks_and_verified_commitments_do_not_mix(self):
        env, snapshot = root()
        original = env.snapshot_json()
        cache = PolicyCache()
        expected = Policies().rank(env, snapshot)
        first = Policies(cache=cache)
        self.assertEqual(first.rank(env, snapshot), expected)
        repeated = Policies(cache=cache)
        self.assertEqual(repeated.rank(env, snapshot), expected)
        self.assertEqual(first.memory, repeated.memory)
        self.assertEqual(cache.stats()['hits'], 1)
        index = next(i for i, c in enumerate(snapshot['candidates'])
                     if c['action']['type'] == 'Upgrade' and not blocked(expected[i]))
        actor = str(snapshot['player'])
        required = {identity(snapshot): [identity(snapshot['candidates'][index]['action'])]}
        guarded = Policies({actor: required}, cache=cache)
        ranks = guarded.rank(env, snapshot)
        self.assertEqual([i for i, score in enumerate(ranks) if not blocked(score)], [index])
        second = Policies({actor: required}, cache=cache)
        self.assertEqual(second.rank(env, snapshot), ranks)
        self.assertEqual(second.memory, guarded.memory)
        self.assertEqual(cache.stats()['hits'], 2)
        self.assertEqual(original, env.snapshot_json())
        stale = json.loads(original)
        stale['steps'] += 1
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            repeated.rank(env, stale)

    def test_native_repeated_path_is_identical_with_cache_and_parent_unchanged(self):
        env, snapshot = root()
        original = env.snapshot_json()
        cache = PolicyCache()
        cached = Policies(cache=cache)
        uncached = Policies()
        expected_scores = uncached.rank(env, snapshot)
        self.assertEqual(cached.rank(env, snapshot), expected_scores)
        goal = Goal('Science@-3,-4', 'upgrade', '-3,-4', 'Science')
        deadline = time.monotonic()+180
        index = select_goal(env, snapshot, expected_scores, goal, uncached, deadline)
        expected = rollout(env, snapshot, index, goal, uncached, deadline)
        actual = rollout(env, snapshot, index, goal, cached, deadline)
        hits = cache.stats()['hits']
        repeated = rollout(env, snapshot, index, goal, cached, deadline)
        self.assertEqual(actual, expected)
        self.assertEqual(repeated, expected)
        self.assertGreater(cache.stats()['hits'], hits)
        self.assertLessEqual(cache.stats()['bytes_used'], cache.max_bytes)
        self.assertTrue(actual['goal_acquired'])
        self.assertEqual(original, env.snapshot_json())


if __name__ == '__main__':
    unittest.main()
