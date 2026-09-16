import copy
import json
import unittest
from unittest.mock import patch

from action_purpose.teacher import PurposeTeacher, key
from current_actions.teacher import BoosterScoring, CurrentActionTeacher
from current_actions.test_conservation_native import root as native_root
from economy.test_teacher import fixture
from research_context import test_teacher as research_tests


class RouteScoringTests(unittest.TestCase):
    def setUp(self):
        self.before, _ = fixture()
        self.after = copy.deepcopy(self.before)
        self.old = {'type': 'Build', 'coord': '1,0'}
        self.first = {'type': 'ResearchAdvance', 'track': 'Navigation'}
        self.second = {'type': 'ResearchAdvance', 'track': 'Science'}
        self.passive = {'type': 'FreeAction', 'kind': 'PowerToOre', 'count': 1}
        self.after['candidates'] = [{'action': a} for a in
                                    (self.old, self.passive, self.first, self.second)]
        self.legal = {key(self.old)}
        self.actions = [{'type': 'FreeAction', 'kind': 'PowerToOre', 'count': 2}]

    def compare(self, teacher=None):
        teacher = teacher or CurrentActionTeacher()
        calls = []

        def score(instance, snapshot, action):
            self.assertIs(snapshot, self.after)
            self.assertIs(instance._snapshot, self.after)
            for attr in ('_locations', '_preparation', '_research_cache'):
                self.assertIsInstance(getattr(instance, attr), dict)
            self.assertEqual(len(snapshot['candidates']), 4)
            calls.append(action)
            return 20.0, 'unchanged full-menu context'

        units = [{**a, 'count': 1} for a in self.actions for _ in range(a['count'])]
        frozen = copy.deepcopy(self.after)
        with patch.object(BoosterScoring, 'score', score):
            expected = PurposeTeacher.route_value(teacher, self.before, self.after, self.legal, units)
            self.assertEqual(len(calls), 4)
            calls.clear()
            actual = teacher.route_value(self.before, self.after, self.legal, self.actions)
        self.assertEqual(actual, expected)
        self.assertEqual(self.after, frozen)
        self.assertIsNone(getattr(teacher, '_route_context', None))
        for attr in ('_snapshot', '_locations', '_preparation', '_research_cache'):
            self.assertIsNone(getattr(teacher, attr))
        return actual, calls

    def test_only_existing_predicate_survivors_are_scored_with_full_context_and_stable_tie(self):
        actual, calls = self.compare()
        self.assertEqual(calls, [self.first, self.second])
        self.assertEqual(actual, (16.0, self.first))

    def test_no_new_productive_actions_need_no_expensive_scores(self):
        self.legal.update((key(self.first), key(self.second)))
        actual, calls = self.compare()
        self.assertEqual(actual, (-12.0, None))
        self.assertEqual(calls, [])

    def test_subclasses_keep_full_scoring_for_unknown_mutable_semantics(self):
        class StatefulTeacher(CurrentActionTeacher):
            pass

        _, calls = self.compare(StatefulTeacher())
        self.assertEqual(len(calls), 4)

    def test_exception_cleans_up_and_next_root_rank_is_not_filtered(self):
        teacher = CurrentActionTeacher()
        with patch.object(BoosterScoring, 'score', side_effect=RuntimeError('probe')):
            with self.assertRaisesRegex(RuntimeError, 'probe'):
                teacher.route_value(self.before, self.after, self.legal, self.actions)
        self.assertIsNone(getattr(teacher, '_route_context', None))
        for attr in ('_snapshot', '_locations', '_preparation', '_research_cache'):
            self.assertIsNone(getattr(teacher, attr))
        with patch.object(BoosterScoring, 'score', return_value=(7.0, 'root')) as score:
            values = teacher.base_rank(self.after)
        self.assertEqual(score.call_count, 4)
        self.assertEqual(values, [(7.0, 'root')]*4)

    def test_unscored_advanced_choice_still_affects_last_green_research_opportunity(self):
        fixture = research_tests.ResearchContextTests()
        fixture.setUp()
        snapshot, player = fixture.s, fixture.p
        snapshot['state']['round'] = 6
        player['research_tracks']['science'] = 4
        player['resources']['knowledge'] = 4
        player['tech_tiles'] = [7]
        snapshot['state']['research_board']['advanced_tech_tiles'][5] = 10
        research = {'type': 'ResearchAdvance', 'track': 'Science'}
        advanced = {'type': 'Upgrade', 'coord': '0,0', 'to': {'Academy': 'Science'},
                    'tech_tile_choice': {'kind': 'Advanced', 'track': 'Science',
                                         'covered_tile': 7, 'advance_track': None}}
        snapshot['candidates'] = [{'action': research}, {'action': advanced}]
        legal = {key(advanced)}
        actions = [{'type': 'FreeAction', 'kind': 'PowerToKnowledge', 'count': 1}]
        teacher = CurrentActionTeacher()
        expected = PurposeTeacher.route_value(teacher, snapshot, snapshot, legal, actions)
        self.assertEqual(teacher.route_value(snapshot, snapshot, legal, actions), expected)
        # A physically pruned menu would erase this opportunity cost.
        pruned = {**snapshot, 'candidates': [{'action': research}]}
        wrong = teacher.route_value(pruned, pruned, legal, actions)
        self.assertEqual(expected[1], research)
        self.assertLess(expected[0], wrong[0])


class NativeRouteScoringTests(unittest.TestCase):
    def test_complete_ranks_previews_and_commitments_match_full_scoring(self):
        for decision in (35, 160):
            env, snapshot = native_root(decision)
            original = env.snapshot_json()
            for stage in (1, 2, 3, 4):
                with self.subTest(decision=decision, stage=stage):
                    control = CurrentActionTeacher(stage).bind(env)
                    optimized = CurrentActionTeacher(stage).bind(env)
                    # Without the score override this is the unchanged full-rank
                    # implementation, including batch penalties and conservation.
                    with patch.object(CurrentActionTeacher, 'score', BoosterScoring.score):
                        expected = control.rank(snapshot)
                    self.assertEqual(optimized.rank(snapshot), expected)
                    self.assertEqual(optimized.last_scores, control.last_scores)
                    self.assertEqual(optimized.preview_count, control.preview_count)
                    self.assertEqual(optimized._conservation.continuations,
                                     control._conservation.continuations)
                    if decision == 160:
                        index = next(i for i, c in enumerate(snapshot['candidates'])
                                     if c['action'].get('kind') == 'QicToOre')
                        branch = env.fork(snapshot['decision_id'], index)
                        after = json.loads(branch.snapshot_json())
                        with patch.object(CurrentActionTeacher, 'score', BoosterScoring.score):
                            expected = control.bind(branch).rank(after)
                        self.assertEqual(optimized.bind(branch).rank(after), expected)
                        self.assertEqual(optimized._conservation.continuations,
                                         control._conservation.continuations)
                    self.assertEqual(env.snapshot_json(), original)


if __name__ == '__main__':
    unittest.main()
