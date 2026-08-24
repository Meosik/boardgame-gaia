# Test Specification: Gaia Lost Fleet Core Rebuild

**Status:** Direct-execution revision after Architect `ITERATE`; not an Autopilot consensus handoff  
**Companion PRD:** `.omx/plans/prd-gaia-lost-fleet-core.md`  
**Primary claim:** the complete four-player base + Lost Fleet game is rules-correct, deterministic, contract-safe, reconnect/restart-safe, and reproducible locally.

## 1. Verification principles

1. Test authoritative behavior at the pure transition boundary before transport or UI.
2. Derive expected results from rulebook-anchored fixtures, not from the implementation under test.
3. Assert rejected commands preserve canonical state and revision.
4. Exercise the same command/reducer/persistence path used in live play and recovery.
5. Prefer deterministic seeds, canonical snapshots, and minimal counterexamples; never hide required coverage behind ignored tests.
6. Keep a rule traceability matrix mapping every in-scope rule/component/faction to at least one positive and one boundary/negative test where meaningful.

## 2. Test levels and ownership

| Level | Primary owner | Purpose | Required on |
|---|---|---|---|
| Static/schema | Feature executor | Exhaustiveness, data validity, protocol drift | every change |
| Unit/fixture | Rules/data executor | One rule/effect/cost/phase with authoritative oracle | every rule change |
| Property/model | Test engineer + rules owner | Invariants over generated states/sequences | engine/model changes |
| Contract | Protocol/server/web owners | Generated schema and runtime envelope agreement | protocol changes |
| Integration | Server/persistence owner | Transaction, coordinator, projection, reconnect/restart | server changes |
| Browser component | Web owner | selection workflow, rendering, accessibility, errors | web changes |
| E2E | Independent test engineer | Four-client critical journeys and full game | milestone + release |
| Adversarial/UltraQA | Independent verifier | hostile sequencing, gaps, retries, corrupt recovery | M4/release |

The feature author may create tests, but milestone acceptance is performed by a verifier who did not implement the feature.

## 3. Test data and oracle strategy

### 3.1 Rule catalog

Maintain machine-readable records:

```text
rule_id, edition, rulebook, page, section, preconditions,
expected_effect, interactions, fixture_ids, implementation_status, verification_status
```

Catalog partitions:

- `BASE-SETUP`, `BASE-POWER`, `BASE-PHASE`, `BASE-ACTION`, `BASE-TECH`, `BASE-SCORE`, `BASE-FACTION`.
- `LF-SETUP`, `LF-MAP`, `LF-EXPLORE`, `LF-PLANET`, `LF-ACTION`, `LF-TECH`, `LF-ARTIFACT`, `LF-SCORE`, `LF-FACTION`.
- `SYS-ROOM`, `SYS-SESSION`, `SYS-PROTOCOL`, `SYS-PERSIST`, `SYS-RECOVERY`.

### 3.2 Golden fixtures

- Small state fixtures are hand-derived from a cited rule paragraph and reviewed by a second person/agent.
- Setup golden vectors record input seed/version and expected ordered choices, coordinates, orientations, and checksum.
- Full-game scripts record commands plus selected pending-choice answers; expected checkpoints are independently calculated at setup, each round boundary, and final score.
- Canonical JSON fixtures have stable key ordering and explicit schema version.
- A fixture generator may reduce boilerplate but cannot compute the expected value using the production function under test.

### 3.3 State builders

- Builders must create valid states by default.
- Invalid-state builders are restricted to invariant/recovery tests and labeled clearly.
- Late-game fixtures should be reachable through command sequences where practical; direct construction requires an invariant check first.

## 4. Static, build, and schema gates

Required commands will be finalized with the new workspace, but must cover:

- Rust format check, Clippy with warnings denied for production crates, and all workspace tests.
- Test registration is itself a gate: enumerate Cargo, Vitest, and Playwright tests; compare discovery with a checked-in test manifest; fail on nested/orphaned files or required ignored/skipped cases. This prevents recurrence of the legacy green run that executed only 14 tests while map, randomizer, rules, scoring, and property files were dormant.
- TypeScript typecheck, lint, unit tests, and production build.
- JSON/data schema validation and referential integrity.
- Protocol schema regeneration followed by clean diff check.
- Search gate that fails on in-scope `todo!`, `unimplemented!`, placeholder success, ignored required tests, generic faction stubs, or unknown-enum fallthrough.
- Dependency/license inventory for deliverable assets and packages.

## 5. Unit and rule-fixture strategy

### 5.1 Core model invariants

- Resource bounds, conversions, and insufficient-resource rejection.
- Power bowl charge/spend/burn/Gaia-area/Brainstone sequences.
- Piece supply conservation for mines, structures, satellites, Gaiaformers, shuttles, tokens, and artifacts.
- Unique occupancy and component uniqueness.
- Integer axial-hex distance, neighbor detection, board transforms, and federation connectivity.
- Logical equality is independent of process-memory layout. Canonical JSON sorts object keys, preserves array order, contains integers only, includes state/setup schema versions and gameplay revision, and excludes transport presence/caches.
- State checksum is SHA-256 over `gaia-state-v1\0 || canonical_json`; setup checksum uses `gaia-setup-v1\0`. Repeated serialization and replay produce identical bytes and hashes.
- Typed phase/pending-choice transitions; no action while the wrong player/phase/choice owner is active.

### 5.2 Base setup

- Four-player sector arrangement and valid orientations.
- Required counts and uniqueness for standard/advanced tech, federation, round scoring, final scoring, and seven boosters.
- Faction research starts, resources, structure supplies, special setup adjustments, and ordered initial mine placement.
- Same seed/version equals same complete setup; different representative seeds vary while remaining valid.
- Invalid component pool or impossible layout fails explicitly.
- Setup-policy fixtures assert official sequential faction-board/side choice and clockwise turn order. Legacy bidding tests are quarantined and cannot count as product verification.

### 5.3 Phase lifecycle

- Round starts at 1 and ends after round 6.
- Income resolves every uncovered source with correct power ordering/choice behavior.
- Gaia phase handles tokens/areas/Gaiaformers and faction overrides.
- Action turns rotate clockwise and skip passed players. The first release keeps clockwise order between rounds; pass-order reordering belongs only to a future versioned variable-turn-order option.
- Clean-up resets action spaces/tokens, processes boosters/round state, and never runs after final scoring.
- Automatic effect chains stop at typed player choices and resume exactly once.

### 5.4 Base actions

For each action: happy path, exact cost, insufficient cost, wrong phase/actor, unreachable target, occupied/invalid target, supply exhaustion, scoring hooks, faction modifiers, and atomic rejection.

- Build mine: range, Q.I.C. extension, terraform steps/cost, planet types, neighbor effects, Lost Planet interactions.
- Gaia project: transdim eligibility, Gaiaformer/power cost, later Gaia colonization and unavailable-former rejection.
- Upgrade: legal structure graph, neighbor discount, supply return/take, tech choice/pending choices, PI/academy effects.
- Federation: structure power, satellite connectivity/minimality where required, Q.I.C. station/special faction rules, token choice/flip/benefit.
- Research: knowledge cost, track capacity, level-five federation requirement, immediate rewards, tech-triggered progress.
- Shared power/Q.I.C. and special actions: exclusivity per round, exact costs, nested action choices.
- Pass/free/passive-power actions: booster scoring/swap, turn-order result, conversion limits, accept/decline charging and VP cost.

### 5.5 Technologies, scoring, and components

- Every standard and advanced tech tile: immediate, income, pass, ongoing, action effects and replacement/gating.
- Every round booster, round scoring tile, final scoring tile, research reward, and federation token.
- Tie handling for final scoring positions and resource-to-VP conversion.
- Scoring event applied once at the correct timing boundary.
- Research fixtures assert Base p. 22 values and timing: Terraforming ore at levels 1/4 and federation token at 5; Navigation Q.I.C. at 1/3 and immediate Lost Planet at 5; AI 1/1/2/2/4 Q.I.C.; Gaia Project level-2 power tokens, level-4 Gaiaformer, level-5 `4 VP + Gaia planets`; Economy level-5 immediate 3 ore/6 credits/charge 6 with level-4 income lost; Science level-5 immediate 9 knowledge; and both seeded Lost Fleet Economy 3/4 overlays.
- Base final-scoring fixtures assert 18/12/6/0, every tie split, research scoring, resource conversion, and single execution. Lost Fleet fixtures cover only most Asteroids, PI-to-Academy distance with missing-structure zero, and most Deep Space sectors including Lost Planet.

### 5.6 All 14 base factions

For Terrans, Lantids, Xenos, Gleens, Taklons, Ambas, Hadsch Hallas, Ivits, Geodens, Bal T'aks, Firaks, Bescods, Itars, and Nevlas, require:

- Initial state/setup fixture.
- Every ongoing cost/rule modification.
- PI/academy unlock and special action.
- Income/Gaia/pass/final-scoring behavior where applicable.
- At least one negative/boundary fixture proving the ability does not apply outside its conditions.
- Interaction fixtures with affected shared rules (power, federation, occupied planets, research, Gaiaforming, structure downgrade/upgrade, etc.).

Generic no-op success is forbidden. A not-yet-implemented ability must make its catalog row fail verification.

### 5.7 Lost Fleet setup and map

- Four-player setup uses all ten Space Sectors: white-numbered faces of 05/06/07, two random 01–04 sectors in the center, and the other eight around them.
- All ten four-player Interspace tiles are present as a distinct type; all eight Deep Space sectors are placed on persisted seeded random faces.
- Space Sector, Deep Space sector, Interspace tile, spaceship board, and single-hex spaceship tile stay distinct; reviewed fixtures verify every printed connection and coordinate.
- Lost Fleet tile/planet/blank placement and spaceship constraints are enforced; spaceship tiles at axial distance 3 are rejected and distance 4 is accepted, proving PD-004's minimum distance of four.
- Asteroid-count exception for the relevant final-scoring tile is enforced.
- Exploration boards/shuttles, overlay/scoring extensions, new tech/actions/federations/boosters/scoring are populated correctly.
- Visual coordinate fixtures compare machine geometry to reviewed reference diagrams without relying on legacy coordinates.

### 5.8 Lost Fleet rules

- Explore spaceship: range/Q.I.C. extension, lowest open shuttle position, standard and faction-adjusted deployment cost, power charge, one-shuttle-per-player-per-ship, no range origin from ship.
- Examine artifact: eligibility, six-power discard across areas, artifact availability and artifact effect timing.
- Protoplanet: three steps, six VP during play, no initial-placement VP.
- Asteroid: available Gaiaformer required, Gaiaformer permanently consumed, ordinary mine ore/credit cost waived, other scoring hooks preserved.
- Modified advanced-tech access and thresholds; replacement/federation/cover conditions retained.
- No federation satellite on a spaceship tile; ship federation tokens only available to explorers and consumed correctly.
- Ship power/Q.I.C./knowledge/credit actions: unlock, exact mixed costs, shared exclusivity/action marker reset.
- New special/free actions and all expansion artifacts, techs, boosters, round/final tiles.

### 5.9 Four Lost Fleet factions and base adjustments

- Tinkeroids, Moweyds, Space Giants, and Darkanians: dynamic terraforming relation, starting planet/structure, new board pieces, round abilities, PI/academy effects, exploration adjustments, and final scoring.
- Base-faction Lost Fleet adjustments (including shuttle costs/resources and documented Ivits/Bescods/Lantids/Xenos/Gleens/Taklons/Nevlas/Itars/Bal T'aks cases) each have direct fixtures.
- Pairwise tests cover rule-changing expansion factions against affected base components and spaceship abilities.

## 6. Property and model-based testing

### 6.1 Generated state/action properties

- For any valid state, any enumerated legal command is accepted and produces a valid state.
- Any rejected command preserves canonical state, revision, resource totals, and audit count.
- Accepted command increments revision once; repeating the same command ID never applies effects twice.
- Resource/piece counts stay within modeled bounds.
- No two incompatible structures/components occupy the same location.
- Current actor is connected, unpassed, and legal for the phase whenever a gameplay command is accepted.
- A game cannot advance beyond round 6 or score final results twice.

### 6.2 State-machine model

Use a small independent reference model for room lifecycle, revision/idempotency, pause/resume, and turn/pass ordering. Generate command sequences including join, attach, ready, action, pass, disconnect, reconnect, duplicate, stale, and restart. Compare implementation outputs to model states.

### 6.3 Map properties

- Board transforms preserve sector internal distances and do not overlap hexes.
- Same setup input is deterministic under test parallelism and platform changes.
- Valid generator outputs always satisfy all four-player base + Lost Fleet topology/count constraints.
- Shrunk failure includes seed, setup version, and minimal conflicting placements.

### 6.4 Differential/replay properties

- Applying committed commands live and replaying their canonical command/event log reach identical checksummed states at every revision.
- Loading any supported snapshot plus subsequent log reaches the same state as replay from origin.
- Projection reducer receiving snapshot+deltas equals fresh projection of canonical state.

## 7. Protocol contract tests

- `cargo run -p protocol-codegen -- --check` emits byte-identical checked-in JSON Schema, TypeScript declarations, and browser runtime validators from the Rust protocol manifest.
- Generated artifacts carry the same protocol version and SHA-256 schema hash; altering variant order, field policy, or integer bounds changes the hash deterministically.
- Golden JSON for every command/event/envelope variant round-trips Rust -> JSON -> browser validator and browser fixture -> server decoder.
- Internally tagged snake-case variants round-trip exactly. Unknown variant, missing field, extra forbidden field, wrong protocol/schema version, oversized envelope, malformed ID, invalid UTF-8/JSON, and values outside the JavaScript-safe signed integer range fail closed.
- Actor identity comes from attached session, not a trusted player ID in payload.
- Every rejection has stable code, human-safe message key/context, command ID, and unchanged revision.
- Snapshot and delta schemas contain no raw/hash session token or another seat's private data.
- Client supports gap detection, duplicate delta suppression, snapshot replacement, and protocol mismatch UI.

## 8. Server and persistence integration tests

Run against isolated temporary PostgreSQL databases/schemas with real migrations, server router, WebSocket stack, and controllable heartbeat clock; Compose startup waits for PostgreSQL health, not merely container creation.

### 8.1 Room/session

- Concurrent room creation does not collide.
- First four valid guests claim distinct seats; fifth is rejected.
- Duplicate nickname/invalid nickname/code cases are typed and non-mutating.
- Token reclaim restores only original seat; invalid token cannot attach.
- Newest duplicate attachment replaces prior socket consistently.

### 8.2 Command transaction

- Concurrent commands for one revision serialize; exactly one conflicting action commits.
- Database revision compare-and-swap rejects stale writes.
- PostgreSQL serialization/locking conflicts use a bounded repository retry and never apply an engine effect twice.
- Kill/fault before commit yields no state/event; fault after commit recovers committed state even if publish failed.
- Same `(room_id, command_id)` and canonical payload hash returns the original durable outcome without duplicate effects. Reusing the ID with a different payload hash is a typed protocol violation.
- A serialization retry reloads the committed aggregate and re-runs the pure transition; a stale candidate transition is never committed.
- Snapshot/projection published only after commit.

### 8.3 Pause/reconnect matrix

For each seat 1–4 and each lifecycle stage (`waiting`, setup placement, pending choice, normal action, after pass, round transition):

- Confirm heartbeat/grace threshold then pause.
- Reject commands from every seat while paused without revision change.
- Permit valid attach/resync traffic.
- Reconnect with original token and verify exact canonical/projection checksums.
- Resume only when every missing seat is attached.
- Disconnect two seats and reconnect in both orders.
- Retry the command whose ack was lost immediately before disconnect; ensure at-most-once effect.
- Assert attach/detach/heartbeat expiry changes `control_revision` but not gameplay revision or command audit.
- Enqueue command-before-disconnect and disconnect-before-command cases; queue order is the linearization point and only the former may commit.
- Replace one seat with a newer connection generation and prove late detach/message events from the old generation have no effect.

### 8.4 Restart recovery matrix

- Restart after every transaction fault boundary.
- Restart while playing, paused, and finished.
- Restore a pending multi-step choice and current actor exactly.
- Initially expose recovered active games as paused until all four seats reattach.
- Verify startup durably sets `recovery_hold`, gameplay remains blocked while it is set, and clearing it increments only `control_revision`.
- Detect corrupt checksum, missing migration, unsupported version, or truncated database and fail loudly without inventing state.

## 9. Browser/component testing

- Board maps reviewed coordinates to stable clickable targets at multiple zoom levels.
- Dashboard correctly renders resources, power bowls/Gaia area, structures, research, scores, boosters, shuttles, artifacts, and connection state.
- Every action family and pending-choice type has a component test for select, review cost, cancel, submit, ack, and typed rejection.
- Controls disabled by local affordance are still tested against server rejection when bypassed.
- Snapshot replacement clears stale local selections; revision deltas do not double-render effects.
- Reconnect overlay, pause reason, seat roster, protocol mismatch, and terminal score screen.
- Keyboard tab order, accessible labels/names, focus return after dialog, non-color-only planet/connection markers, and 200% zoom smoke.
- Nickname and server error text render escaped.

## 10. Browser E2E scenarios

Use Playwright with four isolated browser contexts and a real built client/server against a temporary PostgreSQL database. Network behavior is controlled per context.

### E2E-1 Room through setup

1. Host creates room; three guests join by code.
2. Fifth client is rejected.
3. Start seeded Lost Fleet setup.
4. Complete faction selection and all initial placements, including at least one expansion faction.
5. Assert all four clients converge on the same revision/checksum and board/component inventory.

### E2E-2 Golden full game (mandatory completion gate)

1. Start from a reviewed deterministic seed and four factions selected to exercise base and Lost Fleet mechanics.
2. Submit a reviewed legal command script through the browser, including every phase, pass order changes, power charging choices, federation, Gaia project, research/tech, spaceship exploration, artifact, asteroid, protoplanet, expansion action, and faction special effects.
3. Complete rounds 1–6.
4. Check canonical checkpoint summaries after each round.
5. Assert final tile scoring, leftover resource conversion, ranking/ties, final scores, finished state, and command rejection after finish.

The one game need not cover all 18 factions; per-faction rule fixtures and additional scenario games close that coverage. The golden game's expected checkpoints require independent expert/second-agent review.

### E2E-3 Disconnect and reconnect

- At setup, pending choice, normal action, and round transition, drop each player's network separately.
- Verify pause after grace period, blocked actions, visible roster, token reclaim, exact revision, and resume.
- Drop two clients, refresh one, reconnect in reverse order, and retry an unacknowledged command.

### E2E-4 Process restart

- Kill the server immediately after a committed mid-round command.
- Restart with the same database, reattach four browser contexts, compare pre/post state checksum, continue at least one round, and complete final scoring in the golden run variant.

### E2E-5 Hostile protocol/UI

- Send stale revision, duplicate ID with same payload, duplicate ID with different payload, out-of-turn action, action while paused, malformed/oversized envelope, forged seat ID, and unknown version.
- Assert typed error, no mutation, healthy connection or deliberate protocol close as specified, and convergence afterward.

### E2E-6 Clean-checkout smoke

- From a clean workspace with no secrets or prior database, execute documented start command, run four-client setup and one committed action, then execute documented golden E2E command.

## 11. Observability and diagnostic verification

Production monitoring is out of scope, but local diagnostics must make failures reproducible.

### Required structured fields

- `room_id` (non-secret internal ID), `revision`, `command_id`, `command_kind`, `seat_id`, `phase`, `round`, `result`, `error_code`, `duration_ms`, `protocol_version`.
- Connection logs include attach/detach reason and seat but never session token, nickname control characters, full canonical state, or database secrets.
- Recovery logs include schema version, recovered revision, replay/snapshot counts, and checksum result.

### Tests

- Capture logs for accepted, rejected, duplicated, paused, reconnect, and recovery paths and assert required fields.
- Secret-redaction test scans captured logs for raw tokens and known sensitive fixtures.
- Correlation test proves one command ID appears consistently across receive, commit, and publish records.
- Failure-injection test verifies transaction/recovery errors are surfaced with actionable code and revision.
- Local health/readiness endpoint reports process/database/migration readiness but exposes no room state.
- Optional local counters (commands accepted/rejected, active sockets, pause events, recovery duration) are tested if implemented; external monitoring integration is not required.

## 12. Performance and soak checks

- Benchmark representative early/mid/late valid actions; engine transition p95 <100 ms locally.
- Four loopback clients command-to-render p95 <300 ms under representative game traffic.
- Engine-only full-game script <10 seconds in test profile.
- Run repeated randomized legal-action simulations and 1,000 connect/disconnect/resync cycles; assert no revision drift, task leak trend, or unbounded retained command payloads.
- PostgreSQL lock/serialization-conflict behavior under simultaneous room activity is bounded and retried only at repository layer; a room command is never applied twice.

## 13. Security/adversarial matrix

- Guessing room code does not recover a seat; only valid session token does.
- Brute-force protection is conservative local throttling/connection caps, not a production auth system.
- Payload size limits and rate limits prevent trivial memory growth.
- XSS fixtures in nickname/error context render inert.
- SQL parameters are bound; database credentials and DSN are configuration, never client input.
- Cross-room token/command IDs cannot authorize or deduplicate in another room.
- Finished/paused/waiting room states reject inappropriate actions.
- Fuzz decoders and engine command validation; crashes/panics are failures.

## 14. Coverage matrix and milestone gates

### M0 gate

- Rule catalog/component inventory schema valid.
- Protocol generation deterministic and drift-tested.
- Canonical state/revision/checksum sample deterministic.
- PostgreSQL WAL recovery, atomicity/fault-boundary, and bounded serialization-retry spike proven.
- Discovered tests match the checked-in manifest; no dormant, orphaned, skipped, or ignored required tests exist.
- PD-001 through PD-004 fixtures pass: official sequential faction selection, clockwise ordering, persisted final-player sector rotations, and spaceship distance `>= 4`.
- Gameplay revision/control revision separation, recovery hold, connection generation replacement, and both disconnect/command queue orders are executable and green.
- Command-ID payload-hash deduplication tests cover same-payload retry and different-payload rejection.
- Asset/license ledger exists.

### M1 gate

- All base + Lost Fleet four-player setup rows verified.
- Setup golden/property tests green over a large deterministic seed corpus.
- Room/session/attach contract tests green.
- Four-browser setup E2E green.

### M2 gate

- Every base rule/component/faction row verified.
- Base six-round engine and browser golden scenario green.
- Persistence, pause, reconnect, and restart matrices green for base game.

### M3 gate

- Every Lost Fleet rule/component/faction/adjustment row verified.
- Expansion cross-product properties and Lost Fleet six-round golden E2E green.
- No faction/default stub or ignored required test exists.

### M4 / final gate

- Full test suite, static gates, contract drift, integration, four-browser golden full game, disconnect/reconnect, restart, hostile protocol, clean-checkout smoke, accessibility smoke, and performance guardrails green.
- Test failures reproduce with seed, protocol/setup/schema versions, command log, and last committed revision.
- Independent verifier signs the traceability matrix and acceptance criteria.

## 15. Three adversarial pre-mortem test campaigns

### Campaign A: hidden faction interaction defect

Generate late-game valid states varying faction capability, tech, booster, ship unlock, round tile, and target type. Use pairwise coverage plus handpicked high-risk triples. Mutation-test cost/scoring hooks so removing a faction modifier causes a fixture to fail.

### Campaign B: split-brain reconnect

Inject ack loss, duplicate publish, reordered delta, network partition, dual sockets for one seat, two simultaneous reconnects, and process restart. Assert database revision is unique, every client converges by checksum, and each command has at most one effect.

### Campaign C: nondeterministic recovery/setup

Run golden seeds and command logs repeatedly with randomized hash seeds, parallel test order, debug/release builds, and supported platforms/toolchain lock. Compare canonical bytes/checksums. Any unordered iteration or float-derived coordinate difference fails the gate.

## 16. Completion evidence package

The final verifier must attach:

- Rule traceability summary with zero unverified in-scope rows.
- Exact commands and fresh outputs for format/lint/type/schema/unit/property/contract/integration/build/E2E checks.
- Golden seed, setup checksum, per-round revisions/checksums, and final score oracle review.
- Disconnect/reconnect and restart matrix results.
- Protocol schema version/hash and clean generation diff.
- Database migration/recovery versions tested.
- Test manifest versus discovered Cargo/Vitest/Playwright cases proves all required tests are registered and executed.
- Known test exclusions (must not intersect scope) and remaining non-product risks.
- Asset license/replacement disposition.

## 17. Unresolved verification risks

1. Official errata/FAQ availability and exact expansion component interpretation require official-source research before catalog freeze.
2. Full-game expected scores need independent domain-expert calculation; snapshots generated only by the implementation are circular evidence.
3. Cross-browser automation availability may vary locally; at minimum Chromium is mandatory, with Firefox/WebKit smoke when browser binaries can be installed reproducibly.
4. Property test state generation can overproduce unreachable states; supplement with command-sequence generators and reachability assertions.
5. Asset visual comparison cannot establish redistribution rights; licensing is a separate release gate.
6. The four setup decisions are fixed for direct execution, but their image-derived board fixtures still require independent review before the M1 oracle can be accepted.
