"""A trained policy checkpoint in a teacher seat (HANDOFF E128 step 2): teacher_ab spec
{"source": "gaia-rl/baseline-teacher-20260917", "factory": "policy_teacher:make",
 "kwargs": {"checkpoint": "<dir>", "capacity": 4096}} (capacity is optional).
The checkpoint directory (inference.pt + metadata.json from tools/bc_train.py or gaia_rl.training) is read by
gaia_rl.evaluation.OfflinePolicy: one forward pass per decision, argmax over the legal candidates, no search.
The checkpoint's metadata sets the encoding and the width; an encoding 4 checkpoint previews the state after every
candidate on the bound environment (no step, no search).
A relative checkpoint path is resolved against gaia-rl/ (runs/ is not in git: the checkpoint must exist on the
machine that plays)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PolicyTeacher:
    def __init__(self, checkpoint, capacity=None):
        from gaia_rl.evaluation import OfflinePolicy
        path = Path(checkpoint)
        self.checkpoint = path if path.is_absolute() else ROOT/path
        self.policy = OfflinePolicy(self.checkpoint, capacity)
        self.last_audit = None
        self.env = None

    def bind(self, env):
        self.env = env

    def choose(self, snapshot):
        decision, index = self.policy.choose(snapshot, self.env)
        # The decision log reads these keys (teacher_ab.worker): no plans were compared, nothing was searched.
        self.last_audit = {'decision_id': decision, 'selected': 'policy', 'plans': [], 'unsearched_comparisons': 0}
        return decision, index

    def observe(self, before, index, after):
        pass


def make(seed, target_seconds=None, maximum_seconds=None, adaptive_clock=None, checkpoint=None, capacity=None, **_):
    """teacher_ab factory: the clock arguments are accepted and ignored (a forward pass has no budget).

    kwargs.capacity: the candidate capacity at run time (default: the checkpoint's own, 2048 for the BC checkpoints).
    A game decision can list more candidates than 2048 (2,257 in 119, HANDOFF E165); 4096 scores it with the same
    weights instead of stopping the game with EncodingError."""
    if not checkpoint:
        raise ValueError('policy_teacher: kwargs.checkpoint (checkpoint directory) is required')
    return PolicyTeacher(checkpoint, capacity)
