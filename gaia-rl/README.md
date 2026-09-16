# Offline Gaia AI

Local four-player Lost Fleet simulator, PettingZoo AEC adapter and shared-policy
RLlib PPO candidate scorer. **No live-game AI opponent integration.**
Completed evaluations can be published to the read-only frontend replay viewer.
The bundled pilot checkpoints are verification artifacts, not a strong opponent.

## Build

From this directory, using the existing virtual environment:

```sh
VIRTUAL_ENV="$PWD/.venv" .venv/bin/maturin develop --release
.venv/bin/python -m unittest discover -s python/tests -v
cargo test
```

A fresh environment needs Python 3.12+, maturin and the pinned dependencies from
`pyproject.toml` (including the `train` extra for PPO/evaluation).

## Short training, resume, evaluation

For normal **evaluation with automatic public replays**, use the external runner
(from repository root). It preserves checkpoint fingerprints and does not train:

```sh
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py ppo \
  --checkpoint gaia-rl/runs/example-resumed --seeds 2 \
  --output gaia-rl/runs/new-evaluation
```

The approved origin is `agentmaco` / `shgaia.com`. SSH must already work; no credential,
tunnel or service-restart automation is performed. See [replay operations](tools/README.md)
for teacher comparisons, retries and retention. Commands below are the frozen low-level
training/reproducibility interfaces; they do **not** publish on their own.

```sh
.venv/bin/python -m gaia_rl.training --output runs/example --iterations 1
.venv/bin/python -m gaia_rl.training --resume runs/example --output runs/example-resumed
.venv/bin/python -m gaia_rl.evaluation --checkpoint runs/example-resumed \
  --seeds 2 --output runs/example-random.json
.venv/bin/python -m gaia_rl.evaluation --checkpoint runs/example-resumed \
  --opponent runs/example --seeds 2 --output runs/example-frozen.json
```

Output destinations must be new. Defaults deliberately use CPU, two Torch threads,
a local RLlib worker, a small training batch and one iteration. Training is NOT
started automatically. Longer runs should wait for stable rules and simulator gates.

The explicit end-to-end harness `python/tests/pilot_integration.py` verifies model
and optimizer restoration exactly, then runs held-out seat-rotated evaluation.
It is not part of automatic unit-test discovery, and refuses an existing output.

## Version and failure boundaries

- Native build fingerprint, Python source fingerprint and dependency versions must
  match a checkpoint. A rule change requires rebuild and a new run; transferring
  a policy across rule versions is not implemented.
- New CLI runs reject a stale native build. An already started run keeps its compiled
  rules when files are edited. This also means saved results describe that build,
  not necessarily the latest working tree.
- Resume restores model, optimizer and RNG state, then starts the next fresh episode.
  It does **not** resume an unfinished board or guarantee bit-identical uninterrupted training.
- Only load trusted local checkpoints: RLlib and RNG restoration use pickle formats.
- Unknown action fields/categories, candidate/board capacity overflow and engine search
  failures raise errors. No candidate pruning, automatic pass or fabricated victory.
- PPO's generic random-action precheck is disabled because it ignores padded-action
  masks. Dedicated AEC API, mask, legality and finite-gradient tests cover this interface.
- Current features use fixed axial-coordinate rows (256 maximum), explicit action
  parameters and federation membership bits. Candidate padding defaults to 2,048.
- Evaluation uses complete games and four seat rotations per seed, shares tied wins,
  and bootstraps whole seed groups. Two seeds are only a pipeline smoke test.

## Encoding update (2026-09-10)

Encoding v2 includes `ItarsGaiaTechChoice` (standard, advanced and Lost Fleet
advanced choices, covering, research and free-mine coordinates). The legacy
`ItarsGaiaTechTile` category remains supported. Adding a category changes the
normalized categorical features, so v1 checkpoints must not be resumed or used
for inference with v2. Existing fingerprint/encoding checks reject that mismatch;
checkpoint migration and training are not performed by this update.

Manual faction verification: [Korean checklist](../docs/faction-manual-test-checklist.md).

## Booster 12 and conversion candidates (2026-09-12)

Encoding v3 adds `RoundBoosterTerraformBuild`: one free terraforming step, not a
free mine. The engine still charges the normal mine cost, additional terraforming
and applicable range/Gaia-entry QIC. Ownership and once-per-round usage are checked.
The AI menu also includes every legal same-kind free-action count (1–30), retaining
single conversions. Nevlas PI can therefore choose a two-ore batch for three tokens;
this is availability, not a strategy bonus. Mixed-kind batches are not implemented.

Rebuild native rules before a new run. The added category changes normalized
features, and the expanded candidate menu changes both policy and random-opponent
choices. Do not resume v2 checkpoints or treat old evaluations as matched controls.
Archived teacher experiments and their weights remain unchanged; this repair does
not add booster-tier scoring, train/promote a model or rewrite historical replays.

## Inference boundary

`gaia_rl.evaluation.OfflinePolicy(checkpoint).choose(snapshot)` returns
`(decision_id, candidate_index)`. It does not mutate the engine. The caller must apply
that index against the exact same decision; stale-index checks remain authoritative.

## Optional strategy-teacher pilot

The [experiment-only comparison](experiments/README.md) evaluates a conditional
Xenos/Hadsch Hallas teacher, behavior-cloning warm-start and matched-budget PPO.
It does not change normal training defaults, game rewards or the server. Its outputs
are separate inference-only research artifacts, not resumable production checkpoints.

## AI observation replay

The [read-only replay viewer and exporter](tools/README.md) reproduce existing pilot
evaluations for board-level inspection, without additional training or live commands.
