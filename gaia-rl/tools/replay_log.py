"""Decision deltas plus exact, state-verified income events (never reward signals)."""
from replay_income import recover_income


def add_decision_log(replay, *, income_by_frame=None):
    events = []
    frames = replay['frames']
    # Verify everything before modifying the input; a rule mismatch must not invent income.
    if income_by_frame is None:
        income_by_frame = recover_income(frames)
    frames[0]['event_end'] = 0
    for index, (before, after) in enumerate(zip(frames, frames[1:]), 1):
        changes = []
        for old, new in zip(before['state']['players'], after['state']['players']):
            delta = {key: new['resources'][key] - old['resources'][key]
                     for key in ('ore', 'credits', 'knowledge', 'qic')}
            delta['vp'] = new['vp'] - old['vp']
            delta = {key: value for key, value in delta.items() if value}
            if delta:
                changes.append({'player': new['player_id'], 'delta': delta})
        events.append({'ReplayDecision': {
            'player': after['player'], 'step': after['decision_id'],
            'round': before['state']['round'], 'action': after['action'],
            'net_changes': changes,
        }})
        events.extend(income_by_frame.get(index, []))
        after['event_end'] = len(events)
    replay['events'] = events
    replay['metadata']['log_source'] = ('recorded_decisions_and_state_deltas_with_verified_income'
                                      if income_by_frame else 'recorded_decisions_and_state_deltas')
    return replay
