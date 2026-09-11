# AI observation replay

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

## Publish new learning games without deleting history

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
keeps only the newest **24 published games** in `index.json`, and retains every entry
in `archive-index.json`. This is publication order, not ordering by seed or score.
Older `.json.gz` files remain unchanged and accessible at their existing URLs; only
the selector hides them. No age-based or disk-space deletion is performed. Repeating
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
