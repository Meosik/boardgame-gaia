"""Fit term weights to *differences between moves from the same position* (counterfactual).

Input: tools/branch_dataset.py output. For every position (root) and every pair of its
branches, the target is the difference of the mover's final margin (own VP minus the mean of
the other three) between the two branches, and the features are the difference of the
mover's post-move terms (own minus others' mean). A ridge without intercept on these
differences learns how much each term is worth *as a consequence of a move*, which outcome
regression (cycle 019) could not separate from player strength.

Positions are split by seed. On validation positions it reports, for each evaluator:
  pair accuracy  for branch pairs with different results, is the better one ranked higher?
  best-branch    how often the evaluator's top branch is (one of) the actually best
  regret         mean margin lost against the best branch when following the evaluator
Evaluators: potential (hand weights), outcome weights (--outcome-weights, cycle 019 file),
branch weights (fitted here), and the reference rows `recorded` / `rank1`.

  .venv/bin/python tools/branch_value.py datasets/branches.jsonl.gz \\
      --outcome-weights datasets/value-weights.json --save-weights datasets/branch-weights.json
"""
import argparse
from collections import defaultdict
from itertools import combinations
import gzip
import hashlib
import json

import numpy as np


def load(path):
    roots = defaultdict(list)
    with gzip.open(path, 'rt') as rows:
        for line in rows:
            row = json.loads(line)
            roots[row['root']].append(row)
    return {root: rows for root, rows in roots.items() if len(rows) >= 2}


def seed_of(root):
    return root.split('@')[0]


def margin(row):
    final, a = row['final_vp'], row['actor']
    return final[a] - (sum(final)-final[a])/3


def relative_terms(row, keys):
    a = row['actor']
    players = row['after']
    own = np.array([players[a]['terms'].get(k, 0.0) for k in keys])
    others = np.array([[p['terms'].get(k, 0.0) for k in keys] for i, p in enumerate(players) if i != a])
    return own - others.mean(axis=0)


def weighted(weights_by_round, keys):
    def evaluate(row):
        w = weights_by_round.get(str(min(row['round'], 6)), {})
        return float(relative_terms(row, keys) @ np.array([w.get(k, 0.0) for k in keys]))
    return evaluate


def potential_value(row):
    a = row['actor']
    return row['after'][a]['potential'] - np.mean([p['potential'] for i, p in enumerate(row['after']) if i != a])


def evaluate(roots, score):
    right = total = best_hits = 0
    regret = []
    for rows in roots.values():
        margins = [margin(r) for r in rows]
        values = [score(r) for r in rows]
        for i, j in combinations(range(len(rows)), 2):
            if margins[i] != margins[j]:
                total += 1
                right += (margins[i] > margins[j]) == (values[i] > values[j])
        pick = int(np.argmax(values))
        best_hits += margins[pick] == max(margins)
        regret.append(max(margins) - margins[pick])
    return {'pair_acc': right/total if total else float('nan'), 'pairs': total,
            'best': best_hits/len(roots), 'regret': float(np.mean(regret)), 'positions': len(roots)}


def fit(roots, keys, alpha, rounds):
    """Ridge without intercept on within-position differences; one model per round group."""
    groups = defaultdict(lambda: ([], []))
    for rows in roots.values():
        group = rounds(rows[0]['round'])
        X, y = groups[group]
        for a, b in combinations(rows, 2):
            X.append(relative_terms(a, keys) - relative_terms(b, keys))
            y.append(margin(a) - margin(b))
    weights = {}
    for group, (X, y) in groups.items():
        X, y = np.array(X), np.array(y)
        scale = X.std(axis=0)
        scale[scale == 0] = 1
        Z = X/scale
        coef = np.linalg.solve(Z.T @ Z + alpha*len(y)*np.eye(len(keys)), Z.T @ y)/scale
        weights[group] = dict(zip(keys, coef.tolist()))
    return weights


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('dataset')
    parser.add_argument('--outcome-weights', help='cycle-019 value-weights.json, for comparison')
    parser.add_argument('--validation-fraction', type=float, default=.25)
    parser.add_argument('--alpha', type=float, default=.1)
    parser.add_argument('--per-round', action='store_true', help='One model per round instead of R1-5 pooled + R6')
    parser.add_argument('--save-weights')
    parser.add_argument('--report')
    args = parser.parse_args()
    roots = load(args.dataset)
    keys = sorted({k for rows in roots.values() for r in rows for p in r['after'] for k in p['terms']})
    seeds = sorted({seed_of(r) for r in roots})
    held = {s for s in seeds if int(hashlib.sha256(s.encode()).hexdigest(), 16) % 1000 < args.validation_fraction*1000}
    if not held or held == set(seeds):
        held = set(seeds[:max(1, len(seeds)//4)])
    train = {r: rows for r, rows in roots.items() if seed_of(r) not in held}
    valid = {r: rows for r, rows in roots.items() if seed_of(r) in held}

    def rounds(r):
        return str(r) if args.per_round else ('6' if r >= 6 else '1-5')

    def expand(groups):
        return {str(r): groups.get(rounds(r), {}) for r in range(1, 7)}
    branch_weights = expand(fit(train, keys, args.alpha, rounds))
    evaluators = {'potential (hand weights)': potential_value,
                  'branch weights (this fit)': weighted(branch_weights, keys)}
    if args.outcome_weights:
        with open(args.outcome_weights) as source:
            evaluators['outcome weights (cycle 019)'] = weighted(json.load(source)['rounds'], keys)
    lines = [f'# Branch value — {len(train)} training / {len(valid)} validation positions '
             f'({len(held)} of {len(seeds)} seeds held out)', '',
             '| Evaluator | Pair accuracy | Best branch | Regret (VP margin) | Pairs |', '|---|---:|---:|---:|---:|']
    for name, score in evaluators.items():
        r = evaluate(valid, score)
        lines.append(f"| {name} | {r['pair_acc']:.3f} | {r['best']:.3f} | {r['regret']:.2f} | {r['pairs']} |")
    for kind in ('recorded', 'rank1'):
        subset = {root: rows for root, rows in valid.items() if any(r['branch'] == kind for r in rows)}
        r = evaluate(subset, lambda row, kind=kind: float(row['branch'] == kind))
        lines.append(f"| always the {kind} move | — | {r['best']:.3f} | {r['regret']:.2f} | — |")
    by_kind = defaultdict(list)
    for rows in valid.values():
        best = max(margin(r) for r in rows)
        for r in rows:
            by_kind[r['branch']].append(best - margin(r))
    lines += ['', '| Branch kind | Mean loss vs best branch | Positions |', '|---|---:|---:|']
    for kind, losses in sorted(by_kind.items()):
        lines.append(f'| {kind} | {np.mean(losses):.2f} | {len(losses)} |')
    groups = sorted({rounds(r) for r in range(1, 7)}, key=lambda g: g)
    lines += ['', '## Branch-fitted weights (teacher uses 1.0)', '', '| Term | ' + ' | '.join(groups) + ' |',
              '|---|' + '---:|'*len(groups)]
    fitted = fit(train, keys, args.alpha, rounds)
    for k in keys:
        lines.append(f'| {k} | ' + ' | '.join(f'{fitted.get(g, {}).get(k, 0):.2f}' for g in groups) + ' |')
    if args.save_weights:
        all_weights = expand(fit(roots, keys, args.alpha, rounds))
        with open(args.save_weights, 'w') as out:
            json.dump({'target': 'within-position difference of the mover final margin',
                       'model': 'ridge without intercept on post-move term differences',
                       'alpha': args.alpha, 'positions': len(roots), 'seeds': len(seeds),
                       'rounds': all_weights}, out, indent=1)
        lines += ['', f'Saved weights refitted on all {len(roots)} positions to {args.save_weights}']
    report = '\n'.join(lines)+'\n'
    print(report)
    if args.report:
        with open(args.report, 'w') as out:
            out.write(report)


if __name__ == '__main__':
    main()
