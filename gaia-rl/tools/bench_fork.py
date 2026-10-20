"""Micro-benchmark of the native engine calls a teacher decision is made of.

Replays a recorded lab/teacher_ab game to decision STEP (engine only, no teacher) and times,
on that one state, each native call the search uses: fork (clone + apply + next candidates),
preview_state_json (apply + serialize the state only), snapshot_json (serialize state + candidates)
and json.loads of that snapshot. Prints per-call microseconds so the split between cloning,
candidate generation and serialization can be read off (E57 lever choice).

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:tools .venv/bin/python tools/bench_fork.py \\
    ~/projects/gaia-lab/gaia-rl/runs/lab-092-guide-vs-weak-4r/pair-012/game-0-A02 --steps 30 100 160 [--repeat 300]
"""
import argparse
import gzip
import json
import time
from pathlib import Path


def replay(game_dir, step):
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        for i, line in enumerate(f):
            if i == step:
                break
            row = json.loads(line)
            env.step(row['decision_id'], row['index'])
    return env


def timed(fn, repeat):
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter()-t0)/repeat*1e6


def bench(env, repeat):
    snapshot = json.loads(env.snapshot_json())
    did = snapshot['decision_id']
    n = len(snapshot['candidates'])
    idx = list(range(n))
    cursor = [0]

    def nxt():
        i = idx[cursor[0] % n]
        cursor[0] += 1
        return i

    rows = {
        'candidates': n,
        'snapshot_json_bytes': len(env.snapshot_json()),
        'state_json_bytes': len(json.dumps(snapshot['state'])),
        'fork_us': timed(lambda: env.fork(did, nxt()), repeat),
        'preview_state_json_us': timed(lambda: env.preview_state_json(did, nxt()), repeat),
        'snapshot_json_us': timed(lambda: env.snapshot_json(), repeat),
        'json_loads_snapshot_us': timed(lambda: json.loads(env.snapshot_json()), repeat),
    }
    branch = env.fork(did, 0)
    rows['fork_then_snapshot_loads_us'] = timed(lambda: json.loads(env.fork(did, nxt()).snapshot_json()), repeat)
    rows['branch_candidates'] = len(json.loads(branch.snapshot_json())['candidates'])
    # candidate generation + env clone ≈ fork − (preview_state_json − state serialization share)
    rows['serialize_share_est_us'] = rows['snapshot_json_us']
    rows['apply_only_est_us'] = max(rows['preview_state_json_us']-rows['snapshot_json_us'], 0.0)
    rows['clone_plus_candidates_est_us'] = max(rows['fork_us']-rows['apply_only_est_us'], 0.0)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game_dir', type=Path)
    parser.add_argument('--steps', type=int, nargs='+', default=[100])
    parser.add_argument('--repeat', type=int, default=300)
    args = parser.parse_args()
    for step in args.steps:
        env = replay(args.game_dir, step)
        snapshot = json.loads(env.snapshot_json())
        print(f"step {step}: round {snapshot['state'].get('round')} phase {snapshot['state'].get('phase')} "
              f"player {snapshot['player']}")
        for key, value in bench(env, args.repeat).items():
            print(f'  {key:32s} {value:10.1f}' if isinstance(value, float) else f'  {key:32s} {value:10d}')


if __name__ == '__main__':
    main()
