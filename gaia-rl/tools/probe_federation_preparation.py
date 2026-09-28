"""Compare the two existing pilot continuations at a saved R5 state, not a new game."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from compare_plan_preservation import compare
from diagnose_plan_completion import federation_status
from current_actions.conservation import blocked
from faction_teachers.guidance import preserves_plan
from four_factions import preparation as prep


def probe(fixture, seconds):
    observations = []
    original = prep.select_goal

    def observe(env, snapshot, scores, goal, policies, deadline, **kwargs):
        index = original(env, snapshot, scores, goal, policies, deadline, **kwargs)
        if (preserves_plan(goal) and goal.target == 'Ambas' and len(goal.steps) == 1
                and goal.steps[0].family == 'federation-race'
                and 'ActionPhase' in snapshot['state']['phase']):
            target = goal.steps[0].coord
            status = federation_status(snapshot, snapshot['player'], target)
            status['policy_eligible_target_federations'] = sum(
                c['action']['type'] == 'FormFederation' and target in c['action']['hexes'] and not blocked(scores[i])
                for i, c in enumerate(snapshot['candidates']))
            status['selected_action'] = snapshot['candidates'][index]['action'] if index is not None else None
            observations.append(status)
        return index

    with patch.object(prep, 'select_goal', side_effect=observe):
        result = compare(fixture, seconds)
    result['power_preparation_observations'] = observations
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--seconds', type=float, default=60)
    args = parser.parse_args()
    result = probe(json.loads(args.fixture.read_text())['fixture'], args.seconds)
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['fixture_sha256'] = hashlib.sha256(args.fixture.read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
