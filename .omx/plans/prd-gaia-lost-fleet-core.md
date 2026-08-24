# Product Requirements Document: Gaia Lost Fleet Core Rebuild

**Status:** Direct-execution revision after Architect `ITERATE`; not an Autopilot consensus handoff  
**Date:** 2026-08-17  
**Planning scope:** complete four-player browser game; base Gaia Project plus Lost Fleet  
**Authoritative brief:** `.omx/specs/deep-interview-gaia-lost-fleet-core.md`

## 1. Product outcome

Build a complete, locally reproducible, server-authoritative browser implementation of Gaia Project for exactly four guest players, including the full Lost Fleet expansion. Four independent clients must be able to create or join a room, complete deterministic setup, play every legal branch required by the selected factions and components through all six rounds, reconnect after a disconnect, and receive correct final scores.

Completion means the entire acceptance contract passes. Milestones are sequencing devices, not permission to ship a rules-reduced game.

## 2. Source of truth and evidence policy

Use sources in this order:

1. Official base rulebook: `docs/EN_Gaia_rulebook_lo.pdf`.
2. Official Lost Fleet rulebook: `docs/GP_Exp_Rule_EN_V1_Web.pdf` (Version 1.0).
3. Explicit decisions in `.omx/specs/deep-interview-gaia-lost-fleet-core.md`.
4. Rule fixtures and data independently checked against items 1–3.
5. Legacy code and AIDLC documents as non-authoritative discovery material only.
Planning evidence memos: `.omx/context/gaia-stack-evidence-20260814.md` and `.omx/context/gaia-rules-evidence-20260814.md`. Frozen official PDF hashes are base `195f8db89bea4189e018ccf45d9ccf7fd5663d76c5c2cd0eec9335dad49f9185` and Lost Fleet `c8e6509e3106041df3c514b5eeb10c307c26c43599329fc04b3035dd46a5fc22`.

Every rule implementation must link to a stable rule catalog ID and a rulebook page/section. Ambiguities or rulebook/data conflicts enter a checked-in decision ledger before code is accepted. Legacy behavior is never evidence by itself.

### Evidence anchors

- The base rulebook defines game setup, the power cycle, six rounds, Income/Gaia/Action/Clean-up, ten action categories (including free and passive actions), game end/scoring, 14 factions, research, boosters, and tiles (base rulebook contents, pp. 1, 8–24).
- The Lost Fleet rulebook changes setup for four players, adds Deep Space sectors, spaceships, Exploration boards/shuttles, protoplanets and asteroids, new actions, altered base actions, new technologies/federation tokens/scoring, artifacts, and four factions (Lost Fleet rulebook, pp. 4–16).
- For four players, Lost Fleet uses all ten Space Sector tiles: white-numbered faces of 05/06/07, two random sectors from 01–04 in the center, and the other eight around them; it also uses ten four-player Interspace tiles and all eight Deep Space sectors on seeded random faces (Lost Fleet rulebook, p. 5).
- Exploring a spaceship is range-based, consumes an available shuttle, has faction-adjusted costs, and unlocks ship-specific content; spaceships are explored rather than colonized (Lost Fleet rulebook, p. 9).
- Protoplanets require three terraforming steps and award six VP when colonized during play; asteroids consume an available Gaiaformer permanently and waive the ordinary mine build cost (Lost Fleet rulebook, p. 10).
- Legacy evidence shows why this is a rebuild: all 18 faction abilities are registered as stubs (`gaia-engine/src/faction/registry.rs`, `gaia-engine/src/faction/ability.rs`); Deep Space placement is marked TODO (`gaia-engine/src/randomizer.rs`); replay ignores loaded events (`gaia-server/src/services/reconnect.rs`); and client action tags such as `BuildMine` differ from server tags such as `Build` (`gaia-frontend/src/types/game.ts`, `gaia-engine/src/rules/actions.rs`). Fresh `cargo test -p gaia-engine` executed only 14 tests; the nested map, randomizer, rules, scoring, and property files were dormant because they were not registered test roots (rules evidence memo section 6).

## 3. Scope

### 3.1 In scope

- Exactly four human guest players.
- Room creation, shareable room code, nickname entry, and room joining.
- Opaque, rotatable session token stored by each browser for identity recovery.
- Deterministic setup from a shareable seed, including all applicable base and Lost Fleet random choices and placement constraints.
- Faction selection and all initial placement/setup rules, including faction-specific setup adjustments.
- All 18 factions and every rule-changing ability.
- Complete base and Lost Fleet component/rule catalog used in four-player play.
- Server-authoritative action validation and atomic state transitions.
- Complete six-round phase lifecycle and final scoring/tiebreak handling.
- Real-time state synchronization to four browsers.
- Automatic game pause while any participant is disconnected; deterministic resume after all disconnected participants reconnect.
- Durable recovery after server process restart.
- Local structured diagnostics and reproducible local startup/test commands.
- Automated unit, property, contract, integration, recovery, and browser E2E verification.

### 3.2 Explicit non-goals

- AI players, MCTS, or LLM coaching.
- Spectators or a user-facing replay UI.
- Accounts, authentication beyond room-session possession, public lobby, or matchmaking.
- Player replacement.
- Production hosting, CI/CD, alerting, monitoring platform integration, or production operations automation.
- Compatibility with legacy HTTP, WebSocket, persisted-state, or client contracts.

### 3.3 Conservative defaults

- Browser target: current desktop Chrome, Firefox, and Safari; responsive tablet layout is desirable but not a completion gate.
- Accessibility: keyboard-reachable controls, semantic labels, non-color-only status, and readable zoom are required; WCAG certification is not.
- Visual fidelity: clear, unambiguous playability takes precedence over reproducing copyrighted board art.
- Localization: English only.

### 3.4 Approved product decisions and setup boundary

Direct execution adopts the official default rules whenever the legacy prototype introduced an unsupported product deviation.

- **PD-001 Faction selection — official sequential choice:** players choose one available faction-board side in player order (Base p. 19). Legacy random-pair bidding is excluded.
- **PD-002 Turn order — clockwise baseline:** the first release uses clockwise turn order. Optional variable turn order and auction-selected order are excluded until introduced by a separately versioned setup option.
- **PD-003 Board fairness — persisted player rotation:** the seed produces the raw layout. As allowed by Lost Fleet pp. 4–5, the final player may rotate Space Sector tiles through explicit setup commands before confirming the board. Deep Space sectors cannot be rotated by this step. The command sequence, final orientations, and checksum are persisted.
- **PD-004 Spaceship separation — minimum hex distance four:** “not within 3 spaces” (Lost Fleet pp. 4–5) excludes distances 1, 2, and 3. Any two single-hex spaceship tiles therefore require axial-hex distance `>= 4`. The legacy `>= 3` interpretation is rejected as an off-by-one error.

M1 setup fixtures must assert these four decisions and must not count quarantined legacy bidding behavior as coverage.

## 4. Users and critical journeys

### 4.1 Room host

1. Opens the app and creates a room.
2. Receives a short shareable room code and a local session token.
3. Shares the code with exactly three other players.
4. Sees connection/readiness status and starts only when four seats are occupied.

### 4.2 Joining guest

1. Enters a room code and nickname.
2. Receives a stable seat identity and session token.
3. Reuses the token automatically after reload or reconnect.
4. Cannot impersonate another occupied seat without that seat's token.

### 4.3 Four-player game

1. Players confirm or generate a seeded Lost Fleet setup.
2. Players complete official sequential faction choice and all ordered initial placements under PD-001 and PD-002.
3. The server advances through Income, Gaia, Action, Clean-up for rounds 1–6.
4. On an active turn, the owning client sees only commands that can be submitted, but the server independently validates every command.
5. All clients see the same public state and appropriate private/session metadata.
6. Illegal, stale, duplicate, or out-of-turn commands produce typed rejection without mutation.
7. Turn order follows the clockwise PD-002 baseline; pass order does not reorder the next round in the first release.
8. End-of-round effects and final scoring execute from the same rules engine used in tests.

### 4.4 Disconnect and restart

1. Loss of any participating socket marks that seat disconnected and pauses command acceptance.
2. All connected clients receive a pause reason and connection roster.
3. A valid session token reclaims only its original seat.
4. State revision and command history remain unchanged during pause.
5. When all players are connected, the game resumes without advancing time or phase.
6. After process restart, durable state reconstructs the exact committed revision and clients resynchronize.

## 5. Functional requirements

### FR-1 Room and session lifecycle

- Room codes are collision-checked and case-insensitive at entry.
- A room has four seats and explicit states: `waiting`, `setup`, `playing`, `paused`, `finished`, `abandoned` (the last is administrative/local cleanup only).
- Nicknames are length-limited, normalized for display safety, and unique within a room.
- Session tokens are high-entropy opaque values stored hashed at rest; they are never logged.
- REST may create/join/reclaim rooms; one versioned WebSocket channel carries live commands and projections after attachment.
- Duplicate live connections for one seat follow a defined policy: newest valid attachment replaces the older connection.

### FR-2 Deterministic setup

- A canonical UTF-8 seed is converted through a specified, versioned PRNG algorithm.
- Random draws and shuffles are stable across platforms and releases unless setup version changes.
- Setup output includes seed, setup schema version, ordered random decisions, board geometry, component choices, and checksum.
- Seed-derived choices are distinct from persisted player choices; faction, initial-structure, booster, and fairness-rotation decisions are never silently randomized.
- Map validation enforces all ten Space Sectors with white-numbered 05/06/07, two central 01–04 sectors, the other eight surrounding sectors, ten Interspace tiles, eight Deep Space sectors with persisted faces, spaceship distance `>= 4`, asteroid adjustments, and every official four-player constraint.
- The setup command cannot yield an invalid board; generator failure is explicit rather than silently repaired with non-deterministic randomness.

### FR-3 Authoritative rules engine

- The engine is a pure deterministic transition boundary: `(state, command) -> accepted(new_state, events) | rejected(error)`.
- Rejection leaves state byte-for-byte/canonically unchanged.
- All mutation occurs through the transition boundary, including setup, automatic phase work, faction abilities, scoring, recovery verification, and tests.
- Commands carry room ID, acting seat, client command ID, expected state revision, and protocol version.
- Accepted transitions increment revision exactly once and emit ordered domain events/audit facts in the same transaction as persistence.
- Automatic transitions are explicit engine commands/effects, not server-side field mutation.
- Legal-command discovery may assist the UI but never replaces validation.

### FR-4 Complete rule surface

The catalog must cover, at minimum:

- Base setup; faction choice; initial mines/structures; research starts; resources; boosters; round/final tiles.
- Power bowls, charging, spending, burning, Gaia area, Brainstone, and passive power charging decisions.
- Income, Gaia, Action, and Clean-up phases for six rounds.
- Build mine; Gaia project; structure upgrades; federations and satellites; research; shared power/Q.I.C. actions; special actions; pass; free actions; passive charging.
- Range, Q.I.C. range extension, terraforming wheel/cost, structure supply, neighbor discounts, tech acquisition/replacement, advanced-tech gates, federation token state, action-space contention, round scoring, income, and final scoring.
- All 14 base factions (Terrans, Lantids, Xenos, Gleens, Taklons, Ambas, Hadsch Hallas, Ivits, Geodens, Bal T'aks, Firaks, Bescods, Itars, Nevlas) and all four Lost Fleet factions (Tinkeroids, Moweyds, Space Giants, Darkanians), including setup exceptions, passive hooks, special actions, altered costs, resource behavior, and final scoring.
- Lost Fleet four-player map/setup, Exploration boards and shuttles, all spaceship boards, exploring, artifacts, protoplanets, asteroids, modified advanced-tech access, ship actions/tech/federations, new boosters/round/final scoring, and expansion faction adjustments.
- Research must be re-transcribed from Base p. 22 with typed timing: Terraforming grants 2 ore at levels 1/4 and its setup federation token at level 5; Navigation grants Q.I.C. at levels 1/3 and places/colonizes the Lost Planet at level 5; Artificial Intelligence grants 1/1/2/2/4 Q.I.C.; Gaia Project grants three power tokens at level 2, a Gaiaformer at level 4, and `4 VP + colonized Gaia planets` at level 5; Economy level 5 is immediate 3 ore, 6 credits, charge 6 with level-4 income lost; Science level 5 is immediate 9 knowledge.
- Final scoring implements base 18/12/6/0 ranks with official tie splitting, research and resource scoring (Base p. 18). Lost Fleet has exactly three final tiles: most colonized Asteroids; longest PI-to-one-Academy range distance, zero without either required structure; and most Deep Space sectors with a colonized planet, counting Lost Planet (Lost Fleet p. 15).
- Tie resolution and score conversion exactly as stated by the official rules.

The rule inventory is a traceability matrix with one of: `not_started`, `implemented`, `verified`, `blocked_by_interpretation`. Product completion requires every in-scope entry to be `verified`.

### FR-5 Protocol and projections

- Rust wire DTOs in `crates/protocol` are the protocol authority. A pinned repository generator emits checked-in JSON Schema, TypeScript declarations, and a browser runtime validator from the same tagged-variant manifest; generated files are never edited manually.
- Serde uses internally tagged snake-case unions, rejects unknown fields, and limits wire integers to the JavaScript-safe signed integer range. Every envelope carries `protocol_version` and `schema_hash`.
- The generation command writes to a temporary directory, byte-compares all outputs, and fails on a dirty diff. Golden fixtures cover every envelope variant in both directions.
- WebSocket envelopes distinguish attach, command, ack, rejection, snapshot, delta/event, pause/resume, and protocol error.
- The server redacts session tokens and any seat-private setup choice from other players.
- A joining/rejoining client receives a full projection at a committed revision, then ordered deltas; revision gaps trigger snapshot resync.
- Command IDs provide idempotency across retries and reconnects.
- Unknown protocol versions/tags fail closed with a structured error.

### FR-6 Pause and reconnection semantics

- The server uses transport heartbeats plus a short grace interval to avoid pausing on a single delayed packet; the exact interval is configurable for tests.
- Once a disconnect is confirmed, no gameplay command may commit while any required seat is disconnected.
- Reconnection attachment and read-only resync messages remain allowed while paused.
- The paused state and connection roster are visible to all clients; server restart initially restores a safe paused state until all seats reattach.
- No gameplay clock exists, so pause has no hidden time progression.
- Gameplay revision never changes for attach, detach, heartbeat expiry, or recovery hold. Presence projections use a separate monotonic `control_revision`.
- A per-room coordinator orders confirmed disconnects, attachments, and gameplay commands. A command ordered before disconnect confirmation may commit; once the disconnect is ordered, later gameplay commands are rejected until the effective pause clears.
- Every attachment receives a connection generation. A newer valid attachment replaces the prior generation, and late events from an older generation are ignored.

### FR-7 Persistence and recovery

- PostgreSQL is the durable store. Local Compose pins its version and gates application startup on a database health check.
- Each accepted command transaction atomically writes: expected prior revision, new revision, canonical command metadata, ordered event/audit payload, and canonical post-state snapshot (or a snapshot plus verified event position).
- Recovery reads the last committed state, validates schema/version/checksum, and replays through the same reducer when event replay is used.
- Persisted schemas are versioned; unsupported versions fail loudly with actionable diagnostics.
- A crash between validation and commit cannot expose partial state.
- Room state in memory is a cache/coordination aid, not the source of truth.
- Durable storage separates the revisioned game aggregate from room/session control data. Seat identity, hashed reconnect capability, lifecycle, `control_revision`, and `recovery_hold` are durable; socket generations and heartbeat timestamps are ephemeral.
- Server startup sets `recovery_hold` for every unfinished recovered room. Gameplay remains paused until all required seats attach and the coordinator durably clears the hold.
- Command idempotency uses unique `(room_id, command_id)` plus a canonical payload hash. Same ID and payload returns the original durable result; same ID with a different payload is a protocol violation.
- A transaction locks or compare-and-swaps the committed revision, re-runs the pure transition after any bounded serialization retry, stores state/events/outcome atomically, and publishes only the committed revision.

### FR-8 Browser client

- The client renders board geometry, planets, structures, Deep Space, spaceships, player boards/resources, research, scoring, boosters/tiles, phase/turn, connection/pause status, and action prompts.
- Multi-step actions are explicit workflows with cancellable selection before submission.
- Confirmations clearly show total cost, gained effects, and irreversible choice.
- Rejections retain user context and explain the failed precondition without inventing state.
- The browser never predicts committed state; optimistic affordances are allowed only if rolled back to server revision immediately.

### FR-9 Local operation

- One documented command starts the server, client, and durable store from a clean checkout.
- One documented command runs the complete verification suite; a narrower smoke command runs the golden four-player E2E.
- Test fixtures use deterministic seeds and isolated temporary databases.
- No secret is required for local play.

## 6. Non-functional requirements

### Correctness and consistency

- Identical seed + setup version produces identical setup checksum.
- Identical initial state + accepted command sequence produces identical final canonical state and event sequence.
- All four clients converge to the same committed revision.
- Monetary/resource counters, piece supplies, unique components, and map occupancy never violate modeled invariants.

### Reliability

- Commands are at-most-once in effect through command-ID deduplication.
- A process kill after any committed action recovers that exact revision.
- WebSocket reconnect and snapshot resync do not require a page restart.

### Performance

- Server validation/transition p95 under 100 ms on a normal developer laptop for representative late-game states, excluding disk startup.
- Committed command-to-rendered-update p95 under 300 ms on local loopback.
- A full deterministic engine-only game simulation completes within 10 seconds in test profile.
- Performance targets are guardrails, not production SLOs.

### Security and privacy

- Treat all browser input as hostile; enforce size limits, enum/schema validation, authorization by seat, and state revision.
- Tokens are random, hashed at rest, redacted from structured logs, and scoped to one room/seat.
- Render nicknames as text, never HTML.
- Database paths and room codes cannot influence filesystem paths.

### Maintainability

- Rule logic has no dependency on HTTP, WebSocket, database, wall clock, or browser packages.
- Data files are schema-validated at build/test time and referentially complete.
- No faction is implemented as a no-op placeholder; explicit unsupported paths fail tests.
- Public protocol changes require version and compatibility fixture updates.

## 7. RALPLAN-DR: decision record

### 7.1 Principles

1. **One transition truth:** live play, simulation, recovery, and tests use one deterministic engine boundary.
2. **Rules before screens:** traceability and executable invariants outrank UI speed or legacy reuse.
3. **Contracts are generated and versioned:** no hand-maintained duplicate action unions.
4. **Durability is transactional:** a visible accepted action and its recovery record are one commit.
5. **Local simplicity with replaceable boundaries:** choose the least operational surface that fulfills the explicit local, four-player contract without coupling rules to infrastructure.

### 7.2 Top decision drivers

1. Rule correctness across a large interaction surface, including 18 asymmetric factions and Lost Fleet modifications.
2. Deterministic testing and exact recovery from a committed revision.
3. Contract safety and maintainability across browser/server boundaries with low local operational burden.

### 7.3 Viable options

#### Option A — Rust engine/server + generated TypeScript contracts + PostgreSQL (recommended)

Shape: Cargo workspace with pure `game-domain`/`game-engine` crates; Axum/Tokio adapter; SQLx PostgreSQL repository; checked-in JSON Schema generated from Rust protocol types; generated TypeScript client types; React/Vite UI; Playwright E2E.

Pros:

- Strong algebraic types and exhaustive matching suit phase/action/faction rules and illegal-state prevention.
- Existing team/repository competence and selected pure utilities can be validated and migrated without accepting legacy architecture.
- Pure Rust simulations/property tests can exercise millions of transitions quickly and deterministically.
- Axum and SQLx provide a thin adapter; PostgreSQL WAL, transaction locking/version checks, and explicit serialization retries support crash recovery and concurrent command safety.
- Generated schema creates an explicit cross-language review boundary.

Cons:

- Cross-language contract generation adds tooling and must include runtime schema tests, not only compile-time types.
- Rust rule modeling has a higher initial implementation cost and can become monolithic without capability/effect boundaries.
- Browser and engine logic cannot share executable code directly; projections/UX helpers need generated contracts or a WASM decision later.

#### Option B — TypeScript monorepo + Fastify/WebSocket + React + PostgreSQL

Shape: shared pure engine package, Zod/TypeBox schemas as runtime and inferred types, Fastify server, React client, PostgreSQL repository, Playwright.

Pros:

- One language and package graph; protocol/runtime validation and client types can originate from the same schema.
- Faster UI-to-server iteration and simpler contributor onboarding.
- Strong ecosystem for browser contract tests and property testing (`fast-check`).

Cons:

- Structural typing and mutable object defaults make illegal state and accidental mutation easier unless discipline is exceptional.
- Numeric/resource invariants and exhaustive rule coverage receive less compiler assistance.
- Long-running domain complexity may concentrate in schema refinements and runtime checks.
- Node dependency/tooling churn expands the trusted supply chain.

#### Option C — Rust server with shared Rust/WASM projection helpers + React + PostgreSQL

Pros:

- Reuses the authoritative Rust model for local move previews and projection helpers.
- Differential native/WASM tests can expose hidden platform assumptions and reduce duplicated UI affordance logic.

Cons:

- Adds a second Rust target, JavaScript glue, initialization/version skew, browser caching, and another test matrix before core rules work.
- Browser execution remains non-authoritative and cannot receive hidden canonical state, so wire contracts and redacted projections remain necessary.
- The added target/interoperability cost does not advance the initial full-game or reconnect acceptance gates.

### 7.4 ADR-001: select Option A with a new architecture

**Decision:** Use a newly structured Rust engine and Axum server, a generated versioned JSON protocol consumed by a TypeScript/React client, and PostgreSQL persistence. The decision reuses technologies only where they fit the drivers; it does not preserve legacy module boundaries, schemas, database assumptions, or implementation.

**Why:** Rust best supports explicit phase/state machines, atomic transition semantics, deterministic property tests, and exhaustive asymmetric-rule composition. PostgreSQL is selected because WAL-backed commits, explicit transaction-conflict handling, and the existing SQLx/PostgreSQL baseline better evidence the required exact restart-recovery contract; this deliberately accepts a health-checked local database service over SQLite’s lower operational overhead. React remains a pragmatic view layer, while generated contracts remove the current hand-maintained schema split.

**Rejected for now:**

- Full TypeScript is viable but offers weaker compile-time protection for the domain's central risk: illegal state and partial mutation.
- SQLite was viable for a single-process local game and lower setup cost, but is rejected because crash recovery, concurrent command serialization, fault injection, and Compose reproducibility are hard acceptance gates already supported by the approved PostgreSQL topology.
- Event-sourcing-only recovery is rejected because replay evolution is risky during initial rule construction. Store an authoritative post-state for every committed revision (or frequent snapshots) plus the auditable command/events; continuously verify replay equivalence.
- Sharing the Rust engine with the browser via WASM is deferred. The server must remain authoritative, and WASM would add build/version complexity before the protocol stabilizes.

**Consequences/trade-offs:** Maintain generated TypeScript declarations plus golden Serde JSON checks; pin Rust, Node, PostgreSQL, and Playwright; health-gate startup; define canonical serialization and migrations early; keep the database repository and transport outside the engine; accept slightly higher initial modeling cost to reduce late correctness risk.

## 8. Proposed architecture and boundaries

```text
apps/web (React, generated protocol types)
          | HTTPS + versioned WebSocket envelopes
apps/server (Axum transport, session registry, room actor/coordinator)
          | commands / projections
crates/protocol (wire DTOs + JSON Schema generation)
          | maps explicitly; never aliases internal state blindly
crates/game-engine (pure transition, rule catalog, projections)
          |
crates/game-model (IDs, state-machine types, resources, board geometry)
          |
crates/game-data (validated official component data + provenance)

apps/server -> crates/persistence-postgres (transactions, revisions, recovery)
tests/rules-fixtures + tests/e2e (golden games, browser orchestration)
```

### Protocol generation contract

1. `crates/protocol` owns a restricted code-native tagged-variant manifest and the corresponding Rust Serde DTOs.
2. The repository-pinned generator derives JSON Schema, TypeScript declarations, and the browser runtime validator from that manifest in one invocation.
3. Encoding is UTF-8 JSON with snake-case discriminants, denied unknown fields, explicit JavaScript-safe integer bounds, and no untagged/catch-all variants.
4. `protocol_version` changes for compatibility policy changes; `schema_hash` is SHA-256 over the canonical generated schema bytes.
5. `cargo run -p protocol-codegen -- --check` regenerates into a temporary directory and requires a clean byte-for-byte diff.
6. Golden fixtures include every client and server envelope variant, boundary integers, unknown tags/fields, and Rust/browser rejection agreement.

If the M0 generator cannot produce reproducible round trips for representative nested pending choices, Option A must be revisited before M1 rather than adding hand-maintained browser types.

### Canonical state and checksum contract

- Logical game-state equality is defined by typed model equality; it is distinct from process-memory representation.
- Canonical persisted bytes are UTF-8 JSON with lexicographically ordered object keys, array order preserved, integers only, and no insignificant whitespace.
- Transient transport presence, socket generations, caches, and diagnostics are excluded. `state_schema_version`, `setup_version`, and gameplay `revision` are included.
- The state checksum is SHA-256 over `gaia-state-v1\0` followed by the canonical bytes. Setup checksum uses the separate domain prefix `gaia-setup-v1\0`.
- Rejected commands must preserve typed state equality, gameplay revision, audit length, canonical bytes, and checksum.

### Presence, pause, and recovery boundary

```text
Durable game aggregate: game state + gameplay revision + command/event audit
Durable room control: seats + token hashes + lifecycle + control revision + recovery hold
Ephemeral presence: socket generation + heartbeat lease
Effective pause: recovery_hold || any required seat lacks a live lease
```

Control events and gameplay commands enter one per-room coordinator queue. Queue order is the linearization point. Connection changes increment only `control_revision`; accepted gameplay increments only gameplay `revision`. On restart all unfinished rooms enter durable recovery hold, so absence of reconstructed sockets can never admit a gameplay command.

### Command transaction and delivery contract

1. Canonicalize the command payload and calculate its payload hash.
2. Look up `(room_id, command_id)`. Return the durable original result for the same hash; reject a different hash.
3. Verify effective pause, seat authorization, protocol version, and expected gameplay revision in coordinator order.
4. Lock/CAS the committed aggregate, run the pure engine from that committed state, and atomically store the new state, events, outcome, checksum, and incremented revision.
5. On a bounded serialization retry, reload the committed state and re-run validation and transition; never reuse a stale candidate.
6. Publish only after commit. Delivery may repeat, so clients apply snapshots/deltas idempotently by revision and request a snapshot on a gap.

### Domain modeling guidance

- Encode phase-specific allowed commands using explicit phase enums and validation dispatch, while retaining serializable aggregate state.
- Use typed IDs for seat, room, hex, component, command, revision, and rule catalog entries.
- Model faction behavior as declared capabilities/effects and narrowly scoped hooks (`validate`, `cost_adjustment`, `after_effect`, `income`, `scoring`) rather than 18 unrestricted service objects.
- Capability hooks return a closed typed effect algebra. Effects have deterministic priority/order, conflicting exclusive effects fail explicitly, every registered faction capability is exhaustive, and any escape hatch is isolated behind a reviewed rule-catalog entry rather than a generic callback.
- Use a deterministic effect queue for nested bonuses/free actions/choices. If resolution requires player input, transition to a typed `PendingChoice` state; never guess or block a server thread.
- Separate private canonical state from per-seat/public projection. Test redaction.
- Store rulebook provenance beside data entries and rule fixtures.

### Concurrency and transaction flow

1. A per-room coordinator serializes command handling.
2. It authenticates seat/token and checks connection/pause state.
3. It deduplicates `command_id` and checks `expected_revision`.
4. The pure engine validates and creates a candidate transition.
5. Repository transaction compares prior revision and atomically persists new canonical state plus command/event audit.
6. Only after commit does the coordinator publish revisioned projections.
7. On publish failure, clients recover via snapshot at the committed revision.

## 9. Data and rulebook reconciliation gate

Before rule implementation begins, create:

- A component inventory for base + Lost Fleet with stable IDs and rulebook provenance.
- A rule traceability matrix covering setup, phases, actions, components, factions, scoring, and expansion overrides.
- Executable fixtures for PD-001 through PD-004; quarantine legacy bidding/turn-order tests permanently unless a future versioned product decision reintroduces them.
- Re-transcribed research tracks with typed effect timing and seeded Lost Fleet Economy overlays; reject current `research_tracks.toml` as facts.
- Canonical final-scoring catalog using only the three official Lost Fleet conditions; reject current fabricated identifiers.
- Machine-readable map-sector geometry derived independently from official boards and verified by visual/table fixtures.
- A conflict ledger for contradictory translations, icon interpretation, component images, legacy TOML, and rulebook wording.
- A legal decision for every legacy image: licensed for redistribution, replaceable with newly created/code-native representation, or excluded.

No legacy TOML or image becomes authoritative merely because it is complete-looking.

## 10. Delivery milestones (full-contract preserving)

### M0 — Authority and skeleton gate

- Rule/component traceability inventory and conflict ledger.
- ADR-001 reviewed; clean workspace layout; canonical serialization/protocol generation spike.
- PD-001 through PD-004 fixtures encode official sequential selection, clockwise order, persisted last-player rotation, and spaceship distance `>= 4`.
- Game revision, durable room control, and ephemeral presence are separate types with coordinator-order tests.
- Command ID/payload-hash deduplication and disconnect/command linearization have executable transaction fixtures.
- Asset license audit and placeholder strategy.
- Verification: schema-generation reproducibility, sample transition determinism, PostgreSQL crash-commit and serialization-retry spike.

### M1 — Deterministic model and four-player setup

- Complete base + Lost Fleet component data required for setup.
- Seed/version PRNG, four-player board generation/validation, room/session lifecycle, approved faction-selection and turn-order policy, faction-specific starting state, initial placement, projections.
- Verification: golden setup vectors, map properties, four-browser setup E2E, illegal setup mutation checks.

### M2 — Base-game engine vertical completion

- Complete base phases/actions/power/research/technology/federation/scoring and all 14 base factions.
- Server transaction/persistence and reconnect pause integrated throughout.
- UI supports all base pending choices and action workflows.
- Verification: base rule traceability 100% verified, deterministic six-round base golden game, crash/reconnect matrices.

### M3 — Lost Fleet vertical completion

- Deep Space/spaceships/exploration/artifacts/new planets/modified actions/new components and all four expansion factions.
- UI representations and multi-step actions complete.
- Verification: Lost Fleet traceability 100% verified; targeted cross-product tests for expansion overrides; six-round expansion golden game.

### M4 — Full-system hardening

- Four-browser full-game E2E, stale/duplicate/illegal/adversarial protocol tests, every-seat disconnect and process restart recovery, browser/accessibility smoke, performance guardrails, clean-checkout local commands.
- All acceptance criteria and test-spec gates green; no ignored or placeholder required tests.

## 11. Pre-mortem

### Scenario 1: “Most rules work” but rare faction/expansion interactions invalidate late games

- Early warning: faction branches contain generic default hooks; traceability rows lack direct fixtures; manual bug reports cluster after round 4.
- Prevention: capability/effect architecture, rule IDs on tests, pairwise cross-product coverage, deterministic scripted late-game states, no stub/default success path.
- Containment: failing game command log reproduces engine-only; affected catalog entries return to `implemented` until reviewed.

### Scenario 2: WebSocket clients diverge or double-apply after reconnect

- Early warning: client stores mutate outside revisioned reducer; command retries lack IDs; snapshots and deltas use different DTOs.
- Prevention: revisioned envelopes, idempotent command ledger, commit-before-publish, gap detection/full resync, chaos tests for duplicate/drop/reorder/disconnect.
- Containment: client discards local derived state and replaces it with authoritative projection at a checksum-verified revision.

### Scenario 3: “Deterministic” setup or recovery changes after a release/toolchain update

- Early warning: use of library default shuffle, unordered map iteration in serialization, float geometry, or replay logic separate from live reducer.
- Prevention: versioned PRNG and canonical ordering, integer axial coordinates, golden vectors, same reducer for live/replay, schema checksums/migration fixtures.
- Containment: preserve setup/serialization version and route old games through pinned decoder; fail loudly rather than regenerate.

## 12. Staffing and agent roster guidance

Use a coordinated team because rule cataloging, engine work, transport/persistence, and browser/E2E are parallelizable but share contracts.

- **Architect (1, owner):** boundaries, ADR enforcement, canonical state/transition/protocol review; no feature implementation ownership.
- **Rules/data executors (2):** one base-game lane and one Lost Fleet/faction lane; own traceability rows, fixtures, and narrowly scoped engine modules.
- **Server/persistence executor (1):** room/session coordinator, PostgreSQL transactions, recovery, pause semantics, transport adapters.
- **Web executor/designer (1):** projections, generated protocol consumption, complete action/choice UI, accessibility.
- **Test engineer (1):** property model, golden game DSL, contract/chaos/E2E harness; independent from feature acceptance.
- **Verifier/code reviewer (1):** sequential milestone audits against rule matrix, mutation/negative tests, forbidden-stub search, completion evidence.
- **Asset/license research lane (bounded):** establish redistribution status and replacement plan before assets enter deliverables.

Shared-file rule: one owner for canonical protocol, rule catalog, and data schema at a time. Feature agents add through reviewed slices; they do not rewrite shared foundations concurrently.

## 13. Ultragoal and Team handoff

### Ultragoal decomposition

Create durable goals aligned to M0–M4, plus a final acceptance goal that depends on all milestones. Each goal must include the relevant rule-matrix rows, tests, changed-file ownership, and evidence command. Never mark the Autopilot goal complete at a vertical slice.

Recommended goal graph:

1. `authority-data-contracts` (M0) — prerequisite for all.
2. `deterministic-setup` and `room-session-foundation` (parallel after M0, converge at M1).
3. `base-engine`, `durability-reconnect`, and `base-web-workflows` (coordinated M2 lanes).
4. `lost-fleet-engine-data` and `lost-fleet-web-workflows` (M3, based on stable M2 boundaries).
5. `full-game-hardening` (M4) — depends on every prior goal.
6. `code-review-clean` then `ultraqa-clean` — required Autopilot exit gates.

### Team execution guidance

- Use Team mode for M1–M4 due to parallel lanes and explicit ownership.
- Begin each milestone with contract/rule-row assignment and finish with independent verifier acceptance.
- Run dependent work sequentially: data/schema -> engine rule -> server/projection -> browser workflow -> E2E.
- Reuse the same lane agents for follow-up fixes to preserve context.
- Escalate rule ambiguity to the rule decision ledger; do not encode a silent interpretation.

## 14. Exit criteria

The PRD is satisfied only when:

- All ten acceptance criteria in the clarified specification pass.
- Every in-scope rule traceability row is `verified` with unit/property/fixture evidence.
- Exactly four real browser contexts complete deterministic Lost Fleet setup and an entire six-round game to final scores.
- Illegal/stale/duplicate actions show no partial mutation.
- Each player disconnect case pauses; session reconnect restores exact revision; process restart recovers exact committed state.
- Protocol generation drift check, explicit test-discovery/registration check, Rust lint/type/test, client lint/type/test/build, integration suite, and Playwright E2E are green with no dormant, orphaned, or ignored required tests.
- Local startup and verification work from a clean checkout without secrets.
- Asset usage is legally resolved or replaced.
- Sequential Architect and Critic approvals, then code-review and UltraQA clean evidence, are recorded.

## 15. Unresolved risks requiring explicit closure

1. Asset licensing/redistribution status; this can block use of current scans but not engine implementation if code-native placeholders are used.
2. Official rule wording/icon ambiguities and possible published clarifications/errata; research must use official/upstream sources and record version/date.
3. Canonical full-game oracle: a scripted game requires expert validation of every expected transition and score, not self-confirmation by the engine under test.
4. Scope size of pairwise faction interaction testing; use risk-based pairwise generation plus exhaustive per-faction ability fixtures, not an impossible exhaustive game tree.
5. Persistence format evolution during construction; version fixtures from M0 and avoid accepting unrecoverable migrations.
6. Image-derived setup geometry and component facts still require independent verification even though PD-001 through PD-004 are now fixed for direct execution.
