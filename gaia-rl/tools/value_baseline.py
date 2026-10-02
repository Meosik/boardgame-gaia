"""Can a learned value predict the final result better than the teacher's `potential`?

Reads tools/extract_dataset.py output. Every position yields four perspective rows; the
target is the player's final VP minus the mean final VP of the other three. Features are
the player's own value minus the others' mean (so a linear model sees relative standing).

Models, each a ridge regression fitted separately per round (weights may change by phase):
  vp         current VP difference only
  potential  the teacher's potential difference only (its hand weights, refitted scale)
  terms      potential's terms as separate features (Texel-style re-weighting)
  full       terms + rule facts + own faction

Games are split by seed (both games of a seat-swapped pair stay on the same side), so
validation games are unseen boards. Reported on validation positions:
  MAE / R2 of the target, and pairwise order accuracy (for every pair of players with
  different final VP, is their predicted order right?) — overall and by round.

  .venv/bin/python tools/value_baseline.py datasets/positions.jsonl.gz --report runs/value-baseline.md
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json

import numpy as np

MODELS = ('vp', 'potential', 'terms', 'full')


def load(path):
    with gzip.open(path, 'rt') as rows:
        return [json.loads(line) for line in rows]


def validation_seed(seed, fraction):
    return int(hashlib.sha256(seed.encode()).hexdigest(), 16) % 1000 < fraction*1000


def design(rows):
    term_keys = sorted({k for r in rows for p in r['players'] for k in p['terms']})
    fact_keys = sorted({k for r in rows for p in r['players'] for k in p['facts']})
    factions = sorted({p['faction'] for r in rows for p in r['players']})
    out = []
    for r in rows:
        final = np.array(r['final_vp'], dtype=float)
        terms = np.array([[p['terms'].get(k, 0.0) for k in term_keys] for p in r['players']])
        facts = np.array([[p['facts'].get(k, 0.0) for k in fact_keys] for p in r['players']])
        pot = np.array([p['potential'] for p in r['players']])
        vp = np.array([p['terms']['vp'] for p in r['players']])
        for i, p in enumerate(r['players']):
            others = [j for j in range(4) if j != i]

            def rel(x):
                return x[i] - x[others].mean(axis=0)
            onehot = np.array([float(p['faction'] == f) for f in factions])
            out.append({'seed': r['seed'], 'position': (r['game'], r['step']), 'player': i,
                        'round': r['round'], 'target': final[i] - final[others].mean(),
                        'final': final[i],
                        'X': {'vp': np.array([rel(vp)]), 'potential': np.array([rel(pot)]),
                              'terms': rel(terms), 'full': np.concatenate([rel(terms), rel(facts), onehot])}})
    return out, term_keys


class Ridge:
    def __init__(self, alpha):
        self.alpha = alpha

    def fit(self, X, y):
        self.mean, self.scale = X.mean(axis=0), X.std(axis=0)
        self.scale[self.scale == 0] = 1
        Z = (X-self.mean)/self.scale
        self.intercept = y.mean()
        A = Z.T @ Z + self.alpha*len(y)*np.eye(Z.shape[1])
        self.coef = np.linalg.solve(A, Z.T @ (y-self.intercept))
        return self

    def predict(self, X):
        return self.intercept + ((X-self.mean)/self.scale) @ self.coef


def pairwise_accuracy(samples, predictions):
    by_position = defaultdict(list)
    for s, p in zip(samples, predictions):
        by_position[s['position']].append((s['final'], p))
    right = total = 0
    for players in by_position.values():
        for a in range(len(players)):
            for b in range(a+1, len(players)):
                (fa, pa), (fb, pb) = players[a], players[b]
                if fa != fb:
                    total += 1
                    right += (fa > fb) == (pa > pb)
    return right/total if total else float('nan'), total


def metrics(samples, predictions):
    y = np.array([s['target'] for s in samples])
    p = np.array(predictions)
    r2 = 1 - ((y-p)**2).sum()/((y-y.mean())**2).sum() if len(y) > 1 else float('nan')
    accuracy, pairs = pairwise_accuracy(samples, predictions)
    return {'mae': float(np.abs(y-p).mean()), 'r2': float(r2), 'pair_acc': accuracy, 'pairs': pairs}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dataset')
    parser.add_argument('--validation-fraction', type=float, default=.25)
    parser.add_argument('--alpha', type=float, default=1e-2, help='Ridge strength (standardised)')
    parser.add_argument('--report')
    parser.add_argument('--save-weights', help='Refit the terms model on ALL positions and save per-round '
                        'weights (raw term units) for tools/teacher_patches.py calibrated_value')
    args = parser.parse_args()
    samples, term_keys = design(load(args.dataset))
    seeds = sorted({s['seed'] for s in samples})
    held = {seed for seed in seeds if validation_seed(seed, args.validation_fraction)}
    if not held or held == set(seeds):   # tiny datasets: still keep both sides non-empty
        held = set(seeds[:max(1, len(seeds)//4)])
    train = [s for s in samples if s['seed'] not in held]
    valid = [s for s in samples if s['seed'] in held]
    predictions = {m: [0.0]*len(valid) for m in MODELS}
    coefficients = {}
    for rnd in sorted({s['round'] for s in samples}):
        tr = [s for s in train if s['round'] == rnd]
        idx = [i for i, s in enumerate(valid) if s['round'] == rnd]
        if not tr or not idx:
            continue
        for m in MODELS:
            model = Ridge(args.alpha).fit(np.array([s['X'][m] for s in tr]), np.array([s['target'] for s in tr]))
            for i, p in zip(idx, model.predict(np.array([valid[i]['X'][m] for i in idx]))):
                predictions[m][i] = float(p)
            if m == 'terms':
                coefficients[rnd] = dict(zip(term_keys, (model.coef/model.scale).round(3).tolist()))
    lines = [f'# Value baseline — {len({s["position"][0] for s in train})} training games, '
             f'{len({s["position"][0] for s in valid})} validation games ({len(held)} of {len(seeds)} seeds held out)', '',
             '| Model | MAE | R² | Pair order accuracy | Pairs |', '|---|---:|---:|---:|---:|']
    for m in MODELS:
        r = metrics(valid, predictions[m])
        lines.append(f"| {m} | {r['mae']:.2f} | {r['r2']:.3f} | {r['pair_acc']:.3f} | {r['pairs']} |")
    lines += ['', '## Pair order accuracy by round', '',
              '| Round | ' + ' | '.join(MODELS) + ' |', '|---|' + '---:|'*len(MODELS)]
    for rnd in sorted({s['round'] for s in valid}):
        idx = [i for i, s in enumerate(valid) if s['round'] == rnd]
        cells = [f"{metrics([valid[i] for i in idx], [predictions[m][i] for i in idx])['pair_acc']:.3f}" for m in MODELS]
        lines.append(f'| {rnd} | ' + ' | '.join(cells) + ' |')
    lines += ['', '## Refitted term weights (VP of final margin per unit of term difference; teacher uses 1.0)', '',
              '| Term | ' + ' | '.join(f'R{r}' for r in coefficients) + ' |', '|---|' + '---:|'*len(coefficients)]
    for k in term_keys:
        lines.append(f'| {k} | ' + ' | '.join(f'{coefficients[r].get(k, 0):.2f}' for r in coefficients) + ' |')
    if args.save_weights:
        rounds = {}
        for rnd in sorted({s['round'] for s in samples}):
            group = [s for s in samples if s['round'] == rnd]
            model = Ridge(args.alpha).fit(np.array([s['X']['terms'] for s in group]),
                                          np.array([s['target'] for s in group]))
            rounds[str(rnd)] = dict(zip(term_keys, (model.coef/model.scale).tolist()))
        valid_terms = metrics(valid, predictions['terms'])
        with open(args.save_weights, 'w') as out:
            json.dump({'target': 'final VP minus the mean of the other three', 'model': 'per-round ridge on '
                       'potential terms (own minus others mean)', 'alpha': args.alpha,
                       'games': len({s['position'][0] for s in samples}), 'seeds': len(seeds),
                       'validation': {'pair_acc_terms': valid_terms['pair_acc'], 'r2_terms': valid_terms['r2'],
                                      'pair_acc_potential': metrics(valid, predictions['potential'])['pair_acc']},
                       'rounds': rounds}, out, indent=1)
        lines += ['', f'Saved per-round weights (refitted on all {len(samples)} rows) to {args.save_weights}']
    report = '\n'.join(lines)+'\n'
    print(report)
    if args.report:
        with open(args.report, 'w') as out:
            out.write(report)


if __name__ == '__main__':
    main()
