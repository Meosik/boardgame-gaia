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
    def __init__(self, factory=None):
        env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1',
               'PYTHONPATH': os.pathsep.join(str(GAIA_RL/p) for p in ('python', 'baseline-teacher-20260917', 'tools'))}
        if factory:
            env['GAIA_AI_TEACHER'] = factory
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


class BoosterTierWorkerTests(unittest.TestCase):
    """Lab 126 (HANDOFF E204): budget_teacher.install runs on every request and reset TimedPreparationTeacher.choose,
    so the all_tier factory's booster-tier pick was gone from a room's second request on and the worker searched the
    starting-booster pick (up to 120 s) where the lab teacher answers at once."""
    NEW = 'guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier'

    def test_new_factory_keeps_the_booster_tier_pick_after_the_first_request(self):
        env = Environment('quartet-e-88365', 2000)
        snapshot = json.loads(env.snapshot_json())
        for _ in range(60):     # first candidate at every start place: no teacher needed to reach the booster pick
            if snapshot['candidates'][0]['action'].get('type') == 'SelectStartingBooster':
                break
            env.step(snapshot['decision_id'], 0)
            snapshot = json.loads(env.snapshot_json())
        else:
            self.fail('no starting-booster pick reached')
        worker = Worker(self.NEW)
        try:
            for request in range(3):
                reply = worker.ask({'op': 'choose', 'room': 'tier', 'level': 'hard',
                                    'state': snapshot['state'], 'player': snapshot['player']})
                self.assertTrue(reply['ok'], reply)
                self.assertTrue(str(reply['selected']).startswith('booster-tier-'), (request, reply))
                self.assertEqual(reply['completed_comparisons'], 0, (request, reply))
                self.assertLess(reply['seconds'], 5, (request, reply))
        finally:
            worker.close()


class LevelTableTests(unittest.TestCase):
    """User 2026-11-19 (HANDOFF E207): the level budgets are not touched; GAIA_AI_TEACHER only picks the factory."""
    NEW = 'guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier'

    def test_default_keeps_the_deployed_factory(self):
        import ai_worker
        factory = ai_worker.factory_name({})
        self.assertEqual(factory, 'guide_r1_charge3_lf_more_vm_lf_ts_ships')
        self.assertEqual(ai_worker.factory_name({'GAIA_AI_TEACHER': ''}), factory)
        self.assertEqual(ai_worker.factory_name({'GAIA_AI_TEACHER': self.NEW}), self.NEW)

    def test_level_budgets_are_the_deployed_ones(self):
        import ai_worker
        self.assertEqual(ai_worker.LEVELS,
                         {'easy': {'comparisons': 0, 'horizon_incomes': 2, 'max_seconds': None},
                          'normal': {'comparisons': 2, 'horizon_incomes': 1, 'max_seconds': 5},
                          'hard': {'comparisons': 4, 'horizon_incomes': 1, 'max_seconds': 20}})
        self.assertFalse(hasattr(ai_worker, 'FACTORY_LEVELS'))


if __name__ == '__main__':
    unittest.main()
