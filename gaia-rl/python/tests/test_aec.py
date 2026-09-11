"""Adapter contract tests. CounterEncoder is deliberately not a training encoder."""
import unittest
from unittest.mock import patch

import numpy as np
from gymnasium import spaces
from pettingzoo.test import api_test

from gaia_rl.aec import GaiaAEC, CandidateCapacityError


class CounterEncoder:
    candidate_capacity = 2048
    observation_space = spaces.Dict({
        "observation": spaces.Box(0, 10000, (2,), dtype=np.float32),
        "action_mask": spaces.MultiBinary(candidate_capacity),
    })

    def encode(self, snapshot, player):
        return {"observation": np.array([snapshot["steps"], player], dtype=np.float32)}


class AdapterTests(unittest.TestCase):
    def test_api(self):
        api_test(GaiaAEC(CounterEncoder(), max_steps=12), num_cycles=15)

    def test_seed_mask_and_atomic_rejection(self):
        env = GaiaAEC(CounterEncoder())
        env.reset(seed=91)
        before = env.snapshot
        actor = env.agent_selection
        self.assertEqual(env.observe(actor)["action_mask"].sum(), len(before["candidates"]))
        for other in env.agents:
            if other != actor:
                self.assertEqual(env.observe(other)["action_mask"].sum(), 0)
        for invalid in [-1, len(before["candidates"]), True, 0.1, None]:
            with self.assertRaises(ValueError):
                env.step(invalid)
            self.assertEqual(before, env.snapshot)
            self.assertEqual(env.last()[1], 0)
        env.reset(seed=91)
        self.assertEqual(before, env.snapshot)
        env.step(np.int64(0))
        self.assertEqual(env.agent_selection, f"player_{env.snapshot['player']}")

    def test_limit_drains_all_seats_without_terminal_rewards(self):
        env = GaiaAEC(CounterEncoder(), max_steps=1)
        env.reset(seed=4)
        env.step(0)
        seen = []
        for agent in env.agent_iter():
            observation, reward, terminal, truncated, info = env.last()
            seen.append(agent)
            self.assertFalse(terminal)
            self.assertTrue(truncated)
            self.assertEqual(reward, 0)
            self.assertEqual(observation["action_mask"].sum(), 0)
            self.assertEqual(info["truncation_reason"], "step_limit")
            self.assertNotIn("final_scores", info)
            env.step(None)
        self.assertEqual(set(seen), set(env.possible_agents))

    def test_capacity_never_prunes(self):
        encoder = CounterEncoder()
        encoder.candidate_capacity = 1
        with self.assertRaises(CandidateCapacityError):
            GaiaAEC(encoder).reset(seed=91)

    def test_same_actor_and_terminal_reward_delivery(self):
        # The adapter must honor engine ownership, including repeated free actions.
        env = GaiaAEC(CounterEncoder())
        env.reset(seed=4)
        actor = env.agent_selection
        with patch.object(env, "_read_snapshot"):
            with patch.object(env, "_native") as native:
                native.is_terminal.return_value = False
                env.step(0)
                self.assertEqual(env.agent_selection, actor)
                native.is_terminal.return_value = True
                native.rewards.return_value = [0.3, 0.1, -0.1, -0.3]
                native.final_scores.return_value = [(0, 130), (1, 110), (2, 90), (3, 70)]
                env.step(0)
        delivered = {}
        for agent in env.agent_iter():
            _, reward, terminal, truncated, info = env.last()
            self.assertTrue(terminal)
            self.assertFalse(truncated)
            self.assertIn("final_scores", info)
            delivered[agent] = reward
            env.step(None)
        self.assertEqual(list(delivered.values()), [0.3, 0.1, -0.1, -0.3])
        self.assertAlmostEqual(sum(delivered.values()), 0)


if __name__ == "__main__":
    unittest.main()

class ResumeSeedTests(unittest.TestCase):
    def test_resume_uses_next_episode_despite_initial_seed(self):
        import copy
        first=GaiaAEC(CounterEncoder());first.reset(seed=14)
        rng=copy.deepcopy(first._seed_rng.bit_generator.state)
        first.reset()
        resumed=GaiaAEC(CounterEncoder());resumed.restore_episode_rng(rng)
        resumed.reset(seed=14)
        self.assertEqual(first.snapshot,resumed.snapshot)
