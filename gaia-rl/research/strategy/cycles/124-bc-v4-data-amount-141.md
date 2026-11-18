# Cycle 124 — BC encoding 4 on 141 games: data amount one step further (about 113 against about 75 games at equal steps), 18-epoch curve, checkpoints of a training on all 141 games — command, no games

Not a teacher A/B: no A and B specs. One script, `lab/scratch_v4_amount_141.py` (commit 8354afb, committed before the
queue file; it refuses to start with uncommitted changes to itself or an existing checkpoint folder — E162 rule), run
as a lab command in the work tree venv. Queued 2026-11-19 by E183 (user 2026-11-13 「codex 이상 없으면 추천대로 진행해」 +
a clean Codex round on E182 (ㄱ)); it is the next step that the 123 queue note fixed in advance.
Steps: ① `bc_dataset.py export --encoding 4 --capacity 4096` of the 123 manifest (48 games, 14,050 decisions) —
the 114 and 119 shards are those of 120 and 121a ② the 141 games (114 46 + 119 47 + 123 48, 42,148 decisions, all
replayed strictly on engine fc19671c4278) in 5 quartet-stratified folds (the 114 and 119 games keep their folds of
121a and 122) ③ per fold two arms with the network and step of `tools/bc_train.py` (width 256, lr 0.001, batch 256,
torch seed 0): `all` (every training game, 110–115, 18 epochs, validation after each epoch) and `twothirds-steps`
(two of every three training games of each quartet, 75–79 games, stopped at the step count of 9 epochs of `all`)
④ the same settings on all 141 games for 18 epochs, a checkpoint per epoch.
Pre-registered reading: **amount** (one main comparison) = per-game accuracy of `all` at epoch 9 minus
`twothirds-steps` at the same step count, paired over the 141 validation games, t 95% interval — above 0 → the
number of games is still one of the limits at about 113 games (more collection of the same kind stays a lever; how
many is the user's number), includes 0 → no gain shown beyond about 75 games (not read as saturation), below 0 →
report and look at subset and fold noise first; no size comparison with 121a ① (2× against 1.5× the games).
**Epoch** (as 122): checkpoint epoch = lowest fold-mean validation loss; (i) rule epoch − 9 (ii) 18 − 9; when the
epoch of highest accuracy differs from the rule epoch and the paired difference is above 0, both go to the user.
No correction for multiple comparisons.
Host agentmaco, lab commit e1cc517, 2026-11-19 06:59 → 08:25 (1 h 26 min; export 382 s, folds 13–15 min each, the
full training about 11 min). Result: `lab/results/124-bc-v4-data-amount-141.md`.

**Health: clean.** Exit code 0; every assert of the script passed (step counts of both arms, every validation
decision scored once and the same decisions in both arms, finite training loss, the last checkpoint read back with
the same loss and hits). 141 games (geo 6, a 30, b 28, c 27, d 26, e 24), 42,148 decisions, validation games per
fold 31 · 29 · 28 · 27 · 26. The result page has no review section (command job).

## Charges in rounds 1–3 (the verdict)

None — no games were played. The tables below replace it; they measure imitation accuracy (how often the network's
first choice is the teacher's move), not strength.

### Amount: `all` at epoch 9 against `twothirds-steps` at the same step count (pre-registered)

| | training games | steps | per-game accuracy | decision-weighted | fold-mean validation loss |
|---|---:|---:|---:|---:|---:|
| `all`, epoch 9 | 110–115 | 1,242–1,323 | 40.03% | 40.02% | 2.0885 |
| `twothirds-steps`, last point | 75–79 | the same | 37.65% | 37.61% | 2.1547 |

**Difference +2.38pt [+1.88, +2.89], t 9.38, games better/equal/worse 110/6/25 of 141.**
Per fold +1.41 · +1.50 · +2.12 · +3.45 · +3.71 (5/5). Per quartet geo +3.28 (6 games) · a +2.53 · b +2.47 ·
c +2.02 · d +2.06 · e +2.62 (6/6). Per collection 114 +2.13 (46) · 119 +2.75 (47) · 123 +2.26 (48).

Reference, not registered (fold means from the printed curves, no interval — the hits of the intermediate points of
`twothirds-steps` were not stored): the small arm is past its own best point at the equal step count.

| `twothirds-steps` at the step count of `all` epoch | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fold-mean validation loss | 2.2698 | 2.1741 | 2.1475 | 2.1174 | **2.1120** | 2.1351 | 2.1420 | 2.1724 | 2.1547 |
| fold-mean accuracy | 32.89% | 35.73% | 36.28% | 37.52% | **38.07%** | 38.05% | 37.55% | 37.01% | 37.56% |

- Each arm at its own lowest fold-mean loss (`all` epoch 8, 39.83% by fold mean; small arm point 5, 38.07%):
  **+1.76pt**, per fold +1.45 · +3.13 · +2.54 · +1.62 · +0.07.
- `all` at epoch 9 against the small arm's best point (5): +1.96pt, per fold +1.19 · +2.29 · +1.92 · +2.78 · +1.61.

### Epoch curve of `all` (5 folds, 141 validation games)

| epoch | fold-mean validation loss | training loss | per-game accuracy | against epoch 9 [95%] | games better/equal/worse |
|---:|---:|---:|---:|---|---:|
| 1 | 2.2456 | 2.3830 | 33.96% | −6.07 [−6.58, −5.56] | 3/1/137 |
| 3 | 2.1203 | 2.0752 | 37.70% | −2.33 [−2.79, −1.88] | 22/10/109 |
| 6 | 2.1013 | 1.9343 | 38.76% | −1.27 [−1.76, −0.78] | 44/11/86 |
| 7 | 2.0886 | 1.9006 | 39.18% | −0.85 [−1.23, −0.47] | 47/6/88 |
| **8** | **2.0874** | 1.8641 | 39.82% | −0.21 [−0.60, +0.18] | 65/7/69 |
| 9 | 2.0885 | 1.8287 | **40.03%** | 0 | — |
| 10 | 2.1092 | 1.8005 | 40.02% | −0.01 [−0.33, +0.31] | 67/12/62 |
| 11 | 2.1482 | 1.7800 | 39.22% | −0.81 [−1.21, −0.41] | 46/8/87 |
| 12 | 2.1520 | 1.7548 | 39.32% | −0.71 [−1.11, −0.31] | 50/10/81 |
| 13 | 2.1504 | 1.7230 | 39.60% | −0.43 [−0.85, −0.01] | 54/5/82 |
| 14 | 2.1902 | 1.7021 | 39.24% | −0.79 [−1.22, −0.36] | 50/5/86 |
| 15 | 2.1847 | 1.6822 | 39.68% | −0.35 [−0.75, +0.06] | 59/7/75 |
| 18 | 2.2205 | 1.6176 | 39.88% | −0.15 [−0.59, +0.28] | 64/9/68 |

(All 18 rows are in the result page.) Lowest loss per fold: epoch 7 · 8 · 7 · 7 · 10. Decision-weighted accuracy by
collection at epoch 9: 114 games 39.56% · 119 games 40.67% · 123 games 39.80% (epoch 8: 40.03 · 40.14 · 39.41).

- **Checkpoint epoch by the rule: 8** (fold-mean loss 2.0874; epochs 7–9 are level within 0.0012). It is not the
  last epoch: the curve turned (validation loss 2.0874 → 2.2205 while the training loss falls 1.8641 → 1.6176).
- **(i) rule epoch 8 − epoch 9: −0.21pt [−0.60, +0.18], 65/7/69 → includes 0.**
- **(ii) epoch 18 − epoch 9: −0.15pt [−0.59, +0.28], 64/9/68 → includes 0.**
- Highest accuracy (epoch 9) − lowest loss (epoch 8): +0.21pt [−0.18, +0.60], t 1.09, 69/7/65, per fold
  −0.18 · −0.71 · −0.55 · +1.15 · +1.56 → **includes 0 → the rule epoch stays, one candidate.**

### Training on all 141 games

`runs/bc-141-v4-w256-fc19/epoch-01 … epoch-18` (work tree, outside git), each with `inference.pt` + `metadata.json`:
3,078 steps (171 per epoch), training loss 2.3453 → 1.8641 (epoch 8) → 1.5868 (18), last epoch read back equal.
Metadata of `epoch-08`: engine fc19671c4278, `python_build_id` 4feceef9 (120 and 122 had ef5e3507 — the Python
sources changed since, db997d9), `model_build_id` f0dfe94b, encoding 4, width 256, capacity 2048.

## Activation (did the script do what was registered)

- Export: 14,050 samples in 8 shards, 382 s, written to `.partial` and renamed; shard decision counts equal the
  manifests (assert).
- Step counts: `all` = steps per epoch × k (138 · 141 · 142 · 145 · 147 per epoch); `twothirds-steps` stopped at
  1,242 · 1,269 · 1,278 · 1,305 · 1,323 = 9 epochs of `all` in the same fold (assert). Training games of the small
  arm 75 · 76 · 77 · 78 · 79.
- Script commit in the metrics = 8354afbb01cc, engine build id = fc19671c4278 (the build of all three collections).

## Reading (HANDOFF 1 order, adapted — no teacher verdict)

- **Amount: above 0 → by the registration, the number of games is still one of the limits at about 113 games.**
  Every fold, every quartet and every collection is positive, so it is not ① noise of the validation games. The
  **size** carries a ③ design effect that the queue note did not list: at the equal step count the small arm has
  made about 13 passes over its games and is past its own best point (loss lowest at point 5, about 7 passes;
  accuracy 38.07% there against 37.56% at the end). Part of the +2.38pt is that over-training (about 0.5pt by the
  small arm's own curve). With each arm at its own lowest loss the difference is about **+1.8pt** (fold means, no
  interval, not registered; 4 folds clearly positive, fold 4 +0.07). The direction does not depend on the point
  chosen; the size does. 121a's caveat (c) (「the `-steps` arms do not lose accuracy by long training」) was written
  without an accuracy curve; this run stored one and it shows a loss of about 0.5pt.
- The rise of the per-fold difference (+1.41 → +3.71) comes from the end point of the small arm (38.4% → 36.3%
  over the folds) while `all` is level (39.7–40.3%). The small arm's curve moves up to 3.5pt between neighbouring
  points in one fold (fold 0, points 7–9: 37.09% → 34.93% → 38.44%), so one end point per fold carries training noise
  that the interval over validation games does not contain (one torch seed — registered limit).
- **Epoch: rule epoch 8, (i) and (ii) include 0 → 「longer than 9 epochs imitates better」 is not shown**, as in 122.
  Epochs 11–14 are below epoch 9 with intervals under 0 (−0.4 to −0.8pt), then the curve returns to −0.15 to
  −0.35 (epochs 15–18) with intervals that include 0. No comparison of calibration or of the effect on PPO was made.
- **The accuracy peak of 122 at epoch 13 is not repeated**: here 13 − 9 = −0.43pt [−0.85, −0.01] (54/5/82). 122 had
  +0.69pt [+0.15, +1.23] chosen as the best of 18 on its own validation games (its caveat (a)). Different data
  (93 against 141 games), so this is not a test of the 93-game model — but nothing here supports a rule 「epoch 13」.
- **Epoch number or step count for the full training**: the turn follows passes over the data, not steps — the
  small arm turned at about 7 passes (690–735 steps), `all` at 8 passes (1,104–1,176 steps), 122's 72–77 games at
  7–10. That supports carrying the epoch number over (registered rule) → `epoch-08` of the full training
  (1,368 steps). The full model has no validation of its own (registered limit).
- Reference only: `all` at epoch 9 is 40.03% here against 38.90% in 122 (about 113 against 72–77 training games) —
  different validation games, not a paired comparison.
- Limits as registered: the two-thirds subsets overlap between folds, one torch seed, the chosen epoch's numbers
  are optimistic, capacity 2048 in the metadata (games need the run capacity 4096 of db997d9), 12 fallback rows of
  42,148 included, imitation accuracy is not strength (charges in rounds 1–3 are for the BC against teacher A/B).
- Health and timing: 1 h 26 min against 1.5 h estimated.

No code or deployment change (shards, checkpoints and metrics are outside git). The lab queue is empty. Known in
advance (queue note): the `env.rs` suffix work changes the engine build id, after which the full-data checkpoint is
trained again (about 20 min, as 120 did for 114); the amount and epoch measurements stay valid.

## Proposal (user decision, nothing queued)

- (ㄱ) The order fixed in E183: implement the `@factions=` · `@tiles=` suffixes in `gaia-rl/src/env.rs` and push
  (bot turn) → rebuild (user command) → re-index the three manifests and train the 141-game checkpoint again
  (lab about 20 min) → the 12-game baseline of the fixed bundle `quartet-e-88365` (about 4 h).
- (ㄴ) More collection of the same kind (the registered consequence of 「above 0」): the number of games is the
  user's (48 games took 15 h 11 min in 123). Not recommended now: the ladder of (ㄱ) is meant to change the teacher,
  and games of the present teacher would be collected again after it.
- (ㄷ) Close E171 (ㄱ) (epoch 9 or 13 of the 93-game checkpoints): the 141-game `epoch-08` replaces the 93-game
  checkpoint for the BC against teacher A/B (still waiting for torch in the lab venv, a user command).
- (ㄹ) A second torch seed on the same folds to put training noise into the size of the amount effect
  (lab about 1.2 h): not recommended, the direction is not in doubt and the size decides nothing now.

Bot recommendation: (ㄱ); (ㄷ) when the user agrees; (ㄴ) only after the ladder.
