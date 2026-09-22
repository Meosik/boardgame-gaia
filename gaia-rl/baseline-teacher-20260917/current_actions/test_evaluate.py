import copy
import unittest

from current_actions.evaluate import audit_booster_builds, teacher_for_stage
from current_actions.teacher import BOOSTER_BUILD, CurrentActionTeacher, CurrentContextTeacher
from economy.test_teacher import fixture, line_board


class EvaluationTests(unittest.TestCase):
    def test_all_standard_stages_use_current_booster_scoring(self):
        self.assertIsInstance(teacher_for_stage(0), CurrentContextTeacher)
        for stage in range(1, 5):
            policy = teacher_for_stage(stage)
            self.assertIsInstance(policy, CurrentActionTeacher)
            self.assertEqual(policy.stage, stage)
        with self.assertRaises(ValueError):
            teacher_for_stage(5)

    def test_booster_debit_audit_records_paid_mine_and_rejects_free_mine(self):
        snapshot, player = fixture()
        state = snapshot['state']
        line_board(state)
        player['research_tracks']['terraforming'] = 0
        state['board']['hexes']['1,0']['planet']['planet_type'] = 'Volcanic'
        after = copy.deepcopy(state)
        after['players'][1]['resources']['ore'] -= 1
        after['players'][1]['resources']['credits'] -= 2
        replay = {'frames': [{'state': state}, {'state': after}]}
        result = {'seat': 1, 'metrics': {}, 'choices': [
            {'step': 1, 'action': {'type': BOOSTER_BUILD, 'coord': '1,0'}, 'cost': None}]}
        audit_booster_builds(result, replay)
        self.assertEqual(result['metrics']['booster12_uses'], 1)
        self.assertEqual(result['metrics']['verified_build_costs'], 1)
        self.assertEqual(result['choices'][0]['cost']['ore'], 1)
        self.assertEqual(result['choices'][0]['cost']['credits'], 2)
        replay['frames'][1]['state'] = copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError, 'Booster12 cost mismatch'):
            audit_booster_builds(result, replay)


if __name__ == '__main__':
    unittest.main()
