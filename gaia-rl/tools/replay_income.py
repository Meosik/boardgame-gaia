"""Recover exact income from independently verified saved transitions, not delta guesses."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def income_transitions(frames):
    return [(i, before, after) for i, (before, after) in enumerate(zip(frames, frames[1:]), 1)
            if before['state']['round'] != after['state']['round']
            # Income can be paid before the round number advances (PI ordering / Gaia
            # decisions). The final Pass/starting-booster action starts that transition.
            or (after.get('action') or {}).get('type') in
            ('Pass', 'SelectStartingBooster', 'ChooseIncomeOrder')]


def recover_income(frames):
    transitions = income_transitions(frames)
    if not transitions:
        return {}
    binary = Path(os.environ.get('GAIA_REPLAY_INCOME_BIN', ROOT/'target/release/examples/replay_income'))
    if not binary.is_file():
        raise RuntimeError('Build income recovery first: cargo build -p gaia-engine --release --example replay_income')
    requests = []
    for _, before, after in transitions:
        # Offline frames omit the unused server event log, not game state.
        requests.append({'before': {**before['state'], 'event_log': []},
                         'after': {**after['state'], 'event_log': []},
                         'player': after['player'], 'action': after['action']})
    result = subprocess.run([str(binary)], input='\n'.join(json.dumps(r) for r in requests)+'\n',
                            text=True, capture_output=True, check=False, timeout=120)
    if result.returncode:
        raise ValueError(f'Income reconstruction rejected; original replay preserved: {result.stderr.strip()}')
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    if len(rows) != len(transitions):
        raise ValueError('Incomplete income reconstruction')
    return {i: events for (i, _, _), events in zip(transitions, rows) if events}
