import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import decision_probe


def root(first):
    return types.SimpleNamespace(name=f'root-{first}', first=first)


def other():
    return types.SimpleNamespace(name='Ivits-station-then-extend-federation', first=None)


def names(goals):
    return [goal.name for goal in goals]


class FrontFirstTest(unittest.TestCase):
    def test_front_roots_come_first_in_front_order_and_the_rest_keeps_its_order(self):
        goal, r3, r7, r5 = other(), root(3), root(7), root(5)
        result = decision_probe.front_first([goal, r3, r7, r5], [5, 7])
        self.assertEqual(result, [r5, r7, goal, r3])

    def test_an_index_with_no_root_goal_is_skipped(self):
        goal, r3, r7 = other(), root(3), root(7)
        self.assertEqual(decision_probe.front_first([goal, r3, r7], [42, 7]), [r7, goal, r3])

    def test_an_empty_front_keeps_the_order(self):
        goals = [other(), root(3), root(7)]
        self.assertEqual(decision_probe.front_first(goals, []), goals)

    def test_a_non_root_goal_with_a_front_index_is_not_moved(self):
        odd = types.SimpleNamespace(name='plan-x', first=7)
        r3 = root(3)
        self.assertEqual(decision_probe.front_first([odd, r3], [7]), [odd, r3])


class RootRanksTest(unittest.TestCase):
    def test_first_root_is_rank_two_and_a_missing_index_is_none(self):
        ranks = decision_probe.root_ranks([root(3), root(7)], [3, 7, 99])
        self.assertEqual(ranks, {'3': 2, '7': 3, '99': None})

    def test_keys_are_strings(self):
        ranks = decision_probe.root_ranks([root(3)], [3])
        self.assertTrue(all(isinstance(key, str) for key in ranks))


class ParseAskTest(unittest.TestCase):
    def test_an_ask_without_cap_or_front(self):
        self.assertEqual(decision_probe.parse_ask('asis:4:0:', 0),
                         {'label': 'asis', 'comparisons': 4, 'cap': None, 'front': []})

    def test_an_ask_with_cap_and_front(self):
        ask = decision_probe.parse_ask('user:4:60:0,2', 3)
        self.assertEqual(ask, {'label': 'user', 'comparisons': 4, 'cap': 60.0, 'front': [0, 2]})

    def test_wrong_number_of_parts_exits(self):
        for text in ('asis:4:0', 'asis:4:0::', 'a'):
            with self.assertRaises(SystemExit, msg=text):
                decision_probe.parse_ask(text, 3)

    def test_an_empty_label_exits(self):
        with self.assertRaises(SystemExit):
            decision_probe.parse_ask(':4:0:', 3)

    def test_a_front_position_out_of_range_exits(self):
        with self.assertRaises(SystemExit):
            decision_probe.parse_ask('x:4:0:3', 3)

    def test_a_repeated_front_position_exits(self):
        with self.assertRaises(SystemExit):
            decision_probe.parse_ask('x:4:0:1,1', 3)

    def test_zero_comparisons_exits(self):
        with self.assertRaises(SystemExit):
            decision_probe.parse_ask('x:0:0:', 3)


class AskSpecTest(unittest.TestCase):
    def setUp(self):
        self.teacher = {'name': 't', 'factory': 'mod:make', 'comparisons': 100, 'max_seconds': 5,
                        'env': {'KEEP': '1'}}

    def test_an_empty_front_leaves_factory_and_env_alone(self):
        ask = {'label': 'a', 'comparisons': 9, 'cap': 60.0, 'front': []}
        spec = decision_probe.ask_spec(self.teacher, ask, [4, 8], '/tmp/log')
        self.assertEqual(spec['factory'], 'mod:make')
        self.assertEqual(spec['env'], {'KEEP': '1'})
        self.assertEqual(spec['comparisons'], 9)
        self.assertEqual(spec['max_seconds'], 60.0)

    def test_a_front_installs_the_probe_factory_and_environment(self):
        ask = {'label': 'a', 'comparisons': 9, 'cap': None, 'front': [1]}
        before = json.loads(json.dumps(self.teacher))
        spec = decision_probe.ask_spec(self.teacher, ask, [4, 8], '/tmp/log')
        self.assertEqual(spec['factory'], 'decision_probe:factory')
        self.assertIsNone(spec['max_seconds'])
        self.assertEqual(spec['env'], {
            'KEEP': '1', 'GAIA_PROBE_FACTORY': 'mod:make', 'GAIA_PROBE_FRONT': json.dumps([8]),
            'GAIA_PROBE_WATCH': json.dumps([4, 8]), 'GAIA_PROBE_LOG': '/tmp/log'})
        self.assertEqual(self.teacher, before)


class ByTypeTest(unittest.TestCase):
    def test_counts_by_type_descending_with_upgrade_targets(self):
        candidates = [
            {'action': {'type': 'Build'}},
            {'action': {'type': 'Upgrade', 'to': 'TradingStation'}},
            {'action': {'type': 'Upgrade', 'to': {'Academy': 'Qic'}}},
            {'action': {'type': 'Upgrade', 'to': {'Academy': 'Qic'}}},
            {'action': {'type': 'Pass'}},
            {'action': {'type': 'Build'}},
            {'action': {'type': 'Upgrade', 'to': 'TradingStation'}},
            {'action': {'type': 'Upgrade', 'to': 'TradingStation'}},
        ]
        kinds, upgrades = decision_probe.by_type(candidates)
        self.assertEqual(kinds, {'Upgrade': 5, 'Build': 2, 'Pass': 1})
        self.assertEqual(list(kinds), ['Upgrade', 'Build', 'Pass'])
        self.assertEqual(upgrades, {'TradingStation': 3, json.dumps({'Academy': 'Qic'}, sort_keys=True): 2})


class InstallFrontTest(unittest.TestCase):
    def setUp(self):
        self.package = types.ModuleType('four_factions')
        self.module = types.ModuleType('four_factions.preparation')

        def interleave_families(items, family):
            return list(items)
        interleave_families._plan_menu = True
        self.original = interleave_families
        self.module.interleave_families = interleave_families
        self.package.preparation = self.module
        patcher = mock.patch.dict(sys.modules, {'four_factions': self.package,
                                                'four_factions.preparation': self.module})
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.log = Path(directory.name)/'roots.jsonl'

    def test_root_calls_put_the_front_first_and_log_the_ranks(self):
        decision_probe.install_front([7], watch=[7, 99], log_path=str(self.log))
        r3, r7, r5 = root(3), root(7), root(5)
        result = self.module.interleave_families([r3, r7, r5], 'family')
        self.assertEqual(result, [r7, r3, r5])
        lines = self.log.read_text().splitlines()
        self.assertEqual([json.loads(line) for line in lines], [{'roots': 3, 'rank': {'7': 3, '99': None}}])

    def test_non_root_calls_pass_through_without_a_log_line(self):
        decision_probe.install_front([7], watch=[7], log_path=str(self.log))
        self.assertEqual(self.module.interleave_families([5, 6, 7], 'family'), [5, 6, 7])
        self.assertFalse(self.log.exists())

    def test_the_wrapper_keeps_flags_and_a_second_install_does_not_wrap_again(self):
        decision_probe.install_front([7], log_path=str(self.log))
        wrapper = self.module.interleave_families
        self.assertTrue(wrapper._probe_front)
        self.assertTrue(wrapper._plan_menu)
        self.assertIs(wrapper.__wrapped__, self.original)
        decision_probe.install_front([7], log_path=str(self.log))
        self.assertIs(self.module.interleave_families, wrapper)


class ComparisonTimesTest(unittest.TestCase):
    def test_a_start_and_its_end_give_one_finished_row_with_the_end_fields(self):
        lines = [{'event': 'start', 'call': 'rollout', 'goal': 'root-7', 'first': 7, 'pid': 11, 'at': 105.12345},
                 {'event': 'end', 'call': 'rollout', 'goal': 'root-7', 'first': 7, 'pid': 11, 'at': 109.0,
                  'seconds': 3.9, 'decisions': 7, 'complete': True, 'error': None}]
        rows = decision_probe.comparison_times(lines, 100.0)
        self.assertEqual(rows, [{'call': 'rollout', 'goal': 'root-7', 'first': 7, 'pid': 11, 'started': 5.123,
                                 'finished': True, 'seconds': 3.9, 'decisions': 7, 'complete': True,
                                 'error': None}])
        self.assertNotIn('event', rows[0])
        self.assertNotIn('at', rows[0])

    def test_own_decisions_of_the_end_line_reach_the_row(self):
        own = [{'round': 5, 'candidates': 2}]
        lines = [{'event': 'start', 'call': 'rollout', 'goal': 'g', 'first': 1, 'pid': 1, 'at': 101.0},
                 {'event': 'end', 'call': 'rollout', 'goal': 'g', 'first': 1, 'pid': 1, 'at': 102.0,
                  'own_decisions': own}]
        self.assertEqual(decision_probe.comparison_times(lines, 100.0)[0]['own_decisions'], own)

    def test_a_start_with_no_end_is_not_finished(self):
        lines = [{'event': 'start', 'call': 'rollout', 'goal': 'root-7', 'first': 7, 'pid': 11, 'at': 101.0}]
        rows = decision_probe.comparison_times(lines, 100.0)
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]['finished'], False)
        self.assertNotIn('seconds', rows[0])

    def test_interleaved_rollouts_of_different_goals_and_pids_are_matched_and_kept_in_start_order(self):
        lines = [{'event': 'start', 'call': 'rollout', 'goal': 'A', 'first': 1, 'pid': 1, 'at': 101.0},
                 {'event': 'start', 'call': 'rollout', 'goal': 'B', 'first': 2, 'pid': 2, 'at': 102.0},
                 {'event': 'end', 'call': 'rollout', 'goal': 'B', 'first': 2, 'pid': 2, 'at': 103.0, 'seconds': 1.0},
                 {'event': 'end', 'call': 'rollout', 'goal': 'A', 'first': 1, 'pid': 1, 'at': 104.0, 'seconds': 3.0}]
        rows = decision_probe.comparison_times(lines, 100.0)
        self.assertEqual([row['goal'] for row in rows], ['A', 'B'])
        self.assertEqual([row['seconds'] for row in rows], [3.0, 1.0])
        self.assertEqual([row['finished'] for row in rows], [True, True])
        self.assertEqual([row['started'] for row in rows], [1.0, 2.0])

    def test_lines_without_an_event_and_tasks_lines_are_ignored(self):
        lines = [{'roots': 3, 'rank': {}},
                 {'event': 'tasks', 'planned': 2, 'order': []},
                 {'event': 'start', 'call': 'select_goal', 'goal': 'g', 'pid': 1, 'at': 101.0}]
        rows = decision_probe.comparison_times(lines, 100.0)
        self.assertEqual([row['goal'] for row in rows], ['g'])


class InstallTimingTest(unittest.TestCase):
    def setUp(self):
        decision_probe._inside['depth'] = 0
        self.addCleanup(decision_probe._inside.update, depth=0)
        self.package = types.ModuleType('four_factions')
        self.module = module = types.ModuleType('four_factions.preparation')
        self.raises = None
        self.result = {'complete': True, 'value': 1.0, 'decisions': 7}

        class Policies:
            def rank(self, env, snapshot):
                return [0, 1, 2]

        def select_goal(env, snapshot, scores, goal, policies, deadline):
            return 5

        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            module.Policies().rank(None, {'candidates': [1, 2, 3]})
            module.Policies().rank(None, {'candidates': [1, 2, 3]})
            module.select_goal(None, {}, [], goal, None, 0)
            if self.raises:
                raise self.raises
            return self.result
        module.Policies, module.select_goal, module.rollout = Policies, select_goal, rollout
        self.package.preparation = module
        patcher = mock.patch.dict(sys.modules, {'four_factions': self.package,
                                                'four_factions.preparation': module})
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.log = Path(directory.name)/'timing.jsonl'
        self.goal = types.SimpleNamespace(name='root-7')

    def lines(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_a_top_level_rollout_logs_start_and_end_with_the_inside_counts_and_no_select_lines(self):
        decision_probe.install_timing(str(self.log))
        result = self.module.rollout(None, {}, 7, self.goal, None, 0)
        self.assertEqual(result, {'complete': True, 'value': 1.0, 'decisions': 7})
        lines = self.lines()
        self.assertEqual([line['event'] for line in lines], ['start', 'end'])
        self.assertTrue(all(line['call'] == 'rollout' and line['goal'] == 'root-7' and line['first'] == 7
                            for line in lines))
        end = lines[1]
        self.assertIs(end['complete'], True)
        self.assertEqual(end['decisions'], 7)
        self.assertEqual(end['rank_calls'], 2)
        self.assertEqual(end['ranked_candidates'], 6)
        self.assertEqual(end['select_calls'], 1)
        self.assertIsNone(end['error'])

    def test_the_end_line_records_the_rollouts_course_and_the_result_is_untouched(self):
        self.result = {'complete': True, 'value': 2.5, 'decisions': 3, 'goal_acquired': True,
                       'remaining_goal': {'name': 'x'}, 'end_round': 6,
                       'actions': [{'round': 5, 'action': {'type': 'A'}, 'resources_before': {'o': 1},
                                    'resources_after': {'o': 0}, 'vp_before': 10, 'vp_after': 12},
                                   {'round': 6, 'action': {'type': 'B'}, 'resources_before': {'o': 2},
                                    'resources_after': {'o': 3}, 'vp_before': 12, 'vp_after': 19}]}
        decision_probe.install_timing(str(self.log))
        result = self.module.rollout(None, {}, 7, self.goal, None, 0)
        self.assertIs(result, self.result)
        self.assertIn('resources_before', result['actions'][0])
        end = self.lines()[-1]
        self.assertEqual(end['value'], 2.5)
        self.assertIs(end['goal_acquired'], True)
        self.assertEqual(end['remaining_goal'], {'name': 'x'})
        self.assertEqual(end['end_round'], 6)
        self.assertEqual(end['actions'], [{'round': 5, 'action': {'type': 'A'}, 'vp_before': 10, 'vp_after': 12},
                                          {'round': 6, 'action': {'type': 'B'}, 'vp_before': 12, 'vp_after': 19}])

    def test_a_raising_rollout_leaves_no_actions_in_the_end_line(self):
        decision_probe.install_timing(str(self.log))
        self.raises = RuntimeError('boom')
        with self.assertRaises(RuntimeError):
            self.module.rollout(None, {}, 7, self.goal, None, 0)
        self.assertNotIn('actions', self.lines()[-1])

    def test_own_decisions_hold_one_record_per_inner_select_and_the_return_is_unchanged(self):
        returned = []

        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            returned.append(self.module.select_goal(
                None, snap(*[{'type': 'Build'}]*6), [(1, 'a')]*6, goal, None, 0))
            return self.result
        self.module.rollout = rollout
        decision_probe.install_timing(str(self.log))
        self.module.rollout(None, {}, 7, self.goal, None, 0)
        self.assertEqual(returned, [5])
        own = self.lines()[-1]['own_decisions']
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]['round'], 5)

    def test_own_decisions_chosen_matches_the_returned_index(self):
        self.module.select_goal = lambda env, snapshot, scores, goal, policies, deadline: 1
        returned = []

        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            returned.append(self.module.select_goal(
                None, snap({'type': 'Build'}, {'type': 'Pass'}), [(1, 'a'), (2, 'b')], goal, None, 0))
            return self.result
        self.module.rollout = rollout
        decision_probe.install_timing(str(self.log))
        self.module.rollout(None, {}, 7, self.goal, None, 0)
        own = self.lines()[-1]['own_decisions']
        self.assertEqual((returned, own[0]['chosen']['index'], own[0]['chosen']['type']), ([1], 1, 'Pass'))

    def test_a_malformed_scores_still_returns_the_index_and_records_an_error(self):
        returned = []

        def rollout(env, snapshot, first, goal, policies, deadline, *args, **kwargs):
            returned.append(self.module.select_goal(None, snap({'type': 'Pass'}), None, goal, None, 0))
            return self.result
        self.module.rollout = rollout
        decision_probe.install_timing(str(self.log))
        self.module.rollout(None, {}, 7, self.goal, None, 0)
        self.assertEqual(returned, [5])
        own = self.lines()[-1]['own_decisions']
        self.assertEqual(len(own), 1)
        self.assertEqual(list(own[0]), ['error'])

    def test_a_top_level_select_goal_logs_start_and_end_with_the_first_move(self):
        decision_probe.install_timing(str(self.log))
        self.assertEqual(self.module.select_goal(None, {}, [], self.goal, None, 0), 5)
        lines = self.lines()
        self.assertEqual([line['event'] for line in lines], ['start', 'end'])
        self.assertTrue(all(line['call'] == 'select_goal' for line in lines))
        self.assertEqual(lines[1]['first'], 5)

    def test_a_rank_call_outside_a_rollout_passes_through_and_writes_nothing(self):
        decision_probe.install_timing(str(self.log))
        self.assertEqual(self.module.Policies().rank(None, {'candidates': [1]}), [0, 1, 2])
        self.assertFalse(self.log.exists())

    def test_an_exception_propagates_is_logged_and_resets_the_depth(self):
        decision_probe.install_timing(str(self.log))
        self.raises = RuntimeError('boom')
        with self.assertRaises(RuntimeError):
            self.module.rollout(None, {}, 7, self.goal, None, 0)
        end = self.lines()[-1]
        self.assertEqual(end['event'], 'end')
        self.assertEqual(end['error'], 'RuntimeError')
        self.assertIsNone(end['complete'])
        self.assertEqual(decision_probe._inside['depth'], 0)

    def test_the_flag_is_set_and_a_second_install_does_not_wrap_again(self):
        decision_probe.install_timing(str(self.log))
        wrapper = self.module.rollout
        self.assertTrue(wrapper._probe_timing)
        decision_probe.install_timing(str(self.log))
        self.assertIs(self.module.rollout, wrapper)

    def test_select_goal_wrapped_is_itself_when_the_original_has_none(self):
        decision_probe.install_timing(str(self.log))
        self.assertIs(self.module.select_goal.__wrapped__, self.module.select_goal)

    def test_select_goal_wrapped_is_a_timed_wrapper_of_the_originals_wrapped(self):
        def other_function(env, snapshot, scores, goal, policies, deadline):
            return 9
        self.module.select_goal.__wrapped__ = other_function
        decision_probe.install_timing(str(self.log))
        wrapped = self.module.select_goal.__wrapped__
        self.assertIsNot(wrapped, self.module.select_goal)
        self.assertIsNot(wrapped, other_function)
        self.assertEqual(wrapped(None, {}, [], self.goal, None, 0), 9)
        lines = self.lines()
        self.assertEqual([line['event'] for line in lines], ['start', 'end'])
        self.assertEqual(lines[1]['first'], 9)


class RolloutRecordTest(unittest.TestCase):
    def test_no_result_gives_an_empty_record(self):
        self.assertEqual(decision_probe.rollout_record(None), {})

    def test_a_result_without_actions_gives_an_empty_list(self):
        self.assertEqual(decision_probe.rollout_record({'value': 1.0})['actions'], [])


BLOCK = 'conservation blocked: no'


def snap(*actions, round_=5):
    return {'state': {'round': round_}, 'candidates': [{'action': action} for action in actions]}


class DecisionRecordTest(unittest.TestCase):
    def test_counts_by_type_and_the_chosen_and_top_entries(self):
        snapshot = snap({'type': 'Build'}, {'type': 'Pass'}, {'type': 'Build'}, {'type': 'Build'})
        scores = [(3, 'a'), (2, 'b'), (7, BLOCK), (3, 'c')]
        record = decision_probe.decision_record(snapshot, scores, 1)
        self.assertEqual(record['round'], 5)
        self.assertEqual(record['candidates'], 4)
        self.assertEqual(record['by_type'], {'Build': 3, 'Pass': 1})
        self.assertEqual(record['chosen'], {'index': 1, 'type': 'Pass', 'score': 2, 'blocked': False, 'reason': 'b'})
        self.assertEqual(record['top']['index'], 0)
        self.assertEqual(record['best_pass']['score'], 2)
        self.assertEqual(record['federations'], 0)

    def test_federation_candidates_pick_the_best_unblocked_and_count_the_blocked(self):
        fed = {'type': 'FormFederation', 'satellite_hexes': [1, 2, 3], 'hexes': [[0, 0]], 'token': 'Credits'}
        small = {'type': 'FormFederation', 'satellite_hexes': [1], 'hexes': [[1, 1]], 'token': 'Ore'}
        snapshot = snap({'type': 'Pass'}, small, fed, dict(fed))
        scores = [[1, 'p'], [4, 'small'], [9, BLOCK], [6, 'big']]
        record = decision_probe.decision_record(snapshot, scores, 0)
        self.assertEqual(record['federations'], 3)
        self.assertEqual(record['federations_blocked'], 1)
        best = record['best_federation']
        self.assertEqual((best['index'], best['score'], best['satellites']), (3, 6, 3))
        self.assertEqual((best['hexes'], best['token']), ([[0, 0]], 'Credits'))
        self.assertEqual(record['top']['index'], 3)
        blocked = decision_probe.decision_record(snapshot, scores, 2)['chosen']
        self.assertIsNone(blocked['score'])
        self.assertIs(blocked['blocked'], True)

    def test_all_blocked_federations_give_the_blocked_best_and_none_when_absent(self):
        snapshot = snap({'type': 'Build'}, {'type': 'FormFederation'}, {'type': 'FormFederation'})
        scores = [(1, 'x'), (2, BLOCK), (5, BLOCK)]
        record = decision_probe.decision_record(snapshot, scores, 0)
        self.assertEqual(record['best_federation']['index'], 2)
        self.assertIs(record['best_federation']['blocked'], True)
        self.assertEqual(record['federations_blocked'], 2)
        self.assertIsNone(record['best_pass'])
        plain = decision_probe.decision_record(snap({'type': 'Build'}), [(1, 'x')], 0)
        self.assertIsNone(plain['best_federation'])
        self.assertIsNone(plain['best_pass'])
        none_top = decision_probe.decision_record(snap({'type': 'Pass'}), [(1, BLOCK)], None)
        self.assertIsNone(none_top['top'])

    def test_a_none_index_gives_no_chosen(self):
        record = decision_probe.decision_record(snap({'type': 'Pass'}), [(1, 'x')], None)
        self.assertIsNone(record['chosen'])


def seat(vp, passed=False, ore=1, credits=2, knowledge=3, qic=4):
    return {'vp': vp, 'passed': passed,
            'resources': {'ore': ore, 'credits': credits, 'knowledge': knowledge, 'qic': qic}}


def seats_snap(*actions, player=1):
    players = [seat(10, True), seat(20, ore=7), seat(30, True), seat(40)]
    return {'state': {'round': 5, 'players': players}, 'player': player, 'decision_id': 'd1',
            'candidates': [{'action': action} for action in actions]}


class FakeBranch:
    def __init__(self, payload):
        self.payload = payload

    def snapshot_json(self):
        return json.dumps(self.payload)


class FakeEnv:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, []

    def fork(self, decision_id, index):
        self.calls.append((decision_id, index))
        if self.error:
            raise self.error
        return FakeBranch(self.payload)


class DecisionRecordOthersTest(unittest.TestCase):
    ACTIONS = ({'type': 'Pass'}, {'type': 'Build'}, {'type': 'Pass'}, {'type': 'FormFederation'},
               {'type': 'Build'}, {'type': 'FormFederation'}, {'type': 'Build'}, {'type': 'Build'})
    SCORES = [(5, 'a'), (3, 'b'), (9, 'c'), (4, 'd'), (3, 'e'), (8, 'f'), (-1, 'g'), (9, BLOCK)]

    def record(self, env=None):
        return decision_probe.decision_record(seats_snap(*self.ACTIONS), self.SCORES, 1, env)

    def test_new_keys_without_env(self):
        record = self.record()
        self.assertEqual((record['others'], record['others_passed']), (3, 2))
        self.assertEqual(record['own'], {'vp': 20, 'ore': 7, 'credits': 2, 'knowledge': 3, 'qic': 4})
        self.assertEqual(record['positive_others'], 4)
        self.assertEqual([row['index'] for row in record['top_others']], [5, 3, 1])
        self.assertIsNone(record['pass_after'])
        self.assertIsNone(record['federation_after'])

    def test_missing_stock_keys_give_none(self):
        stock = decision_probe.own_stock({'players': [{}]}, 0)
        self.assertEqual(stock, {'vp': None, 'ore': None, 'credits': None, 'knowledge': None, 'qic': None})

    def test_fork_of_the_best_pass_and_federation(self):
        after = {'player': 2, 'state': {'round': 5, 'phase': {'Action': {'x': 1}},
                                        'players': [seat(10, True), seat(21, True, ore=0), seat(30, True), seat(40)]}}
        env = FakeEnv(after)
        record = self.record(env)
        self.assertEqual(env.calls, [('d1', 2), ('d1', 5)])
        self.assertEqual(record['pass_after'], {'round': 5, 'phase': 'Action', 'player': 2,
                                                'own': {'vp': 21, 'ore': 0, 'credits': 2, 'knowledge': 3, 'qic': 4},
                                                'others_passed': 2})
        self.assertEqual(record['federation_after'],
                         {'round': 5, 'own': {'vp': 21, 'ore': 0, 'credits': 2, 'knowledge': 3, 'qic': 4}})

    def test_a_string_phase_is_kept(self):
        env = FakeEnv({'player': 0, 'state': {'round': 6, 'phase': 'Income', 'players': []}})
        self.assertEqual(self.record(env)['pass_after']['phase'], 'Income')

    def test_a_failing_fork_leaves_the_rest_of_the_record(self):
        record = self.record(FakeEnv(error=RuntimeError('boom')))
        self.assertIn('boom', record['pass_after']['error'])
        self.assertIn('boom', record['federation_after']['error'])
        self.assertEqual(record['others_passed'], 2)
        self.assertEqual(record['positive_others'], 4)

    def test_decision_line_shows_the_new_text_and_survives_an_old_item(self):
        env = FakeEnv({'player': 0, 'state': {'round': 6, 'phase': 'Income', 'players': []}})
        line = decision_probe.decision_line(self.record(env))
        self.assertIn(' | others passed 2/3 | after pass R6 | 4 positive', line)
        old = decision_probe.decision_line({'round': 3, 'candidates': 2, 'federations': 0})
        self.assertIn('others passed None/None | after pass R- | None positive', old)


class InstallTaskLogTest(unittest.TestCase):
    def setUp(self):
        self.goals = [types.SimpleNamespace(name='root-3', family='roots', first=3),
                      types.SimpleNamespace(name='plan-x', family='plans', first=None)]
        self.module = types.ModuleType('parallel_search')
        self.module._planned_tasks = lambda *args, **kwargs: (self.goals, False)
        patcher = mock.patch.dict(sys.modules, {'parallel_search': self.module})
        patcher.start()
        self.addCleanup(patcher.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.log = Path(directory.name)/'tasks.jsonl'

    def test_the_planned_tasks_are_returned_unchanged_and_logged_once(self):
        decision_probe.install_task_log(str(self.log))
        self.assertEqual(self.module._planned_tasks(1, 2), (self.goals, False))
        lines = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(lines, [{'event': 'tasks', 'planned': 2,
                                  'order': [['root-3', 'roots', 3], ['plan-x', 'plans', None]]}])

    def test_a_second_install_does_not_wrap_again(self):
        decision_probe.install_task_log(str(self.log))
        wrapper = self.module._planned_tasks
        decision_probe.install_task_log(str(self.log))
        self.assertIs(self.module._planned_tasks, wrapper)


if __name__ == '__main__':
    unittest.main()
