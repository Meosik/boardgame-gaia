"""Basics per arm and faction over a lab/teacher_ab run: held resources, income and passes in rounds 1-3.

User (2026-10-22, "기본기 — 수입 늘리기·불필요한 자원 소모 줄이기"), HANDOFF E86 (ㄷ): next to the charge
table every A/B result shows how the seats handled the basics. Per seat: the ore/credits/knowledge/QIC
held at the round-4 start (stock4); the income of rounds 1-3 per resource, i.e. the change from the last
action-phase snapshot of round N-1 to the first of round N for N = 2, 3, 4 (across the income and Gaia
phases, so the last pass action, which gives no ore/credits/knowledge/QIC, is excluded); and, per
pass in rounds 1-3, the builds the seat made earlier that round and the resources it still held.
Secondary indicator only: the verdict stays the rounds 1-3 charge table (charge_rounds.py).

  .venv/bin/python tools/basics_rounds.py ~/projects/gaia-lab/gaia-rl/runs/lab-036-... [--json out.json]
"""
import argparse
import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]

from charge_rounds import round_started

KEYS = ('ore', 'credits', 'knowledge', 'qic')
BUILD_TYPES = ('Build', 'Upgrade', 'RoundBoosterTerraformBuild', 'RoundBoosterRangeBuild', 'TwilightRangeBuild')


def held(state, seat):
    return {k: state['players'][seat]['resources'][k] for k in KEYS}


def game_basics(game_dir):
    """(result, {seat: {'stock4', 'income', 'passes'}}) or (result, None) if round 4 is never reached."""
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    first, last = {}, {}   # round -> {seat: resources} at its first / last action-phase snapshot
    builds = defaultdict(int)   # (seat, round) -> builds so far
    passes = defaultdict(list)
    for row in rows + [None]:
        snap = json.loads(env.snapshot_json())
        state = snap['state']
        seats = range(len(state['players']))
        for n in (1, 2, 3, 4):
            if round_started(state, n):
                now = {s: held(state, s) for s in seats}
                first.setdefault(n, now)
                if n < 4 and not round_started(state, n+1):
                    last[n] = now
        if 4 in first or row is None:
            break
        action = snap['candidates'][row['index']].get('action') or {}   # phase candidates carry no action
        seat, rnd = snap['player'], state['round']
        if action.get('type') == 'Pass' and rnd <= 3 and seat is not None:
            passes[seat].append({'round': rnd, 'builds': builds[seat, rnd], 'resources': held(state, seat)})
        elif action.get('type') in BUILD_TYPES:
            builds[seat, rnd] += 1
        env.step(row['decision_id'], row['index'])
    if 4 not in first:
        return result, None
    return result, {s: {'stock4': first[4][s],
                        'income': {k: sum(first[n][s][k]-last[n-1][s][k] for n in (2, 3, 4)) for k in KEYS},
                        'passes': passes[s]} for s in first[4]}


def mean(values):
    return sum(values)/len(values) if values else float('nan')


def arm_row(seats):
    """Mean over the seats of one arm of a faction ([seat record, ...])."""
    passes = [p for s in seats for p in s['passes']]
    parts = {k: mean([p['resources'][k] for p in passes]) for k in KEYS}
    return {'stock4': {k: mean([s['stock4'][k] for s in seats]) for k in KEYS},
            'income': {k: mean([s['income'][k] for s in seats]) for k in KEYS},
            'pass_builds': mean([p['builds'] for p in passes]),
            'pass_stock': mean([sum(p['resources'][k] for k in KEYS) for p in passes]),
            'pass_parts': parts}


def summarize(records):
    """{faction: {'pairs', 'A', 'B'}} from {(pair, faction): {arm: seat record}}; only pairs with both arms."""
    table = {}
    for faction in sorted({f for _, f in records}):
        both = [arms for (_, f), arms in records.items() if f == faction and len(arms) == 2]
        table[faction] = {'pairs': len(both)}
        for arm in 'AB':
            table[faction][arm] = arm_row([arms[arm] for arms in both]) if both else None
    return table


def text_table(table):
    quad = lambda d: '/'.join(f'{d[k]:.1f}' for k in KEYS)
    lines = [f"{'faction':<9} {'pairs':>5}  {'stock at R4 (ore/cr/kn/qic) A | B':<44} {'income R1-3 A | B':<44} builds A|B  pass stock A|B"]
    for faction, r in table.items():
        if not r['pairs']:
            lines.append(f"{faction:<9} {0:>5}")
            continue
        a, b = r['A'], r['B']
        lines.append(f"{faction:<9} {r['pairs']:>5}  {quad(a['stock4'])} | {quad(b['stock4'])}   "
                     f"{quad(a['income'])} | {quad(b['income'])}   {a['pass_builds']:.1f}|{b['pass_builds']:.1f}   "
                     f"{a['pass_stock']:.1f}|{b['pass_stock']:.1f}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--json', type=Path, help='Also write the table here (lab.py reads it)')
    args = parser.parse_args()
    records = defaultdict(dict)
    incomplete = 0
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result, values = game_basics(game_dir)
        if values is None:
            continue
        incomplete += not result.get('complete', True)
        factions = list(result.get('factions') or [])
        if not factions:
            from gaia_rl import Environment
            state = json.loads(Environment(result['seed'], 2000).snapshot_json())['state']
            factions = [p['faction'] for p in state['players']]
        for seat, record in values.items():
            arm = 'A' if seat in result['a_seats'] else 'B'
            records[(game_dir.parent.name, factions[seat])][arm] = record
    table = summarize(records)
    print(text_table(table))
    if args.json:
        args.json.write_text(json.dumps({'factions': table, 'games_incomplete': incomplete}, indent=1)+'\n')


if __name__ == '__main__':
    main()
