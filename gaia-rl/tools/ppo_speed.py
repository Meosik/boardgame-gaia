"""PPO speed smoke (HANDOFF E329): the same from-scratch run with sampling in the driver and with remote env runners.

Runs `python -m gaia_rl.training` twice from gaia-rl/, one arm after the other, each for --minutes (it stops at the
first iteration boundary after that): `single` = --env-runners 0, `parallel` = --env-runners N. Same seed, encoding,
capacity, batch and minibatch size; no initial checkpoint, no teacher. Not a strength measurement: it reports
decisions and finished games per hour, the sampling and update seconds of an iteration and the driver's peak memory.

  cd gaia-rl && GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools .venv/bin/python \\
      tools/ppo_speed.py --out runs/<name>/metrics.json --minutes 30 --runners 12

The metrics file is written even when an arm fails (its `error` holds the end of the log); the exit code is then 1.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def number(value):
    return float(value) if isinstance(value, (int, float)) else None


def summarize(report, batch_size):
    """One arm's numbers from the pilot.json of gaia_rl.training (pure: tested in test_ppo_runners.py)."""
    results = report.get('results') or []
    seconds = [float(x) for x in report.get('iteration_seconds') or []]
    total = sum(seconds)
    decisions = number((results[-1] if results else {}).get('num_env_steps_sampled_lifetime'))
    if decisions is None:
        decisions = float(batch_size*len(seconds))

    def mean(values):
        values = [v for v in values if v is not None]
        return sum(values)/len(values) if values else None

    timers = [result.get('timers') or {} for result in results]
    runners = [result.get('env_runners') or {} for result in results]
    episodes = sum(v for v in (number(r.get('num_episodes')) for r in runners) if v is not None)
    length = next((v for v in (number(r.get('episode_len_mean')) for r in reversed(runners)) if v), None)
    per_hour = decisions/total*3600 if total else None
    learner = [(result.get('learners') or {}).get('shared') or {} for result in results]
    return {'iterations': len(seconds), 'seconds': round(total, 1), 'decisions': decisions,
            'decisions_per_hour': per_hour and round(per_hour),
            'iteration_seconds_mean': mean(seconds), 'iteration_seconds_first': seconds[0] if seconds else None,
            'sampling_seconds_mean': mean([number(t.get('env_runner_sampling_timer')) for t in timers]),
            'update_seconds_mean': mean([number(t.get('learner_update_timer')) for t in timers]),
            'episodes_finished': episodes, 'episode_len_mean': length,
            'games_per_hour': round(episodes/total*3600, 1) if total else None,
            'games_per_hour_by_length': round(per_hour/length, 1) if per_hour and length else None,
            'peak_driver_rss_mib': report.get('peak_driver_rss_mib'),
            'total_loss_first': number(learner[0].get('total_loss')) if learner else None,
            'total_loss_last': number(learner[-1].get('total_loss')) if learner else None}


def run_arm(name, runners, args, folder):
    output = folder/name
    command = [sys.executable, '-m', 'gaia_rl.training', '--output', str(output), '--iterations', '1000000',
               '--max-minutes', str(args.minutes), '--seed', str(args.seed), '--capacity', str(args.capacity),
               '--batch-size', str(args.batch_size), '--minibatch-size', str(args.minibatch_size),
               '--encoding', str(args.encoding), '--env-runners', str(runners)]
    env = dict(os.environ, GAIA_ENGINE_FIXES_2='1',
               PYTHONPATH=os.pathsep.join(str(ROOT/part) for part in ('python', 'baseline-teacher-20260917', 'tools')))
    log = folder/f'{name}.log'
    started = time.monotonic()
    # An iteration is not interrupted, so the arm may run past --minutes: three times the budget is the hard stop.
    limit = args.minutes*60*3+900
    with open(log, 'w') as stream:
        try:
            code = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                  timeout=limit).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    arm = {'env_runners': runners, 'returncode': code, 'wall_seconds': round(time.monotonic()-started, 1)}
    pilot = output/'pilot.json'
    if code == 0 and pilot.exists():
        arm.update(summarize(json.loads(pilot.read_text()), args.batch_size))
        versions = json.loads((output/'metadata.json').read_text()).get('versions') or {}
        arm['engine_build_id'] = versions.get('engine_build_id')
    else:
        arm['error'] = log.read_text(errors='replace')[-1500:]
    return arm


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True, help='metrics.json; the runs go next to it')
    parser.add_argument('--minutes', type=float, default=30)
    parser.add_argument('--runners', type=int, default=12)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--encoding', type=int, default=4)
    parser.add_argument('--capacity', type=int, default=4096)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--minibatch-size', type=int, default=64)
    args = parser.parse_args()
    out = args.out if args.out.is_absolute() else Path.cwd()/args.out
    folder = out.parent
    if any((folder/name).exists() for name in ('single', 'parallel')):
        parser.error(f'{folder} already holds a run: give a fresh run folder')
    folder.mkdir(parents=True, exist_ok=True)
    arms = {'single': run_arm('single', 0, args, folder), 'parallel': run_arm('parallel', args.runners, args, folder)}
    single, parallel = (arms[name].get('decisions_per_hour') for name in ('single', 'parallel'))
    metrics = {'settings': {key: getattr(args, key) for key in
                            ('minutes', 'runners', 'seed', 'encoding', 'capacity', 'batch_size', 'minibatch_size')},
               'arms': arms,
               'parallel_over_single_decisions_per_hour': round(parallel/single, 2) if single and parallel else None}
    out.write_text(json.dumps(metrics, indent=1))
    print(json.dumps(metrics, indent=1))
    return 0 if all(arm['returncode'] == 0 for arm in arms.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
