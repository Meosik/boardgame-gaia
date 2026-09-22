"""Observed root decisions only; simulated branches are not additional game turns."""


def summarize_candidate_limits(rows):
    known, unknown, hits = 0, 0, 0
    reasons = {}
    for row in rows:
        diagnostics = row['audit'].get('candidate_generation')
        if diagnostics is None:
            unknown += 1
            continue
        count = diagnostics['federation_limit_hits']
        labels = diagnostics['federation_limit_reasons']
        if (type(count) is not int or count < 0 or not isinstance(labels, list)
                or len(labels) != count or any(not isinstance(label, str) for label in labels)):
            raise ValueError('Invalid native candidate-generation diagnostics')
        known += 1
        hits += count
        for label in labels:
            reasons[label] = reasons.get(label, 0)+1
    return {'scope': 'recorded root decisions; excludes simulated branch generation',
            'audited_decisions': known, 'unknown_decisions': unknown,
            'federation_limit_hits': hits, 'federation_limit_reasons': reasons}
