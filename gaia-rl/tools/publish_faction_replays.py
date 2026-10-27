"""Export and publish one replay per distinct game from a lab run; games are chosen as the seat per faction whose 1-3 round charges are closest to that faction's median.

Usage (cwd gaia-rl/): python tools/publish_faction_replays.py runs/<lab run> --destination <dir> [--output <work dir>] [--also PAIR/GAME ...]
"""
import argparse
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import json
import tempfile

GAIA_RL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pick_median_seats(seats):
    """seats: {"pair/game": [{faction, arm, charges}, ...]} (list index = seat).
    Returns {faction: (game, seat, charges, median)}, the seat closest to the faction's median (ties: first seen)."""
    by_faction = {}
    for game, entries in seats.items():
        for seat, entry in enumerate(entries):
            by_faction.setdefault(entry['faction'], []).append((game, seat, entry['charges']))
    picks = {}
    for faction, rows in by_faction.items():
        median = statistics.median(charges for _, _, charges in rows)
        game, seat, charges = min(rows, key=lambda row: abs(row[2] - median))
        picks[faction] = (game, seat, charges, median)
    return picks


def group_by_game(picks):
    """picks: pick_median_seats output. Returns {game: [(faction, seat, charges, median), ...]}, each list sorted by faction."""
    games = {}
    for faction, (game, seat, charges, median) in picks.items():
        games.setdefault(game, []).append((faction, seat, charges, median))
    return {game: sorted(rows, key=lambda row: row[0]) for game, rows in games.items()}


def run(command, env):
    return subprocess.run(command, cwd=GAIA_RL, env=env).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--also', action='append', default=[], metavar='PAIR/GAME',
                        help='extra game (e.g. pair-001/game-0-A23) to republish with --focus best, so a game that is not a median pick is kept when old files of the run are taken down')
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    destination = args.destination.resolve()
    output = (args.output or Path(f'/tmp/faction-replays-{run_dir.name}')).resolve()
    seats = json.loads((run_dir/'charges.json').read_text())['seats']
    picks = pick_median_seats(seats)

    env = {**os.environ, 'GAIA_ENGINE_FIXES_2': '1', 'PYTHONPATH': 'python:tools'}
    failed = False
    # ab_replays export refuses an existing output directory and writes its own index.json, so each pick
    # exports into its own part directory and the parts are merged into one source for a single publish.
    # Each run works in its own fresh folder under output (a previous run's parts would make the export refuse),
    # so nothing already under a user-supplied --output is ever deleted.
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=output))
    parts = work/'parts'
    merged = work/'merged'
    merged.mkdir(parents=True)
    catalog = []
    from publish_replays import read_catalog, write_catalog
    def export_game(game, focus):
        part = parts/game.replace('/', '-')
        if run([sys.executable, 'tools/ab_replays.py', 'export', str(run_dir/game),
                '--output', str(part), '--focus', str(focus)], env) != 0:
            return False
        for item in read_catalog(part/'index.json'):
            shutil.copy2(part/item['file'], merged/item['file'])
            catalog.append(item)
        return True

    grouped = group_by_game(picks)
    for game, reps in sorted(grouped.items()):
        # min is stable, so ties go to the first faction in the sorted list.
        focus = min(reps, key=lambda row: abs(row[2] - row[3]))[1]
        listed = ', '.join(f'{faction} seat {seat} (charges {charges:.1f}, median {median:.1f})'
                           for faction, seat, charges, median in reps)
        print(f'{game}: focus seat {focus}; representatives {listed}', flush=True)
        if not export_game(game, focus):
            failed = True
    for game in args.also:
        if game in grouped:
            continue
        print(f'{game}: focus best; extra (--also)', flush=True)
        if not export_game(game, 'best'):
            failed = True
    if failed:
        print('export failed; nothing published', file=sys.stderr)
        return 1
    write_catalog(merged/'index.json', catalog)
    if run([sys.executable, 'tools/publish_replays.py', '--source', str(merged),
            '--destination', str(destination), '--replace-same-experiment'], env) != 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
