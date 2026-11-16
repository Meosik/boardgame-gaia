# Cycle 118 — encoding 4 through the real tools on the 46 games of 114: export, row equality, 5-fold `bc_train` at width 256 — command, no teacher verdict

A = the measured network of cycle 117 (`lab/scratch_bc114_size.py`, arm `w256-all`: `expand+o` input, width 256,
9 epochs, decision-weighted accuracy 36.51%; `w64-all` 34.69%). B = the same data through the shipped tools of
encoding 4 step 2 (da3829e): `bc_dataset.py export --encoding 4` (`FeatureEncoderV4`, a preview state per candidate)
→ `tools/bc_train.py` (`gaia_rl/network.py`: field embeddings + 3 board planes + 58 outcome columns, legal
candidates only), width 256, 9 epochs, lr 0.001, batch 256, seed 0, the fold's games held out whole, weights of the
lowest validation loss epoch saved. Script `lab/scratch_v4_pipeline.py`. Queued 2026-11-16 by the user
「대충 알아서 돌려」·「진행해」 (HANDOFF E153 (ㄱ) step 2, E155). No games, not a teacher verdict: a reproduction check
before step 3.
Pre-registered reading (queue note), on the 9-epoch decision-weighted accuracy over the 5 folds, line = midpoint of
the two 117 arms 35.60%: ≥ 35.60% → the real tools reproduce the width 256 result → step 3 (`OfflinePolicy`, policy
teacher, PPO); 34.69–35.60% → partly reproduced, find the cause first; < 34.69% → not reproduced, step 3 on hold.
The saved-epoch value is chosen on the validation games, reference only. No pairing and no interval (117 stored no
per-game arrays), one torch seed, different initial random numbers than 117.
46 games of 114 (13,841 decisions, 536,858 candidate rows), the 5 folds of 117 (stratified by quartet, k-th game of
a quartet → fold k mod 5; 11·11·10·8·6 games), work tree venv (the lab venv has no torch), host agentmaco, commit
43a30a5, 2026-11-16 10:15:06 → 10:30:14 (15 min 8 s; estimate was ≈ 70 min). Result: lab/results/118-bc114-v4-pipeline.md,
metrics `gaia-rl/runs/bc-114-v4-pipeline/metrics.json`, checkpoints `gaia-rl/runs/bc-114-v4-w256-20261116-102118/fold-0…4`.

**Health: clean.** Exit code 0, no assert failed. Export of the 46 games 10:15 → 10:21 (7 shards; ≈ 6 min, not the
estimated 30), 5 folds of training ≈ 9 min (≈ 110 s per fold). The result page has no second-model review section
(command job).

## The pre-registered reading (9-epoch decision-weighted accuracy)

| | 117 `w64-all` | line | 117 `w256-all` | **118 real tools, width 256** |
|---|---:|---:|---:|---:|
| Decision-weighted accuracy, epoch 9 | 34.69% | 35.60% | 36.51% | **36.38%** |
| Fold-mean validation loss, epoch 9 | 2.215 | | 2.275 | **2.208** |
| Fold-mean validation loss, lowest point | 2.215 (epoch 9) | | 2.188 (epoch 5) | **2.200 (epoch 7)** |

**36.38% ≥ 35.60% → reproduced (pre-registered word) → step 3.** −0.13 pt from the 117 `w256-all` figure, +1.69 pt
over `w64-all`; means only, no interval.

Per fold (metrics.json; accuracy and loss on the held-out games):

| Fold | Games | Decisions | Chance | Acc. epoch 9 | Loss epoch 9 | 117 loss epoch 9 | Saved epoch | Acc. saved | Loss saved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 11 | 3,242 | 15.0% | 35.66% | 2.285 | 2.268 | 6 | 37.94% | 2.221 |
| 1 | 11 | 3,409 | 15.4% | 38.02% | 2.161 | 2.191 | 6 | 35.52% | 2.160 |
| 2 | 10 | 3,137 | 15.6% | 35.19% | 2.187 | 2.328 | 8 | 36.18% | 2.164 |
| 3 | 8 | 2,302 | 14.4% | 36.23% | 2.212 | 2.350 | 9 | 36.23% | 2.212 |
| 4 | 6 | 1,751 | 15.0% | 36.89% | 2.193 | 2.238 | 4 | 35.58% | 2.192 |
| **All** | 46 | 13,841 | | **36.38%** | 2.208 | 2.275 | | 36.36% | 2.190 |

Decision-weighted accuracy by epoch 1–9 (recomputed from metrics.json): 28.37 · 31.28 · 33.32 · 34.20 · 34.92 ·
35.55 · 35.94 · 35.55 · **36.38**%. Fold-mean validation loss by epoch: 2.419 · 2.328 · 2.283 · 2.255 · 2.219 ·
2.206 · **2.200** · 2.216 · 2.208. Training loss at epoch 9: 1.85–1.92 (training accuracy 43–45%).

## Activation (did the real path run, and on the same rows)

Step 2 of the script, every row of the fresh encoding 4 shards against the stored v3 shards (`runs/bc-114-shards`)
and `outcome.npz`; any difference is an assert failure, none happened:

- decisions 13,841, candidate rows 536,858; candidate counts, chosen index and state vector equal;
- board columns equal, field present/absent equal, field id ↔ v3 value one-to-one in each of the 34 fields
  (distinct ids per field 1–50; `distinct_ids_per_field` in metrics.json);
- 53 outcome columns equal, the 5 new outcome columns all zero; game number = manifest line.

So the input of 118 is the `expand+o` input of 115–117 row for row; what differs from 117 is the network code and
the training loop (E155: the state layer reads all 16,384 columns, the full vocabulary per field, shuffling inside
a shard only, other initial random numbers).

## Reading (HANDOFF 1 order)

- **Reproduction**: the pre-registered point (epoch 9) is 36.38%, above the line by 0.78 pt. ① Noise: that margin
  is the size of the epoch-to-epoch movement of this figure — epochs 6 and 8 are 35.55% (0.05 pt under the line),
  epoch 7 35.94%; one fold moves up to 3 pt between neighbouring epochs (fold 0: 37.94 → 36.15 → 34.95 → 35.66,
  fold 4: 34.21 → 36.89). What holds without picking an epoch: every epoch from 6 on is ≥ 35.55%, i.e. ≥ +0.86 pt
  over the 117 `w64-all` 34.69%, and the last one is 0.13 pt from `w256-all`. The 117 per-epoch accuracies were not
  stored, so the same wobble cannot be put on the reference. One torch seed, no pairing: "reproduced" means "the
  real tools land in the width 256 range", not "equal to 117".
- **Loss curve**: the late overfitting of the 117 script is milder here — fold-mean loss at epoch 9 2.208 against
  2.275 (4 of 5 folds lower; fold 0 2.285 against 2.268), lowest point at epoch 7 (2.200) instead of epoch 5
  (2.188; the lowest value itself is 0.012 worse). ③ Which of the three listed differences does this is not
  measured.
- **Lowest validation loss epoch** (the stopping rule of step 2): the saved epochs are 6·6·8·9·4, and the
  saved-epoch accuracy 36.36% equals the epoch 9 accuracy 36.38% — on these 46 games the rule does not cost or gain
  accuracy; its loss 2.190 is selected on the same validation games (optimistic, reference only). The spread 4–9
  says a single fold's lowest epoch is noisy; the fold mean puts it at 7.
- ② Activation: the export path, the equality and the training all ran in this job (shards written 10:16–10:21).
- Health and timing: 15 min instead of 70; the export estimate from E154 (6 games 238 s) was 5× too high.
- Second-model review: no section on the result page (command job) — nothing to answer.

No code or deployment change in this cycle (scratch script only). `ENCODING_VERSION` is still 3; `OfflinePolicy`,
the policy teacher factory and PPO still read v3 only. Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Encoding 4 step 3 (the pre-registered next step): `OfflinePolicy` and the policy teacher factory pass the
  preview state and read width and encoding from the checkpoint metadata, unit tests, then a 4-seat 6R smoke with a
  118 fold checkpoint (the v3 BC smoke of E147 scored 55.5 per seat, teacher ≈ 100); the PPO environment and
  `ENCODING_VERSION` 4 after that. Bot turns 2–3; the smoke goes to the lab queue if it takes over 5 minutes.
  Open point inside it: a checkpoint trained on all 46 games has no held-out games for the stopping rule — hold
  some out (`--val-every 5`) or fix the epoch count near 7.
- (ㄴ) More torch seeds for the width comparison, now with per-epoch and per-game arrays stored (lab command, about
  10 min per seed; the number of seeds is the user's).
- (ㄷ) More collection (on hold by the user; 117 ③ is the first evidence, 114 took 15 h 43 min for 48 games; the
  number of games is the user's).
- (ㄹ) BC (encoding 4) vs teacher A/B on charges in rounds 1–3 — after (ㄱ); the seed count is the user's, and the
  lab venv needs torch.
Bot recommendation: (ㄱ).
