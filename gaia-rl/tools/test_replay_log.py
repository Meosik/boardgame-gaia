import copy
import unittest

from replay_log import add_decision_log


class DecisionLogTest(unittest.TestCase):
    def test_records_observed_deltas_without_rewriting_states(self):
        player = {'player_id': 0, 'vp': 10, 'resources':
                  {'ore': 4, 'credits': 15, 'knowledge': 3, 'qic': 1}}
        initial = {'decision_id': 0, 'player': None, 'action': None,
                   'state': {'round': 1, 'players': [player]}}
        after = copy.deepcopy(initial)
        after.update(decision_id=1, player=0, action={'type': 'Pass'})
        after['state']['round'] = 2
        after['state']['players'][0]['resources']['ore'] += 2
        after['state']['players'][0]['vp'] += 3
        replay = {'metadata': {}, 'frames': [initial, after]}
        states = [copy.deepcopy(frame['state']) for frame in replay['frames']]
        add_decision_log(replay, income_by_frame={})
        self.assertEqual([f['state'] for f in replay['frames']], states)
        self.assertEqual([f['event_end'] for f in replay['frames']], [0, 1])
        event = replay['events'][0]['ReplayDecision']
        self.assertEqual(event['round'], 1)
        self.assertEqual(event['net_changes'], [{'player': 0, 'delta': {'ore': 2, 'vp': 3}}])
        self.assertEqual(event['action'], {'type': 'Pass'})
        once = copy.deepcopy(replay)
        self.assertEqual(add_decision_log(replay, income_by_frame={}), once)

    def test_income_is_separate_from_action_delta_and_in_the_same_frame(self):
        player = {'player_id': 0, 'vp': 10, 'resources':
                  {'ore': 4, 'credits': 15, 'knowledge': 3, 'qic': 1}}
        before = {'decision_id': 0, 'player': None, 'action': None,
                  'state': {'round': 1, 'players': [player]}}
        after = copy.deepcopy(before)
        after.update(decision_id=1, player=0, action={'type': 'Pass'})
        after['state']['round'] = 2
        after['state']['players'][0]['resources']['ore'] += 2
        income = {'IncomeReceived': {'player': 0, 'round': 2, 'ore': 2, 'credits': 0,
                  'knowledge': 0, 'qic': 0, 'power_charge': 5, 'power_tokens': 2, 'vp': 0}}
        exact = {1: [income, {'RoundStarted': {'round': 2}}]}
        replay = {'metadata': {}, 'frames': [before, after]}
        original = copy.deepcopy(replay)
        add_decision_log(replay, income_by_frame=exact)
        self.assertEqual(replay['events'][1], income)
        self.assertEqual([f['event_end'] for f in replay['frames']], [0, 3])
        self.assertEqual([f['state'] for f in replay['frames']],
                         [f['state'] for f in original['frames']])
        self.assertEqual(add_decision_log(copy.deepcopy(replay), income_by_frame=exact), replay)


if __name__ == '__main__':
    unittest.main()
