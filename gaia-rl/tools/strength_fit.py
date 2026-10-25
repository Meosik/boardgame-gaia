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


QUEUE = ROOT/'lab'/'queue'


def _stop_round(name):
    """The run's stop_round from its queue file (0 = six rounds); None when the file is gone."""
    for path in (QUEUE/f'{name}.json', QUEUE/f'_{name}.json'):
        if path.exists():
            try:
                return json.loads(path.read_text()).get('stop_round', 0) or 0
            except ValueError:
                return None
    return None


def games(first, limit):
    """(run, seed, [rounds 1-3 charges per seat], [factions]) for every game of results named >= `first` that played
    at least to the start of round 4 (debate 1/1: 1R smokes measure a shorter window)."""
    out = []
    for path in sorted(RESULTS.glob('*.json')):
        if path.stem[:3] < first or not path.stem[:3].isdigit():
            continue
        stop = _stop_round(path.stem)
        if stop is None or 0 < stop < 3:
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
    from scipy.optimize import nnls
    cache, xs, ys, groups, skipped = {}, [], [], [], 0
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
        z = {}
        for k in keys:
            values = [feats[s][k] for s in range(4)]
            m, sd = statistics.mean(values), statistics.pstdev(values) or 1.0
            z[k] = [(v - m) / sd for v in values]
        for s in range(4):
            xs.append([z[k][s] for k in keys])
            ys.append(charges[s] - mean)
            groups.append(seed)
    x, y = np.array(xs), np.array(ys)
    print(f'games {len(rows_all)}, seats used {len(ys)}, games skipped (factions differ now) {skipped}, '
          f'seeds {len(cache)}')
    for i, k in enumerate(keys):
        r = float(np.corrcoef(x[:, i], y)[0, 1]) if x[:, i].std() else float('nan')
        print(f'  {k:<8} corr {r:+.3f}')

    def r2(w, rows):
        pred = x[rows] @ w
        return 1 - float(((y[rows] - pred) ** 2).sum() / (y[rows] ** 2).sum())
    every = np.arange(len(y))
    w_ls, *_ = np.linalg.lstsq(x, y, rcond=None)
    w_nn, _ = nnls(x, y)
    print('least squares:', ', '.join(f'{k} {v:+.1f}' for k, v in zip(keys, w_ls)), f'| R2 {r2(w_ls, every):.3f}')
    print('non-negative: ', ', '.join(f'{k} {v:+.1f}' for k, v in zip(keys, w_nn)), f'| R2 {r2(w_nn, every):.3f}')
    # Debate 1/1: seeds split in two halves (no seed in both), fit on one, score on the other, and both ways round.
    seeds = sorted(set(groups))
    half = {s: i % 2 for i, s in enumerate(seeds)}
    fold = np.array([half[g] for g in groups])
    current = np.array([fs.WEIGHTS[k] for k in keys])
    for f in (0, 1):
        train, test = every[fold == f], every[fold != f]
        w_f, _ = nnls(x[train], y[train])
        print(f'fold {f}: non-negative fit on {len(set(np.array(groups)[train]))} seeds -> held-out R2 '
              f'{r2(w_f, test):.3f}; faction_strength.WEIGHTS held-out R2 {r2(current, test):.3f}; '
              f'tier only {r2(np.array([w_f[0]] + [0] * (len(keys) - 1)), test):.3f}')


if __name__ == '__main__':
    main()
