"""Ask the teacher one recorded decision again, several ways (HANDOFF E268, cycle 130).

The decision is reached like tools/room_handover.py does it: an engine state file (`--state`, e.g. a handover
run's states/round-5.json) and the first K decisions of a game played from it (`--prefix-log`, `--prefix-steps`).
The state's digest is compared with row K of that log, so the answer says whether this is the decision the
logged game faced (same engine build, same position).

Each `--ask LABEL:COMPARISONS:CAP:FRONT` starts a fresh teacher worker (teacher_ab.Worker — the process, patches
and budget of a lab game), lets it watch the prefix and asks it to choose once:
  COMPARISONS  the comparison budget of this ask;
  CAP          the safety cap in seconds, 0 = none (the search runs until the budget is used);
  FRONT        positions in the `--move` list (comma separated, may be empty): the root comparisons of those
               moves are put at the start of the root-N list, in that order. The task order of the search is
               control, goals[0], roots[0], pairs[0], goals[1], roots[1], ... (four_factions.preparation.search,
               teacher_patches.install_plan_menu), so the first such move is the third comparison, the second
               the sixth, the third the ninth. The goals, the pairs and the control are the teacher's own; with
               an empty FRONT the teacher is untouched (its own factory, no wrapper).
Asks without a cap run one after another; the asks with a cap are sent together, so they share the host the
way the games of a lab run do (a capped decision depends on the load).

Every `--move` is an action (JSON, or the part that names it) that must match exactly one legal candidate.
Output: metrics.json in `--output` — the candidates by action type, each move's index and rank in the root
ranking, and per ask the chosen move, the compared plans with their values and the timing.

  cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python \\
      tools/decision_probe.py --state runs/<run>/states/round-5.json \\
      --prefix-log runs/<run>/round-5/move-0/game-0/decisions.jsonl.gz --prefix-steps 5 \\
      --teacher tools/<spec>.json --move '<action json>' --ask asis:4:0: --ask front:9:0:0 --output runs/<name>
"""
import argparse
import gzip
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import teacher_ab

FACTORY_ENV, FRONT_ENV, WATCH_ENV, LOG_ENV = ('GAIA_PROBE_FACTORY', 'GAIA_PROBE_FRONT', 'GAIA_PROBE_WATCH',
                                              'GAIA_PROBE_LOG')


def is_root(goal):
    return str(getattr(goal, 'name', '')).startswith('root-')


def front_first(ordered, front):
    """`ordered` (the comparison order of the root list) with the root goals whose first move is in `front` at
    the start, in the order of `front`. A move with no root goal (the control's move, a blocked one) is skipped;
    anything else keeps its order."""
    by_first = {goal.first: goal for goal in ordered if is_root(goal)}
    lead = [by_first[index] for index in front if index in by_first]
    return lead + [goal for goal in ordered if not any(goal is led for led in lead)]


def root_ranks(roots, watch):
    """{move index: rank} among the eligible root moves. `roots` is the search's root list in score order; it
    leaves out the control's move, which is rank 1, so the first root is rank 2. None = not in the list."""
    position = {goal.first: n for n, goal in enumerate(roots)}
    return {str(index): position[index]+2 if index in position else None for index in watch}


def install_front(front, watch=(), log_path=None):
    """Wrap preparation.interleave_families (outermost): the root-N call gets front_first, every other call
    passes through. Appends one JSON line per root call to log_path: the list length and the watched ranks."""
    import four_factions.preparation as p
    inner = p.interleave_families
    if getattr(inner, '_probe_front', False):
        return

    def interleave_families(items, family):
        ordered = inner(items, family)
        if not (items and all(is_root(goal) for goal in items)):
            return ordered
        if log_path:
            with open(log_path, 'a') as f:
                f.write(json.dumps({'roots': len(items), 'rank': root_ranks(items, watch)})+'\n')
        return front_first(ordered, front)
    for name, value in vars(inner).items():          # the idempotence flags of the wrappers underneath
        if name.startswith('_') and isinstance(value, bool):
            setattr(interleave_families, name, value)
    interleave_families._probe_front = True
    interleave_families.__wrapped__ = inner
    p.interleave_families = interleave_families


def factory(seed, **kwargs):
    """Teacher spec factory `decision_probe:factory`: the real factory (GAIA_PROBE_FACTORY), then install_front
    with GAIA_PROBE_FRONT / GAIA_PROBE_WATCH (JSON lists of candidate indices) and GAIA_PROBE_LOG."""
    from importlib import import_module
    module, _, attribute = os.environ[FACTORY_ENV].partition(':')
    teacher = getattr(import_module(module), attribute)(seed, **kwargs)
    install_front(json.loads(os.environ.get(FRONT_ENV, '[]')), json.loads(os.environ.get(WATCH_ENV, '[]')),
                  os.environ.get(LOG_ENV))
    return teacher


def parse_ask(text, moves):
    """'LABEL:COMPARISONS:CAP:FRONT' -> {'label', 'comparisons', 'cap' (None = no cap), 'front' (move positions)}."""
    parts = text.split(':')
    if len(parts) != 4 or not parts[0]:
        raise SystemExit(f'--ask must be LABEL:COMPARISONS:CAP:FRONT: {text}')
    label, comparisons, cap, front = parts
    front = [int(n) for n in front.split(',') if n.strip()]
    if any(not 0 <= n < moves for n in front) or len(set(front)) != len(front):
        raise SystemExit(f'--ask {label}: FRONT must be distinct positions in the --move list (0..{moves-1})')
    cap = float(cap)
    if int(comparisons) < 1 or cap < 0:
        raise SystemExit(f'--ask {label}: COMPARISONS must be at least 1 and CAP at least 0')
    return {'label': label, 'comparisons': int(comparisons), 'cap': cap or None, 'front': front}


def ask_spec(teacher, ask, indices, log_path):
    """The teacher spec of one ask: the budget and cap of the ask; with a FRONT, the probe factory around the
    teacher's own (the indices travel in the worker's environment)."""
    spec = {**teacher, 'comparisons': ask['comparisons'], 'max_seconds': ask['cap']}
    if ask['front']:
        spec['env'] = {**teacher.get('env', {}), FACTORY_ENV: teacher['factory'],
                       FRONT_ENV: json.dumps([indices[n] for n in ask['front']]),
                       WATCH_ENV: json.dumps(indices), LOG_ENV: str(log_path)}
        spec['factory'] = 'decision_probe:factory'
    return spec


def by_type(candidates):
    """({action type: count}, {upgrade target: count}) of a candidate list."""
    kinds, upgrades = Counter(), Counter()
    for candidate in candidates:
        action = candidate.get('action')
        kind = action.get('type', '?') if isinstance(action, dict) else str(action)
        kinds[kind] += 1
        if kind == 'Upgrade':
            target = action.get('to')
            upgrades[target if isinstance(target, str) else json.dumps(target, sort_keys=True)] += 1
    return dict(kinds.most_common()), dict(upgrades.most_common())


def reach(state_path, prefix_log, prefix_steps):
    """(snapshot at the decision, [(decision_id, index, digest after)] of the prefix, start digest, row K of the
    log or None)."""
    from gaia_rl import Environment
    rows = []
    if prefix_log is not None:
        with gzip.open(prefix_log, 'rt') as f:
            rows = [json.loads(line) for _, line in zip(range(prefix_steps+1), f)]
    if len(rows) < prefix_steps:
        raise SystemExit(f'{prefix_log} holds fewer than {prefix_steps} decisions')
    env = Environment.from_state_json(Path(state_path).read_text(), teacher_ab.MAX_DECISIONS)
    snapshot = json.loads(env.snapshot_json())
    start, prefix = teacher_ab.digest(snapshot), []
    for row in rows[:prefix_steps]:
        index = teacher_ab.scripted_index(snapshot['candidates'], row['chosen']['action'])
        decision = snapshot['decision_id']
        env.step(decision, index)
        snapshot = json.loads(env.snapshot_json())
        prefix.append((decision, index, teacher_ab.digest(snapshot)))
    return snapshot, prefix, start, rows[prefix_steps] if len(rows) > prefix_steps else None


def run_ask(ask, teacher, seed, state_path, start, prefix, snapshot, indices, output, timeout):
    """One fresh worker: watch the prefix, choose once. Returns the ask's row for metrics.json."""
    folder = output/ask['label']
    folder.mkdir(parents=True)
    log_path = (folder/'roots.jsonl').resolve()
    clock = {**teacher_ab.budget_clock(ask['comparisons']), 'fast_copy': True}
    row = {**ask, 'front_indices': [indices[n] for n in ask['front']]}
    candidates = snapshot['candidates']
    with (folder/'worker.log').open('w') as log:
        worker = teacher_ab.Worker(ask_spec(teacher, ask, indices, log_path), seed, clock, log, state_path)
        try:
            if worker.request(None, timeout=300).get('digest') != start:
                raise RuntimeError('the worker started from a different native state')
            for decision, index, after in prefix:
                if worker.request({'op': 'step', 'decision_id': decision, 'index': index}, 300).get('digest') != after:
                    raise RuntimeError('the worker diverged while watching the prefix')
            tick = time.monotonic()
            reply = worker.request({'op': 'choose', 'digest': teacher_ab.digest(snapshot)}, timeout)
            row['wall_seconds'] = round(time.monotonic()-tick, 3)
            if 'index' not in reply:
                raise RuntimeError(json.dumps(reply)[:300])
        except Exception as error:      # one failed ask must not lose the others
            row['error'] = repr(error)[:400]
            return row
        finally:
            worker.close()
    chosen = reply['index']
    row.update(index=chosen, action=candidates[chosen]['action'],
               chose_move=indices.index(chosen) if chosen in indices else None,
               selected=reply.get('selected'), completed_comparisons=reply.get('completed_comparisons'),
               unsearched_comparisons=reply.get('unsearched_comparisons'),
               fallback_timeout=reply.get('fallback_timeout'), timing=reply.get('timing'),
               compared=[{**plan, 'action': candidates[plan['first']]['action']
                          if isinstance(plan.get('first'), int) and 0 <= plan['first'] < len(candidates) else None,
                          'move': indices.index(plan['first']) if plan.get('first') in indices else None}
                         for plan in reply.get('compared', [])])
    if log_path.exists():
        lines = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        if lines:
            row.update(roots=lines[-1]['roots'], move_ranks=lines[-1]['rank'])
    return row


def short(action, limit=120):
    text = json.dumps(action, ensure_ascii=False, separators=(',', ':'))
    return text if len(text) <= limit else text[:limit-1]+'…'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--state', type=Path, required=True, help='Engine state file the game started from')
    parser.add_argument('--prefix-log', type=Path, help='decisions.jsonl.gz of a game played from --state')
    parser.add_argument('--prefix-steps', type=int, default=0, help='Decisions of --prefix-log before the asked one')
    parser.add_argument('--seed', help='Teacher seed label (default: the seed in result.json beside --prefix-log)')
    parser.add_argument('--teacher', required=True, help='teachers.json name or spec .json path')
    parser.add_argument('--move', action='append', default=[], help='An action (JSON) to watch / put in front')
    parser.add_argument('--ask', action='append', required=True, help='LABEL:COMPARISONS:CAP:FRONT (see above)')
    parser.add_argument('--timeout', type=float, default=1800, help='Seconds to wait for one choice')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('A new output directory is required')
    teacher = teacher_ab.resolve_teacher(args.teacher)
    problems = teacher_ab.frozen_problems(teacher)
    if problems:
        raise SystemExit(f'Frozen teacher ({teacher["name"]}) changed: {problems[:5]}')
    asks = [parse_ask(text, len(args.move)) for text in args.ask]
    if len({ask['label'] for ask in asks}) != len(asks):
        raise SystemExit('--ask labels must differ')
    seed = args.seed
    if seed is None:
        if args.prefix_log is None:
            raise SystemExit('--seed is required without --prefix-log')
        seed = json.loads((args.prefix_log.parent/'result.json').read_text())['seed']
    snapshot, prefix, start, logged = reach(args.state, args.prefix_log, args.prefix_steps)
    candidates = snapshot['candidates']
    indices = [teacher_ab.scripted_index(candidates, json.loads(text)) for text in args.move]
    kinds, upgrades = by_type(candidates)
    digest = teacher_ab.digest(snapshot)
    player = snapshot['state']['players'][snapshot['player']]
    metrics = {
        'created_at': teacher_ab.now(), 'state': str(args.state), 'prefix_log': str(args.prefix_log),
        'prefix_steps': args.prefix_steps, 'teacher': teacher['name'], 'seed': seed, 'digest': digest,
        'digest_in_log': logged and logged.get('digest'),
        'digest_matches_log': None if logged is None else logged.get('digest') == digest,
        'logged_choice': logged and {'index': logged['index'], 'action': logged['chosen'].get('action'),
                                     'selected': logged.get('selected'), 'seconds': logged.get('seconds'),
                                     'completed_comparisons': logged.get('completed_comparisons'),
                                     'timing': logged.get('timing')},
        'round': snapshot['state']['round'], 'seat': snapshot['player'], 'faction': player['faction'],
        'candidates': len(candidates), 'candidates_by_type': kinds, 'upgrade_candidates_by_target': upgrades,
        'moves': [{'position': n, 'index': index, 'action': candidates[index]['action']}
                  for n, index in enumerate(indices)]}
    args.output.mkdir(parents=True)
    state_path = args.state.resolve()

    def one(ask):
        row = run_ask(ask, teacher, seed, state_path, start, prefix, snapshot, indices, args.output, args.timeout)
        print(json.dumps({key: row.get(key) for key in ('label', 'index', 'chose_move', 'selected',
                                                        'completed_comparisons', 'wall_seconds', 'error')}), flush=True)
        return row

    rows = {ask['label']: one(ask) for ask in asks if ask['cap'] is None}
    capped = [ask for ask in asks if ask['cap'] is not None]
    if capped:
        with ThreadPoolExecutor(max_workers=len(capped)) as pool:
            rows.update(zip((ask['label'] for ask in capped), pool.map(one, capped)))
    metrics['asks'] = [rows[ask['label']] for ask in asks]
    metrics['failures'] = [row['label'] for row in metrics['asks'] if 'error' in row]
    ranks = next((row['move_ranks'] for row in metrics['asks'] if row.get('move_ranks')), None)
    for move in metrics['moves']:
        move['rank'] = None if ranks is None else ranks.get(str(move['index']))
    metrics['root_moves'] = next((row['roots']+1 for row in metrics['asks'] if row.get('roots')), None)
    teacher_ab.write_json(args.output/'metrics.json', metrics)

    print(f"round {metrics['round']} seat {metrics['seat']} {metrics['faction']}: {len(candidates)} candidates, "
          f"digest matches the log: {metrics['digest_matches_log']}")
    print('candidates by type: ' + ', '.join(f'{kind} {count}' for kind, count in kinds.items()))
    if upgrades:
        print('upgrades by target: ' + ', '.join(f'{kind} {count}' for kind, count in upgrades.items()))
    if logged:
        print(f"logged choice: [{logged['index']}] {short(logged['chosen'].get('action'))} "
              f"({logged.get('selected')}, {logged.get('seconds')} s, {logged.get('completed_comparisons')} compared)")
    for move in metrics['moves']:
        print(f"move {move['position']}: [{move['index']}] rank {move['rank']} of {metrics['root_moves']} "
              f"{short(move['action'])}")
    for row in metrics['asks']:
        head = f"ask {row['label']}: budget {row['comparisons']}, cap {row['cap']}, front {row['front_indices']}"
        if 'error' in row:
            print(f'{head} — failed: {row["error"]}')
            continue
        timing = row.get('timing') or {}
        print(f"{head} → [{row['index']}] {short(row['action'])} ({row['selected']}; move {row['chose_move']}; "
              f"{row['completed_comparisons']} compared, {row['wall_seconds']} s, capped {timing.get('time_capped')}, "
              f"published at {timing.get('published_at')}, stages {timing.get('stages')})")
        for plan in row['compared']:
            value = plan.get('value')
            print(f"    {str(plan.get('goal'))[:44]:<44} {'' if value is None else format(value, '8.2f'):>8} "
                  f"{'done' if plan.get('complete') else 'open'} [{plan.get('first')}]"
                  f"{'' if plan.get('move') is None else ' = move '+str(plan['move'])} {short(plan.get('action'), 70)}")


if __name__ == '__main__':
    main()
