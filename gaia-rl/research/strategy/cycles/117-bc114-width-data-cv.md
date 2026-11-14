# Cycle 117 — network width 64 vs 256 × all vs half the training games on the 114 BC samples — 7 arms, 5 game-level folds, command, no teacher verdict

A = `w64-all`: the 116 A arm (`expand+o`, 53 outcome columns, width 64, all training games of the fold, 9 epochs).
B arms (`lab/scratch_bc114_size.py`, the loading, network and training steps of the 116 script with the width as an
argument): `w64-half` (half the training games, 9 epochs), `w64-half-steps` (half the games, stopped mid-epoch at the
step count of the same fold's all-games arm, 9 × ceil(N_all/256)), `w256-all`, `w256-half`, `w256-half-steps`,
`w256-all-o2` (`expand+o2`, 72 outcome columns). Half = every other training game inside each quartet in manifest
order (no randomness). Queued 2026-11-14 by the user 「진행해」 (HANDOFF E151 (ㄴ) with the corrections of debate 1/1
and 2/2, E152). No games, not a teacher verdict: it chooses the settings of encoding v4.
Pre-registered report (queue note): per arm the per-game accuracy, decision-weighted accuracy, validation loss per
fold, step count, the 9-point validation loss curve; per comparison the per-game accuracy difference, game-level t
interval, n/46, per quartet. Four main comparisons, read by the interval: ① width `w256-all − w64-all`: above 0 →
width 256 becomes the v4 candidate, includes 0 → not confirmed (64 stays); judged on the 9-epoch value, the lowest
point of the width-256 curve reported beside it ②③ data amount `all − half-steps` at width 64 and 256: above 0 →
the game count is one of the limits in this setting (grounds for more collection), includes 0 → not confirmed
④ o2 `w256-all-o2 − w256-all`: above 0 → o2 returns as a v4 candidate at width 256, includes 0 → not confirmed as in
116, below 0 → dropped. Two beside comparisons (`all − half`, same epochs, fewer steps) are reference only. Checks:
`w64-all` within ±0.0005 of the 116 A arm 0.3466; step counts of the half-steps arms asserted equal; o2.npz checked
against outcome.npz.
114 samples (46 games, 13,841 decisions), 5 quartet-stratified game-level folds (validation 11·11·10·8·6 games),
lr 0.001, batch 256, one torch seed and one batch-order seed, no epoch chosen on the validation fold, work tree
venv on agentmaco, commit 9f971cc, 2026-11-14 21:58:32 → 22:25:34 (27 min; script 1,619 s).
Result: lab/results/117-bc114-width-data-cv.md.

**Health: clean.** Exit code 0. Reproduction check passed: `w64-all` per game 0.3462 against 0.3466 (fold losses
2.234 2.186 2.207 2.258 2.190, the same to three decimals as 116). Step counts equal in every fold (378 369 378 414
432 for the all and half-steps arms; half arms at 9 epochs 207 198 198 225 225). Halves: 19–21 of 35–40 training
games, 5,544–6,379 of 10,432–12,090 decisions (52–55%). o columns 53, o2 columns 72. The result page has no review
section (command job).

## Per-game accuracy (the pre-registered measure; no games, so no charges table)

| Arm | Width | Games | Stop | Per game | Decision-weighted | Loss at stop (fold mean) | Lowest of the 9 points |
|---|---:|---|---|---:|---:|---:|---|
| `w64-all` | 64 | all | 9 epochs | 34.62% | 34.69% | 2.215 | point 9 (2.215) |
| `w64-half` | 64 | half | 9 epochs | 32.52% | 32.58% | 2.302 | point 9 (2.302) |
| `w64-half-steps` | 64 | half | steps of all | 34.24% | 34.30% | 2.349 | point 6 (2.289) |
| `w256-all` | 256 | all | 9 epochs | 36.45% | 36.51% | 2.275 | point 5 (2.188) |
| `w256-half` | 256 | half | 9 epochs | 34.48% | 34.51% | 2.280 | point 7 (2.262) |
| `w256-half-steps` | 256 | half | steps of all | 35.09% | 35.18% | 2.667 | point 3 (2.269) |
| `w256-all-o2` | 256 | all, o2 | 9 epochs | 36.68% | 36.72% | 2.265 | point 5 (2.192) |

| # | Comparison | Difference | 95% CI | Games better / equal / worse | Per fold (pt) | Per quartet (pt, games better) | Pre-registered reading |
|---|---|---:|---|---:|---|---|---|
| ① | width: `w256-all − w64-all` | **+1.83 pt** | [+1.00, +2.65] | 33 / 1 / 12 | +2.2 +2.2 +0.1 +3.2 +2.0 | geo +3.6 2/2, a +1.5 6/10, b +2.0 7/9, c +0.6 4/9, d +1.6 6/8, e +3.3 8/8 | above 0 → width 256 is the v4 candidate |
| ② | data, width 64: `w64-all − w64-half-steps` | +0.39 pt | [−0.24, +1.01] | 24 / 3 / 19 | +0.2 0.0 +1.3 −0.7 +1.1 | geo −1.0 0/2, a +0.6 6/10, b +0.2 6/9, c +0.7 5/9, d +1.5 4/8, e −0.7 3/8 | includes 0 → not confirmed |
| ③ | data, width 256: `w256-all − w256-half-steps` | **+1.36 pt** | [+0.55, +2.17] | 31 / 1 / 14 | +1.2 +1.0 +0.3 +2.5 +2.9 | geo −0.3 1/2, a +1.1 7/10, b +1.2 6/9, c +1.3 5/9, d +2.0 6/8, e +1.7 6/8 | above 0 → the game count is one of the limits |
| ④ | o2, width 256: `w256-all-o2 − w256-all` | +0.23 pt | [−0.30, +0.77] | 21 / 6 / 19 | +0.2 +0.3 +0.2 −1.0 +1.4 | geo +0.4 1/2, a +1.1 5/10, b +0.2 4/9, c −1.2 2/9, d +0.4 4/8, e +0.6 5/8 | includes 0 → not confirmed, as in 116 |
| beside | width 64: `w64-all − w64-half` (same epochs) | +2.11 pt | [+1.41, +2.80] | 37 / 1 / 8 | | | reference only |
| beside | width 256: `w256-all − w256-half` (same epochs) | +1.97 pt | [+1.12, +2.83] | 34 / 2 / 10 | | | reference only |

Differences, intervals, game counts and quartets are the script's output (n = 46 games). The per-fold column is the
difference of the fold accuracies in the fold lines (decision-weighted inside the fold, three decimals; bot
subtraction). t from the reported intervals (df 45, bot calculation): ① 4.47, ② 1.26, ③ 3.38, ④ 0.87 — ① and ③
stay beyond a Bonferroni bound for six comparisons (≈ 2.8), though the pre-registration applied no correction.

## Activation (what each arm actually did)

- Step counts: the half-steps arms ran the same number of updates as the all-games arm of their fold (assert passed),
  which is ≈ 16.6–17.5 passes over the half data (steps × 256 / half decisions, bot calculation) against 9 passes
  for the all-games arm.
- Validation loss curves (fold mean, 9 points): `w64-all` still falls at the end (2.221 → 2.215). `w256-all` is
  lowest at point 5 (2.188) and rises to 2.275 at point 9; its loss at 9 epochs is above `w64-all` in 5/5 folds
  (2.268 2.191 2.328 2.350 2.238 against 2.234 2.186 2.207 2.258 2.190) while its accuracy is higher in 5/5 folds.
  The half-steps arms rise after point 6 (width 64, to 2.349) and point 3 (width 256, to 2.667).
- The script wrote the loss at the 9 points but not the accuracy, and it did not save the per-game arrays: the
  accuracy of `w256-all` at its lowest-loss point and intervals for comparisons other than the six are not available.
- o2: 72 columns loaded; loss 2.275 → 2.265, lower in 4/5 folds (2.268→2.262, 2.191→2.186, 2.328→2.304,
  2.350→2.366, 2.238→2.205).

## Reading (HANDOFF 1 order)

- ① Width — **width 256 is better, pre-registered reading: v4 candidate.** ① noise: no — 33/46 games, 5/5 folds,
  6/6 quartets positive (c weakest, +0.6, 4/9), t 4.47; one torch seed remains the limit. ④ interaction with the
  epoch count: 9 epochs was set at width 64. At width 256 the loss turns at epoch 5 and is worse than width 64 at
  epoch 9, so the wider net at 9 epochs picks the teacher's move more often but puts worse probabilities on it.
  The verdict is on the 9-epoch accuracy as pre-registered; the lowest point is a validation-selected value and is
  only reported. Consequence for v4: width 256 needs its own stopping rule (where the probabilities are used —
  PPO start, sampling — the loss matters, for argmax play the accuracy does).
- ②③ Data amount — **not confirmed at width 64 (+0.39 pt, interval includes 0), confirmed at width 256 (+1.36 pt):
  in the width-256 setting the game count is one of the limits (grounds for more collection).** At width 64 the
  accuracy does not separate (24/46) although the final loss is lower with all games in 5/5 folds (2.215 against
  2.349); the pre-registered measure is accuracy, so ② stays "not confirmed". Scope: the comparison is 19–21 games
  against 35–40; what a further doubling gives was not measured. At equal steps the half arm passes ≈ 17 times
  over its data and is far past its lowest loss, so part of ③ is over-training of the half arm — that is the
  data-amount effect at a fixed update count as pre-registered; at each arm's own lowest point the loss gap has the
  same direction (2.188 against 2.262–2.269; selected on validation, reference only).
- Width × data (not pre-registered, differences of arm means, no interval): the width gain with half the games is
  +0.85 pt (half-steps arms) or +1.96 pt (half arms, 9 epochs) against +1.83 pt with all games. No interaction is
  claimed.
- ④ o2 — **not confirmed again** (+0.23 pt, 21/46, 6 equal). The difference is smaller than 116's +0.47 pt at width
  64, so 116's reading ④ (a narrow net hiding o2) is not supported by this run; the loss is lower in 4/5 folds by
  0.010 on average. o2 stays out of encoding v4 (not below 0, so not rejected either).
- Beside comparisons (+2.11, +1.97 pt): data amount and update count are mixed, reference only.
- Reproduction: 0.3462 against 0.3466 with the same seed and the same fold losses is inside the pre-registered
  ±0.0005 but not bit-identical (≈ 5 of 13,841 decisions): the run-to-run floor is ≈ 0.04 pt, far below ① and ③.
- Limits: one torch seed, one way of choosing the half, six comparisons without correction (exploratory), and the
  game-level interval treats the 46 games as independent although each fold shares one model.
- Health and timing: clean, 27 minutes (estimate 30–35).

No code or deployment change (scratch script only). `tools/bc_train.py` still has `WIDTH = 64` fixed to match
`OfflinePolicy` and PPO; the width change belongs to encoding v4. The lab queue is empty.

## Proposal (user decision, nothing queued)

- (ㄱ) Encoding v4 without o2, network width as a parameter with default 256 (candidate fields by category + the 53
  outcome columns; module, `bc_train`, `OfflinePolicy`, export, PPO input), and `bc_train` keeps the epoch with the
  lowest loss on held-out games instead of a fixed count. Bot turns 2–3.
- (ㄴ) Width on more torch seeds, with the accuracy at every point and the per-game arrays saved (`w64-all` and
  `w256-all`, 5 folds; lab command, about 10 minutes per seed — 2 of the 7 arms of this 27-minute run). Removes the one-seed limit of ①; the number of
  seeds is the user's.
- (ㄷ) More collection (on hold by the user): ③ is the first evidence for it — half → all games is +1.36 pt at equal
  steps at width 256. 114 took 15 h 43 min for 48 games on the lab; the game count is the user's.
- (ㄹ) BC vs teacher A/B (lab torch install command + seed count). (ㅁ) PPO as it is (Seraph, user).
Bot recommendation: (ㄱ) now; (ㄷ) beside it on the idle lab if the user lifts the hold; (ㄴ) optional.
