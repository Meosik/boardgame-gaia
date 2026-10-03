# Cycle 020 — Counterfactual branches: one move is below the noise

## Data
`tools/branch_dataset.py` on the user's laptop: 1368 positions from 37 seeds, 4 first moves
each (recorded, easy rank 1–2, one random, further ranks), every branch finished by the same
deterministic easy teacher. `tools/branch_value.py`, 10 seeds held out (368 positions).
Full table: `020-branch-value-report.md`.

## Result (validation)

| Evaluator | Pair accuracy | Best branch | Regret (VP) |
|---|---:|---:|---:|
| potential (hand weights) | 0.533 | 0.361 | 7.81 |
| branch-fitted weights | 0.514 | 0.348 | 7.95 |
| outcome weights (cycle 019) | 0.526 | 0.367 | 8.02 |
| always the recorded move | — | 0.367 | 7.69 |

| Branch kind | Mean loss vs best branch |
|---|---:|
| recorded | 7.69 |
| rank1 | 7.90 |
| random | 8.51 |

## Reading
- Every evaluator is at chance (0.51–0.53). The fitted weights collapsed towards 0.
- A uniformly random legal move loses only ~0.8 VP more than the move the teacher played,
  while branches of the same position differ by ~8 VP on average. The final score after one
  different move is dominated by how the rest of the game unfolds (a deterministic but chaotic
  continuation), not by the move. Separating a ~1 VP effect from ~8 VP spread needs on the
  order of (8/1)² ≈ 60 playouts per branch — infeasible with ~15 s Python playouts.
- Conclusion: at this data scale neither outcome regression (cycle 019, confounded) nor
  single-playout counterfactuals (this cycle, too noisy) can learn a decision value. Learning
  needs orders of magnitude more games, i.e. a much faster playout, or a value bootstrapped at a
  short horizon (TD-style) instead of the game end.
