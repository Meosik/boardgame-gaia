"""Counterfactual data: from the same position, play several different moves to the end.

Cycle 019 showed that weights fitted to *outcomes of the moves teachers actually played*
predict results but choose moves badly (a strong player both scores well and holds few
resources, so resources were fitted as worthless and spent on pointless conversions). A
decision value needs to see different moves from the same position.

For sampled action-phase positions of finished teacher_ab games (replayed and verified as in
tools/extract_dataset.py), this plays up to `--branches` distinct moves:
  recorded  the move the match teacher played,
  rank1/2   the easy teacher's two best-ranked moves (one-step ranking),
  random    one uniformly drawn legal move (bans included: an untested ban is a judgment),
  rank3/4   further ranked moves while branches remain,
then finishes the game from each with the same deterministic easy teacher (live teacher's
patches, comparison budget 0) for all seats. The only difference between the branches of
one position is that first move, so their final-score differences measure its value.

Per branch row: the post-move features of all four players (terms, facts, potential as in
extract_dataset), the four final scores, the root id, the actor and the branch kind.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools \\
    .venv/bin/python tools/branch_dataset.py runs/ab-* --per-game 8 --jobs 7 \\
    --output datasets/branches.jsonl.gz
"""
import argparse
import gzip
import hashlib
import json
from multiprocessing import Pool
import random
import sys
import time

MAX_DECISIONS = 2000
_worker = {}


def _init():
    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    budget_teacher.install(0)
    budget_teacher.set_horizon(2)
    from faction_teachers.profiles import profiles
    _worker['homes'] = {name: p.home for name, p in profiles().items()}


def _teacher(env, name):
    import teacher_patches
    teacher = teacher_patches.geodens_guide(name, bgg_openings=True, shared_factions=True)
    teacher.bind(env)
    return teacher


def _features(state):
    from extract_dataset import facts, pass_terms, potential_terms
    players = []
    for i, p in enumerate(state['players']):
        terms = potential_terms(state, i, _worker['homes'][p['faction']])
        players.append({'faction': p['faction'], 'terms': {**terms, **pass_terms(state, i)},
                        'facts': facts(state, i), 'potential': sum(terms.values())})
    return players


def _finish(state_json, name):
    """Play to the end with the easy teacher for every seat; return final scores by list index."""
    from gaia_rl import Environment
    env = Environment.from_state_json(state_json, MAX_DECISIONS)
    teacher = _teacher(env, name)
    snapshot = json.loads(env.snapshot_json())
    while not env.is_terminal():
        decision_id, index = teacher.choose(snapshot)
        before = snapshot
        env.step(decision_id, index)
        snapshot = json.loads(env.snapshot_json())
        teacher.observe(before, index, snapshot)
    final = dict(snapshot['state']['phase']['Ended']['final_scores'])
    return [final[p['player_id']] for p in snapshot['state']['players']]


def branch_task(task):
    """One position: choose distinct first moves, apply each, finish each game."""
    from gaia_rl import Environment
    started = time.monotonic()
    state_json, root, recorded, branches, seed = task
    env = Environment.from_state_json(state_json, MAX_DECISIONS)
    snapshot = json.loads(env.snapshot_json())
    candidates = snapshot['candidates']
    teacher = _teacher(env, root)
    teacher.choose(snapshot)
    scores = teacher.last_scores
    ranked = sorted(range(len(candidates)), key=lambda i: (-scores[i][0], i))
    # The random move keeps a reserved slot: it is the only branch the teachers never prefer.
    chosen = [('recorded', recorded), ('rank1', ranked[0]), ('rank2', ranked[1]),
              ('random', random.Random(seed).randrange(len(candidates))), *(
              (f'rank{k+3}', i) for k, i in enumerate(ranked[2:4]))]
    picked, seen = [], set()
    for kind, index in chosen:
        if index not in seen and len(picked) < branches:
            seen.add(index)
            picked.append((kind, index))
    rows = []
    for kind, index in picked:
        branch = Environment.from_state_json(state_json, MAX_DECISIONS)
        first = json.loads(branch.snapshot_json())
        branch.step(first['decision_id'], index)
        after = json.loads(branch.snapshot_json())
        final = (after['state']['phase']['Ended']['final_scores'] if branch.is_terminal() else None)
        if final is not None:
            final = [dict(final)[p['player_id']] for p in after['state']['players']]
        else:
            final = _finish(json.dumps(after['state']), f'{root}/{kind}')
        action = candidates[index].get('action', {})
        rows.append({'root': root, 'round': snapshot['state']['round'], 'actor': snapshot['player'],
                     'branch': kind, 'index': index, 'candidates': len(candidates),
                     'action_type': action.get('type') if isinstance(action, dict) else str(action),
                     'after': _features(after['state']), 'final_vp': final})
    return rows, time.monotonic()-started


def positions(run_dirs, per_game):
    """Replay each finished game and pick up to `per_game` evenly spaced choice positions."""
    from extract_dataset import games
    from gaia_rl import Environment
    seen = set()
    for game_dir, result, trace in games(run_dirs):
        key = (result['seed'], trace.read_bytes())
        if key in seen:
            continue
        seen.add(key)
        try:
            env = Environment(result['seed'], MAX_DECISIONS)
            snapshot = json.loads(env.snapshot_json())
            eligible = []
            with gzip.open(trace, 'rt') as rows:
                for line in rows:
                    row = json.loads(line)
                    if row['decision_id'] != snapshot['decision_id']:
                        raise ValueError(f'replay diverged at step {row["step"]}')
                    if 'ActionPhase' in snapshot['state']['phase'] and len(snapshot['candidates']) >= 2:
                        eligible.append((json.dumps(snapshot['state']), snapshot['steps'], row['index']))
                    env.step(row['decision_id'], row['index'])
                    snapshot = json.loads(env.snapshot_json())
        except (ValueError, RuntimeError) as error:
            print(f'skip {game_dir}: {error}', file=sys.stderr)
            continue
        if not eligible:
            continue
        step = max(1, len(eligible)//per_game)
        for state_json, steps, recorded in eligible[step//2::step][:per_game]:
            root = f'{result["seed"]}@{game_dir.parent.parent.name}/{game_dir.name}#{steps}'
            yield state_json, root, recorded, result['seed']


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--output', required=True)
    parser.add_argument('--per-game', type=int, default=8)
    parser.add_argument('--branches', type=int, default=4)
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--limit', type=int, help='Stop after this many positions (smoke runs)')
    args = parser.parse_args()
    _init()
    tasks = []
    for state_json, root, recorded, seed in positions(args.runs, args.per_game):
        digest = int(hashlib.sha256(root.encode()).hexdigest()[:8], 16)
        tasks.append((state_json, root, recorded, args.branches, digest))
        if args.limit and len(tasks) >= args.limit:
            break
    print(f'{len(tasks)} positions, up to {args.branches} branches each', file=sys.stderr, flush=True)
    done = rows_written = 0
    started = time.monotonic()
    with gzip.open(args.output, 'wt') as out, Pool(args.jobs, initializer=_init) as pool:
        for rows, seconds in pool.imap_unordered(branch_task, tasks):
            for row in rows:
                out.write(json.dumps(row, allow_nan=False)+'\n')
            out.flush()
            done += 1
            rows_written += len(rows)
            elapsed = time.monotonic()-started
            print(f'{done}/{len(tasks)} positions ({seconds:.0f}s this one; '
                  f'eta {elapsed/done*(len(tasks)-done)/60:.0f} min)', file=sys.stderr, flush=True)
    print(json.dumps({'positions': done, 'branches': rows_written, 'output': args.output}))


if __name__ == '__main__':
    main()
