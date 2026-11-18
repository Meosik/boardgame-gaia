# Cycle 122 — BC encoding 4 on 93 games: 18-epoch curve of the `all` arm (5 folds) + one training on all 93 games with a checkpoint per epoch — command, no games

Not a teacher A/B: no arms, no charges. One script, `lab/scratch_v4_epochs.py` (commit 6c4ace7, committed before the
queue; it refuses to start with uncommitted changes to itself or an existing checkpoint folder and writes its commit id
to `script_commit` — the E162 rule). Queued 2026-11-18 by E167 (E166 (ㄱ), clean Codex round under the standing order of
2026-11-13): the `all` arm of 121a had its lowest validation loss at the last of 9 epochs, so longer training was
unmeasured, and no checkpoint trained on all 93 games existed.
Data: the shards of 121a (`runs/bc-114-v4-shards-fc19` + `runs/bc-119-v4-shards-fc19-c4096`, 93 games, 28,098 decisions,
engine fc19671c4278), no export. Steps: ① the quartet-stratified 5 folds of 121a, per fold the `all` arm (72–77 training
games; the network and training step of `tools/bc_train.py`: width 256, lr 0.001, batch 256, torch seed 0, batch-order
seed 0) to **18 epochs**, validation loss and per-decision hits at every epoch ② the same settings on **all 93 games**
for 18 epochs with a checkpoint per epoch (`runs/bc-93-v4-w256-fc19/epoch-01…18`, `inference.pt` + `metadata.json` as
`bc_train` writes them; work tree, outside git).
Pre-registered checks: (가) epoch 9 per fold equals the 121a `all` arm to the fourth decimal (`identical_to_121a`)
(나) the last checkpoint read back gives the same loss and hits (다) finite training loss.
Pre-registered reading: checkpoint epoch = the epoch with the lowest fold-mean validation loss (the `bc_train` rule,
117); lowest at epoch 18 = "not turned yet". Accuracy: per-game accuracy at every epoch and the paired difference
against epoch 9 (93 validation games, t 95% interval, no correction); two main comparisons — (i) rule epoch − epoch 9
(ii) epoch 18 − epoch 9: above 0 = longer training raises imitation accuracy, includes 0 = unconfirmed, below 0 = it
hurts. If the highest-accuracy epoch differs from the lowest-loss epoch: their paired difference includes 0 → the loss
rule stands; above 0 → two candidates are reported (policy teacher plays the argmax = accuracy, PPO starting point is a
distribution = loss) and **the user chooses — no automatic rule**. Limits written in advance: an epoch picked among 18
on the validation games has optimistic numbers, one seed, fold curves use 72–77 games and the full training 93 (carried
over by epoch count, not step count), the full model has no validation of its own, metadata capacity is the default
2048, `OfflinePolicy` loading and play are not checked here.
Work tree venv (the lab venv has no torch), host agentmaco, lab commit 99b8394, 2026-11-18 14:49:41 → 15:28:08
(38 min; script 2,304 s). Result: lab/results/122-bc-v4-epochs-93.md.

**Health: clean.** Exit code 0. (가) `identical_to_121a` true, `max_abs_difference_from_121a` 0.0 (epoch 9 loss
2.0816·2.0940·2.1144·2.1069·2.1488, accuracy 40.52·40.07·36.47·38.07·39.17%) → epochs 1–9 are the computation of 121a.
(나) `last_epoch_read_back_equal` true. (다) passed (the script asserts it). 93 games (geo 4 · a 20 · b 18 · c 18 ·
d 17 · e 16), 28,098 decisions, validation games per fold 21·20·19·17·16, steps per fold 1,638–1,782 (91–99 per epoch),
full training 2,052 steps (114 per epoch). No second-model review section on the result page (command job).
Checkpoints (bot turn, read of the 18 `metadata.json`): 18 folders, 18 `inference.pt`, **one** `versions` value across
all 18 — engine fc19671c4278, `python_build_id` ef5e3507 (the id of 120), torch 2.14.0 — so no source changed under the
run (the reason E169 held the capacity change); `model_build_id` f0dfe94b (the id of the 120 fold checkpoints),
encoding 4, width 256, `settings.capacity` 2048.

## The curve (5 folds, 93 validation games; this replaces the charges table — no verdict on the teacher)

| Epoch | Validation loss (fold mean) | Training loss (fold mean) | Per-game accuracy | − epoch 9 | 95% interval | Games better / equal / worse |
|---:|---:|---:|---:|---:|---|---|
| 1 | 2.3140 | 2.4384 | 31.53% | −7.37 | [−7.99, −6.75] | 0 / 0 / 93 |
| 2 | 2.2173 | 2.2272 | 33.75% | −5.15 | [−5.83, −4.48] | 7 / 1 / 85 |
| 3 | 2.1717 | 2.1279 | 35.40% | −3.50 | [−4.04, −2.95] | 7 / 2 / 84 |
| 4 | 2.1476 | 2.0572 | 35.76% | −3.14 | [−3.81, −2.48] | 14 / 3 / 76 |
| 5 | 2.1408 | 2.0027 | 37.18% | −1.72 | [−2.36, −1.07] | 24 / 4 / 65 |
| 6 | 2.1178 | 1.9695 | 37.34% | −1.56 | [−2.22, −0.90] | 21 / 2 / 70 |
| 7 | 2.1118 | 1.9211 | 38.40% | −0.50 | [−1.04, +0.03] | 39 / 3 / 51 |
| 8 | 2.1220 | 1.8914 | 38.77% | −0.13 | [−0.66, +0.39] | 44 / 4 / 45 |
| **9** | **2.1091** | 1.8487 | 38.90% | 0 | — | — |
| 10 | 2.1141 | 1.8171 | 38.69% | −0.21 | [−0.69, +0.26] | 38 / 6 / 49 |
| 11 | 2.1251 | 1.7894 | 39.05% | +0.15 | [−0.47, +0.78] | 41 / 1 / 51 |
| 12 | 2.1514 | 1.7608 | 38.46% | −0.45 | [−1.06, +0.17] | 41 / 1 / 51 |
| 13 | 2.1495 | 1.7396 | **39.59%** | **+0.69** | **[+0.15, +1.23]** | 55 / 5 / 33 |
| 14 | 2.1606 | 1.7142 | 38.64% | −0.26 | [−0.85, +0.32] | 39 / 4 / 50 |
| 15 | 2.1979 | 1.6898 | 38.76% | −0.14 | [−0.72, +0.44] | 44 / 1 / 48 |
| 16 | 2.2157 | 1.6640 | 38.85% | −0.05 | [−0.63, +0.54] | 43 / 5 / 45 |
| 17 | 2.2162 | 1.6433 | 39.39% | +0.49 | [−0.12, +1.10] | 48 / 5 / 40 |
| 18 | 2.2262 | 1.6168 | 39.17% | +0.27 | [−0.31, +0.85] | 44 / 2 / 47 |

Differences in percentage points, paired over the 93 validation games, t interval, no correction (result page).
Lowest-loss epoch per fold: 9 · 7 · 7 · 9 · 6. Decision-weighted accuracy: epoch 9 38.90% (114 games 38.78%, 119 games
39.01%), epoch 13 39.66% (39.45% / 39.87%), epoch 18 39.21% (39.01% / 39.40%) — `metrics.epochs` of the result json.

**Checkpoint epoch by the rule: 9** (fold-mean validation loss 2.1091; `lowest_loss_is_the_last_epoch` false). The
curve has turned: validation loss falls to epoch 9 and rises to 2.2262 at epoch 18 while training loss keeps falling
(1.8487 → 1.6168). The floor is flat over epochs 7–10 (2.1118 · 2.1220 · 2.1091 · 2.1141, a range of 0.013).

**(i) rule epoch − epoch 9: the same epoch, difference 0 by identity** — the loss rule does not pick a longer training.
**(ii) epoch 18 − epoch 9: +0.27pt [−0.31, +0.85], 44 / 2 / 47 games, per fold −0.64 · −0.22 · +2.66 · +0.90 · −1.44
(2/5) → includes 0 = unconfirmed** (18 epochs are not told apart from 9 on imitation accuracy).

**Highest-accuracy epoch 13 against lowest-loss epoch 9: +0.69pt [+0.15, +1.23], t 2.55, 55 / 5 / 33 games, per fold
+1.29 · +0.96 · +1.68 · −0.54 · −0.29 (3/5) → above 0 → by the pre-registered wording two candidates go to the user:
epoch 9 (loss) and epoch 13 (accuracy).** No automatic rule.

## Activation (did the script do what was registered)

- Epochs 1–9 reproduce 121a exactly (check (가)), so the curve from epoch 10 on is the continuation of the same runs.
- Every epoch scored all validation decisions of its fold (per-game accuracy over 93 games at every epoch).
- 18 checkpoints written, the last one read back equal; full-training loss 2.4007 → 1.8211 (epoch 9) → 1.7219
  (epoch 13) → 1.6081 (epoch 18), close to the fold-mean training loss at the same epochs (1.8487 · 1.7396 · 1.6168).
- Not done here, as registered: `OfflinePolicy` loading and a played game with these checkpoints.

## Reading (HANDOFF 1 order, adapted — no teacher verdict)

- **Epoch by the loss rule = 9; "longer is better" is not shown.** After epoch 9 the model overfits in the sense the
  rule measures (validation loss +0.117 by epoch 18) while accuracy stays level: the mean of epochs 10–18 is 38.96%
  against 38.90% at epoch 9 (table above). Rising loss with level accuracy = the argmax is kept, the probabilities get
  over-confident — which matters for a PPO starting point (a distribution), less for a policy teacher (argmax).
- **Epoch 13 (① noise is not excluded).** The pre-registered comparison is above 0, and that is what is reported. What
  weakens it, all of it written in the queue note as limits or visible in the table: (a) epoch 13 is the best of 18
  epochs picked on the same 93 games and the interval is uncorrected — against 17 other epochs the Bonferroni two-sided
  5% threshold is t 3.06 (92 df), and t is 2.55, uncorrected p 0.012 (b) its neighbours are below epoch 9 (epoch 12 −0.45, epoch 14 −0.26) —
  a peak, not a plateau (c) 3/5 folds (d) within a fold the accuracy moves up to about 3pt from one epoch to the next
  (fold 0: 38.52 → 41.84 → 39.16% at epochs 12–14; fold 4: 35.98 → 31.90 → 36.99% at epochs 3–5), more than the
  0.69pt in question, with one torch seed and one batch order (e) its validation loss is 2.1495 against 2.1091.
  So: epoch 13 is a registered candidate, not a measured improvement; a second torch seed on the same folds would
  tell (not run).
- **Scope: epoch count against step count.** The fold runs make 91–99 steps per epoch and the full training 114, so
  epoch 9 of the full model is 1,026 steps against 819–891 in the folds (the same step count would be epoch 7–8 of the
  full model). The registered transfer is by epoch count; the floor of the curve is flat over epochs 7–10, so the two
  transfers land in the same basin. The full model has no validation of its own.
- **Measurement.** Imitation accuracy (38.9%) is not strength; whether the checkpoint plays well is the A/B against
  the teacher on charges in rounds 1–3 (E166 (ㄹ)), which this cycle does not touch.
- **Condition.** Checkpoint metadata says capacity 2048; one decision in 28,098 has more candidates (E165), so play
  needs the run-time capacity 4096 change (E168 (가), held by E169 until this run ended — it ended, and the 18
  checkpoints carry one `python_build_id`).
- Health and timing: clean, 38 min against the 40 estimated.

No code or deployment change (the run wrote checkpoints outside git). Lab: 123 (48-game 6R collection, about 16 h) is
next in the queue.

## Proposal (user decision, nothing queued)

- (ㄱ) **Checkpoint epoch — the user's choice (pre-registered)**: `epoch-09` (lowest validation loss; the rule) or
  `epoch-13` (highest accuracy, +0.69pt [+0.15, +1.23] uncorrected, a single peak), or both as two BC arms in (ㄹ).
  Bot recommendation: `epoch-09` for both uses (policy teacher and PPO starting point); `epoch-13` stays on disk.
- (ㄴ) Run-time capacity 4096 as listed in E169 (`evaluation.py` `OfflinePolicy(checkpoint, capacity=None)`,
  `policy_teacher.make(..., capacity)`, `training.py` `initialize_from`, tests) + a spec for the 93-game checkpoint +
  the smoke seed of E158/E164 (quartet-b-68171@order=0,2,3,1, four seats the same BC, 6R) — bot turn. Loading does not
  depend on the choice in (ㄱ).
- (ㄷ) BC (encoding 4, 93 games) against the teacher, 12 pairs, charges in rounds 1–3 (E157 rule) — after (ㄴ); the lab
  venv needs torch (user command); the lab is busy with 123 for about 16 h.
- (ㄹ) A second torch seed on the same 5 folds (lab command, about 35 min, after 123) to tell whether epoch 13 is
  noise — not recommended: 0.7pt of imitation accuracy does not decide strength, (ㄷ) does.
Bot recommendation: (ㄱ) `epoch-09` → (ㄴ) now → (ㄷ) when 123 ends and torch is in the lab venv.
