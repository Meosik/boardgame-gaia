"""Teacher B uses the frozen A supervisor, candidate planner and search unchanged.

Loaded from a generated sibling source tree; see tools/build_state_teacher.py.
The only active overrides are state evaluation and the explicit conservation arm.
Setup decisions (including their rollouts) retain A's evaluator as well.
"""
import os
from four_factions.timed import TimedPreparationTeacher


class StateTeacher(TimedPreparationTeacher):
    def __init__(self, seed, *, conserve_resources=True, **kwargs):
        super().__init__(seed, bgg_openings=True, shared_factions=True, **kwargs)
        self.conserve_resources = conserve_resources

    def choose(self, snapshot):
        # Inherited subprocesses receive the same root scope; setup rollout leaves
        # must not silently switch to B and thereby redesign initial placement.
        os.environ['GAIA_STATE_EVALUATION'] = '0' if 'Setup' in snapshot['state']['phase'] else '1'
        os.environ['GAIA_CONSERVATION_OFF'] = '0' if self.conserve_resources else '1'
        result = super().choose(snapshot)
        self.last_audit['evaluation_arm'] = 'state-B'
        self.last_audit['conserve_resources'] = self.conserve_resources
        return result
