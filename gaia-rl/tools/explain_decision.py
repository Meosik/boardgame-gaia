"""Why did the teacher play that? Rebuild one decision of a lab/teacher_ab game and show it.

Replays the recorded game up to decision STEP (the frame number in the replay viewer), then
asks that seat's teacher (the A or B spec from the run's manifest) to choose again and prints:
the move actually played, the move chosen now, the root ranking (one-step scores with the
teacher's reasons) and each compared plan with its forecast value.

The teacher starts without the game's earlier plan memory, so a remembered plan can make the
recorded move differ from the one chosen here; the output says when they differ.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools \\
    .venv/bin/python tools/explain_decision.py ~/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-004/game-0-A01 \\
    --step 57 [--top 8] [--spec tools/teacher-a-....json] [--comparisons N]
"""
import argparse
import gzip
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def short(action, limit=110):
    if not isinstance(action, dict):
        return str(action)[:limit]
    kind = action.get('type', '?')
    rest = {k: v for k, v in action.items() if k != 'type' and v not in (None, [], {})}
    text = f'{kind} {json.dumps(rest, ensure_ascii=False, separators=(",", ":"))}' if rest else kind
    return text if len(text) <= limit else text[:limit-1]+'…'


def load_spec(game_dir, arm, override):
    if override:
        return json.loads(Path(override).read_text())
    manifest = json.loads((game_dir.parents[1]/'manifest.json').read_text())
    return manifest['teachers'][arm]


def rebuild(game_dir, step, teacher):
    """Replay to STEP with the teacher watching every earlier move (it needs the full prefix)."""
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    if not 0 <= step < len(rows):
        raise SystemExit(f'--step must be 0..{len(rows)-1}')
    env = Environment(result['seed'], 2000)
    snapshot = json.loads(env.snapshot_json())
    teacher.bind(env)
    for row in rows[:step]:
        before = snapshot
        env.step(row['decision_id'], row['index'])
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, row['index'], snapshot)
    if snapshot['decision_id'] != rows[step]['decision_id']:
        raise SystemExit('replay diverged from the recorded game')
    return result, snapshot, rows[step]['index']


def actor_at(game_dir, step):
    """(acting seat at STEP, seed, A seats) from an engine-only replay."""
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        for i, line in enumerate(f):
            if i == step:
                break
            row = json.loads(line)
            env.step(row['decision_id'], row['index'])
    return json.loads(env.snapshot_json())['player'], result['seed'], result['a_seats']


def explain(game_dir, step, top=8, spec_path=None, comparisons=None):
    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    # The teacher must watch from the first move, so find the seat acting at STEP first
    # (engine only), then build that arm's teacher and replay with it watching.
    actor, seed, a_seats = actor_at(game_dir, step)
    arm = 'A' if actor in a_seats else 'B'
    spec = load_spec(game_dir, arm, spec_path)
    budget_teacher.install(spec.get('comparisons', 2) if comparisons is None else comparisons)
    budget_teacher.set_horizon(spec.get('horizon_incomes', 1))
    module, _, name = spec['factory'].partition(':')
    teacher = getattr(importlib.import_module(module), name)(seed, **spec.get('kwargs', {}))
    result, snapshot, recorded = rebuild(game_dir, step, teacher)
    _, chosen = teacher.choose(snapshot)
    audit = teacher.last_audit or {}
    scores = audit.get('scores') or getattr(teacher, 'last_scores', None) or []
    candidates = snapshot['candidates']
    state = snapshot['state']
    player = state['players'][actor]
    lines = [f"seed {result['seed']} · 결정 {step} · {state['round']}라운드 · 좌석 {actor} {player['faction']} "
             f"({arm}팔, {Path(spec_path).stem if spec_path else spec.get('description', spec['factory'])[:60]})",
             f"VP {player['vp']} · 후보 {len(candidates)}개",
             f"실제로 둔 수: [{recorded}] {short(candidates[recorded]['action'])}",
             f"지금 다시 고른 수: [{chosen}] {short(candidates[chosen]['action'])}"
             + ('' if chosen == recorded else '  ← 다름 (실제 판의 계획 기억이 없어서일 수 있음)'),
             '', f'기본 순위 (한 수 앞 점수, 상위 {top}개)']
    ranked = sorted(range(len(scores)), key=lambda i: (-scores[i][0], i))[:top] if scores else []
    for i in ranked:
        mark = ('★' if i == recorded else ' ') + ('◆' if i == chosen else ' ')
        value, reason = scores[i][0], scores[i][1] if len(scores[i]) > 1 else ''
        lines.append(f'{mark}[{i}] {value:8.2f}  {short(candidates[i]["action"])}')
        if reason:
            lines.append(f'            └ {str(reason)[:120]}')
    for index, mark, label in ((recorded, '★ ', '실제로 둔 수'), (chosen, ' ◆', '지금 다시 고른 수')):
        if scores and index not in ranked:
            lines.append(f"{mark}[{index}] {scores[index][0]:8.2f}  {short(candidates[index]['action'])}  ({label}, 순위 밖)")
    plans = audit.get('plans') or []
    if plans:
        lines += ['', f"비교한 계획 {len(plans)}개 (선택: {audit.get('selected')})"]
        for plan in plans:
            first = plan.get('first')
            what = short(candidates[first]['action'], 70) if isinstance(first, int) and first < len(candidates) else '?'
            value = plan.get('value')
            lines.append(f"  {plan.get('goal', '?'):<22} {'' if value is None else f'{value:8.2f}'}  "
                         f"{'완료' if plan.get('complete') else '미완'}  첫 수 [{first}] {what}")
    lines += ['', '★ 실제로 둔 수  ◆ 지금 다시 고른 수']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game_dir', type=Path)
    parser.add_argument('--step', type=int, required=True, help='Decision number (the replay viewer frame)')
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--spec', help='Teacher spec to use instead of the run manifest')
    parser.add_argument('--comparisons', type=int, help='Override the spec comparison budget')
    args = parser.parse_args()
    print(explain(args.game_dir.expanduser(), args.step, args.top, args.spec, args.comparisons))


if __name__ == '__main__':
    main()
