"""Two-faction B policy: one B19-guided leaf utility, no action-type score bonuses."""
import json
import math

from current_actions.conservation import blocked
from current_actions.teacher import CurrentActionTeacher, CurrentContextTeacher
from research_plans.value import endpoint_value


class StateDeltaTeacher(CurrentActionTeacher):
    """Native paid V(after)-V(before); no new prices or learned-value claims.

    Setup retains the control policy so the first experiment changes play, not
    placement. In play, historical scores only order previews: they are neither
    added to the delta nor used to discard candidates. Conservation proofs are
    unchanged. The endpoint now includes conditional B19 expansion opportunities;
    it remains an approximation, not a calibrated VP model or financing solver.
    """

    def rank(self, snapshot):
        if self.env is None or json.loads(self.env.snapshot_json()) != snapshot:
            raise ValueError('State-delta teacher requires its current native snapshot')
        actor = snapshot['player']
        if actor is None or not snapshot['candidates']:
            raise ValueError('No live decision')
        reference = snapshot['state']['players'][actor]
        if reference['faction'] not in ('Xenos', 'HadschHallas'):
            raise ValueError('State-delta experiment is limited to Xenos/HadschHallas')
        if 'Setup' in snapshot['state']['phase']:
            return super().rank(snapshot)

        priors = self.base_rank(snapshot)
        scores = self.apply_conservation(snapshot, priors)
        evaluator = CurrentContextTeacher()
        before = endpoint_value(snapshot['state'], actor, reference, evaluator, guide_tracks=True)
        if not math.isfinite(before):
            raise ValueError('Nonfinite state value')
        order = sorted((i for i, score in enumerate(scores) if not blocked(score)),
                       key=lambda i: (-priors[i][0], i))
        for index in order:
            # Unlike fork(), this does not enumerate the next decision's menu.
            # It still pays all costs and applies the same native transitions.
            after = json.loads(self.env.preview_state_json(snapshot['decision_id'], index))
            value = endpoint_value(after, actor, reference, evaluator, guide_tracks=True)
            delta = value-before
            if not math.isfinite(delta):
                raise ValueError('Nonfinite state delta')
            scores[index] = (delta, f'state-delta: after={value:.6f}; before={before:.6f}; '
                             'same B19-guided endpoint; prior used for preview order only')
        if not order:
            raise ValueError('No eligible state-delta action; never auto-pass')
        self.last_scores = scores
        return scores
