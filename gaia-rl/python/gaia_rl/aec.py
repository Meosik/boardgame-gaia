"""Turn-taking adapter; the engine, not seat rotation, chooses every decision owner."""
import json
import copy
import operator
from typing import Protocol

import numpy as np
from gymnasium import spaces
from pettingzoo import AECEnv

from ._native import Environment


class ObservationEncoder(Protocol):
    observation_space: spaces.Space
    candidate_capacity: int

    def encode(self, snapshot: dict, player: int) -> dict: ...


class CandidateCapacityError(RuntimeError):
    """Increase the declared capacity; never silently discard legal decisions."""


class GaiaAEC(AECEnv):
    metadata = {"name": "gaia_lost_fleet_v1", "render_modes": [], "is_parallelizable": False}
    possible_agents = [f"player_{player}" for player in range(4)]

    def __init__(self, encoder: ObservationEncoder, *, max_steps: int = 10_000):
        super().__init__()
        if max_steps <= 0 or encoder.candidate_capacity <= 0:
            raise ValueError("max_steps and candidate_capacity must be positive")
        self.encoder = encoder
        self.max_steps = max_steps
        self._action_space = spaces.Discrete(encoder.candidate_capacity)
        self._native = None
        self._snapshot = None
        self._seed_rng = np.random.default_rng()
        self._resume_rng_state = None
        self.agents = []

    def observation_space(self, agent):
        return self.encoder.observation_space

    def action_space(self, agent):
        return self._action_space

    @property
    def snapshot(self) -> dict:
        """Return an independent copy so diagnostics cannot mutate the decision cache."""
        if self._snapshot is None:
            raise RuntimeError("reset() is required")
        return json.loads(json.dumps(self._snapshot))

    def _read_snapshot(self):
        self._snapshot = json.loads(self._native.snapshot_json())
        count = len(self._snapshot["candidates"])
        if count > self.encoder.candidate_capacity:
            raise CandidateCapacityError(
                f"{count} legal candidates exceed capacity {self.encoder.candidate_capacity}; "
                "the episode must be discarded, not truncated into a training sample"
            )

    def restore_episode_rng(self, state):
        """Resume with the next fresh episode, even if RLlib supplies its initial seed."""
        self._resume_rng_state = copy.deepcopy(state)

    def reset(self, seed=None, options=None):
        # Reserved by the AEC API; this environment has no optional setup overrides.
        if self._resume_rng_state is not None:
            self._seed_rng.bit_generator.state = self._resume_rng_state
            self._resume_rng_state = None
        elif seed is not None:
            self._seed_rng = np.random.default_rng(seed)
        episode_seed = str(int(self._seed_rng.integers(0, 2**63)))
        self._native = Environment(episode_seed, self.max_steps)
        self._read_snapshot()
        self.agents = self.possible_agents[:]
        self.rewards = dict.fromkeys(self.agents, 0.0)
        self._cumulative_rewards = dict.fromkeys(self.agents, 0.0)
        self.terminations = dict.fromkeys(self.agents, False)
        self.truncations = dict.fromkeys(self.agents, False)
        self.infos = {agent: {} for agent in self.agents}
        self._skip_agent_selection = None
        self.agent_selection = f"player_{self._snapshot['player']}"
        self._update_infos()

    def _update_infos(self):
        for agent in self.agents:
            self.infos[agent] = {
                "decision_id": self._snapshot["decision_id"],
                "engine_build_id": self._snapshot["engine_build_id"],
                "steps": self._snapshot["steps"],
            }

    def observe(self, agent):
        if self._snapshot is None:
            raise RuntimeError("reset() is required")
        player = self.possible_agents.index(agent)
        observation = dict(self.encoder.encode(self._snapshot, player))
        mask = np.zeros(self.encoder.candidate_capacity, dtype=np.int8)
        if (agent == self.agent_selection and agent in self.agents
                and not self.terminations[agent] and not self.truncations[agent]):
            mask[:len(self._snapshot["candidates"])] = 1
        observation["action_mask"] = mask
        return observation

    def step(self, action):
        if not self.agents:
            raise RuntimeError("reset() is required or the episode has already ended")
        actor = self.agent_selection
        if self.terminations[actor] or self.truncations[actor]:
            self._was_dead_step(action)
            return
        # Reject invalid input before touching either rewards or the native environment.
        if isinstance(action, (bool, np.bool_)):
            raise ValueError("action must be a candidate index")
        try:
            index = operator.index(action)
        except TypeError as error:
            raise ValueError("action must be a candidate index") from error
        if not 0 <= index < len(self._snapshot["candidates"]):
            raise ValueError("action is masked or outside the candidate list")
        self._native.step(self._snapshot["decision_id"], index)
        self._read_snapshot()
        self._cumulative_rewards[actor] = 0.0
        self._clear_rewards()
        self._update_infos()
        if self._native.is_terminal():
            scores = self._native.final_scores()
            for player, reward in enumerate(self._native.rewards()):
                agent = self.possible_agents[player]
                self.rewards[agent] = reward
                self.terminations[agent] = True
                self.infos[agent]["final_scores"] = scores
            self._deads_step_first()
        elif self._snapshot["steps"] >= self.max_steps:
            # A safety limit is explicitly nonterminal: never fabricate final VP/rewards.
            for agent in self.agents:
                self.truncations[agent] = True
                self.infos[agent]["truncation_reason"] = "step_limit"
            self._deads_step_first()
        else:
            self.agent_selection = f"player_{self._snapshot['player']}"
        self._accumulate_rewards()
