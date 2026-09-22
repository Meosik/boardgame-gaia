# Additional learning from the economic teacher

Approved scope: more short offline learning, not hosting/sharing, production gameplay,
or new faction strategies. The economic teacher still labels **Xenos/Hadsch Hallas**
only. Shared PPO receives experience from all four players; this does not imply that
other factions' recommended strategies have been implemented.

## Comparison

Both arms begin at `strategy-pilot-v2/baseline/inference.pt`, the stronger existing
neural policy in that pilot. Original files are read-only and their hash is checked.
These artifacts contain inference weights, **not optimizer state**. Both PPO arms
therefore start fresh optimizers; this is continued-weight learning, not an exact
checkpoint resume.

1. `continued_ppo`: starting weights + another four PPO iterations × 256 configured steps.
2. `bc_only`: starting weights + four epochs of economic-teacher demonstrations;
   diagnostic evaluation before reinforcement learning.
3. `economy_bc_ppo`: the BC weights + exactly the same extra PPO settings as arm 1.

The BC arm has extra supervised compute; total compute is not matched. Same PPO seed,
setup pool and optimizer settings are used. No extra reward shaping/encoder changes.

- Demonstrations: six training games, two validation games; economic teacher controls
  only the two target factions and random legal policy controls others.
- Unmodeled and single-candidate forced decisions are excluded from supervised labels;
  raw decision logs preserve the teacher choices and reasons.
- Training, validation and evaluation seeds stay disjoint. Evaluation reuses the same
  four previously inspected maps and balances each target faction across all seats.
- Eight complete games attempted for each learned policy, versus three independently
  seeded random opponents. This is not a fresh generalization benchmark or human play.
- Completed-only averages are explicitly labeled and failures are retained.

## Reproduce

From the repository root:

```sh
OMP_NUM_THREADS=2 PYTHONPATH=gaia-rl/experiments gaia-rl/.venv/bin/python \
  -m unittest discover -s gaia-rl/experiments/economy_learning -p 'test_train.py' -v
OMP_NUM_THREADS=2 gaia-rl/.venv/bin/python \
  gaia-rl/experiments/economy_learning/train.py --output gaia-rl/runs/economy-learning-new
```

A new output path is mandatory. Runtime/native/encoder versions and original/economic/
learning source hashes guard startup and completion. No original training defaults,
models, game rules or frontend catalog are changed. Manifest records starting weights,
versions, split seeds, budget and the reset-optimizer limitation. The run retains
teacher decision logs, sample statistics, BC metrics, inference-only intermediate and
final weights, PPO losses/sample diagnostics, all evaluation games and a final report.
No automatic deployment or repeated tuning on evaluation results.

## Known limits

- Recent academy timing, goal-directed resource conversion, costly power acceptance,
  range/terraform combination comparison and federation-cluster planning suggestions
  are **not implemented** in this trial. It uses the already-tested economic teacher.
- That teacher's improved direct score does not guarantee improved imitation or PPO.
- Pinned engine still contains the raw-Gaia entry-QIC and TF Mars combined-credit
  validation discrepancies identified in `../economy/README.md`. They are not repaired
  as a side effect of training; a fix needs versioned rebuild and new baseline.
- The original module/RLlib deprecation warning remains; no dependency migration was
  attempted in this bounded run.

## First completed continuation — `runs/economy-learning-v1`

**Training completed; playing performance regressed.** Do not replace the preserved
starting model or claim successful strategy transfer.

| Policy | Xenos mean VP | Hadsch Hallas mean VP | Focal federations (8 games total) |
|---|---:|---:|---:|
| Preserved starting PPO (prior evaluation) | 66.50 | 52.50 | 7 |
| Additional PPO only | 46.25 | 34.50 | 5 |
| Economic BC only | 52.25 | 28.50 | 3 |
| Economic BC + additional PPO | 41.50 | 35.25 | 0 |

- Six demo and two validation games completed. 907 training labels (Xenos513, HH394),
  324 validation labels (Xenos179, HH145); raw logs independently audited for faction,
  legal index and sample-count agreement.
- BC four epochs/456 gradient steps. Validation agreement17.28%→30.56%,
  cross-entropy2.8728→2.3227. Both refer to this new teacher's same validation dataset,
  not the previous pilot's different teacher/data.
- Each PPO arm completed four iterations, 1,024 native environment steps and 1,042
  module samples. Optimizers reset in both arms; BC adds extra supervised compute.
- 24/24 post-training evaluation games complete. ~283 seconds for this run, excluding
  startup tests and post-run artifact verification. No failed games omitted.
- Total/policy/value losses and weights finite. RLlib's ancillary
  `num_trainable_parameters` diagnostic is NaN (not a model tensor or loss); the stored
  training logs retain it rather than inventing a parameter count.
- Four new tests pass. All three saved models reloaded, finite weights and initial legal
  decisions checked; evaluation means recomputed. Original weight and all source/runtime
  fingerprints preserved. No frontend catalog/server inference changes.

Both the BC-only and PPO-only arms are worse than the common starting model. This
rules out attributing this run's regression exclusively to PPO after BC, but does not
isolate the cause. Small/reused map sample, limited data, distribution shifts, flat
features, optimization and sparse action learning remain hypotheses. Better teacher
scores alone are not evidence that its imitation student will improve. No automatic
larger run, policy retuning, reward changes or deployment followed this result.
