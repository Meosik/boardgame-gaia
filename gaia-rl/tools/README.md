# AI observation replay

## Automatic evaluation → public replay (standard commands)

From the repository root:

```sh
# New PPO evaluation: default 2 maps × 4 seats, three random legal-action opponents.
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py ppo \
  --checkpoint gaia-rl/runs/deploy-learn-20260911.WOE0E7/fresh-ppo \
  --output gaia-rl/runs/my-new-evaluation

# Current teacher comparison: booster12 selection/use and purposeful same-kind batches.
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py purpose \
  --output gaia-rl/runs/my-new-teacher-comparison

# Hadsch research plans: identical current stage1 control versus two-income plans.
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py research \
  --specs /path/to/hadsch-specs.json --output gaia-rl/runs/my-new-research-comparison

# Xenos conditional resource preparation/continuations, not a fixed faction opening.
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py resources \
  --specs /path/to/xenos-specs.json --output gaia-rl/runs/my-new-resource-comparison

# Publish a completed report, or retry export/network failure. Does not retrain.
gaia-rl/.venv/bin/python gaia-rl/tools/simulate.py publish \
  --run gaia-rl/runs/my-new-evaluation
```

These are the standard simulation commands going forward. They automatically export,
validate and publish completed evaluation batches at `https://shgaia.com/?aiReplay=1`.
Training-internal episodes are excluded. The frozen `gaia_rl.evaluation` module and
historical experimental scripts remain low-level reproducibility interfaces; invoking
them directly does **not** auto-publish. Keeping this adapter outside the fingerprinted
policy package avoids invalidating existing checkpoints for a recording-only change.

`purpose` now selects `experiments/current_actions/evaluate.py`: all stages include
booster12 selection/build scoring and exact build-debit audits; stages1..4 include
the current purposeful batch adapter. The old `action_purpose.evaluate` remains a
frozen low-level runner, not the default. New manifests record the teacher variant
and source hashes; do not compare old/new stage numbers as identical policies.

`research` is the explicit Hadsch-only research-plan comparison. Its variants0/1
both use purpose stage1, with only variant1 adding two-income native planning.
It does not silently replace the preserved `purpose` control or any PPO model.
See `experiments/research_plans/README.md` for forecast limits and audit fields.

`resources` explicitly compares the unchanged current stage1 Xenos teacher with
`ResourcePlanTeacher`. It also plans at construction/conversion/ship/federation
roots; it does not alter Hadsch or silently promote a new default. Both variants
retain native/source manifests and automatically publish completed replays. See
`experiments/resource_plans/README.md` for the conditional goals and search limits.

PPO export reconstructs the exact evaluated games with the same policy, map and opponent
RNG; every player's final score and decision count must match. The current teacher
adapter reads existing complete records instead. Both validate terminal states, frame/log
boundaries and catalog metadata; no partial batch is selectable. Income recovery uses the
existing full-state equality checks. Nothing here updates weights or promotes a strategy.

Evaluation reports, exports and publication status stay under the chosen run directory.
`publication.json` explicitly reports `pending`, `failed` or `published`; failures return
nonzero and retain the report. Retry uses a completed export when available, otherwise
reconstructs the same evaluation, not a new sample. There is no background retry daemon.

Public deployment uses the already approved SSH alias `agentmaco`, project path
`/home/sohegi/projects/gaia`, and existing `gaia-gaia-server-1` container. It verifies the
public origin against the live/source catalog before changing anything; preserves remote
backups; publishes payloads before atomically switching catalogs; checks public bytes;
and updates the existing image tags with a replay-only release preserving the live
frontend/server. No services restart, rooms reset, credentials change or tunnels move.
An origin/permission/concurrent-deployment conflict fails rather than guessing another
target. `replay-publication/` retains receipts and the remote backup location.

### Retention approved 2026-09-12

- Newest **24 games** remain visible and are always protected.
- Other viewing `.json.gz` files expire **after 30 days from first publication**.
- Cleanup runs on publication, not on a daily scheduler. Recent hidden records remain
  in `archive-index.json`; expired records are removed from that catalog before deletion.
- `publication-times.json` preserves first-publication times/tombstones; republishing
  does not reset age or promote an old batch. Expired IDs cannot be resurrected by retry.
- Legacy records with unknown publication dates start their clock at migration. Their
  mtimes/seeds are not dates; nothing is immediately deleted based on a guess.
- Only catalog-owned viewing files inside the publication directory are pruned.
  Checkpoints, scores, raw evaluation/replay sources and unrelated files are untouched.

Open `http://localhost:8081/?aiReplay=1` after building `gaia-frontend` (or use the
Vite frontend URL with the same query). This is a read-only route: no game socket,
commands, training, or human-game import. It reuses the in-game boards with a bottom
selector, previous/next, playback speed, timeline, and clickable full decision log.
At 1× it advances one engine decision per second; browser background throttling can
slow playback. Records begin at initial placement and retain the final board.

## Reproduce the existing pilot

From the repository root, with the matching native build and experimental dependencies:

```sh
gaia-rl/.venv/bin/python gaia-rl/tools/export_replays.py \
  --run gaia-rl/runs/strategy-pilot-v2 --output /tmp/gaia-ai-replays-new
```

Output must not exist. The exporter checks engine/package/experiment fingerprints and
exact saved final scores, step counts, and focal action counts. It does not train.
Only a completed export has an `index.json`. The current verified 24-game catalog is
in `gaia-frontend/public/ai-replays/`; build copies it to the static frontend.

## Format and limits

Schema 1 separates catalog, metadata, gzip-compressed frames and logs. Metadata retains
seed, focal player, policy, versions, scores and reproduction evidence. Frame 0 is the
initial state. Frame N is the state AFTER decision N, with the selected action/actor
and legal action/federation candidate counts from BEFORE that decision. Coordinate
strings are decoded by the existing frontend wire decoder. Event offsets map log
entries to the earliest resulting frame.

The offline native environment currently discards detailed engine events. Logs here
are therefore explicitly `ReplayDecision` records derived from selected actions and
snapshot differences (`log_source: recorded_decisions_and_state_deltas`), NOT invented
engine reward events. Expand a log entry for raw action parameters and observed net
resource/VP changes. Those changes can include automatic income, phase transitions or
final scoring; they are not an attribution of reward solely to the displayed action.
Power/research/building changes remain visible in the recorded board snapshots.

Federation candidates reflect the engine's enumerated legal candidates, not exhaustive
search of every possible federation. Multiple decisions with available candidates can
be repeated opportunities for the same federation; do not count them as distinct
missed federations. No record of the policy's subjective reasoning is available.

Human-game persistence, uploads and resuming play from a replay are deferred. New
record sources can later reuse this display boundary without enabling live commands.

## Manual publication of historical exports

```sh
gaia-rl/.venv/bin/python gaia-rl/tools/export_replays.py \
  --run gaia-rl/runs/economy-learning-v1 \
  --output gaia-rl/runs/economy-learning-v1/browser-replays
gaia-rl/.venv/bin/python gaia-rl/tools/publish_replays.py \
  --source gaia-rl/runs/economy-learning-v1/browser-replays \
  --destination gaia-frontend/public/ai-replays
cd gaia-frontend && npm run build
```

The learning exporter checks all three saved source fingerprints and reproduces each
saved evaluation exactly; it does not retrain. Its filenames include the run name.
The publisher puts new batches first (preserving their internal policy/seed order),
keeps only the newest **24 published games** in `index.json`, and retains unexpired entries
in `archive-index.json`. This is publication order, not ordering by seed or score.
Older `.json.gz` URLs remain available until the retention policy above expires them. Repeating
a publication is idempotent, and conflicting IDs/files are rejected. Publish only a
completed trusted local export. The local lock prevents competing publishers; after
an interrupted process, inspect its status before manually removing a stale lock.

## Replay keyboard and automatic positioning

- Left/right: previous/next decision (pauses playback).
- Up/down: next/previous playback speed among0.5×,1×,2×,4×; clamps at either end.
- Space: play/pause; holding Space does not repeatedly toggle. At the end it stays paused.
- Focused form controls, buttons/links, editable fields and dialogs retain native keys;
  modifier/IME shortcuts are not intercepted. Click the board to use replay shortcuts.

Every selected decision (including log/timeline seek, reverse navigation and automatic
playback) positions its relevant board in view: research, action source, booster or map
location. Another player's booster action uses that player's own board, not the focal
player's shelf. Initial state has no action target. Positioning is immediate so4× playback
does not queue scroll animations; no zoom, game commands or changes to live play.

### Round navigation and consistent replay framing

The **라운드** selector sits immediately after **행동 보기**. Selecting1–6 seeks to
the earliest recorded state of that round, pauses playback and clears any reward
animation. It does not fabricate an income/scoring frame or restrict the seek to the
selected actor; the existing actor filter still applies to subsequent previous/next
and playback. Initial placement remains reachable through the original timeline.

Map-targeting actions center the same map container instead of stopping at whichever
hex is nearest or skipping a partly visible map. Research/power-board destinations
show the bottom rows when taller than the viewport, otherwise align to the board's
start; a newly reached level5 targets its highlighted marker so it is not cut off.
This is common across replays and independent of previous manual scroll position.
Existing compound-action destination priority (e.g. a lab upgrade's research result
or a ship action's source), map size, live-game navigation and other source targets
remain unchanged.

Replay menu names use `AT` (CurrentActionTeacher), `RP` (ResearchPlanTeacher), and
`T` (basic teacher), e.g. `AT · 제노스 75점 · 9/12 17:51`. The trailing date is the
first public registration time in Asia/Seoul, not the simulation start or teacher
version. The former seed-suffix number is omitted from the display only; replay
IDs, full seeds, policies, payloads, ordering and filters remain unchanged.
The optional `publication-times.json` sidecar must not block or reset playback.
Only automatic `eval-` entries have reliable registration timestamps; legacy
entries can contain a later retention-clock start and therefore remain undated.
Missing/invalid/unavailable timestamps are omitted, never inferred from seed names.

### Sidebar income projection (2026-09-13)
The sidebar's `예상 수입` is current recurring production from buildings, active
technology, research, faction, artifacts and the **held** booster. It no longer
uses historical `IncomeReceived` totals as a forecast. Received-income status/log
entries remain historical. Future spending, storage loss, future booster choice,
charging order and an extra income after round6 are not promised by this display.

Frontend production tables are generated from real native income transitions,
not a separate handwritten faction table. After changing income rules, regenerate
both files and run parity tests:

```sh
cargo run -p gaia-engine --example income_projection_data > gaia-frontend/src/data/income.json
cargo run -p gaia-engine --example income_projection_data -- --fixtures > gaia-frontend/src/tests/fixtures/incomeProjection.json
cargo test -p gaia-engine --example income_projection_data
(cd gaia-frontend && npm test -- --run src/tests/IncomeProjection.test.ts src/tests/OpponentPanels.test.tsx src/tests/ReplayIncome.test.tsx)
```

The fixture covers18factions, both economy sides, PI/Academy, booster, covered
technology and artifact combinations. The replay timeline never grants projected
resources or rewrites the saved game. No new replay schema/server field is needed.


## Local live AI spectator (2026-09-14)

The existing `/?aiReplay=1` game selector also lists **LIVE · AI 실시간 관전**
when `/ai-live/index.json` is present. Selecting a running game opens at the latest
received action, playing. Pause/seek keeps the current view fixed while new data
arrives. Play catches up sequentially at the existing speed; **LIVE · 최신 수**
clears the actor filter, jumps to the latest received action, and follows again.
Completed historical replay navigation/settlement stays unchanged. No game commands
are enabled. Failed reads retain the last validated state and show a connection
message; failed recordings never acquire invented final scores.

`watch_ai_game.py` observes one existing `four_factions` game without editing its
pinned training sources or running its teacher/model again. The producer flushes
its *before-state and chosen candidate* after executing each action. The observer
checks every before-state against a separate compatible native Environment and
executes only that recorded choice to obtain its exact after-state. Terminal
state/score files must agree before completion is published. A changed version,
rewritten/truncated trace, or mismatched state is rejected rather than guessed.

```sh
# From repository root; use the original seed/manifest for the game.
gaia-rl/.venv/bin/python -u gaia-rl/tools/watch_ai_game.py \
  --game /absolute/run/training/0 \
  --manifest /absolute/run/manifest.json \
  --seed THE_EXACT_RECORDED_SEED \
  --output gaia-frontend/public/ai-live
```

The output must be a **new directory**. Immutable compressed revisions precede
atomic index updates. The reader polls the small index every two seconds and only
fetches changed revisions, one request chain at a time. Old revisions remain intact.
`--once` is a diagnostic prefix export, not a completed game. Stopping an observer
stops delivery, not the AI; a saved running prefix is not proof that its producer
is still connected. The LIVE target is the latest **received** action.

**Standing preference (2026-09-14): live spectating is the default for future local
AI runs.** Start the read-only run observer alongside each new quartet run:

```sh
gaia-rl/.venv/bin/python -u gaia-rl/tools/watch_ai_run.py \
  --run /absolute/run/learning-output --pid EXISTING_TRAINING_PID \
  --output /new/local/public/ai-live
```

The run observer follows the newest recorded game within that run, not a second
simulation. Evaluation records focus the actual evaluated faction. Immutable
revisions and observed previous games remain available for paused viewers; very
short games may finish between polls. This is live viewing, not a guarantee of
capturing every intervening game. `--previous /finished/local/ai-live` retains a
completed earlier observer catalog when reconnecting. It rejects unfinished
catalog entries rather than inventing their completion.

Opening the viewer now prefers the live catalog over saved replays. While following,
it selects the next game automatically, including after the previous game ends.
Pause, rewind, actor filtering or manual game selection preserves the chosen view;
**LIVE · 최신 수** returns to the current game. Existing per-action playback speed
and historical replay controls are unchanged. No new layout or persistence store.

The current local observer is `gaia-ai-watch-v4-auto.service`, limited to 25% of one
CPU and 512 MiB with no swap. Local viewer: `http://localhost:5173/?aiReplay=1`.
Evidence/output are under
`runs/four-faction-pilot-20260913.8pFlH1Uv/viewer-v4-xenos177/auto-live/`.
To detach only the observer: `systemctl --user stop gaia-ai-watch-v4-auto.service`.
It does not launch/restart training or attach itself to an unrelated future run;
launch a new observer with that run's PID and a new output directory. Producer exit
or recorded failure does not acquire a fake completed score. No public deployment.

Tests: `test_watch_ai_game.py` uses a genuinely growing gzip trace and three native
actions; `AiReplayLive.test.tsx`, `LiveReplayTransport.test.ts`, `LiveReplay.test.ts`
cover pause/catch-up/LIVE, unchanged revisions, append-only validation and failure
preservation. A low-memory visual harness at `/previews/live-controls/` renders the
real viewer/data but hides its board viewport; this is not a full-board visual test.
The required `visual-verdict` skill is unavailable; any screenshots are manually
reviewed, not automated skill verdicts. Per-check results are in the run evidence.
