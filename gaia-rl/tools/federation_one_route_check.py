"""Check GAIA_FEDERATION_ONE_ROUTE=1 against recorded lab games.

The engine flag keeps one satellite route per federation building set in the AI candidate
list. This tool replays recorded games (result.json + decisions.jsonl.gz) and, at every
logged decision, forks the recorded move with the flag off and on, timing each fork and
comparing the next decision's candidate lists:

  (a) every flag-on action is in the flag-off list
  (b) the non-FormFederation actions are identical as lists (same order)
  (c) the set of (sorted hexes, token, bonus fields) keys of FormFederation is equal
  (d) flag on: exactly one FormFederation action per key

After the last row (the crash decision of a crashed game) every FreeAction candidate is
forked with the flag off and on to time the free-action enumeration.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=python:baseline-teacher-20260917:tools \\
    .venv/bin/python tools/federation_one_route_check.py GAME [GAME ...] \\
    --out runs/x/metrics.json [--free-action-limit 150]

GAME is a game directory or a pair directory (its single game-* subdirectory is used).
Exit code 1 when a check fails (violation, fork error, or the flag not reducing candidates).
"""
import argparse
import gzip
import json
import os
import sys
import time
from pathlib import Path


def set_flag(on):
    if on:
        os.environ['GAIA_FEDERATION_ONE_ROUTE'] = '1'
    else:
        os.environ.pop('GAIA_FEDERATION_ONE_ROUTE', None)


def resolve_game(path):
    p = Path(path)
    if (p/'result.json').exists():
        return p
    games = sorted(p.glob('game-*'))
    if len(games) != 1:
        raise SystemExit(f'{p}: expected result.json or exactly one game-* subdirectory, found {len(games)}')
    return games[0]


def dumps(action):
    return json.dumps(action, sort_keys=True)


def fed_key(action):
    return json.dumps([sorted(action.get('hexes') or []), action.get('token'),
                       action.get('bonus_build_coord'), action.get('bonus_tech_tile'),
                       action.get('bonus_research_track')], sort_keys=True)


def is_fed(action):
    return isinstance(action, dict) and action.get('type') == 'FormFederation'


def timed_fork(env, decision_id, index):
    t0 = time.monotonic()
    branch = env.fork(decision_id, index)
    dt = time.monotonic()-t0
    return branch, dt


def candidates_of(branch):
    return json.loads(branch.snapshot_json())['candidates']


def check_pair(off, on):
    """Return the set of violated invariant letters and (fed count off, fed count on)."""
    acts_off = [c['action'] for c in off]
    acts_on = [c['action'] for c in on]
    bad = set()
    set_off = {dumps(a) for a in acts_off}
    if any(dumps(a) not in set_off for a in acts_on):
        bad.add('a')
    non_off = [dumps(a) for a in acts_off if not is_fed(a)]
    non_on = [dumps(a) for a in acts_on if not is_fed(a)]
    if non_off != non_on:
        bad.add('b')
    fed_off = [a for a in acts_off if is_fed(a)]
    fed_on = [a for a in acts_on if is_fed(a)]
    keys_off = {fed_key(a) for a in fed_off}
    keys_on_list = [fed_key(a) for a in fed_on]
    if keys_off != set(keys_on_list):
        bad.add('c')
    if len(keys_on_list) != len(set(keys_on_list)):
        bad.add('d')
    return bad, len(fed_off), len(fed_on)


def check_game(game, state):
    from gaia_rl import Environment
    result = json.loads((game/'result.json').read_text())
    with gzip.open(game/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    env = Environment(result['seed'], 2000)
    g = {'steps_checked': 0, 'states_with_federation_off': 0,
         'max_fed_off': 0, 'max_fed_off_step': None, 'max_fed_on': 0, 'max_fed_on_step': None,
         'total_fed_off': 0, 'total_fed_on': 0,
         'fork_seconds_off': 0.0, 'fork_seconds_on': 0.0,
         'max_fork_seconds_off': 0.0, 'max_fork_seconds_on': 0.0}
    name = str(game)
    for n, row in enumerate(rows):
        cands = {}
        for mode in ('off', 'on'):
            set_flag(mode == 'on')
            try:
                branch, dt = timed_fork(env, row['decision_id'], row['index'])
                cands[mode] = candidates_of(branch)
            except Exception as e:
                state['fork_errors'].append({'game': name, 'step': n, 'mode': mode, 'error': repr(e)})
                dt = None
            if dt is not None:
                g[f'fork_seconds_{mode}'] += dt
                g[f'max_fork_seconds_{mode}'] = max(g[f'max_fork_seconds_{mode}'], dt)
        set_flag(False)
        if 'off' in cands and 'on' in cands:
            g['steps_checked'] += 1
            bad, n_off, n_on = check_pair(cands['off'], cands['on'])
            for letter in bad:
                state['violations'][letter] += 1
                ex = state['violation_examples'].setdefault(letter, [])
                if len(ex) < 3:
                    ex.append({'game': name, 'step': n})
            if n_off:
                g['states_with_federation_off'] += 1
            g['total_fed_off'] += n_off
            g['total_fed_on'] += n_on
            if n_off > g['max_fed_off']:
                g['max_fed_off'], g['max_fed_off_step'] = n_off, n
            if n_on > g['max_fed_on']:
                g['max_fed_on'], g['max_fed_on_step'] = n_on, n
        env.step(row['decision_id'], row['index'])

    # State after the whole log: time every free action's fork in both modes.
    snap = json.loads(env.snapshot_json())
    free = [i for i, c in enumerate(snap['candidates']) if c['action'].get('type') == 'FreeAction']
    g['final_free_actions'] = len(free)
    g['final_free_truncated'] = {}
    for mode in ('off', 'on'):
        total = 0.0
        largest = 0
        set_flag(mode == 'on')
        for i in free:
            if total > state['free_limit']:
                g['final_free_truncated'][mode] = True
                break
            try:
                branch, dt = timed_fork(env, snap['decision_id'], i)
                total += dt
                nxt = candidates_of(branch)
                largest = max(largest, sum(1 for c in nxt if is_fed(c['action'])))
            except Exception as e:
                state['fork_errors'].append({'game': name, 'step': 'final', 'mode': mode,
                                             'free_index': i, 'error': repr(e)})
        set_flag(False)
        g[f'final_free_fork_seconds_{mode}'] = total
        g[f'final_free_max_fed_{mode}'] = largest
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('games', nargs='+')
    ap.add_argument('--out', required=True)
    ap.add_argument('--free-action-limit', type=float, default=150.0)
    args = ap.parse_args()

    state = {'violations': {k: 0 for k in 'abcd'}, 'violation_examples': {},
             'fork_errors': [], 'free_limit': args.free_action_limit}
    games = {}
    set_flag(False)
    try:
        for path in args.games:
            game = resolve_game(path)
            games[str(game)] = check_game(game, state)
            g = games[str(game)]
            print(f'{game}: steps={g["steps_checked"]} fed_states={g["states_with_federation_off"]} '
                  f'max_fed off/on={g["max_fed_off"]}/{g["max_fed_on"]} '
                  f'total_fed off/on={g["total_fed_off"]}/{g["total_fed_on"]} '
                  f'fork_s off/on={g["fork_seconds_off"]:.1f}/{g["fork_seconds_on"]:.1f} '
                  f'final_free n={g["final_free_actions"]} '
                  f'off/on={g["final_free_fork_seconds_off"]:.1f}/{g["final_free_fork_seconds_on"]:.1f}s '
                  f'truncated={g["final_free_truncated"] or False}')
    finally:
        set_flag(False)

    total_off = sum(g['total_fed_off'] for g in games.values())
    total_on = sum(g['total_fed_on'] for g in games.values())
    effective = total_on < total_off
    passed = (not any(state['violations'].values()) and not state['fork_errors'] and effective)
    metrics = {'games': games, 'violations': state['violations'],
               'violation_examples': state['violation_examples'],
               'fork_errors': state['fork_errors'], 'flag_effective': effective, 'passed': passed}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    print('violations: ' + ' '.join(f'{k}={v}' for k, v in state['violations'].items())
          + f' fork_errors={len(state["fork_errors"])} flag_effective={effective}')
    print('PASS' if passed else 'FAIL')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
