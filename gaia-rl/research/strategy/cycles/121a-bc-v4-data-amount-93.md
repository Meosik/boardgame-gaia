# Cycle 121a — 93 games (114 + 119) in encoding 4: about 74 training games beat about 37 at the same step count by +2.32 points, 37 against 19 is not confirmed — command, no teacher verdict

A = the smaller training sets, B = the larger ones, same network and training step as `tools/bc_train.py`
(width 256, lr 0.001, batch 256, torch seed 0, batch order seed 0). Script `lab/scratch_v4_amount.py`
(commit 0370eff, recorded in the metrics as `script_commit`). Data: the 46 games of 114 (shards of cycle 120,
`runs/bc-114-v4-shards-fc19`) and the 47 games of 119 exported in this run with `bc_dataset.py export --encoding 4
--capacity 4096` (`runs/bc-119-v4-shards-fc19-c4096`) = 93 games, 28,098 decisions, engine `fc19671c4278`.
121a is the re-run of 121, which failed after 3 minutes in the 119 export (one decision with 2,257 candidates,
encoder capacity 2048; HANDOFF E165, fix 0370eff). Queued 2026-11-18 by the user 「일단 하던거 마저 해」 (E165;
the design is E163 (ㄱ), clean Codex round, user 「진행해」 E164). No games, not a teacher verdict.
Five folds stratified by quartet (k-th game of a quartet → fold k mod 5; the 114 games keep the folds of
117/118/120). Per fold five arms, validated on the held-out games of the fold: `all` (every training game, 9
epochs), `half-steps` (every other training game of a quartet, stopped at the step count of `all`),
`quarter-steps` (every fourth, same step count), `half` and `quarter` (the same subsets at 9 epochs of their
own, fewer steps: beside only).
Pre-registered reading (queue note; per-game accuracy difference at the last point, paired over the 93 validation
games, t 95% interval, no correction, three primary comparisons): ① `all − half-steps` above 0 → the number of
games is still one of the limits at 74 games = a reason to collect more in the same way (how many is the user's
number); includes 0 → a gain beyond 37 games is not confirmed. ② `half-steps − quarter-steps` = whether 117 ③
(35 against 20 games, +1.36 points [+0.55, +2.17]) repeats with the real tools: above 0 → repeated, includes 0 →
not repeated. ③ `all − quarter-steps` = the whole span. Saturation is read only from the upper end of the ①
interval against a threshold the user sets (none set). Beside only: the same-epoch comparisons, the `all` arm on
the 114 games against 36.38% of 118, the lowest point of the curves.
Work tree venv on the lab host (agentmaco), lab commit e7707bf, 2026-11-18 13:29 → 14:34 (65 minutes; export 415
seconds, folds 11–13 minutes each). Result: lab/results/121a-bc-v4-data-amount-93.md.

**Health: clean.** Exit code 0; the script's asserts passed (the `-steps` arms stop at the step count of `all`,
9 validation points per arm, every validation decision scored, shard decision counts equal to the manifests).
Export 14,257 decisions in 8 shards, written to a `.partial` directory and renamed. 93 games: geo 4, a 20, b 18,
c 18, d 17, e 16; validation games per fold 21·20·19·17·16, validation decisions 6,252·5,922·5,859·5,140·4,925 =
28,098. The result page has no second-model section (command job).

## Accuracy by arm (last point, 5 folds)

| Arm | Training games per fold | Steps per fold | Per-game mean | Decision-weighted | 114 games | 119 games | Per fold | Validation loss, last point (fold mean) | Lowest point of 9 |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| `all` | 72–77 | 819·837·846·891·891 | 38.90% | 38.90% | 38.78% | 39.01% | 40.52·40.07·36.47·38.07·39.17 | 2.1091 | 9th (2.1091) |
| `half-steps` | 37–40 | same | 36.58% | 36.65% | 36.04% | 37.24% | 38.93·37.91·35.72·33.87·36.22 | 2.2173 | 4th (2.1677) |
| `quarter-steps` | 20–21 | same | 36.21% | 36.26% | 36.10% | 36.41% | 37.30·37.23·34.60·35.97·36.02 | 2.3338 | 5th (2.2361) |
| `half` (beside) | 37–40 | 450·477·477·495·495 | 34.77% | 34.95% | 34.72% | 35.16% | 34.69·35.12·33.62·34.96·36.61 | 2.2705 | 7th (2.1931) |
| `quarter` (beside) | 20–21 | 279·315·315·315·315 | 32.84% | 32.89% | 32.68% | 33.10% | 32.76·33.77·32.10·32.68·33.16 | 2.2602 | 9th (2.2602) |

## Comparisons (the pre-registered reading)

| Comparison | Mean difference | 95% interval | t | Games better / equal / worse | Per fold (points) | 114 games | 119 games | Reading |
|---|---:|---|---:|---|---|---|---|---|
| ① `all − half-steps` (about 74 against 37 games) | **+2.32** | [+1.68, +2.96] | 7.18 | 72 / 1 / 20 of 93 | +1.68 · +2.15 · +0.77 · +4.28 · +3.14 | +2.82, 39/46 | +1.83, 33/47 | above 0 |
| ② `half-steps − quarter-steps` (about 37 against 19) | +0.37 | [−0.29, +1.02] | 1.12 | 49 / 3 / 41 | +1.67 · +0.62 · +1.27 · −2.24 · +0.05 | −0.08, 24/46 | +0.81, 25/47 | includes 0 |
| ③ `all − quarter-steps` (about 74 against 19) | **+2.69** | [+2.09, +3.30] | 8.83 | 82 / 1 / 10 | +3.34 · +2.77 · +2.05 · +2.04 · +3.19 | +2.74, 40/46 | +2.65, 42/47 | above 0 |
| beside: `all − half` (same epochs) | +4.13 | [+3.40, +4.86] | 11.19 | 81 / 1 / 11 | +6.02 · +5.16 · +3.08 · +3.30 · +2.49 | +4.16 | +4.10 | — |
| beside: `all − quarter` (same epochs) | +6.06 | [+5.38, +6.74] | 17.64 | 90 / 0 / 3 | +7.97 · +6.29 · +4.39 · +5.35 · +6.01 | +6.14 | +5.98 | — |

By quartet (mean difference in points, games better / games): ① geo +1.95 3/4 · a +1.84 14/20 · b +2.35 15/18 ·
c +2.13 13/18 · d +2.88 13/17 · e +2.60 14/16; ② geo −0.19 · a +1.23 · b +0.59 · c +0.22 · d +0.22 · e −0.48;
③ geo +1.76 4/4 · a +3.07 20/20 · b +2.95 18/18 · c +2.35 14/18 · d +3.10 15/17 · e +2.12 11/16.
Beside: the `all` arm scores 38.78% on the 114 games; 118 and 120 (trained on the 114 games only, same folds and
the same validation games, about 400 steps) scored 36.38%.

① **above 0: with these subsets, about 74 training games give +2.32 points over about 37 at the same step
count**; positive in 5/5 folds, 6/6 quartets and on both the 114 and the 119 games. Pre-registered word: the
number of games is still one of the limits at 74 games, so collecting more in the same way is the next lever
candidate; how many games is the user's number. The lower end of the interval is +1.68, so the saturation question
(upper end below a threshold) does not arise.
② **includes 0: 117 ③ is not repeated** at this step count (+0.37 [−0.29, +1.02]; 117 ③ +1.36 [+0.55, +2.17] —
the two intervals overlap, so this is not a contradiction either). On the 114 games alone the difference is −0.08
points.
③ **above 0: +2.69 points over the whole span**, the steadiest of the three (5/5 folds between +2.04 and +3.34).

## Activation (did the design run as written)

- Step counts of the `-steps` arms equal those of `all` in every fold (819·837·846·891·891); `quarter` ⊂ `half` ⊂
  `all` and no validation game in a training set (assert in the script).
- **The subsets repeat across folds** (follows from fold = k mod 5 and "every other / every fourth of the
  remaining games", and is visible in the training decision counts): the `quarter` subset is the games of fold 0
  in folds 1–4 (21 games, 6,252 decisions = the validation set of fold 0) and the games of fold 1 in fold 0 (20
  games, 5,922); the `half` subset is folds 1+3 (fold 0: 37 games, 11,062), folds 0+3 (folds 1 and 2: 38 games,
  11,392) and folds 0+2 (folds 3 and 4: 40 games, 12,111). So there are 2 different quarter subsets and 3
  different half subsets, and folds 3 and 4 train the `half-steps` and the `quarter-steps` arm on the same games
  for the same 891 steps with the same seeds (the same training twice, scored on two validation sets). The queue
  note said "no random draw" but did not spell this out.
- The one decision above capacity 2048 (2,257 candidates) is in the data as one row (export capacity 4096).

## Reading (HANDOFF 1 order)

- ① noise: the t interval is over the 93 validation games and treats them as independent; it does not contain the
  choice of subset (2–3 different subsets, above) or the torch seed (one seed). At the fold level ① is +0.77 to
  +4.28 and depends on the half subset: +1.68 (folds 1+3), +2.15 and +0.77 (folds 0+3), +4.28 and +3.14 (folds
  0+2). The sign is the same with all three subsets, the size is not settled: "+2.3" is the mean over these
  subsets, the fold range is the honest width. For ② the same pair of trainings gives −2.24 on fold 3 and +0.05
  on fold 4, and the other half subsets give +0.62 to +1.67: ② is inside the subset-to-subset spread, so "not
  repeated" is the pre-registered word and "117 ③ was noise" is not shown.
- ② activation: asserts passed, see above.
- ③ scope: one width (256), one lr, one seed, 9 epochs for `all`. The `-steps` arms were not held back in
  accuracy by the long training: at the last point they score above the same subsets at 9 epochs of their own
  (`half-steps` 36.58% against `half` 34.77%, `quarter-steps` 36.21% against `quarter` 32.84%) although their
  validation loss is past its lowest point (4th and 5th of 9). No accuracy curve was saved, so the accuracy at
  the lowest-loss point is not known. Beside: the lowest validation loss of each arm is still ordered by data
  amount (2.109 < 2.168 < 2.236; points picked on the validation games), about −0.06 per doubling with no sign
  of flattening.
- ④ interaction with the step count: 117 ③ ran about 400 steps (matched to about 37 games), ② here runs 819–891
  (matched to about 74 games), which is about 16 epochs for `half-steps` and about 26 for `quarter-steps`. The
  design cannot separate "the 19 → 37 gain is smaller with the real tools" from "it shrinks at twice the steps".
- Epochs for the full-data checkpoint: the `all` curve (fold mean 2.314 · 2.217 · 2.172 · 2.148 · 2.141 · 2.118
  · 2.112 · 2.122 · 2.109) is lowest at the last point, so 9 epochs are not too many at about 74 games; whether
  more than 9 is better was not measured (the curve has not turned, and the small arms gained accuracy from more
  steps). The result gives a lower bound for the epoch count, not the value.
- ⑤ measurement: imitation accuracy is not playing strength. 38.9% is +2.4 points over the 114-only model on the
  same validation games (beside, different step counts); whether that moves charges in rounds 1–3 is not measured
  (E158/E162 smoke: BC 78.5 charges per seat below the teacher, 2 games, not an A/B).
- ⑥ condition: both collections are the same teacher setting (`ships_menu1_all_tier` cap60-p2, 6 rounds); 119 was
  collected after three teacher changes and one engine change, and adding it does not hurt the 114 validation
  games (38.78% against 36.38%, beside).
- Health and timing: clean, 65 minutes (estimate 60).

No code or deployment change. The run wrote no checkpoint (measurement only). Lab queue empty after this cycle.

## Proposal (user decision, nothing queued)

- (ㄱ) Epoch length and full-data checkpoint in one lab command (about 40 minutes): the `all` arm of the same 5
  folds trained to 18 epochs with validation loss and accuracy recorded at every epoch, plus one training on all
  93 games with the weights of every epoch saved; the checkpoint epoch is then read from the fold curves. Needs a
  way to train on the two shard directories together (`bc_train.py` takes one). Script committed before the
  queue file (E162 rule).
- (ㄴ) More collection in the same setting (pre-registered consequence of ①). The number of games is the user's:
  48 games took 15 h 56 min in 119. Before a long collection: the `pair-017` crash (1 of 48 games lost in 119)
  and the pre-search stages that pass the cap (9 fallback decisions) are still open.
- (ㄷ) E165 (가)(나)(다): candidate capacity in play (run-time capacity 4096 with the trained weights, one
  federation route for policy seats, or the first 2,048 candidates) — needed before (ㄹ) and PPO; user answer
  pending.
- (ㄹ) BC (encoding 4) against the teacher, 12 pairs, charges in rounds 1–3 (E157 rule) — after (ㄱ) and (ㄷ);
  torch in the lab venv is a user command.
Bot recommendation: (ㄱ) now; (ㄴ) as soon as the user names the number of games (the lab is otherwise idle);
(ㄷ) → (ㄹ) after that.
