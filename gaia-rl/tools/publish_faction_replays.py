"""Export and publish one replay per faction from a lab run: the seat whose 1-3 round charges are closest to that faction's median.

Usage (cwd gaia-rl/): python tools/publish_faction_replays.py runs/<lab run> --destination <dir> [--output <work dir>]
"""
import argparse
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import json

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


def run(command, env):
    return subprocess.run(command, cwd=GAIA_RL, env=env).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--output', type=Path)
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
    parts = output/'parts'
    merged = output/'merged'
    merged.mkdir(parents=True, exist_ok=True)
    catalog = []
    from publish_replays import read_catalog, write_catalog
    for faction, (game, seat, charges, median) in sorted(picks.items()):
        print(f'{faction}: {game} seat {seat} charges {charges} median {median}', flush=True)
        part = parts/faction.lower().replace(' ', '-')
        if run([sys.executable, 'tools/ab_replays.py', 'export', str(run_dir/game),
                '--output', str(part), '--focus', str(seat)], env) != 0:
            failed = True
            continue
        for item in read_catalog(part/'index.json'):
            shutil.copy2(part/item['file'], merged/item['file'])
            catalog.append(item)
    if failed:
        print('export failed; nothing published', file=sys.stderr)
        return 1
    write_catalog(merged/'index.json', catalog)
    if run([sys.executable, 'tools/publish_replays.py', '--source', str(merged),
            '--destination', str(destination)], env) != 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
