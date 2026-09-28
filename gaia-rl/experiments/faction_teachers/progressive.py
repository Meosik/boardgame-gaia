"""Matched-depth search for the opt-in technology pilot; no new action values."""
from dataclasses import asdict
import time

from current_actions.conservation import identity
from faction_teachers.guidance import PILOT_SOURCE

DEPTHS = (1, 2, 4, 8, 16, 32, 64, 128, None)


def progressive_search(env, snapshot, scores, tasks, control, policies, result,
                       publish_depth, publish_current, *, soft_deadline,
                       hard_deadline, allocation=None, capture_r1=False):
    # Resolve at call time so the worker's diagnostic/test instrumentation also
    # observes progressive comparisons, rather than a private imported alias.
    from four_factions import preparation as prep

    unique = {identity(asdict(goal)): goal for goal in [control, *tasks]}
    tasks = list(unique.values())
    control_id = tasks.index(control)
    order = [control_id] + [i for i, g in enumerate(tasks)
                            if i != control_id and PILOT_SOURCE in g.sources]
    order += [i for i in range(len(tasks)) if i not in order]
    incumbent_id = control_id
    first_actions, full_results = {}, {}
    result.update(comparison_stages=[], planned_comparisons=len(tasks),
                  unsearched_comparisons=len(tasks), extended_reason=None,
                  extension_policy='finish-current-comparison-only')

    try:
        for depth in DEPTHS:
            label = depth if depth is not None else 'two-incomes'
            rows = []
            stage = dict(depth=label, plans=rows, published=False,
                         required_anchors=sorted({control_id, incumbent_id}))
            result['comparison_stages'].append(stage)
            anchors = set(stage['required_anchors'])
            for task_id in order:
                allocated = min(hard_deadline, allocation()) if allocation is not None else soft_deadline
                if time.monotonic() >= allocated:
                    result['stop_reason'] = 'soft time allocation used'
                    publish_current()
                    return result
                prep.check_time(hard_deadline)
                goal = tasks[task_id]
                if task_id not in first_actions:
                    first_actions[task_id] = (goal.first if goal.first is not None else
                        prep.select_goal(env, snapshot, scores, goal, policies, hard_deadline))
                first = first_actions[task_id]
                if first is None:
                    comparison = dict(complete=False, value=None, actions=[],
                                      remaining_goal=asdict(goal),
                                      reason='no eligible first action; unknown, not inferior')
                elif task_id in full_results:
                    comparison = full_results[task_id]
                else:
                    comparison = prep.rollout(env, snapshot, first, goal, policies,
                                              hard_deadline, capture_r1=capture_r1,
                                              decision_depth=depth)
                    if comparison['complete'] and (depth is None or comparison.get('full_horizon_reached')):
                        full_results[task_id] = comparison
                if time.monotonic() >= soft_deadline:
                    result['extended_reason'] = 'finish comparison started before soft deadline'
                row = dict(goal=goal.name, goal_spec=asdict(goal), family=goal.family,
                           first=first, task_id=task_id, comparison_depth=label, **comparison)
                rows.append(row)
                if task_id in anchors and not comparison['complete']:
                    result['stop_reason'] = 'anchor incomplete; retain last matched-depth selection'
                    publish_current()
                    return result
                anchors.discard(task_id)
                if not anchors:
                    # Never compare a fresh deep value to a stale shallow one.
                    result['unsearched_comparisons'] = len(tasks)-len(rows)
                    selected = publish_depth(list(rows), label)
                    incumbent_id = selected['task_id']
                    stage['published'] = True
                    stage['selected_task_id'] = incumbent_id
                else:
                    publish_current()  # Progress only; active-depth plans stay intact.
            stage['coverage_complete'] = all(row['complete'] for row in rows)
            if len(full_results) == len(tasks) or depth is None:
                result['coverage_complete'] = len(full_results) == len(tasks)
                result['stop_reason'] = 'full horizon comparisons finished'
                break
            values = {row['task_id']: row['value'] for row in rows if row['complete']}
            anchors_order = list(dict.fromkeys([incumbent_id, control_id]))
            order = anchors_order + sorted((i for i in range(len(tasks)) if i not in anchors_order),
                                           key=lambda i: (-values.get(i, float('-inf')), i))
    except prep.SearchExpired:
        result['stop_reason'] = 'deadline; partially evaluated route remains unknown'
        result['extended_reason'] = 'in-progress comparison reached hard deadline'
    publish_current()
    return result
