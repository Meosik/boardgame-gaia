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


if __name__ == '__main__':
    unittest.main()
