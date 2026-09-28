"""Inspect a saved pilot continuation and one full-search decision; no game edits."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from gaia_rl import Environment
from faction_teachers.clock import AdaptiveClock
from faction_teachers.guidance import comparison_variants, preserves_plan
from faction_teachers.teacher import SharedTeacher
from federation.teacher import power, minimum
from four_factions import preparation as prep
from four_factions.preparation_cache import PolicyCache
from four_factions.provenance import hashes


WORKER_TRACE = '''import json, sys, time
from four_factions import preparation as prep
from faction_teachers import guidance
from four_factions.timed import worker
def emit(event, **data):
    with open(sys.argv[2], 'a') as stream:
        stream.write(json.dumps(dict(event=event, time=time.monotonic(), **data)) + '\\n')
original_variants, original_rollout = guidance.comparison_variants, prep.rollout
def variants(goal):
    result = original_variants(goal)
    if guidance.PILOT_SOURCE in goal.sources:
        emit('pilot_variants_generated', names=[g.name for g in result])
    return result
def rollout(*args, **kwargs):
    emit('comparison_started', goal=args[3].name)
    result = original_rollout(*args, **kwargs)
    emit('comparison_finished', goal=args[3].name, complete=result['complete'], value=result['value'])
    return result
guidance.comparison_variants, prep.rollout = variants, rollout
worker(sys.argv[1])
'''


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def federation_status(snapshot, actor, target):
    player = snapshot['state']['players'][actor]
    if player['faction'] != 'Ambas' or snapshot['player'] != actor:
        raise ValueError('This diagnostic requires an actual Ambas decision')
    used = set(player['federated_hexes'])
    unused = [dict(hex=s['hex'], kind=s['kind'], power=power(player, s['kind']))
              for s in player['structures'] if s['hex'] not in used]
    actions = [c['action'] for c in snapshot['candidates']]
    federations = [a for a in actions if a['type'] == 'FormFederation']
    total = sum(s['power'] for s in unused)
    return dict(decision_id=snapshot['decision_id'], round=snapshot['state']['round'],
                resources=player['resources'], unfederated_buildings=unused,
                total_unfederated_power=total, required_power=minimum(player),
                power_deficit=max(0, minimum(player)-total),
                legal_federations=len(federations),
                legal_target_federations=sum(target in a['hexes'] for a in federations),
                legal_plain_builds=sum(a['type'] == 'Build' for a in actions),
                candidate_generation=snapshot.get('candidate_generation'))


def inherited_clock(checkpoint, through_decision):
    # Do not reset long-think allowances or borrow receipts from later play.
    spent = checkpoint['memory']['_clock']['spent']
    return AdaptiveClock(state={'spent': [entry for entry in spent if entry[1] <= through_decision]})


def diagnose(fixture, previous, checkpoint):
    sources = hashes()
    if sources != previous['source_hashes']:
        raise ValueError('Pinned continuation sources changed')
    env = Environment(fixture['seed'], 2000)
    for index in fixture['prefix']:
        snapshot = json.loads(env.snapshot_json())
        env.step(snapshot['decision_id'], index)
    root = json.loads(env.snapshot_json())
    if digest(root) != fixture['snapshot_sha256']:
        raise ValueError('Fixture root changed')
    actor = root['player']
    goal = comparison_variants(prep.goal_from_dict(fixture['goal']))[1]
    policies = prep.Policies(shared_factions=True, faction_tech_plans=True, cache=PolicyCache())
    original = prep.select_goal
    observations = []

    def observe(branch, snapshot, scores, remaining, policies, deadline, **kwargs):
        index = original(branch, snapshot, scores, remaining, policies, deadline, **kwargs)
        if (preserves_plan(remaining) and len(remaining.steps) == 1
                and remaining.steps[0].family == 'federation-race'
                and 'ActionPhase' in snapshot['state']['phase']):
            status = federation_status(snapshot, actor, remaining.steps[0].coord)
            status['selected_action'] = snapshot['candidates'][index]['action'] if index is not None else None
            status['remaining_goal'] = asdict(remaining)
            observations.append(status)
        return index

    deadline = time.monotonic() + previous['seconds_per_comparison']
    scores = policies.rank(env, root)
    first = prep.select_goal(env, root, scores, goal, policies, deadline)
    with patch.object(prep, 'select_goal', side_effect=observe):
        continuation = prep.rollout(env, root, first, goal, policies, deadline)
    expected = next(c for c in previous['comparisons'] if c['mode'] == 'preserve')
    for key in ('complete', 'value', 'goal_acquired', 'actions', 'remaining_goal', 'end_round', 'end_player'):
        if digest(continuation.get(key)) != digest(expected.get(key)):
            raise ValueError(f'Pinned continuation did not reproduce: {key}')

    clock = inherited_clock(checkpoint, 67)
    teacher = SharedTeacher(fixture['seed'], prefix=fixture['prefix'],
                            adaptive_clock=clock, faction_tech_plans=True).bind(env)
    remaining_before = clock.remaining(actor)
    teacher.memory = {'_clock': clock.state()}
    # Observe the real supervised worker without changing its candidates,
    # allocation, rankings or stopping policy. Killed comparisons have no finish event.
    popen = subprocess.Popen
    with tempfile.TemporaryDirectory(prefix='gaia-plan-probe-') as directory:
        trace_path = Path(directory) / 'worker-events.jsonl'
        def launch(command, **kwargs):
            return popen([sys.executable, '-c', WORKER_TRACE, command[-1], str(trace_path)], **kwargs)
        with patch('four_factions.timed.subprocess.Popen', side_effect=launch):
            _, index = teacher.choose(root)
        events = [json.loads(line) for line in trace_path.read_text().splitlines()] if trace_path.exists() else []
    audit = teacher.last_audit
    goals = prep.goals_for(root, shared_factions=True, faction_tech_plans=True)
    pilot = [g for g in goals if 'faction-tech-pilot' in g.sources]
    generated = [variant.name for g in pilot for variant in comparison_variants(g)]
    if hashes() != sources or json.loads(env.snapshot_json()) != root:
        raise ValueError('Sources or root changed during diagnosis')
    return dict(scope='Pinned hypothetical branch plus one full-search decision, not a whole game',
                root_sha256=fixture['snapshot_sha256'], source_hashes=sources,
                continuation_reproduced=True, post_swap_observations=observations,
                end_round=continuation['end_round'], end_player=continuation['end_player'],
                full_search_context=dict(clock_inherited_through_recorded_decision=67,
                    long_thinks_remaining_before=remaining_before,
                    memory='No saved plan or conversion commitments, matching isolated branch comparison. '
                           'Clock inherited through ancestor decision 67; not an exact historical controller replay.',
                    reconstructed_pilot_names=generated, chosen_action=root['candidates'][index]['action'],
                    observation='Worker trace adds logging overhead within the unchanged clock limit.'),
                worker_events=events, full_search_audit=audit, root_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('checkpoint', type=Path)
    args = parser.parse_args()
    result = diagnose(json.loads(args.fixture.read_text())['fixture'],
                      json.loads(args.comparison.read_text()), json.loads(args.checkpoint.read_text()))
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
