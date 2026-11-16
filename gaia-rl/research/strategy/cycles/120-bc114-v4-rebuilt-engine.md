# Cycle 120 — the 46 games of 114 exported and trained again on the rebuilt engine: every row equal, the 5 folds of 118 repeated to the last digit — command, no teacher verdict

A = cycle 118 (`lab/scratch_v4_pipeline.py` on the old work tree engine build `36d2e007`): `bc_dataset.py export
--encoding 4` of the 46 games of 114 → `runs/bc-114-v4-shards`, 5 game-level folds through `tools/bc_train.py`
(width 256, 9 epochs, lr 0.001, batch 256, seed 0, weights of the lowest validation loss epoch saved),
decision-weighted epoch 9 accuracy 36.38%. B = the same export and the same folds on the rebuilt work tree engine
`fc19671c4278` (= the lab engine, HANDOFF E161): shards `runs/bc-114-v4-shards-fc19`, checkpoints
`runs/bc-114-v4-w256-fc19/fold-0…4`. Script `lab/scratch_v4_rebuilt.py`. Queued 2026-11-17 by the user 「진행해」
(HANDOFF E160 → E161, queue commit 69f0070). No games, not a teacher verdict: a reproduction check before the 114
shards are merged with 119 and before the fold checkpoints are used in smokes and A/B.
Pre-registered reading (queue note): ① export ② all five arrays (state vectors, candidate rows, candidate counts,
chosen index, game number) equal to the old-build shards, an assert failure otherwise ③ per fold and per epoch the
validation loss, validation accuracy and training loss equal to the 118 metrics (largest difference 0). ② and ③ →
the rebuild changes neither the encoding 4 input nor the training result → merge the 114 shards with 119 and use the
fold checkpoints. ② fails → find which array differs before merging. ② passes and ③ differs → read as training
non-determinism, report `max_abs_difference_from_118` and the 5-fold accuracy.
46 games (13,841 decisions), no seeds played, host agentmaco with the work tree venv (the lab venv has no torch),
lab commit 2e5b23b, 2026-11-17 08:22:08 → 08:37:21 (15 min 13 s; the script's own clock 911 s). Result:
lab/results/120-bc114-v4-rebuilt-engine.md.

**Health: clean.** Exit code 0, the equality assert passed, 5/5 folds trained, 5 checkpoints written. The result
page has no review section (command job). The 119 review turn indexed and counted charges on the same machine while
120 trained, so the duration is a reference only (HANDOFF E162).

Which script ran (HANDOFF E162 correction): the queue runs the work tree file directly, and that file carried an
uncommitted change (a `conditions` record in the metrics) when 120 started; the same content was committed as
e8377c9. The metrics hold the `conditions` key → 120 ran the e8377c9 content, not the 69f0070 one.

## Charges in rounds 1–3 (the verdict)

Not applicable: no games. The pre-registered reading is the row comparison and the fold metrics below.

## Activation — what was compared (result page metrics; `lab/scratch_v4_rebuilt.py`)

Row comparison, new-build shards against old-build shards: **13,841 decisions and 536,858 candidate rows, the five
arrays `observation`, `cand`, `counts`, `chosen`, `game` all equal.**

Folds, against the 118 metrics (`max_abs_difference_from_118` over validation loss, validation accuracy and training
loss of all 9 epochs):

| Fold | Validation decisions | Saved epoch (118) | Epoch 9 validation loss | Epoch 9 validation accuracy | Largest difference from 118 |
|---|---:|---:|---:|---:|---:|
| 0 | 3,242 | 6 (6) | 2.2851 | 35.66% | 0.0 |
| 1 | 3,409 | 6 (6) | 2.1607 | 38.02% | 0.0 |
| 2 | 3,137 | 8 (8) | 2.1873 | 35.19% | 0.0 |
| 3 | 2,302 | 9 (9) | 2.2121 | 36.23% | 0.0 |
| 4 | 1,751 | 4 (4) | 2.1926 | 36.89% | 0.0 |
| **5 folds, decision-weighted** | 13,841 | | 2.2076 (fold mean) | **36.38%** (118: 36.38%) | **0.0**, `identical_to_118` true |

Recorded conditions (`conditions` in the metrics): against 118 only `engine_build_id` (`36d2e007` → `fc19671c4278`)
and `python_build_id` (`af954b2c` → `ef5e3507`) changed; the dependencies are the same string (numpy 2.5.3,
torch 2.14.0, ray 2.58.0, gymnasium 1.2.2, pettingzoo 1.27.0), torch threads 8.

Checkpoints: `runs/bc-114-v4-w256-fc19/fold-0…4` in the work tree (not in git); fold 0 read back in this turn —
`inference.pt` + `metadata.json` with `model_build_id` f0dfe94b…, engine `fc19671c4278`, encoding 4, width 256.

## Reading

- Pre-registered outcome: ② passed and ③ is identical → **the engine rebuild changes neither the encoding 4 input
  nor the training result** for the 46 games of 114. The 114 shards can be merged with 119 (both exported on
  `fc19671c4278`), and the fold checkpoints carry the lab engine build in their metadata — the engine mismatch that made
  `require_loadable_checkpoint` refuse the old ones (E161 「지금 못 읽는 것」) is gone on paper; loading and playing
  from them is not exercised until (ㄴ).
- The Python build changed as well (e4e8279 and later, between 118 and 120) and the figures still repeat: neither
  the export path nor `bc_train` moved for encoding 4.
- What this does not show: (a) it is determinism on one machine and one venv (same torch, 8 threads) — a different
  machine or thread count is not covered; (b) the row comparison covers the 114 games only — the 47 games of 119
  exist only on the new build and have no old-build counterpart (none is needed); (c) the checkpoints were written,
  but no game has been played from them yet — the spec `tools/teacher-policy-bc-114-v4.json` still points at the
  old-build checkpoint `runs/bc-114-v4-w256-fold0-e6b`, which the rebuilt engine refuses.
- Accuracy itself is unchanged from 118 (36.38%; 117 `w256-all` 36.51%): nothing new about the model, only that the
  rebuilt engine is a safe base.

No code or deployment change in this cycle (the script commit e8377c9 was made in the 119 turn). Lab queue empty
after 120.

## Proposal (nothing queued in this turn)

- (ㄱ) Queue 121 (HANDOFF E162 (ㄱ), approved by a clean second-model round 11-17 08:29 on the condition that 120
  shows 「전 행 같음」 — now met): export 114 + 119 (93 games, 28,098 decisions) with encoding 4 and repeat the
  game-level cross-validation of 117 ③ / 118 (width 256, 9 epochs, folds stratified by quartet, about 18 / 37 / 74
  training games, paired on the validation games) to re-measure the effect of the amount of data. Lab command,
  ≈ 40 min. Rule from E162: the script is committed before the queue file, checks at start that it has no
  uncommitted difference and writes its commit id into the metrics.
- (ㄴ) Point `tools/teacher-policy-bc-114-v4.json` at `runs/bc-114-v4-w256-fc19/fold-0` and replay the E158 smoke
  seed (scores then 87·86·49·80) — bot turn; shows that the new checkpoint loads and plays on the rebuilt engine.
- (ㄷ) `pair-017` crash of 119 (quartet-b-86715, `No eligible continuation`): replay to step 17, find the filter
  that empties the candidates, fix, regression seed — bot turns 1–2 + lab ≈ 40 min.
- (ㄹ) BC (v4) vs teacher A/B, 12 pairs (E157 rule), after (ㄱ) with a checkpoint trained on all the data; torch in
  the lab venv is a user command.
- (ㅁ) The pre-search stages (`planned_tasks`, `root_rank`) that run past the cap (E162 (ㄷ)) — on hold until the
  next long collection.
Bot recommendation: (ㄱ) and (ㄴ) together in the next turn, then (ㄷ).
