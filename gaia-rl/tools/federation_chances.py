"""How often a seat could form a federation and what it played instead, per round.

User 2026-10-19 "교사가 아직도 연방을 3개도 못만든다고?": replays each game with snapshots and, at every
action-phase decision, checks whether a FormFederation candidate was legal. Counts per faction and
round: decisions with a legal federation, federations formed, and the move types played instead.

  .venv/bin/python tools/federation_chances.py ~/projects/gaia-lab/gaia-rl/runs/lab-084-ships-vs-byfaction-full
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--list', metavar='TYPE', help='also print each decision that played TYPE while a '
                        'federation was legal (game, 0-based step, round, seat, faction)')
    args = parser.parse_args()
    from gaia_rl import Environment
    chances = Counter()        # (faction, round) -> decisions with a legal federation
    formed = Counter()         # (faction, round) -> federations formed
    seats = Counter()          # faction -> seat-games
    first_chance = defaultdict(list)   # faction -> round of the seat's first legal federation
    instead = defaultdict(Counter)     # faction -> move types played while a federation was legal
    cheapest = defaultdict(list)       # faction -> fewest satellites among the legal federations, per decision
    used = defaultdict(list)           # faction -> (satellites, buildings, fewest legal) of each formed one
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)
        seen = {}
        for faction in result['factions']:
            seats[faction] += 1
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        for step, row in enumerate(rows):
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if 'ActionPhase' in str(state['phase']) and snapshot.get('player') is not None:
                seat = snapshot['player']
                faction = state['players'][seat]['faction']
                feds = [c['action'] for c in snapshot['candidates'] if c['action'].get('type') == 'FormFederation']
                legal = bool(feds)
                chosen = snapshot['candidates'][row['index']]['action']
                played = chosen.get('type')
                if legal:
                    cheapest[faction].append(min(len(a.get('satellite_hexes', [])) for a in feds))
                if played == 'FormFederation':
                    used[faction].append((len(chosen.get('satellite_hexes', [])), len(chosen.get('hexes', [])),
                                          min(len(a.get('satellite_hexes', [])) for a in feds)))
                if legal:
                    chances[(faction, state['round'])] += 1
                    if seat not in seen:
                        seen[seat] = state['round']
                        first_chance[faction].append(state['round'])
                    if played != 'FormFederation':
                        instead[faction][played] += 1
                    if played == args.list:
                        arm = 'A' if seat in result['a_seats'] else 'B'
                        print(f"{game_dir.relative_to(args.run_dir.expanduser())} step {step} R{state['round']} "
                              f"seat {seat} {faction} ({arm})")
                if played == 'FormFederation':
                    formed[(faction, state['round'])] += 1
            env.step(row['decision_id'], row['index'])
        for seat, faction in enumerate(result['factions']):
            if seat not in seen:
                first_chance[faction].append(None)
    print('per seat-game: decisions with a legal federation / federations formed, by round')
    print(f"{'':14s}" + ''.join(f'{"R"+str(r):>11}' for r in range(1, 7)) + f"{'never legal':>13}")
    for faction in sorted(seats):
        n = seats[faction]
        cells = ''.join(f'{chances[(faction, r)]/n:>6.1f}/{formed[(faction, r)]/n:<4.1f}' for r in range(1, 7))
        never = sum(r is None for r in first_chance[faction])
        print(f'{faction:14s}{cells}{never:>8}/{n}')
    print('\nsatellites: formed federations (mean satellites / buildings / fewest legal at that decision), '
          'and the fewest-satellite legal federation at every decision with one')
    for faction in sorted(seats):
        formed_rows = used[faction]
        mean = (lambda i: sum(r[i] for r in formed_rows)/len(formed_rows)) if formed_rows else (lambda i: float('nan'))
        dist = Counter(cheapest[faction])
        print(f'{faction:14s}formed {len(formed_rows):>3}: sat {mean(0):.1f} / bld {mean(1):.1f} / fewest {mean(2):.1f}'
              f'   fewest legal: ' + ', '.join(f'{k} sat x{v}' for k, v in sorted(dist.items())))
    print('\nmoves played while a federation was legal (top 6)')
    for faction in sorted(instead):
        print(f'{faction:14s}' + ', '.join(f'{k} {v}' for k, v in instead[faction].most_common(6)))


if __name__ == '__main__':
    main()
