"""Where the default ranking's first choice is replaced by the search (read only, no verdict).

tally RUN_DIR ... [--jobs N] [--top N]
    Every recorded decision with a `current-choice` comparison (strict replay, the chosen action is checked against
    the candidate list). base = first move of `current-choice` (the default ranking's choice), final = the move played.
    Counts per round: searched, base != final; who replaced it (first root alternative, a later root, a named plan);
    patterns `base type -> final type` with the value difference (winner - current-choice); three examples per
    leading pattern at the quartiles of that difference (not hand-picked).

case GAME_DIR STEP [--comparisons N]
    Ask the teacher again at STEP (as tools/explain_decision.py does: no plan memory of the real game) and print, for
    current-choice and for every compared plan, the forecast line of the acting seat (action, VP change) with the end
    VP and value, and the one-step scores of the base and the played move.
"""
import argparse
import gzip
import importlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path


def kind_of(action):
    return 'Free:' + str(action.get('kind')) if action['type'] == 'FreeAction' else action['type']


def short(action, limit=70):
    rest = {k: v for k, v in action.items() if k != 'type' and v is not None}
    return (action['type'] + (' ' + json.dumps(rest, sort_keys=True, ensure_ascii=False) if rest else ''))[:limit]


def tally_game(game_dir):
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    counts, examples = Counter(), defaultdict(list)
    env = Environment(result['seed'], 2000)
    name = f'{game_dir.parent.parent.name[4:7]} {game_dir.parent.name}/{game_dir.name}'
    for step, row in enumerate(rows):
        compared = row.get('compared') or []
        control = next((c for c in compared if c['goal'] == 'current-choice'), None)
        chosen = row.get('chosen') or {}
        if control is not None and chosen.get('phase') == 'Game':
            snapshot = json.loads(env.snapshot_json())
            candidates = [c['action'] for c in snapshot['candidates']]
            assert candidates[row['index']] == chosen['action'], (str(game_dir), step)
            round_ = snapshot['state']['round']
            counts[f'searched r{round_}'] += 1
            base, final = control['first'], row['index']
            if base != final:
                counts[f'replaced r{round_}'] += 1
                matches = [c for c in compared if c['first'] == final and c is not control]
                named = [c for c in matches if c['goal'] in str(row.get('selected'))]
                winner = (named or sorted(matches, key=lambda c: -(c.get('value') or -1e9)) or [None])[0]
                roots = [c for c in compared if c.get('family') == 'root']
                if winner is None:
                    who = 'no compared entry with the played move'
                elif winner.get('family') == 'root':
                    who = 'first root alternative' if winner is roots[0] else 'later root alternative'
                else:
                    who = 'named plan'
                counts[f'by {who}'] += 1
                counts[f'by {who} r{round_}'] += 1
                pattern = f'{kind_of(candidates[base])} -> {kind_of(candidates[final])}'
                coarse = (('Pass' if candidates[base]['type'] == 'Pass' else 'Free' if candidates[base]['type'] == 'FreeAction'
                           else 'main') + ' -> ' +
                          ('Pass' if candidates[final]['type'] == 'Pass' else 'Free' if candidates[final]['type'] == 'FreeAction'
                           else 'main'))
                counts[f'coarse {coarse}'] += 1
                counts[f'coarse {coarse} r{round_}'] += 1
                counts[f'pattern {pattern}'] += 1
                counts[f'pattern {pattern} r{round_}'] += 1
                if winner is not None and winner.get('complete') and control.get('complete'):
                    examples[pattern].append((round(winner['value'] - control['value'], 2), name, step))
        env.step(row['decision_id'], row['index'])
    return counts, dict(examples)


def tally(args):
    games = [g for run in args.run_dirs for g in sorted(run.expanduser().glob('pair-*/game-*'))
             if (g/'result.json').exists() and json.loads((g/'result.json').read_text()).get('complete')]
    start = time.time()
    total, examples = Counter(), defaultdict(list)
    with Pool(args.jobs) as pool:
        for counts, part in pool.imap_unordered(tally_game, games):
            total += counts
            for pattern, rows in part.items():
                examples[pattern] += rows
    rounds = range(1, 7)
    row = lambda prefix: ' '.join(f'{total[f"{prefix} r{r}"]:6d}' for r in rounds)
    print(f'games {len(games)} | rounds                          ' + ' '.join(f'{"r"+str(r):>6}' for r in rounds) + '   total')
    for prefix in ('searched', 'replaced'):
        print(f'{prefix:46s} {row(prefix)} {sum(total[f"{prefix} r{r}"] for r in rounds):7d}')
    print(f'{"replaced %":46s} ' + ' '.join(f'{100*total[f"replaced r{r}"]/max(1, total[f"searched r{r}"]):6.1f}' for r in rounds)
          + f' {100*sum(total[f"replaced r{r}"] for r in rounds)/max(1, sum(total[f"searched r{r}"] for r in rounds)):7.1f}')
    for who in ('first root alternative', 'later root alternative', 'named plan', 'no compared entry with the played move'):
        print(f'{"by "+who:46s} {row("by "+who)} {total["by "+who]:7d}')
    for coarse in sorted((k[7:] for k in total if k.startswith('coarse ') and ' r' not in k[-3:]), key=lambda k: -total['coarse '+k]):
        print(f'{coarse:46s} {row("coarse "+coarse)} {total["coarse "+coarse]:7d}')
    patterns = sorted((k[8:] for k in total if k.startswith('pattern ') and ' r' not in k[-3:]), key=lambda k: -total['pattern '+k])
    print(f'\npatterns {len(patterns)}, the first {args.top}: base -> final | per round | total | median and mean value difference')
    for pattern in patterns[:args.top]:
        diffs = sorted(d for d, _, _ in examples[pattern])
        stats = f'{statistics.median(diffs):7.2f} {statistics.fmean(diffs):7.2f}' if diffs else ''
        print(f'{pattern[:46]:46s} {row("pattern "+pattern)} {total["pattern "+pattern]:7d} {stats}')
    print('\nexamples at the quartiles of the value difference (difference, game, step)')
    for pattern in patterns[:args.examples]:
        rows = sorted(examples[pattern])
        picks = [rows[len(rows)*q//4] for q in (1, 2, 3)] if len(rows) >= 4 else rows
        print(f'  {pattern}: ' + ' | '.join(f'{d:+.2f} {game} step {step}' for d, game, step in picks))
    print(f'seconds {time.time()-start:.0f}', file=sys.stderr)


def case(args):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'tools'))
    import explain_decision
    import fast_teacher
    fast_teacher.install()
    import budget_teacher
    game_dir = args.game_dir.expanduser()
    actor, seed, a_seats = explain_decision.actor_at(game_dir, args.step)
    spec = explain_decision.load_spec(game_dir, 'A' if actor in a_seats else 'B', None)
    budget_teacher.install(spec.get('comparisons', 2) if args.comparisons is None else args.comparisons)
    budget_teacher.set_horizon(spec.get('horizon_incomes', 1))
    module, _, name = spec['factory'].partition(':')
    teacher = getattr(importlib.import_module(module), name)(seed, **spec.get('kwargs', {}))
    result, snapshot, recorded = explain_decision.rebuild(game_dir, args.step, teacher)
    _, chosen = teacher.choose(snapshot)
    audit = teacher.last_audit or {}
    scores = audit.get('scores') or []
    candidates = snapshot['candidates']
    state = snapshot['state']
    player = state['players'][actor]
    res = player['resources']
    print(f"{game_dir.parent.name}/{game_dir.name} step {args.step} round {state['round']} seat {actor} {player['faction']} "
          f"VP {player['vp']} ore {res['ore']} credits {res['credits']} knowledge {res['knowledge']} qic {res['qic']} "
          f"power {res['power']['bowl1']}/{res['power']['bowl2']}/{res['power']['bowl3']}")
    plans = audit.get('plans') or []
    control = next((p for p in plans if p.get('goal') == 'current-choice'), None)
    print(f"played [{recorded}] {short(candidates[recorded]['action'])} | asked again [{chosen}] "
          f"{short(candidates[chosen]['action'])} | selected {audit.get('selected')}")
    for label, index in (('base', control['first'] if control else None), ('played', recorded)):
        if index is not None and scores:
            rank = sorted(range(len(scores)), key=lambda i: (-scores[i][0], i)).index(index) + 1
            reason = str(scores[index][1])[:160] if len(scores[index]) > 1 else ''
            print(f'  one-step score of the {label} move [{index}]: {scores[index][0]:.2f} (rank {rank} of {len(scores)}) {reason}')
    for plan in plans:
        end = plan.get('end_player') or {}
        value = plan.get('value')
        print(f"\n{plan.get('goal')} | first [{plan.get('first')}] | value {'' if value is None else f'{value:.2f}'} | "
              f"end VP {end.get('vp')} | end round {plan.get('end_round')} | complete {plan.get('complete')}")
        for a in (plan.get('actions') or [])[:args.line]:
            gain = a['vp_after'] - a['vp_before']
            print(f"    r{a['round']} {short(a['action'], 90)}" + (f'  VP {gain:+d}' if gain else ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    many = sub.add_parser('tally')
    many.add_argument('run_dirs', type=Path, nargs='+')
    many.add_argument('--jobs', type=int, default=6)
    many.add_argument('--top', type=int, default=20)
    many.add_argument('--examples', type=int, default=4)
    one = sub.add_parser('case')
    one.add_argument('game_dir', type=Path)
    one.add_argument('step', type=int)
    one.add_argument('--comparisons', type=int)
    one.add_argument('--line', type=int, default=16)
    args = parser.parse_args()
    (tally if args.command == 'tally' else case)(args)


if __name__ == '__main__':
    main()
