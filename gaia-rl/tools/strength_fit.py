"""Calibrate faction_strength.WEIGHTS on finished lab A/B runs (HANDOFF E117, turn order by expected strength).

For every game of the chosen result files (`lab/results/<name>.json`: `seeds`, `charges.seats`), each seat's round 1-3
charges minus the game mean is the target, and each faction_strength feature as a z-score over the game's four seats
is a predictor. Prints the per-feature correlation with the target and least-squares weights (no intercept: both
sides are centred per game). Same-code drift is large (±30 charges a faction), so read the correlations, not one fit.

  GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools \\
    gaia-rl/.venv/bin/python gaia-rl/tools/strength_fit.py --from 084 [--limit 200]
"""
import argparse
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

RESULTS = ROOT/'lab'/'results'


def games(first, limit):
    """(seed, [charges per seat]) for every finished game of results named >= `first`."""
    out = []
    for path in sorted(RESULTS.glob('*.json')):
        if path.stem[:3] < first or not path.stem[:3].isdigit():
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        seeds, seats = data.get('seeds') or [], ((data.get('charges') or {}).get('seats') or {})
        for game, rows in seats.items():
            pair = int(game.split('/')[0].split('-')[1])
            if pair < len(seeds) and len(rows) == 4 and all(isinstance(r.get('charges'), (int, float)) for r in rows):
                out.append((path.stem, seeds[pair], [r['charges'] for r in rows], [r['faction'] for r in rows]))
    return out[:limit] if limit else out


RUNS = Path(os.environ.get('GAIA_LAB_RUNS', Path.home()/'projects'/'gaia-lab'/'gaia-rl'/'runs'))


def full_games(first, limit):
    """(run, seed, [final VP per seat], [factions]) for every complete 6-round game under RUNS/lab-<name>."""
    out = []
    for path in sorted(RUNS.glob('lab-*/pair-*/game-*/result.json')):
        run = path.parts[-4][4:]
        if not run[:3].isdigit() or run[:3] < first:
            continue
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        scores = data.get('scores') or {}
        if not data.get('complete') or data.get('stopped_at_round') or len(scores) != 4:
            continue
        out.append((run, data['seed'], [scores[str(s)] for s in range(4)], data['factions']))
    return out[:limit] if limit else out


def main():
    import numpy as np
    import faction_strength as fs
    from gaia_rl import Environment
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--from', dest='first', default='084')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--target', choices=('charges', 'vp'), default='charges',
                        help='charges: rounds 1-3 charges of the result files; vp: final VP of complete 6-round games')
    args = parser.parse_args()
    keys = list(fs.WEIGHTS)
    cache, xs, ys, skipped = {}, [], [], 0
    rows_all = (games if args.target == 'charges' else full_games)(args.first, args.limit)
    for run, seed, charges, factions in rows_all:
        if seed not in cache:
            state = json.loads(Environment(seed, 2000).snapshot_json())['state']
            cache[seed] = fs.features(state)
        feats = cache[seed]
        if [feats[s]['faction'] for s in range(4)] != factions:
            skipped += 1          # the map or the factions changed since the run (engine updates)
            continue
        mean = statistics.mean(charges)
        for key_rows in [None]:
            z = {}
            for k in keys:
                values = [feats[s][k] for s in range(4)]
                m, sd = statistics.mean(values), statistics.pstdev(values) or 1.0
                z[k] = [(v - m) / sd for v in values]
        for s in range(4):
            xs.append([z[k][s] for k in keys])
            ys.append(charges[s] - mean)
    x, y = np.array(xs), np.array(ys)
    print(f'games {len(rows_all)}, seats used {len(ys)}, games skipped (factions differ now) {skipped}, '
          f'seeds {len(cache)}')
    for i, k in enumerate(keys):
        r = float(np.corrcoef(x[:, i], y)[0, 1]) if x[:, i].std() else float('nan')
        print(f'  {k:<8} corr {r:+.3f}')
    w, *_ = np.linalg.lstsq(x, y, rcond=None)
    pred = x @ w
    r2 = 1 - float(((y - pred) ** 2).sum() / (y ** 2).sum())
    print('weights (charges per z):', ', '.join(f'{k} {v:+.1f}' for k, v in zip(keys, w)), f'| R2 {r2:.3f}')


if __name__ == '__main__':
    main()
