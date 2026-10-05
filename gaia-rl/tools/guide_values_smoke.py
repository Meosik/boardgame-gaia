"""Smoke check for teacher_patches:guide_values: play a few decisions without comparisons.

Prints, for each decision, the actor, the chosen action and the old/new state value, so
a crash or an absurd value shows before any lab run. Not an A/B; decides nothing.

  cd gaia-rl && .venv/bin/python tools/guide_values_smoke.py geo-quartet-306543 --decisions 60

(Sets GAIA_ENGINE_FIXES_2=1 and the import path itself, like the lab runs.)
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
for path in ('tools', 'baseline-teacher-20260917', 'python'):
    sys.path.insert(0, str(ROOT/path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('seed')
    parser.add_argument('--decisions', type=int, default=60)
    parser.add_argument('--baseline', action='store_true', help='play the live hard teacher instead')
    parser.add_argument('--explain', type=int, nargs='*', default=[],
                        help='decision numbers whose candidates are listed with new/old value deltas')
    parser.add_argument('--rows', type=int, default=12)
    args = parser.parse_args()
    sys.setrecursionlimit(10000)
    import budget_teacher
    budget_teacher.install(0, max_seconds=5)
    import teacher_patches
    from gaia_rl import Environment
    from faction_teachers.clock import AdaptiveClock
    from faction_teachers.profiles import profiles
    clock = AdaptiveClock()
    factory = teacher_patches.geodens_guide if args.baseline else teacher_patches.guide_values
    teacher = factory(args.seed, target_seconds=clock.target_seconds,
                                           maximum_seconds=clock.long_seconds, adaptive_clock=clock,
                                           bgg_openings=True, shared_factions=True)
    env = Environment(args.seed, 4000)
    teacher.bind(env)
    snapshot = json.loads(env.snapshot_json())
    for n in range(args.decisions):
        if not snapshot.get('candidates'):
            break
        actor = snapshot['player']
        state = snapshot['state']
        decision, index = teacher.choose(snapshot)
        action = snapshot['candidates'][index]['action']
        faction = state['players'][actor]['faction']
        home = profiles()[faction].home
        old = teacher_patches._original(state, actor, home=home)
        new = teacher_patches.guide_potential(state, actor, home=home)
        print(f'{n:3d} R{state["round"]} {faction:8s} old {old:7.1f} new {new:7.1f}  '
              f'{action["type"]} {json.dumps({k: v for k, v in action.items() if k != "type"})[:70]}',
              flush=True)
        if n in args.explain:
            base = teacher_patches.guide_potential(state, actor, home=home)
            rows = []
            for i, candidate in enumerate(snapshot['candidates']):
                after = json.loads(env.fork(snapshot['decision_id'], i).snapshot_json())['state']
                rows.append((teacher_patches.guide_potential(after, actor, home=home)-base,
                             teacher_patches._original(after, actor, home=home)-old, candidate['action']))
            for new_delta, old_delta, action in sorted(rows, key=lambda r: -r[0])[:args.rows]:
                print(f'      new {new_delta:+6.1f} old {old_delta:+6.1f}  {json.dumps(action)[:90]}')
        before = snapshot
        env.step(decision, index)
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, index, snapshot)


if __name__ == '__main__':
    main()
