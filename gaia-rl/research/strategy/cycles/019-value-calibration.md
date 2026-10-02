# Cycle 019 — Do final results support potential's hand weights?

## Data
`tools/extract_dataset.py` replayed every finished teacher_ab game on the user's machine
(147 games, 25 seeds; each replay checks every decision id and the final scores).
`tools/value_baseline.py`: per-round ridge on own-minus-others features, target = final VP
minus the others' mean, 6 of 25 seeds (38 games) held out. Full table:
`019-value-baseline-report.md`.

## Result (validation games)

| Model | R² | Pair order accuracy |
|---|---:|---:|
| current VP only | 0.117 | 0.576 |
| `potential` (hand weights, refitted scale) | 0.265 | 0.659 |
| `potential` terms, re-weighted | **0.450** | **0.726** |
| terms + rule facts + faction | 0.411 | 0.738 |

Re-weighting the same terms gains +6.7 points of pair accuracy and +0.19 R², most in rounds
1–3 (0.58 → 0.68–0.70). The teacher's information is fine; its weights are not.

## What the fitted weights say (teacher uses 1.0 for every term)
- `materials` (stockpiled resources): 0.0–0.5 in rounds 1–5. The teacher prices held
  resources 2× to 100× above what predicts the result — the hoarding seen in cycles 017/018.
- `structures` 0.8–1.5, `expansion` 1.4–2.6, `ships` 1.2–2.9, `tile_options` 1.4–4.0,
  `advanced` 0.8–1.5: building, expansion, ships and tiles are undervalued.
- `standings` 0.1–0.4 until round 6 (0.86): current end-scoring rank says little early.
- `research_options` ≈ 0 or negative: carries no information.
- Booster terms swing sign between rounds: small spread, unstable; treat as noise.

Caveats: on-policy data (states the A-family teachers reach), correlated terms, 25 seeds.

## Next
`teacher_patches.calibrated_value` evaluates with these weights instead of 1.0
(unit weights reproduce the current value exactly). Pending: export weights on the full
dataset with stronger regularisation, then a 12-seed A/B against the live (geodens_guide) teacher.
