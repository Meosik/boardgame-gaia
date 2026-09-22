import copy
import unittest
from unittest.mock import patch
from action_purpose.test_teacher import node, action, FakeEnv
from action_purpose.teacher import PurposeTeacher
from economy.test_teacher import fixture, line_board
from power_purpose.teacher import PowerPurposeTeacher, contested


class SimpleTeacher(PowerPurposeTeacher):
    def base_rank(self, snapshot):
        return [(v, 'base') for v in snapshot['values']]

    def adjust_research_order(self, snapshot, scores):
        pass


class PowerPurposeTests(unittest.TestCase):
    def route(self, *, power=(2, 4, 3), after_power=(2, 2, 4), rival=0, ore=2, rnd=3):
        burn, skip = action('BurnPower'), {'type': 'Pass'}
        spend = {'type': 'PowerAction', 'id': 3, 'coord': None}
        before = node([burn, skip], [58, 2], power=power, ore=ore, rnd=rnd)
        other = copy.deepcopy(before['state']['players'][0])
        other.update(player_id=1, passed=False)
        other['resources']['power']['bowl3'] = rival
        before['state']['players'].append(other)
        after = copy.deepcopy(before)
        after['candidates'] = [{'action': spend}, {'action': skip}]
        after['values'] = [64, 2]
        after['state']['players'][0]['resources']['power'] = dict(zip(('bowl1', 'bowl2', 'bowl3'), after_power))
        teacher = SimpleTeacher().bind(FakeEnv(before, {0: FakeEnv(after)}))
        return teacher, before, after

    def test_contested_useful_action_prioritizes_burn(self):
        teacher, before, _ = self.route(rival=4)
        result = teacher.rank(before)
        self.assertGreater(result[0][0], result[1][0])
        self.assertIn('PowerAction', result[0][1])

    def test_circulation_congestion_increases_useful_burn_not_idle_burn(self):
        teacher, before, _ = self.route(power=(2, 5, 3), after_power=(2, 3, 4))
        high = teacher.rank(before)[0][0]
        teacher, before, _ = self.route(power=(1, 2, 3), after_power=(1, 0, 4))
        self.assertGreater(high, teacher.rank(before)[0][0])
        teacher, before, after = self.route()
        after['candidates'] = [{'action': {'type': 'Pass'}}];after['values'] = [2]
        teacher.bind(FakeEnv(before, {0: FakeEnv(after)}))
        self.assertLess(teacher.rank(before)[0][0], 0)

    def test_spare_ore_and_low_reserve_do_not_justify_burning(self):
        for kwargs in ({'ore': 8, 'rival': 4},
                       {'power': (0, 2, 2), 'after_power': (0, 0, 3), 'rival': 4}):
            teacher, before, _ = self.route(**kwargs)
            self.assertLess(teacher.rank(before)[0][0], 0)

    def test_burn_liquidation_chain_is_not_a_shared_action_plan(self):
        teacher, before, after = self.route()
        score, target = teacher.route_value(before, after, set(), [action('BurnPower'), action('PowerToOre')])
        self.assertLess(score, 0);self.assertIsNone(target)

    def test_taken_or_already_affordable_slot_never_justifies_burn(self):
        teacher, before, after = self.route(rival=4)
        before['state']['used_power_actions'] = [3]
        self.assertLess(teacher.rank(before)[0][0], 0)
        before['state']['used_power_actions'] = []
        before['candidates'].append(after['candidates'][0]);before['values'].append(64)
        self.assertLess(teacher.rank(before)[0][0], 0)

    def test_passed_opponent_does_not_create_race(self):
        _, before, _ = self.route(rival=4)
        state = before['state'];player = state['players'][0]
        spend = {'type': 'PowerAction', 'id': 3}
        self.assertTrue(contested(state, player, spend))
        state['players'][1]['passed'] = True
        self.assertFalse(contested(state, player, spend))

    def test_expensive_construction_penalties_are_teacher_scores_not_state_changes(self):
        snapshot, player = fixture()
        state = snapshot['state'];line_board(state)
        state['board']['hexes']['1,0']['planet']['planet_type'] = 'Volcanic'
        player['structures'] = [{'hex': '0,0', 'kind': 'Mine'}]
        player['research_tracks']['terraforming'] = 0
        snapshot['candidates'] = [{'action': {'type': 'Build', 'coord': '1,0'}},
                                  {'action': {'type': 'Upgrade', 'coord': '0,0', 'to': 'TradingStation'}}]
        before = copy.deepcopy(snapshot)
        with patch.object(PurposeTeacher, 'base_rank', return_value=[(65, 'base'), (65, 'base')]):
            scores = PowerPurposeTeacher().base_rank(snapshot)
        self.assertEqual([s[0] for s in scores], [41, 47])
        self.assertEqual(snapshot, before)


if __name__ == '__main__':
    unittest.main()
