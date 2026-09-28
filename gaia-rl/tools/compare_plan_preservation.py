"""Compare two short native continuations from a pinned fixture, not a new game."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import time

from gaia_rl import Environment
from gaia_rl.versions import runtime_versions
from faction_teachers.guidance import comparison_variants, preserves_plan
from four_factions.preparation import (Policies, SearchExpired, goal_from_dict,
                                      rollout, select_goal)
from four_factions.provenance import hashes
from four_factions.preparation_cache import PolicyCache


def compare(fixture, seconds):
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Positive finite seconds required')
    sources = hashes()
    env = Environment(fixture['seed'], 2000)
    for index in fixture['prefix']:
        snapshot = json.loads(env.snapshot_json())
        env.step(snapshot['decision_id'], index)
    snapshot = json.loads(env.snapshot_json())
    canonical = json.dumps(snapshot, sort_keys=True, separators=(',', ':'))
    if hashlib.sha256(canonical.encode()).hexdigest() != fixture['snapshot_sha256']:
        raise ValueError('Fixture state changed; do not silently compare a different position')
    comparisons = []
    for goal in comparison_variants(goal_from_dict(fixture['goal'])):
        policies = Policies(shared_factions=True, faction_tech_plans=True, cache=PolicyCache())
        start = time.monotonic()
        deadline = start + seconds
        first = None
        try:
            scores = policies.rank(env, snapshot)
            first = select_goal(env, snapshot, scores, goal, policies, deadline)
            result = (rollout(env, snapshot, first, goal, policies, deadline) if first is not None
                      else dict(complete=False, value=None, reason='no eligible first action'))
        except SearchExpired:
            result = dict(complete=False, value=None, reason='deadline; unknown, not inferior')
        comparisons.append(dict(mode='preserve' if preserves_plan(goal) else 'existing',
            goal_spec=asdict(goal), first=first,
            first_action=snapshot['candidates'][first]['action'] if first is not None else None,
            elapsed_seconds=time.monotonic() - start, **result))
        if json.loads(env.snapshot_json()) != snapshot:
            raise AssertionError('Comparison mutated the shared root')
    if hashes() != sources:
        raise ValueError('Sources changed during comparison')
    return dict(scope='One pinned state, two native horizon comparisons; not a strength benchmark',
                seed=fixture['seed'], decision_id=snapshot['decision_id'],
                root_sha256=fixture['snapshot_sha256'], seconds_per_comparison=seconds,
                horizon_incomes=2, decision_limit=192, versions=runtime_versions(),
                source_hashes=sources, comparisons=comparisons, root_unchanged=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--seconds', type=float, default=60)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.fixture.read_text())['fixture'], args.seconds),
                     ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
