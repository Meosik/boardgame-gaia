"""Rejected AI moves, stage 1 (research/strategy/ai-move-reject-design.md): the worker's `exclude` and `spares`."""
import json
import unittest

from gaia_rl import Environment

import ai_worker
from test_ai_worker import SEED, Worker


def first_decision(seed, wanted, limit=80):
    """Step the first candidate until `wanted(snapshot)`; no teacher is needed to reach the position."""
    env = Environment(seed, 2000)
    for _ in range(limit):
        snapshot = json.loads(env.snapshot_json())
        if wanted(snapshot):
            return snapshot
        env.step(snapshot['decision_id'], 0)
    raise AssertionError('position not reached')


def action_phase(snapshot):
    phase = snapshot['state']['phase']
    return isinstance(phase, dict) and 'ActionPhase' in phase and len(snapshot['candidates']) >= 5


class SpareOrderTests(unittest.TestCase):
    def setUp(self):
        from current_actions.conservation import BLOCKED, PREFIX
        self.scores = [(9.0, 'a'), (1.0, 'b'), (2.0, 'c'), (8.0, 'd'), (BLOCKED, PREFIX+'x'), (3.0, 'e')]
        self.plans = [{'first': 2, 'complete': True, 'value': 5.0},
                      {'first': 1, 'complete': True, 'value': 3.0},
                      {'first': 1, 'complete': True, 'value': 9.0},     # the best value of a first move counts
                      {'first': 3, 'complete': False, 'value': None},   # unfinished: not a search result
                      {'first': 0, 'complete': True, 'value': 99.0}]    # excluded below

    def test_answer_first_then_completed_comparisons_then_the_one_step_ranking(self):
        self.assertEqual(ai_worker.spare_order(2, self.scores, self.plans, {0}),
                         [(2, True), (1, True), (3, False), (5, False)])

    def test_an_answer_without_a_completed_comparison_is_not_searched(self):
        self.assertEqual(ai_worker.spare_order(3, self.scores, self.plans, {0}),
                         [(3, False), (1, True), (2, True), (5, False)])

    def test_no_answer_starts_from_the_best_completed_comparison(self):
        self.assertEqual(ai_worker.spare_order(None, self.scores, self.plans, {0}),
                         [(1, True), (2, True), (3, False), (5, False)])

    def test_without_exclusion_every_unblocked_candidate_is_listed_once(self):
        order = ai_worker.spare_order(0, self.scores, self.plans)
        self.assertEqual(order, [(0, True), (1, True), (2, True), (3, False), (5, False)])


class ExcludedIndicesTests(unittest.TestCase):
    CANDIDATES = [{'phase': 'Game', 'action': {'type': t}} for t in ('A', 'B', 'C')]

    def test_indices_of_the_rejected_moves(self):
        self.assertEqual(ai_worker.excluded_indices(self.CANDIDATES, []), set())
        self.assertEqual(ai_worker.excluded_indices(self.CANDIDATES, [self.CANDIDATES[2], self.CANDIDATES[0]]), {0, 2})

    def test_unknown_move_all_moves_and_a_wrong_type_are_errors(self):
        with self.assertRaises(ValueError):
            ai_worker.excluded_indices(self.CANDIDATES, [{'phase': 'Game', 'action': {'type': 'Z'}}])
        with self.assertRaises(ValueError):
            ai_worker.excluded_indices(self.CANDIDATES, list(self.CANDIDATES))
        with self.assertRaises(ValueError):
            ai_worker.excluded_indices(self.CANDIDATES, self.CANDIDATES[0])


class ExcludingTests(unittest.TestCase):
    """The mark is on the root ranking only and Policies.rank is put back, also after an error."""
    def setUp(self):
        import four_factions.preparation as preparation
        self.preparation = preparation
        self.kept = preparation.Policies.rank
        self.addCleanup(setattr, preparation.Policies, 'rank', self.kept)

    def test_marks_the_root_only_and_restores(self):
        from current_actions.conservation import blocked
        stub = lambda self, env, snapshot: [(3.0, 'a'), (2.0, 'b'), (1.0, 'c')]
        self.preparation.Policies.rank = stub
        root, later = {'decision_id': 7, 'steps': 4}, {'decision_id': 8, 'steps': 5}
        with self.assertRaises(KeyError):
            with ai_worker.excluding(root, {0}):
                rank = self.preparation.Policies.rank
                self.assertEqual([blocked(s) for s in rank(None, None, root)], [True, False, False])
                self.assertEqual([blocked(s) for s in rank(None, None, later)], [False, False, False])
                self.assertFalse(hasattr(rank, '__wrapped__'))
                raise KeyError('search failed')
        self.assertIs(self.preparation.Policies.rank, stub)

    def test_parallel_prefetch_ranking_is_marked_too(self):
        from current_actions.conservation import blocked
        below = lambda self, env, snapshot: [(3.0, 'a'), (2.0, 'b')]
        outer = lambda self, env, snapshot: below(self, env, snapshot)
        outer.__wrapped__, outer._parallel = below, True
        self.preparation.Policies.rank = outer
        root = {'decision_id': 7, 'steps': 4}
        with ai_worker.excluding(root, {1}):
            rank = self.preparation.Policies.rank
            self.assertTrue(rank._parallel)
            self.assertEqual([blocked(s) for s in rank.__wrapped__(None, None, root)], [False, True])
        self.assertIs(self.preparation.Policies.rank, outer)


class ExcludeWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = Worker()
        cls.snapshot = first_decision(SEED, action_phase)

    @classmethod
    def tearDownClass(cls):
        cls.worker.close()

    def ask(self, level, **extra):
        return self.worker.ask({'op': 'choose', 'room': f'exclude-{level}', 'level': level,
                                'state': self.snapshot['state'], 'player': self.snapshot['player'], **extra})

    def check_spares(self, reply, rejected, limit=3):
        candidates = self.snapshot['candidates']
        self.assertTrue(reply['ok'], reply)
        self.assertIn(reply['decision'], candidates)
        self.assertNotIn(reply['decision'], rejected)
        moves = [spare['decision'] for spare in reply['spares']]
        self.assertTrue(1 <= len(moves) <= limit, reply['spares'])
        self.assertEqual(moves[0], reply['decision'])
        for i, move in enumerate(moves):
            self.assertIn(move, candidates)
            self.assertNotIn(move, rejected)
            self.assertNotIn(move, moves[:i])
            self.assertIs(type(reply['spares'][i]['searched']), bool)

    def test_hard_level_answers_another_move_with_at_most_three_spares(self):
        first = self.ask('hard')
        self.assertTrue(first['ok'], first)
        self.assertNotIn('spares', first)             # a request without the keys is answered as before
        self.assertNotIn('exclude_fallback', first)
        second = self.ask('hard', exclude=[first['decision']], spares=3)
        self.check_spares(second, [first['decision']])
        self.assertNotIn('exclude_fallback', second)  # the search itself left the move out
        third = self.ask('hard', exclude=[first['decision'], second['decision']], spares=9)
        self.check_spares(third, [first['decision'], second['decision']])
        self.assertLess(max(reply['seconds'] for reply in (first, second, third)), 30)

    def test_easy_level_spares_are_the_one_step_ranking(self):
        first = self.ask('easy', spares=2)
        self.check_spares(first, [], limit=2)
        self.assertEqual(len(first['spares']), 2)
        second = self.ask('easy', exclude=[first['decision']], spares=3)
        self.check_spares(second, [first['decision']])
        self.assertEqual(second['decision'], first['spares'][1]['decision'])   # the next move of the same ranking
        self.assertEqual([spare['searched'] for spare in second['spares']], [False, False, False])

    def test_bad_exclusions_are_reported_not_played(self):
        self.assertFalse(self.ask('easy', exclude=[{'phase': 'Game', 'action': {'type': 'Nope'}}])['ok'])
        self.assertFalse(self.ask('easy', exclude=self.snapshot['candidates'])['ok'])
        self.assertFalse(self.ask('easy', spares=-1)['ok'])
        self.assertTrue(self.ask('easy')['ok'])       # the worker still answers afterwards


class BoosterTierExcludeTests(unittest.TestCase):
    """The new teacher answers the starting-booster pick outside the ranking: an excluded pick is replaced."""
    NEW = 'guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier'

    def test_excluded_tier_pick_is_replaced_and_reported(self):
        snapshot = first_decision('quartet-e-88365',
                                  lambda s: s['candidates'][0]['action'].get('type') == 'SelectStartingBooster')
        worker = Worker(self.NEW)
        try:
            request = {'op': 'choose', 'room': 'tier', 'level': 'hard', 'state': snapshot['state'],
                       'player': snapshot['player']}
            first = worker.ask(request)
            self.assertTrue(str(first['selected']).startswith('booster-tier-'), first)
            second = worker.ask({**request, 'exclude': [first['decision']], 'spares': 3})
            self.assertTrue(second['ok'], second)
            self.assertTrue(second['exclude_fallback'], second)
            self.assertNotEqual(second['decision'], first['decision'])
            self.assertIn(second['decision'], snapshot['candidates'])
            self.assertEqual(second['spares'][0], {'decision': second['decision'], 'searched': False})
            self.assertNotIn(first['decision'], [spare['decision'] for spare in second['spares']])
        finally:
            worker.close()


if __name__ == '__main__':
    unittest.main()
