"""Read saved pilot outcomes without running the engine or a policy search."""
import argparse
import json
from pathlib import Path


def summarize(rows):
    result = {}
    selected_decisions = {}
    for row in rows:
        audit = row['audit']
        selected = audit.get('selected', '').split(' via ', 1)[-1]
        selected_index = audit.get('selected_index', audit.get('index'))
        for plan in audit.get('plans', []):
            initial = plan.get('goal_spec', {})
            if 'faction-tech-pilot' not in initial.get('sources', []):
                continue
            faction = initial['target']
            if faction not in result:
                result[faction] = dict(evaluated_candidates=0,
                    completed_horizon_comparisons=0, goal_acquired_in_forecast=0,
                    selected_decisions=0, cancelled_evaluated_candidates=0,
                    unknown_outcomes=0, candidate_audit=[])
                selected_decisions[faction] = set()
            metrics = result[faction]
            remaining = plan.get('remaining_goal')
            # Cancellation is recorded during rollout, not on the initial proposal.
            cancelled = remaining.get('payoff') == 'cancelled' if remaining is not None else None
            acquired = plan.get('goal_acquired')
            chosen = (plan['goal'] == selected and selected_index is not None
                      and plan.get('first') == selected_index)
            metrics['evaluated_candidates'] += 1
            metrics['completed_horizon_comparisons'] += bool(plan.get('complete'))
            metrics['goal_acquired_in_forecast'] += acquired is True
            metrics['cancelled_evaluated_candidates'] += cancelled is True
            metrics['unknown_outcomes'] += cancelled is None or acquired is None
            if chosen:
                selected_decisions[faction].add(row['decision_id'])
            metrics['candidate_audit'].append(dict(step=row['decision_id'],
                goal=plan['goal'], comparison_complete=bool(plan.get('complete')),
                goal_acquired_in_forecast=acquired, selected=chosen, cancelled=cancelled))
    for faction, metrics in result.items():
        metrics['selected_decisions'] = len(selected_decisions[faction])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('audit', type=Path, help='Saved teacher-audit.jsonl (read only)')
    args = parser.parse_args()
    with args.audit.open() as stream:
        result = summarize(json.loads(line) for line in stream if line.strip())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
