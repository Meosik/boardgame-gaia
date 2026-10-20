"""Which federation token each seat took, and which it passed over, in a lab run.

User 2026-10-20 ("토큰은 상황에 따라 바꾸고, 근데 구린 토큰이 있긴 한듯"): replays each game and, at every
FormFederation played, records the token taken and the other token kinds that were legal in the same
decision (the engine lists one FormFederation candidate per hex set and token). Counts per faction (or per
faction and arm) and round.

  .venv/bin/python tools/federation_token_counts.py ~/projects/gaia-lab/gaia-rl/runs/lab-090-ships-vs-tokens-full
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

# engine.rs federation_token_kind (ids 1-16)
TOKEN_NAMES = {1: '12VP', 2: '8VP+1QIC', 3: '8VP+2pw', 4: '7VP+2ore', 5: '7VP+6cr', 6: '6VP+2kn',
               7: '1ore1kn2cr', 8: 'LF 8VP+8cr', 9: 'LF 12VP', 10: 'LF 4VP+4kn', 11: 'LF 4VP+2ore1QIC',
               12: 'LF tech tile', 13: 'LF 7VP+2pw3', 14: 'LF mine 3 steps', 15: 'LF mine any range',
               16: 'Gleens PI'}


def token_label(state, token):
    """'<kind name>' for a supply token, '<ship>:<kind name>' for a spaceship's token."""
    if not isinstance(token, dict):
        return str(token)
    if 'ship' in token:
        ship = token['ship']
        kind = next((b['federation_token'] for b in state['spaceship_boards'] if b['id'] == ship), None)
        return f'{ship}:{TOKEN_NAMES.get(kind, kind)}'
    kind = token.get('kind')
    return TOKEN_NAMES.get(kind, str(kind))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--by-arm', action='store_true', help='count each faction per A/B arm')
    parser.add_argument('--list', action='store_true', help='print every federation: game, step, round, seat, '
                        'faction, token taken, tokens passed over, resources held')
    args = parser.parse_args()
    from gaia_rl import Environment
    taken = defaultdict(Counter)        # faction -> token label -> count
    offered = defaultdict(Counter)      # faction -> token label -> decisions where it was legal and not taken
    by_round = defaultdict(Counter)     # faction -> (round, token label)
    seats = Counter()
    skipped = []
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result = json.loads((game_dir/'result.json').read_text())
        if not result.get('complete'):
            continue
        env = Environment(result['seed'], 2000)

        def label(seat):
            faction = result['factions'][seat]
            if not args.by_arm:
                return faction
            return f"{faction} {'A' if seat in result['a_seats'] else 'B'}"
        with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        game_taken, game_offered, game_rounds = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
        replayed = True
        for step, row in enumerate(rows):
            snapshot = json.loads(env.snapshot_json())
            state = snapshot['state']
            if 'ActionPhase' in str(state['phase']) and snapshot.get('player') is not None:
                if row['index'] >= len(snapshot['candidates']):
                    replayed = False          # an older engine wrote this game; its moves no longer line up
                    break
                chosen = snapshot['candidates'][row['index']]['action']
                if chosen.get('type') == 'FormFederation':
                    seat = snapshot['player']
                    faction = label(seat)
                    mine = token_label(state, chosen.get('token'))
                    others = {token_label(state, c['action'].get('token'))
                              for c in snapshot['candidates'] if c['action'].get('type') == 'FormFederation'}
                    others.discard(mine)
                    game_taken[faction][mine] += 1
                    game_rounds[faction][(state['round'], mine)] += 1
                    for other in others:
                        game_offered[faction][other] += 1
                    if args.list:
                        res = state['players'][seat]['resources']
                        held = ' '.join(f'{k}{res.get(k, 0)}' for k in ('ore', 'credits', 'knowledge', 'qic'))
                        print(f"{game_dir.relative_to(args.run_dir.expanduser())} step {step} R{state['round']} "
                              f"seat {seat} {faction}: took {mine}; passed over {sorted(others)}; held {held}")
            try:
                env.step(row['decision_id'], row['index'])
            except RuntimeError:
                replayed = False              # same: the recorded index no longer exists on this engine
                break
        if not replayed:
            skipped.append(game_dir.name)
            continue
        for seat in range(len(result['factions'])):
            seats[label(seat)] += 1
        for faction in game_taken:
            taken[faction].update(game_taken[faction])
            offered[faction].update(game_offered[faction])
            by_round[faction].update(game_rounds[faction])
    if skipped:
        print(f'skipped {len(skipped)} games that no longer replay on this engine')
    print('federation tokens taken per faction (count, and in brackets how often that token was legal but '
          'another was taken)')
    for faction in sorted(seats):
        total = sum(taken[faction].values())
        parts = [f'{name} {n}' + (f' [{offered[faction][name]}]' if offered[faction][name] else '')
                 for name, n in taken[faction].most_common()]
        passed = [f'{name} [{n}]' for name, n in offered[faction].most_common() if name not in taken[faction]]
        print(f'{faction:14s}{total:>3} in {seats[faction]} seat-games: ' + ', '.join(parts + passed))
    print('\nby round')
    for faction in sorted(seats):
        cells = defaultdict(list)
        for (rnd, name), n in sorted(by_round[faction].items()):
            cells[rnd].append(f'{name} {n}')
        print(f'{faction:14s}' + '  '.join(f'R{r}: ' + ', '.join(cells[r]) for r in sorted(cells)))


if __name__ == '__main__':
    main()
