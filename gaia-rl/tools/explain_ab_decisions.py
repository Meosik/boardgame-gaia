"""Re-run one arm's teacher on a recorded lab A/B game and print why it chose given steps.

The arm's teacher is rebuilt as teacher_ab's worker builds it, every recorded decision is
replayed through it (its own seats are re-chosen so its memory matches the game), and at
the asked steps the root ranking and the completed comparisons are printed.

  GAIA_ENGINE_FIXES_2=1 .venv/bin/python tools/explain_ab_decisions.py \
      ~/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-004/game-0-A01 --arm A --steps 11 13 14
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game')
    parser.add_argument('--arm', choices='AB', required=True)
    parser.add_argument('--steps', type=int, nargs='+', required=True, help='0-based steps (replay frame - 1)')
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--spec', help='Another teacher spec .json to ask instead (what would it choose here?)')
    parser.add_argument('--actions', action='store_true', help="Print the actor's own rollout moves per comparison")
    args = parser.parse_args()
    game = Path(args.game)
    manifest = json.loads((game.parents[1]/'manifest.json').read_text())
    spec, clock = manifest['teachers'][args.arm], dict(manifest['clock'])
    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
    result = json.loads((game/'result.json').read_text())
    rows = [json.loads(line) for line in gzip.open(game/'decisions.jsonl.gz', 'rt')]
    # Lab games are played with the second engine-fix set (HANDOFF 5b).
    os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
    source = TOOLS.parent/'baseline-teacher-20260917'
    sys.path[:0] = [str(source), str(TOOLS), str(TOOLS.parent/'python')]
    os.chdir(source)
    clock.pop('preset', None)
    if clock.pop('fast_copy', False):
        import fast_teacher
        fast_teacher.install()
    from importlib import import_module
    from gaia_rl import Environment
    from faction_teachers.clock import AdaptiveClock
    clock.pop('comparisons', None)
    import budget_teacher
    budget_teacher.install(spec['comparisons'], max_seconds=spec.get('max_seconds'))
    if spec.get('horizon_incomes') is not None:
        budget_teacher.set_horizon(spec['horizon_incomes'])
    adaptive = AdaptiveClock(**clock)
    module, _, attribute = spec['factory'].partition(':')
    teacher = getattr(import_module(module), attribute)(
        result['seed'], target_seconds=adaptive.target_seconds, maximum_seconds=adaptive.long_seconds,
        adaptive_clock=adaptive, **spec['kwargs'])
    env = Environment(result['seed'], 2000)
    teacher.bind(env)
    snapshot = json.loads(env.snapshot_json())
    seats = set(result['a_seats']) if args.arm == 'A' else set(range(4))-set(result['a_seats'])
    last = max(args.steps)
    for row in rows:
        if row['step'] > last:
            break
        if row['seat'] in seats:
            decision, index = teacher.choose(snapshot)
            if row['step'] in args.steps:
                report(snapshot, row, index, teacher.last_audit or {}, args.top, result['factions'], args.actions)
            elif index != row['index']:
                print(f"note: step {row['step']} re-chose {index}, game played {row['index']}", file=sys.stderr)
        before = snapshot
        env.step(row['decision_id'], row['index'])
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, row['index'], snapshot)


def short(action):
    return json.dumps(action, ensure_ascii=False, separators=(',', ':'))[:140]


def report(snapshot, row, index, audit, top, factions, actions=False):
    candidates = snapshot['candidates']
    print(f"\n=== step {row['step']} (frame {row['step']+1}) seat {row['seat']} {factions[row['seat']]} "
          f"arm {row['arm']}: played {row['index']} {short(candidates[row['index']]['action'])}; "
          f"re-chose {index}; selected {audit.get('selected')}")
    scores = audit.get('scores') or []
    order = sorted(range(len(scores)), key=lambda i: -scores[i][0] if isinstance(scores[i], (list, tuple)) else 0)
    print('-- root ranking')
    for i in order[:top]:
        print(f"  [{i}] {short(candidates[i]['action'])}  {json.dumps(scores[i], ensure_ascii=False, default=str)[:400]}")
    print('-- comparisons')
    for plan in audit.get('plans') or []:
        extra = {k: plan[k] for k in ('value', 'complete', 'r1_buildings', 'final_vp', 'vp') if k in plan}
        print(f"  {plan['goal']} first=[{plan['first']}] {short(candidates[plan['first']]['action'])} "
              f"{json.dumps(extra, ensure_ascii=False, default=str)[:400]}")
        if actions:
            for move in plan.get('actions') or []:
                r0, r1 = move['resources_before'], move['resources_after']
                delta = {k: r1[k]-r0[k] for k in ('ore', 'credits', 'knowledge', 'qic') if r1[k] != r0[k]}
                print(f"      r{move['round']} {short(move['action'])[:110]} {delta} vp+{move['vp_after']-move['vp_before']}")
            end = plan.get('end_player')
            if end:
                print(f"      end: vp {end['vp']} res { {k: end['resources'][k] for k in ('ore', 'credits', 'knowledge', 'qic')} } "
                      f"buildings {[s['kind'] for s in end['structures']]}")
    if audit.get('bgg_opening'):
        print('-- bgg_opening', json.dumps(audit['bgg_opening'], ensure_ascii=False, default=str)[:600])


if __name__ == '__main__':
    main()
