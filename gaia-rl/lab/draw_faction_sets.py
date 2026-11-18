"""Draw the fixed list of faction sets for the fixed-seed ladder (HANDOFF E178, E180).

Every game has four factions from four different faction boards (the two sides of one board never meet),
every faction appears at least once and the counts are even (floor or ceil of seats / 18), no set repeats.
The draw is deterministic in --draw-seed; the list is drawn once and reused before and after every teacher fix.

  draw_faction_sets.py --games 12 --draw-seed <text> --map-seed <seed> --output <json>
"""
import argparse
import json
import random
from collections import Counter
from pathlib import Path

BOARDS = (('Terrans', 'Lantids'), ('Xenos', 'Gleens'), ('Taklons', 'Ambas'), ('HadschHallas', 'Ivits'), ('Geodens', 'BalTaks'), ('Firaks', 'Bescods'), ('Nevlas', 'Itars'), ('Tinkeroids', 'Darkanians'), ('Moweyds', 'SpaceGiants'))   # gaia-engine/src/game_state.rs other_board_side


def draw(games, draw_seed):
    rng = random.Random(draw_seed)
    factions = [f for board in BOARDS for f in board]
    board_of = {f: i for i, board in enumerate(BOARDS) for f in board}
    seats = games * 4
    base, extra = divmod(seats, len(factions))
    for attempt in range(1, 1000001):
        pool = factions * base + rng.sample(factions, extra)
        rng.shuffle(pool)
        sets = [pool[i:i + 4] for i in range(0, seats, 4)]
        if all(len({board_of[f] for f in s}) == 4 for s in sets) and len({frozenset(s) for s in sets}) == games:
            return sets, attempt
    raise SystemExit('no draw satisfies the constraints')


def check(sets):
    """Independent re-check of the constraints; returns the Counter of appearances."""
    side = {}
    for i, board in enumerate(BOARDS):
        for f in board:
            side[f] = i
    for s in sets:
        assert len(s) == 4 and all(f in side for f in s), s
        assert len({side[f] for f in s}) == 4, s
    assert len({frozenset(s) for s in sets}) == len(sets), 'repeated set'
    counts = Counter(f for s in sets for f in s)
    assert set(counts) == set(side), 'a faction is missing'
    assert max(counts.values()) - min(counts.values()) <= 1, counts
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games', type=int, default=12)
    ap.add_argument('--draw-seed', required=True)
    ap.add_argument('--map-seed', required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    sets, attempts = draw(a.games, a.draw_seed)
    counts = check(sets)
    out = {
        'purpose': 'fixed-seed ladder: faction sets, one per game, seat order as listed; reused before and after every teacher fix (HANDOFF E178, E180)',
        'map_seed': a.map_seed,
        'draw_seed': a.draw_seed,
        'attempts': attempts,
        'games': sets,
        'counts': dict(sorted(counts.items())),
    }
    a.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for i, s in enumerate(sets, 1):
        print(i, ' '.join(s))
    print(out['counts'])
    print('attempts', attempts)


if __name__ == '__main__':
    main()
