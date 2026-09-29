"""Measure where one teacher decision spends its time, without changing the teacher.

Two sub-commands:

  states   Play one seed with the frozen-A quick reserve (cheap, deterministic
           because every eligible candidate is evaluated) and save native action
           prefixes for a few ActionPhase decisions.
  profile  Rebuild each saved state natively and run the teacher's own
           `four_factions.preparation.search` in-process for a fixed wall budget.
           Reports when the root ranking finished (before that point a real game
           would use the quick fallback), how many horizon comparisons completed,
           and a cProfile breakdown by function family.

The teacher source tree is chosen with PYTHONPATH (e.g. baseline-teacher-20260917
for A, state-teacher-bghi-20260918 plus its flags for B). Nothing is written to
the teacher trees; output paths must be new.
"""
import argparse
import cProfile
import json
import math
import pstats
import time
from pathlib import Path

from gaia_rl import Environment


def replay(seed, prefix):
    env = Environment(seed, 2000)
    for index in prefix:
        snapshot = json.loads(env.snapshot_json())
        env.step(snapshot['decision_id'], index)
    return env


def states(args):
    from four_factions.quick import fallback
    env = Environment(args.seed, 2000)
    prefix, saved = [], []
    wanted = set(args.at)
    while not env.is_terminal() and len(saved) < len(wanted):
        snapshot = json.loads(env.snapshot_json())
        phase = snapshot['state']['phase']
        if len(prefix) >= min(wanted) and isinstance(phase, dict) and 'ActionPhase' in phase \
                and len(snapshot['candidates']) > 1 and any(len(prefix) >= w for w in wanted - {s['requested'] for s in saved}):
            target = min(w for w in wanted - {s['requested'] for s in saved} if len(prefix) >= w)
            saved.append({'requested': target, 'step': len(prefix), 'round': snapshot['state']['round'],
                          'player': snapshot['player'], 'candidates': len(snapshot['candidates']),
                          'prefix': list(prefix)})
        if len(snapshot['candidates']) == 1:
            index = 0
        else:
            # A generous deadline makes the reserve score every eligible candidate.
            index = fallback(env, snapshot, {}, deadline=time.monotonic()+60)['index']
        env.step(snapshot['decision_id'], index)
        prefix.append(index)
    Path(args.output).write_text(json.dumps({'seed': args.seed, 'states': saved}, indent=1))
    for s in saved:
        print(s['requested'], 'step', s['step'], 'round', s['round'], 'candidates', s['candidates'])


FAMILIES = (
    ('native snapshot_json', lambda f, n: 'snapshot_json' in n),
    ('json.loads', lambda f, n: n.startswith('<method \'decode\'') or 'loads' in n and 'json' in f),
    ('json.dumps', lambda f, n: 'encode' in n and 'json' in f or n == 'dumps'),
    ('native fork', lambda f, n: "'fork'" in n or n.endswith('.fork>')),
    ('native step', lambda f, n: "'step'" in n or n.endswith('.step>')),
    ('native evaluation_*', lambda f, n: 'evaluation_' in n and '<built-in' in n),
    ('deepcopy', lambda f, n: 'copy.py' in f),
)


def family_seconds(stats):
    totals = {name: 0.0 for name, _ in FAMILIES}
    calls = {name: 0 for name, _ in FAMILIES}
    for (filename, _, name), (_, ncalls, tottime, _, _) in stats.stats.items():
        label = f'{filename}:{name}' if filename != '~' else name
        for family, match in FAMILIES:
            if match(filename, label):
                totals[family] += tottime
                calls[family] += ncalls
                break
    return totals, calls


def run_search(env, snapshot, budget, adaptive):
    from four_factions.preparation import search, SearchExpired
    events = []
    started = time.monotonic()

    def publish(result):
        events.append({'t': time.monotonic()-started, 'plans': len(result.get('plans', ())),
                       'index': result['index'], 'selected': result.get('selected')})
    try:
        search(env, snapshot, {}, publish, soft_deadline=started+budget, hard_deadline=started+budget,
               bgg_openings=True, shared_factions=True, adaptive=adaptive,
               allocation=(lambda: started+budget) if adaptive else None)
        stop = 'returned'
    except SearchExpired:
        stop = 'expired'
    return {'root_ranked_at': events[0]['t'] if events else None,
            'root_ranked_within_budget': bool(events),
            'completed_comparisons': events[-1]['plans'] if events else 0,
            'publishes': len(events), 'stop': stop,
            'selected': events[-1]['selected'] if events else None,
            'elapsed': time.monotonic()-started}


def profile(args):
    data = json.loads(Path(args.states).read_text())
    rows = []
    for state in data['states']:
        env = replay(data['seed'], state['prefix'])
        snapshot = json.loads(env.snapshot_json())
        plain = run_search(env, snapshot, args.budget, args.adaptive)
        if args.no_profile:
            rows.append({**{k: state[k] for k in ("requested", "step", "round", "player", "candidates")}, "plain": plain})
            print(json.dumps(rows[-1]), flush=True)
            continue
        profiler = cProfile.Profile()
        profiler.enable()
        profiled = run_search(env, snapshot, args.budget, args.adaptive)
        profiler.disable()
        stats = pstats.Stats(profiler)
        totals, calls = family_seconds(stats)
        top = sorted(((v[2], k) for k, v in stats.stats.items()), reverse=True)[:args.top]
        row = {**{k: state[k] for k in ('requested', 'step', 'round', 'player', 'candidates')},
               'plain': plain, 'profiled': profiled,
               'profiled_total_tottime': sum(v[2] for v in stats.stats.values()),
               'families_tottime': totals, 'families_calls': calls,
               'top_tottime': [{'seconds': round(t, 3), 'function': f'{k[0]}:{k[1]}:{k[2]}'} for t, k in top]}
        rows.append(row)
        print(json.dumps({k: row[k] for k in ('step', 'round', 'candidates', 'plain')}), flush=True)
    Path(args.output).write_text(json.dumps({'budget_seconds': args.budget, 'adaptive': args.adaptive,
                                             'rows': rows}, indent=1))


def micro(args):
    """Per-call cost of the native and evaluation primitives on saved states."""
    from four_factions.preparation import leaf_value
    import four_factions.preparation as preparation
    data = json.loads(Path(args.states).read_text())
    out = []
    for state in data['states']:
        env = replay(data['seed'], state['prefix'])
        snapshot = json.loads(env.snapshot_json())
        n = 200

        def timed(fn, repeat=n):
            t = time.perf_counter()
            for _ in range(repeat):
                fn()
            return (time.perf_counter()-t)/repeat*1e3
        text = env.snapshot_json()
        actor = snapshot['player']
        root = snapshot['state']['players'][actor]
        row = {'step': state['step'], 'round': state['round'], 'candidates': state['candidates'],
               'snapshot_bytes': len(text),
               'ms_snapshot_json': timed(env.snapshot_json),
               'ms_json_loads': timed(lambda: json.loads(text)),
               'ms_fork': timed(lambda: env.fork(snapshot['decision_id'], 0)),
               'ms_fork_step_snapshot_loads': timed(lambda: json.loads(env.fork(snapshot['decision_id'], 0).snapshot_json())),
               'ms_leaf_value': timed(lambda: leaf_value(snapshot, actor, root), 20)}
        policies = preparation.Policies({}, cache=preparation.PolicyCache(), shared_factions=True)
        t = time.perf_counter()
        policies.rank(env, snapshot)
        row['ms_rank_once'] = (time.perf_counter()-t)*1e3
        out.append(row)
        print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()}), flush=True)
    Path(args.output).write_text(json.dumps(out, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('states')
    p.add_argument('--seed', default='state-evaluation-ab-20260917-1580')
    p.add_argument('--at', type=int, nargs='+', default=[40, 80, 120, 160])
    p.add_argument('--output', required=True)
    p = sub.add_parser('profile')
    p.add_argument('--states', required=True)
    p.add_argument('--budget', type=float, default=10.0)
    p.add_argument('--adaptive', action='store_true')
    p.add_argument('--top', type=int, default=25)
    p.add_argument('--no-profile', action='store_true')
    p.add_argument('--output', required=True)
    p = sub.add_parser('micro')
    p.add_argument('--states', required=True)
    p.add_argument('--output', required=True)
    args = parser.parse_args()
    for path in (args.output,):
        if Path(path).exists():
            parser.error('output must not already exist')
    {'states': states, 'profile': profile, 'micro': micro}[args.command](args)


if __name__ == '__main__':
    main()
