"""Drives tools/ai_worker.py as a real subprocess over its JSON-lines protocol."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from gaia_rl import Environment

GAIA_RL = Path(__file__).resolve().parents[1]
SEED = 'state-evaluation-ab-20260917-1580'


class Worker:
    def __init__(self):
        env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1',
               'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
        self.process = subprocess.Popen([sys.executable, str(GAIA_RL/'tools'/'ai_worker.py')], cwd=GAIA_RL, env=env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        text=True)

    def ask(self, request):
        self.process.stdin.write(json.dumps(request)+'\n')
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def close(self):
        self.process.stdin.close()
        self.process.wait(timeout=30)


class AiWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.worker = Worker()

    @classmethod
    def tearDownClass(cls):
        cls.worker.close()

    def play(self, decisions, level):
        env = Environment(SEED, 2000)
        for _ in range(decisions):
            snapshot = json.loads(env.snapshot_json())
            reply = self.worker.ask({'op': 'choose', 'room': f'test-{level}', 'level': level,
                                     'state': snapshot['state'], 'player': snapshot['player']})
            self.assertTrue(reply['ok'], reply)
            self.assertIn(reply['decision'], snapshot['candidates'])
            env.step(snapshot['decision_id'], snapshot['candidates'].index(reply['decision']))
        return reply

    def test_ping_and_unknown_op(self):
        self.assertEqual(self.worker.ask({'op': 'ping'}), {'ok': True, 'pong': True})
        self.assertFalse(self.worker.ask({'op': 'nope'})['ok'])

    def test_easy_level_plays_legal_moves_through_setup_and_round_one(self):
        self.play(40, 'easy')

    def test_normal_level_searches_and_respects_the_cap(self):
        reply = self.play(30, 'normal')
        self.assertLess(reply['seconds'], 30)

    def test_hard_level_plays_legal_moves(self):
        reply = self.play(25, 'hard')
        self.assertLess(reply['seconds'], 30)

    def test_wrong_seat_is_reported_not_played(self):
        snapshot = json.loads(Environment(SEED, 2000).snapshot_json())
        reply = self.worker.ask({'op': 'choose', 'room': 'x', 'state': snapshot['state'],
                                 'player': (snapshot['player']+1) % 4})
        self.assertFalse(reply['ok'])


if __name__ == '__main__':
    unittest.main()
