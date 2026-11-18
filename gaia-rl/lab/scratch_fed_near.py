"""What did the seats that ended 1-2 power short of a second federation do in rounds 5-6 (HANDOFF E175 (a))?

Reads runs/fed-why-93/seats.json (scratch_fed_why.py), takes the seats that stopped at one federation and were short by
1 or 2 at their last main turn of round 6, replays their games (snapshots only) and counts, for rounds 5 and 6:
  the main actions played (by type), the resources left at the round's Pass, and at each main-turn decision whether
  a candidate that adds building power existed (a new mine or an upgrade) and what was played instead.
A building adds to the second federation only when it lands outside the first one; that is not decided here
(a mine next to the federation joins it), so "a build candidate existed" is an upper bound on what was possible.

  scratch_fed_near.py <seats.json> <run dir> [<run dir> ...] [--gaps 1 2] [--examples N]
"""
import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

MINES = ('Build', 'EclipseAsteroidMine', 'RoundBoosterTerraformBuild', 'TwilightRangeBuild', 'SpaceshipCreditTerraform')
BUILD = MINES + ('Upgrade', 'TwilightFreeResearchLab', 'RebellionFreeTradingStation')
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


def label(action):
    kind = action.get('type')
    for key in ('to', 'kind', 'track', 'id'):
        if key in action and isinstance(action[key], (str, dict, int)):
            value = action[key] if not isinstance(action[key], dict) else next(iter(action[key]))
            return f'{kind}:{value}'
    return kind


def adds_outside(action, federated):
    """The candidate raises the power value outside the seat's federation: a mine not next to it (a mine next to
    a federation joins it), or an upgrade of a building outside it to a higher power value (mine -> trading
    station, trading station -> institute, lab -> academy; trading station -> lab stays at 2)."""
    kind, coord = action.get('type'), action.get('coord')
    if kind not in BUILD or coord is None or coord in federated:
        return False
    if kind in MINES:
        q, r = (int(v) for v in coord.split(','))
        return not any(f'{q+dq},{r+dr}' in federated for dq, dr in NEIGHBOURS)
    if kind == 'Upgrade':
        to = action['to'] if isinstance(action['to'], str) else next(iter(action['to']))
        return to != 'ResearchLab'
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('seats', type=Path)
    parser.add_argument('run_dirs', type=Path, nargs='+')
    parser.add_argument('--gaps', type=int, nargs='+', default=[1, 2])
    parser.add_argument('--examples', type=int, default=6)
    parser.add_argument('--keys', action='store_true', help='print one example action per type and stop after 3 games')
    args = parser.parse_args()
    from gaia_rl import Environment
    wanted = defaultdict(dict)
    for s in json.loads(args.seats.read_text()):
        r6 = s['rounds'].get('6')
        if s['formed'] == 1 and r6 and r6['stage'] == 1 and r6['need'] - r6['total'] in args.gaps:
            wanted[s['game']][s['seat']] = s
    print('seats', sum(len(v) for v in wanted.values()), 'in games', len(wanted))
    played = {5: Counter(), 6: Counter()}
    instead = {5: Counter(), 6: Counter()}
    left = {5: [], 6: []}
    with_build = {5: [0, 0], 6: [0, 0]}                      # decisions, of them with a build/upgrade candidate
    pass_with_build = {5: 0, 6: 0}
    passes = {5: 0, 6: 0}
    examples, shapes, lines = [], {}, []
    games = 0
    for run_dir in args.run_dirs:
        for game_dir in sorted(run_dir.expanduser().glob('pair-*/game-*')):
            name = f"{game_dir.parent.parent.name[4:7]} {game_dir.parent.name}/{game_dir.name}"
            if name not in wanted:
                continue
            games += 1
            if args.keys and games > 3:
                break
            result = json.loads((game_dir/'result.json').read_text())
            env = Environment(result['seed'], 2000)
            with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
                rows = [json.loads(line) for line in f]
            history = defaultdict(list)
            for step, row in enumerate(rows):
                snapshot = json.loads(env.snapshot_json())
                state = snapshot['state']
                seat = snapshot.get('player')
                if ('ActionPhase' in str(state['phase']) and seat in wanted[name] and state['round'] in (5, 6)):
                    actions = [c['action'] for c in snapshot['candidates']]
                    types = [a.get('type') for a in actions]
                    if 'Pass' in types:
                        round_ = state['round']
                        action = actions[row['index']]
                        for a in actions:
                            shapes.setdefault(a.get('type'), a)
                        kind = label(action)
                        if action.get('type') != 'FreeAction':
                            played[round_][kind] += 1
                        player = next(p for p in state['players'] if p['player_id'] == seat)
                        federated = set(player['federated_hexes'])
                        build = sorted({label(a) for a in actions if adds_outside(a, federated)})
                        with_build[round_][0] += 1
                        if build:
                            with_build[round_][1] += 1
                            if not adds_outside(action, federated) and action.get('type') != 'FreeAction':
                                instead[round_][kind] += 1
                        if adds_outside(action, federated):
                            played[round_]['(adds power outside the federation)'] += 1
                        res = player['resources']
                        history[seat].append((round_, step, kind, res['ore'], res['credits'], res['knowledge'], res['qic'],
                                              res['power']['bowl3'], len(build)))
                        if action.get('type') == 'Pass':
                            passes[round_] += 1
                            pass_with_build[round_] += bool(build)
                            left[round_].append((res['ore'], res['credits'], res['knowledge'], res['qic'], res['power']['bowl3']))
                            if round_ == 6:
                                s = wanted[name][seat]
                                examples.append((bool(build), res['ore'], name, seat, s['faction'], step, build[:6],
                                                 (res['ore'], res['credits'], res['knowledge'], res['qic'], res['power']['bowl3']),
                                                 f"power outside {s['rounds']['6']['total']} of {s['rounds']['6']['need']}, "
                                                 f"satellite funds {s['rounds']['6']['funds']}"))
                env.step(row['decision_id'], row['index'])
            for seat, items in history.items():
                lines.append((name, seat, wanted[name][seat]['faction'], items))
    if args.keys:
        for kind, action in sorted(shapes.items()):
            print(kind, json.dumps(action)[:260])
        return
    for round_ in (5, 6):
        print(f"\nR{round_}: main actions played {sum(played[round_].values())}: {played[round_].most_common(14)}")
        print(f"  main-turn decisions {with_build[round_][0]}, with a mine/upgrade candidate {with_build[round_][1]}; "
              f"played instead of building at those: {instead[round_].most_common(10)}")
        rows = left[round_]
        if rows:
            means = [round(sum(r[i] for r in rows)/len(rows), 2) for i in range(5)]
            print(f"  at Pass ({passes[round_]} seats): mean ore {means[0]} credits {means[1]} knowledge {means[2]} qic {means[3]} "
                  f"bowl3 {means[4]} | Pass with a mine/upgrade candidate still legal: {pass_with_build[round_]}")
    examples.sort(reverse=True)
    print('\nR6 Pass examples (a build candidate legal, most ore first):')
    for row in examples[:args.examples]:
        print(f"  {row[2]} seat {row[3]} {row[4]} step {row[5]} left ore/credits/knowledge/qic/bowl3 {row[7]} candidates {row[6]} | {row[8]}")
    legal = [row for row in examples if row[0]]
    print(f"R6 Pass with such a candidate legal: {len(legal)} seats, short by 1: "
          f"{sum('power outside 6 of 7' in row[8] or 'power outside 5 of 6' in row[8] for row in legal)} | "
          f"satellite funds 0: {sum(row[8].endswith('funds 0') for row in legal)} | ore >= 6: {sum(row[1] >= 6 for row in legal)}")
    shown = {(row[2], row[3]) for row in examples[:3]}
    for name, seat, faction, items in lines:
        if (name, seat) in shown:
            print(f"\n{name} seat {seat} {faction}: round step action (ore credits knowledge qic bowl3 before | build candidates)")
            for item in items:
                if not item[2].startswith('FreeAction'):
                    print(f"  R{item[0]} {item[1]} {item[2]} ({item[3]} {item[4]} {item[5]} {item[6]} {item[7]} | {item[8]})")


if __name__ == '__main__':
    main()
