import copy
import gzip
import json
from pathlib import Path
import unittest

from replay_income import ROOT, recover_income
from replay_log import add_decision_log


class ReplayIncomeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT/'gaia-rl/runs/source-routes-v1/replay-publication/source-routes-v1-candidate-1.json.gz'
        if not path.exists():
            raise unittest.SkipTest('Historical replay fixture unavailable')
        with gzip.open(path, 'rt') as f:
            cls.replay = json.load(f)

    def test_six_rounds_all_players_power_and_state_preserved(self):
        original = copy.deepcopy(self.replay)
        updated = add_decision_log(copy.deepcopy(original))
        income = [e['IncomeReceived'] for e in updated['events'] if 'IncomeReceived' in e]
        self.assertEqual(len(income), 24)
        self.assertEqual({(i['player'], i['round']) for i in income},
                         {(p, r) for p in range(4) for r in range(1, 7)})
        self.assertTrue(any(i['power_charge'] for i in income))
        self.assertTrue(any(i['power_tokens'] for i in income))
        for old, new in zip(original['frames'], updated['frames']):
            self.assertEqual(old['state'], new['state'])
            self.assertEqual(old['action'], new['action'])
        self.assertEqual(updated['frames'][-1]['event_end'], len(updated['events']))
        self.assertEqual(add_decision_log(copy.deepcopy(updated)), updated)

    def test_mismatched_state_rejected_without_mutation(self):
        replay = copy.deepcopy(self.replay)
        frame = next(a for b, a in zip(replay['frames'], replay['frames'][1:])
                     if b['state']['round'] != a['state']['round'])
        frame['state']['players'][0]['resources']['ore'] += 1
        original = copy.deepcopy(replay)
        with self.assertRaisesRegex(ValueError, 'reconstruction rejected'):
            add_decision_log(replay)
        self.assertEqual(replay, original)

    def test_pending_income_order_does_not_hide_income_before_round_increments(self):
        path = ROOT/'gaia-frontend/public/ai-replays/economy-learning-v1-bc_only-1.json.gz'
        if not path.exists():
            self.skipTest('Income-order replay unavailable')
        with gzip.open(path, 'rt') as f:
            replay = json.load(f)
        updated = add_decision_log(copy.deepcopy(replay))
        income = [e['IncomeReceived'] for e in updated['events'] if 'IncomeReceived' in e]
        self.assertEqual(len(income), 24)
        self.assertEqual({(i['player'], i['round']) for i in income},
                         {(p, r) for p in range(4) for r in range(1, 7)})


if __name__ == '__main__':
    unittest.main()
