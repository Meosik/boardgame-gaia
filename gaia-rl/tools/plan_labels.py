"""Count the selected plan labels per arm and faction over a lab/teacher_ab run.

Reads `decisions.jsonl.gz` (`selected` = "<label> via <plan>") and `result.json` (factions, a_seats) of every
complete game; no replay. Answers "did the B arm ever pick a BGG opening plan" (092: HadschHallas B 0 of 42)
without listing decisions. Labels are counted by their "via" plan (the plan that put the move forward); the
opening plans carry a `BGG-R1-` prefix, so `--prefix BGG-R1-` isolates round-1 openings.

  .venv/bin/python tools/plan_labels.py ~/projects/gaia-lab/gaia-rl/runs/lab-093-... [--prefix BGG-R1-] [--factions Ambas,Gleens]
"""
import argparse
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--prefix', default='', help='only labels whose via-plan starts with this (e.g. BGG-R1-)')
    parser.add_argument('--factions', default='', help='comma-separated faction filter')
    parser.add_argument('--top', type=int, default=8)
    args = parser.parse_args()
    wanted = {f for f in args.factions.split(',') if f}
    counts = defaultdict(Counter)
    seats = Counter()
    for game_dir in sorted(args.run_dir.expanduser().glob('pair-*/game-*')):
        result_path = game_dir/'result.json'
        log_path = game_dir/'decisions.jsonl.gz'
        if not result_path.exists() or not log_path.exists():
            continue
        result = json.loads(result_path.read_text())
        if not result.get('complete'):
            continue
        factions = result['factions']
        a_seats = set(result['a_seats'])
        for seat, faction in enumerate(factions):
            seats[('A' if seat in a_seats else 'B', faction)] += 1
        with gzip.open(log_path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                faction = factions[row['seat']]
                if wanted and faction not in wanted:
                    continue
                selected = row.get('selected') or ''
                via = selected.split(' via ', 1)[1] if ' via ' in selected else selected
                if args.prefix and not via.startswith(args.prefix):
                    continue
                counts[(row['arm'], faction)][via] += 1
    for arm, faction in sorted(counts):
        total = sum(counts[(arm, faction)].values())
        top = ' · '.join(f'{label} ×{n}' for label, n in counts[(arm, faction)].most_common(args.top))
        print(f'{arm} {faction:<13} ({seats[(arm, faction)]} seat-games, {total} picks): {top}')


if __name__ == '__main__':
    main()
