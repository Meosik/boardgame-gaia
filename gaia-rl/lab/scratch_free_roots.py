"""Free-action alternatives in the comparison list (HANDOFF E179 (b), read only, no verdict).

unlock GAME_DIR STEP [--roots i ...]
    Replay to STEP; for every free action there: which main actions (type != FreeAction) are legal after it that were
    not legal before (one conversion), and after one more free action (two conversions). Legality only: the engine's
    candidate list, not the teacher's ranking.

tally RUN_DIR ... [--jobs N]
    Over every recorded decision (strict replay, the chosen action is checked against the candidate list):
    - root alternatives in `compared` (family root) by the type of their first move: slot, complete, value against
      current-choice (above / equal / below), selected;
    - turns as played: k free actions then a main action M - was M legal before the first free action, or after how
      many of them it became legal (exact JSON of the action).
"""
import argparse
import gzip
import json
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path


def key(action):
    return json.dumps(action, sort_keys=True)


def label(action):
    rest = {k: v for k, v in action.items() if k != 'type'}
    return (action['type'] + ' ' + json.dumps(rest, sort_keys=True, ensure_ascii=False))[:110]


def is_free(action):
    return action.get('type') == 'FreeAction'


def load(game_dir):
    result = json.loads((game_dir/'result.json').read_text())
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    return result, rows


def main_keys(snapshot):
    return {key(c['action']) for c in snapshot['candidates'] if not is_free(c['action'])}


def unlock(args):
    from gaia_rl import Environment
    result, rows = load(args.game_dir)
    env = Environment(result['seed'], 2000)
    for row in rows[:args.step]:
        env.step(row['decision_id'], row['index'])
    snapshot = json.loads(env.snapshot_json())
    assert snapshot['decision_id'] == rows[args.step]['decision_id']
    seat = snapshot['player']
    player = next(p for p in snapshot['state']['players'] if p['player_id'] == seat)
    actions = [c['action'] for c in snapshot['candidates']]
    assert actions[rows[args.step]['index']] == rows[args.step]['chosen']['action'], 'replay diverged'
    before = main_keys(snapshot)
    res = player['resources']
    print(f"{args.game_dir.parent.name}/{args.game_dir.name} step {args.step} round {snapshot['state']['round']} seat {seat} "
          f"{player['faction']} | ore {res['ore']} credits {res['credits']} knowledge {res['knowledge']} qic {res['qic']} "
          f"power {res['power']} | candidates {len(actions)}: main {len(before)}, free {sum(map(is_free, actions))}")
    print('chosen:', label(rows[args.step]['chosen']['action']), '| compared:',
          [(c['goal'], c['value']) for c in rows[args.step].get('compared') or []])
    one_total, two_total = set(), set()
    unlocking = Counter()
    for i, action in enumerate(actions):
        if not is_free(action):
            continue
        branch = env.fork(snapshot['decision_id'], i)
        after = json.loads(branch.snapshot_json())
        if after['player'] != seat:
            print(f'  [{i}] {label(action)} -> turn ended')
            continue
        first = main_keys(after)
        new_one = first - before
        new_two = set()
        pairs = 0
        for j, c in enumerate(after['candidates']):
            if not is_free(c['action']):
                continue
            second = json.loads(branch.fork(after['decision_id'], j).snapshot_json())
            if second['player'] != seat:
                continue
            pairs += 1
            new_two |= main_keys(second) - before - first
        one_total |= new_one
        two_total |= new_two
        unlocking[bool(new_one)] += 1
        if i not in args.roots and not args.all:
            continue
        mark = ' <- compared root' if i in args.roots else ''
        print(f'  [{i}] {label(action)}{mark}: new main actions after it {len(new_one)}, '
              f'after one more free action ({pairs} tried) {len(new_two)} more')
        for k in sorted(new_one)[:args.show]:
            print('        +1:', label(json.loads(k)))
        for k in sorted(new_two)[:args.show]:
            print('        +2:', label(json.loads(k)))
    print(f'free actions that unlock a main action by themselves: {unlocking[True]} of {unlocking[True]+unlocking[False]}')
    print(f'any single free action: {len(one_total)} new main actions; any two: {len(two_total - one_total)} more')
    for k in sorted(one_total):
        print('   one:', label(json.loads(k)))
    for k in sorted(two_total - one_total):
        print('   two:', label(json.loads(k)))


def tally_game(game_dir):
    from gaia_rl import Environment
    result, rows = load(game_dir)
    out = Counter()
    env = Environment(result['seed'], 2000)
    chain = None                                     # {'seat', 'sets': [main keys before each free action], 'kinds'}
    for step, row in enumerate(rows):
        chosen = row.get('chosen') or {}
        action = chosen.get('action') if chosen.get('phase') == 'Game' else None
        roots = [(p, c) for p, c in enumerate(row.get('compared') or []) if c.get('family') == 'root']
        need = action is not None and (is_free(action) or chain is not None or roots)
        if need:
            snapshot = json.loads(env.snapshot_json())
            assert snapshot['decision_id'] == row['decision_id']
            candidates = [c['action'] for c in snapshot['candidates']]
            assert candidates[row['index']] == action, (str(game_dir), step)
            late = 'r56' if snapshot['state']['round'] >= 5 else 'r14'
            if roots:
                control = next((c for c in row['compared'] if c['goal'] == 'current-choice'), None)
                out['decisions with a root alternative'] += 1
                first_root = True
                for p, c in roots:
                    kind = 'free' if is_free(candidates[c['first']]) else 'main'
                    for scope in ('all', late):
                        name = f'{scope} root {kind}'
                        out[name] += 1
                        out[f'{name} slot {min(p+1, 6)}'] += 1
                        if first_root:
                            out[f'{scope} first root is {kind}'] += 1
                            if kind == 'free' and control is not None:
                                others = sum(1 for i, a in enumerate(candidates)
                                             if not is_free(a) and i != control['first'])
                                out[f"{scope} first root is free: other main actions legal {'yes' if others else 'no'}"] += 1
                        if not c.get('complete') or control is None or not control.get('complete'):
                            out[f'{name} incomplete'] += 1
                        else:
                            diff = c['value'] - control['value']
                            out[f"{name} {'above' if diff > 0 else 'equal' if diff == 0 else 'below'}"] += 1
                        if row.get('selected') == c['goal'] and row['index'] == c['first']:
                            out[f'{name} selected'] += 1
                    if kind == 'free':
                        out[f"all root free kind {candidates[c['first']].get('kind')}"] += 1
                    first_root = False
                kinds = {('free' if is_free(candidates[c['first']]) else 'main') for _, c in roots}
                out[f"decisions with root alternatives {'+'.join(sorted(kinds))}"] += 1
            if is_free(action):
                if chain is None or chain['seat'] != row['seat']:
                    chain = {'seat': row['seat'], 'sets': [], 'kinds': [], 'selected': row.get('selected') or ''}
                chain['sets'].append(main_keys(snapshot))
                chain['kinds'].append(action.get('kind'))
            elif chain is not None:
                if chain['seat'] == row['seat']:
                    k, target = len(chain['sets']), key(action)
                    sets = chain['sets'] + [main_keys(snapshot)]
                    after = next(j for j, legal in enumerate(sets) if target in legal)
                    for scope in ('all', late):
                        out[f'{scope} turns with free actions'] += 1
                        out[f'{scope} chain length {min(k, 4)}'] += 1
                        out[f'{scope} main action legal after {min(after, 3)} free actions'] += 1
                        out[f"{scope} main action {action['type']} legal after {min(after, 3)}"] += 1
                    if chain['selected'].startswith('root-'):
                        out[f'chain started by a selected root: main action legal after {min(after, 3)}'] += 1
                        out[f"chain started by a selected root: then {action['type']}"] += 1
                else:
                    out['chains interrupted by another seat'] += 1
                chain = None
        elif chain is not None and action is None:
            out['chains interrupted by a non-game decision'] += 1
            chain = None
        if action is not None and not is_free(action):
            out['main actions played'] += 1
        env.step(row['decision_id'], row['index'])
    out['games'] += 1
    out['decisions'] += len(rows)
    return out


def tally(args):
    games = [g for run in args.run_dirs for g in sorted(run.expanduser().glob('pair-*/game-*'))
             if (g/'result.json').exists() and json.loads((g/'result.json').read_text()).get('complete')]
    if args.limit:
        games = games[:args.limit]
    start = time.time()
    total = Counter()
    with Pool(args.jobs) as pool:
        for part in pool.imap_unordered(tally_game, games):
            total += part
    for name in sorted(total):
        words = name.split(' main action ')
        by_type = len(words) == 2 and words[1][0].isupper()
        if args.types or not by_type or (name.startswith('all ') and name[-1] in '23'):
            print(f'{total[name]:7d}  {name}')
    print(f'seconds {time.time()-start:.0f}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    one = sub.add_parser('unlock')
    one.add_argument('game_dir', type=Path)
    one.add_argument('step', type=int)
    one.add_argument('--roots', type=int, nargs='*', default=[])
    one.add_argument('--show', type=int, default=4)
    one.add_argument('--all', action='store_true', help='print every free action, not only --roots')
    many = sub.add_parser('tally')
    many.add_argument('run_dirs', type=Path, nargs='+')
    many.add_argument('--jobs', type=int, default=6)
    many.add_argument('--limit', type=int, default=0)
    many.add_argument('--types', action='store_true', help='print every per-type line')
    args = parser.parse_args()
    (unlock if args.command == 'unlock' else tally)(args)


if __name__ == '__main__':
    main()
