# Public Branch Coverage Matrix

## Scope and interpretation

A single four-player match cannot reach mutually exclusive outcomes (for example, an accepted command and the same command's rejection). The verification therefore combines one real six-round four-player playthrough with isolated REST, WebSocket, React control, and engine rule scenarios.

“Covered” below means an externally observable branch has an executable test and the test was run. It does **not** mean compiler-level 100% branch coverage: this repository does not include `cargo-llvm-cov`, a Vitest coverage provider, Playwright, or Cypress, and no new dependency was added merely to manufacture a percentage.

## End-to-end game lifecycle

| Branch | Success evidence | Failure/alternate evidence |
|---|---|---|
| Sequential setup | `sequential_setup_reaches_action_phase_after_structures_boosters_and_income` | wrong setup-phase action and stale revision tests |
| Bidding setup | `all_four_players_ready_starts_bidding` | engine bidding invalid bid/pass/reward tests |
| Full four-player game | `a_full_four_player_game_reaches_game_ended_with_real_scores` reaches round 6, final scoring, and `game_ended` | `game_action_in_lobby_is_rejected_without_advancing_revision` |
| Disconnect/reconnect | `disconnect_pauses_and_reconnect_resumes_without_revision_change` | paused command, invalid token, and cross-room token rejection |
| Restart recovery | `restart_recovery_reconstructs_committed_revision` | missing room and invalid session branches |
| Idempotency | `duplicate_command_id_replays_recorded_result` | `rejected_command_id_replays_original_rejection` preserves the original rejection code/message |
| Optimistic concurrency | current revision commands throughout the suite | `revision_conflict_rejects_stale_expected_revision` |

## REST routes

| Route | Success branches | Failure branches |
|---|---|---|
| `GET /health` | healthy 200 | process/network failure is infrastructure, not an application response branch |
| `POST /api/rooms` | sequential and bidding creation | malformed setup mode; blank nickname |
| `GET /api/rooms/{code}` | lobby state | room not found |
| `POST /api/rooms/{code}/join` | new player; same-player reconnect | missing room; blank nickname; invalid token; cross-room token; full room; already started |
| `GET /api/rooms/{code}/preview_board` | map, six round tiles, two final tiles, spaceship boards | room not found |
| `POST /api/rooms/{code}/regenerate` | host regeneration; setup mode preserved | invalid token; cross-room token; non-host; already started |

Primary executable evidence: `gaia-server/tests/integration/room_lifecycle.rs`.

## WebSocket protocol

| Area | Accepted branch | Rejected branches |
|---|---|---|
| First frame | valid `join_room` | binary, malformed JSON, command-before-join, URL/payload room mismatch, missing room, blank nickname |
| Session boundary | valid same-room reconnect | invalid token, cross-room token, token player absent from roster |
| Join capacity/state | joins through four seats; started-player reconnect | fifth player; tokenless join after start |
| Post-join frame | revisioned command accepted | repeated join, payload room mismatch, malformed/unknown frame |
| Compatibility | current protocol version/schema | unsupported version; schema mismatch |
| Concurrency | current revision | stale revision |
| Command replay | accepted replay returns original revision | rejected replay returns original code/message/revision |

Primary executable evidence: `gaia-server/tests/integration/websocket_messaging.rs` and `revision_and_recovery_flow.rs`.

## UI controls

React Testing Library dispatches real click/input events against rendered components for:

- create room: blank/valid nickname, seed trimming, sequential/bidding toggle, regenerate, back;
- join room: blank code, blank nickname, uppercase normalization, loading state, valid submit, back;
- waiting room: ready toggle, host/non-host regenerate visibility, board overlay open/close, command rejection revision resync;
- board overlay: close button, backdrop close, interior click retention;
- map: valid target click and invalid target suppression;
- action panel: success payload, visibility, and disabled/failure state for round-booster range exploration, Twilight range Gaia formation, Gleens build/Gaia/explore, and Space Giants build;
- player/research/faction boards, scoring, boosters, opponents, log, bidding, and game-over rendering.

Primary executable evidence: `gaia-frontend/src/tests/UiControlBranches.test.tsx`, `ActionPanel.test.tsx`, and the remaining component test files. This is click-level DOM coverage, not pixel/browser-driver coverage.

## Engine actions and rule failures

Every currently implemented `GameAction` variant is referenced by executable engine tests (47 variants total):

- base actions: build, upgrade, research, federation, power action, pass, charging, Gaia formation, academy/free actions;
- faction actions: Ambas, Firaks, Bescods, Ivits, Tinkeroids, Moweyds, Taklons, Terrans, Itars, Gleens, Space Giants;
- tile/booster actions: tech-tile specials and all implemented round-booster special modes;
- Lost Fleet: explore/examine; Credit/Twilight/Rebellion/T F Mars/Eclipse action spaces and their range modes.

Failure families exercised across these tests include wrong phase/turn/faction, missing prerequisite building/tile/ship, unavailable or reused shared slot, insufficient resources, invalid/missing target, occupied/out-of-range target, exhausted supply, duplicate ownership, maxed track, invalid follow-up choice, and once-per-round/game reuse. The detailed executable cases live under `gaia-engine/tests/unit`, `gaia-engine/tests/property`, and the top-level engine integration tests.

## Explicit boundaries / known model limits

- Artifacts 8 and 12 are coordinate-less virtual Protoplanet/Asteroid mines. They trigger current Build-a-Mine and new-planet-type scoring, count toward mine/building/planet-type/Asteroid objectives, and deliberately count toward no sector, federation, physical-piece supply, or income row.
- Browser pixel automation is not installed. Visual asset correctness is guarded by component/image mapping tests and production build, while the prior real multi-tab manual session is documented in `README.md`.
- Infrastructure outages (database unavailable, port unavailable, process killed) are operational failures rather than deterministic application response branches in this matrix.

## Verification command

```bash
set -a; source gaia-server/.env; set +a
cargo test --workspace
cargo test -p gaia-server --test integration_tests -- --ignored --test-threads=1
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all -- --check
(cd gaia-frontend && npm test -- --reporter=dot && npm run build)
git diff --check
```
