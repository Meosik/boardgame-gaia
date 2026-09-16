"""Record existing comparisons without changing ranks or treating forecasts as facts."""
from copy import deepcopy
import math

from current_actions.conservation import blocked


def capture_decision(snapshot: dict, scores: list, plans: list, native_preview=None) -> dict:
    if len(scores) != len(snapshot['candidates']) or not all(math.isfinite(v) for v, _ in scores):
        raise ValueError('Audit ranks must match the finite native candidate menu')
    eligible = [i for i, score in enumerate(scores) if not blocked(score)]
    if not eligible:
        raise ValueError('No eligible evaluated action to record')
    actor = snapshot['player']
    return {'schema_version': 1, 'decision_id': snapshot['decision_id'], 'player': actor,
            'faction': snapshot['state']['players'][actor]['faction'],
            'round': snapshot['state']['round'],
            'candidate_generation': deepcopy(snapshot.get('candidate_generation')),
            'selected_index': max(eligible, key=lambda i: (scores[i][0], -i)),
            'candidate_scores': [{'index': i, 'value': value, 'reason': reason,
                                  'eligible': not blocked((value, reason))}
                                 for i, (value, reason) in enumerate(scores)],
            'forecast_audits': deepcopy(plans),
            'native_preview_audit': deepcopy(native_preview),
            'predictions_are_not_observed_outcomes': True}
