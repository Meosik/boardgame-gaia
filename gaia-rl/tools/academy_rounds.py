"""Round of each seat's first research lab, academy and planetary institute over a lab/teacher_ab run.

  .venv/bin/python tools/academy_rounds.py ~/projects/gaia-lab/gaia-rl/runs/lab-040-... [--games]

User (2026-10-07): the BGG openings say most factions take an academy in round 1; check whether
the AI ever does. Counts per arm and faction; --games prints every seat.
"""
import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

KINDS = {'ResearchLab': 'RL', 'Academy': 'AC', 'PlanetaryInstitute': 'PI'}


def kind_of(structure):
    kind = structure['kind']
    return KINDS.get(next(iter(kind)) if isinstance(kind, dict) else kind)


def first_rounds(game_dir):
    from gaia_rl import Environment
    result = json.loads((game_dir/'result.json').read_text())
    env = Environment(result['seed'], 2000)
    first = {}
    with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
        rows = [json.loads(line) for line in f]
    for row in rows + [None]:
        state = json.loads(env.snapshot_json())['state']
        for seat, player in enumerate(state['players']):
            for structure in player['structures']:
                kind = kind_of(structure)
                if kind:
                    first.setdefault((seat, kind), state['round'])
        if row is None:
            break
        env.step(row['decision_id'], row['index'])
    return result, first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run')
    parser.add_argument('--games', action='store_true')
    args = parser.parse_args()
    table = Counter()
    seats = Counter()
    for game_dir in sorted(Path(args.run).glob('pair-*/game-*')):
        result, first = first_rounds(game_dir)
        for seat, faction in enumerate(result['factions']):
            arm = 'A' if seat in result['a_seats'] else 'B'
            seats[arm, faction] += 1
            line = []
            for kind in ('RL', 'AC', 'PI'):
                found = first.get((seat, kind))
                if found is not None:
                    table[arm, faction, kind, found] += 1
                line.append(f'{kind} R{found}' if found is not None else f'{kind} -')
            if args.games:
                print(f'{game_dir.parent.name}/{game_dir.name} {faction:8} {arm}  ' + '  '.join(line))
    print('First built in round (seats; counted when it first appears after a move)')
    for arm, faction in sorted(seats):
        parts = []
        for kind in ('RL', 'AC', 'PI'):
            rounds = ' '.join(f'R{r}:{table[arm, faction, kind, r]}' for r in range(1, 7)
                              if table[arm, faction, kind, r])
            parts.append(f'{kind} [{rounds or "none"}]')
        print(f'{arm} {faction:8} n={seats[arm, faction]}  ' + '  '.join(parts))


if __name__ == '__main__':
    main()
