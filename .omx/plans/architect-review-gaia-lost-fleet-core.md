# Architect Review: Gaia Lost Fleet Core Rebuild

**Date:** 2026-08-14  
**Reviewed artifacts:** PRD, test specification, clarified specification, interview transcript, stack evidence, and rules evidence listed in the review assignment  
**Scope:** architecture and plan review only; no implementation review

## Executive assessment

The proposed direction is substantially sound: a pure authoritative transition boundary, transport and persistence adapters outside the rules engine, versioned cross-language contracts, per-seat projections, transactional durability, deterministic setup, and layered rule-to-browser verification are appropriate for this product. The plan also correctly rejects the legacy code and data as authorities and incorporates the most material evidence corrections.

It is not yet an execution-ready consensus plan. Four setup decisions are explicitly unresolved, while setup and the mandatory full-game oracle depend on them (`prd-gaia-lost-fleet-core.md:71-80`, `test-spec-gaia-lost-fleet-core.md:93,143,345,408`). In addition, presence/pause semantics, protocol generation, canonicalization, and command transaction linearization are described at an architectural-intent level but not precisely enough to prevent two incompatible implementations. These are plan defects rather than implementation details.

## What is architecturally strong

1. **Authority boundary:** `(state, command) -> accepted(new_state, events) | rejected(error)` is the correct center of gravity. Keeping HTTP, WebSocket, database, wall clock, and browser dependencies outside the engine is consistent with deterministic simulation and recovery.
2. **Rule authority and traceability:** official PDFs, frozen hashes, stable rule/component IDs, a conflict ledger, and independently reviewed fixtures directly address the dominant risk: incorrect transcription and invented legacy rules.
3. **Durability model:** commit-before-publish, revision compare-and-swap, durable command metadata, post-state snapshots, and replay-equivalence checks form a credible recovery design (`prd:182-189,351-359`). PostgreSQL is a defensible choice despite higher local operating cost.
4. **Protocol posture:** explicit wire DTOs, per-seat projections, version rejection, idempotent command IDs, gap detection, and snapshot resynchronization correctly avoid trusting the browser.
5. **Testing shape:** the test specification is unusually strong. It prevents circular oracles, registers otherwise dormant tests, covers negative and property cases, uses real PostgreSQL and WebSockets, includes every-seat reconnect/restart matrices, and makes the four-browser six-round game a mandatory gate.
6. **Milestone integrity:** M0-M4 sequence preserves the final contract rather than redefining partial vertical slices as completion.

## Blocking findings

### A1 — Product decisions PD-001 through PD-004 are unresolved

The PRD correctly identifies these as blockers, but a Ralplan artifact intended for execution handoff cannot both require their approval and leave them undecided. They determine the setup state machine, legal command vocabulary, setup checksum, map validator, and E2E oracle.

Required revision:

- **PD-001:** select official sequential faction board/side choice unless the user explicitly authorizes a deviation. Legacy bidding has no authority under the declared source precedence.
- **PD-002:** select the official default clockwise order for the first-round baseline. If optional variable turn order is in scope, model it as an explicit seeded/setup option and state how passing determines subsequent rounds; do not mix it with auction ordering.
- **PD-003:** prefer the official last-player rotation as persisted setup commands. This preserves player agency and determinism without inventing an unverified fairness solver. The resulting commands, orientations, and checksum must be durable.
- **PD-004:** obtain upstream clarification or independently reviewed official examples. If no clarification exists, record one explicit interpretation in the decision ledger, its grammatical rationale, and golden fixtures distinguishing distance 3 from 4. Silent inheritance of legacy `>= 3` is forbidden.

**Execution impact:** M1 and any setup/full-game implementation are blocked. M0 evidence gathering and disposable spikes could run, but Autopilot should not hand off the complete plan as approved while these decisions are open.

### A2 — Canonical game state and ephemeral presence/pause state are conflated

The room lifecycle includes `paused` (`prd:123`), the pause must not change state revision or command history (`test-spec:230`), connection roster is visible (`prd:178-179`), and restart restores a safe paused condition (`test-spec:240-242`). Those requirements are compatible only if the plan distinguishes at least:

- the durable, revisioned game aggregate;
- durable room/session identity and token records;
- ephemeral connection leases/generations;
- an effective command-admission gate such as `recovery_hold || any_required_seat_disconnected`.

Required revision: define whether pause is a derived transport/coordinator condition or a separately versioned room-control record. Specify its persistence, ordering relative to in-flight commands, heartbeat grace expiration, duplicate attachment replacement, and restart semantics. Gameplay revision must not increment merely because a socket dropped, while every client must still receive an ordered presence/pause projection.

### A3 — The protocol source and runtime validation path are underspecified

The plan names Rust DTOs, generated JSON Schema, generated TypeScript declarations, and a browser validator (`prd:260-262,330`; `test-spec:196-197`) without choosing the exact authority/generation chain. Type declarations alone provide no runtime validation, and independently generated schema/types can drift semantically.

Required revision: select one checked-in protocol authority and specify:

1. generator/tool and pinned version;
2. how Rust Serde behavior, JSON Schema, TypeScript types, and browser runtime validators are derived;
3. tagged-union representation, integer bounds, unknown-field policy, and schema hash/version policy;
4. generation order and clean-diff command;
5. golden fixtures for every envelope variant in both directions.

This must be an M0 exit artifact, not left to feature executors.

### A4 — Command linearization and idempotency need an implementable transaction contract

The per-room coordinator plus database CAS is directionally correct (`prd:351-359`), but bounded PostgreSQL retry, duplicate connections, ack loss, and process restart leave several possible semantics.

Required revision: specify a transaction contract such as:

- unique key `(room_id, command_id)` plus canonical payload hash;
- same ID/same payload returns the durable original outcome; same ID/different payload is a typed protocol violation;
- lock/CAS the expected revision, run the pure transition from the locked committed state, and write state/event/outcome atomically;
- on serialization retry, reload and re-evaluate rather than reuse a candidate based on stale state;
- publish only the committed revision; projection delivery is at-least-once and client application is revision-idempotent;
- define the linearization order between disconnect confirmation and a command already being validated/committed.

Without this, two implementations can both claim compliance while disagreeing on whether an action commits at the pause boundary.

### A5 — “Canonical bytes/checksum” is not yet a defined invariant

The PRD requires byte-for-byte/canonical non-mutation and stable checksums (`prd:131,141,211`), while the test plan relies on canonical JSON. Rust in-memory bytes are not a stable semantic artifact, and ordinary JSON serialization does not by itself define numeric representation, map order, excluded fields, or hash domain.

Required revision: define logical state equality separately from canonical persisted/wire encoding. Pin the canonicalization algorithm, field ordering, integer-only numeric domain, schema/setup version inclusion, excluded transient fields, and checksum algorithm/domain separator. Rejection tests should compare semantic state plus canonical encoding and revision, not process-memory bytes.

## Significant non-blocking revisions

1. **Rule extension mechanism:** `validate`, `cost_adjustment`, `after_effect`, `income`, and `scoring` hooks are a good sketch, but unrestricted hooks can recreate the current stubbed architecture. M0 should define a closed typed effect algebra, deterministic ordering, conflict rules, exhaustive capability registration, and a narrowly reviewed escape hatch.
2. **ADR alternative quality:** Option B is credible, but Kotlin/Ktor is a weak third alternative because no repository evidence supports it. Replace or supplement it with Rust server + shared Rust/WASM rule/projection helpers, which is the strongest alternative for eliminating client affordance drift. Keep WASM deferred only after comparing build/version and browser-debug cost.
3. **ADR falsifiability:** add an M0 pivot criterion. For example, if schema/runtime-validator generation cannot round-trip all protocol variants reproducibly, or the Rust modeling spike cannot express representative nested pending choices without catch-all hooks, revisit Option A before M1.
4. **Data gate sequencing:** distinguish engine-safe code-native representations from copyrighted art. Licensing blocks redistribution, not abstract rule modeling; authoritative icon/layout transcription and independent review do block affected rule verification.
5. **Full-game oracle staffing:** “second-agent review” is necessary but may not be sufficient for board-game rules expertise. State the reviewer qualification/evidence method and require the oracle to be derived without executing production scoring code.

## Steelman antithesis

The strongest case against Option A is a strict TypeScript monorepo with a schema-first runtime contract, immutable reducer, discriminated unions, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, exhaustive matching, property testing, PostgreSQL, and Playwright.

The product's largest correctness risk is not memory unsafety; it is mistranscribed rules, incorrectly ordered effects, and mismatched browser workflows. A single language can shorten the feedback loop across engine, protocol, projection, UI, scenario DSL, and E2E while eliminating the Rust-to-schema-to-TypeScript generation boundary. Runtime validation originates from the same schema consumed by client and server. Faster iteration matters because eighteen asymmetric factions and Lost Fleet create a very large rule/UI surface. Rust's type system prevents some illegal representations but cannot prove official rule fidelity, and it may encourage an overly elaborate domain model before rule interactions are understood.

This antithesis is credible. Option A remains reasonable only if the M0 spike proves that Rust's exhaustive domain model and property-test throughput outweigh cross-language friction and that the protocol generation chain is deterministic and runtime-safe.

## Tradeoff tension and synthesis

**Tension:** maximize compile-time prevention of illegal domain states (Rust) versus minimize cross-boundary duplication and maximize iteration speed (full TypeScript). Both serve correctness in different ways; neither dominates solely from the current evidence.

**Synthesis:** retain a server-authoritative Rust reducer and PostgreSQL transaction boundary, but make the wire contract a deliberately narrow, generated, runtime-validated projection/command surface rather than exposing domain types. Keep all rule calculations and optimistic state transitions off the browser. Use M0 representative spikes for nested pending choices, protocol round trips, fault recovery, and a minimal four-context workflow, with explicit pivot thresholds. Defer WASM until a measured UI need appears.

## Principle compliance

| Principle | Assessment |
|---|---|
| One transition truth | Strong direction; recovery and automatic effects share the reducer. Clarify whether presence/pause is outside game revision. |
| Rules before screens | Strong; rule catalog and independent fixtures are appropriate. |
| Generated/versioned contracts | Incomplete until the exact authority and runtime validator pipeline is selected. |
| Transactional durability | Strong direction; linearization/idempotency contract must be made precise. |
| Local simplicity/replaceable boundaries | Mostly satisfied; PostgreSQL cost is consciously accepted, adapters are separated. |

## Required iteration checklist

The next plan revision must:

1. close PD-001 through PD-004 with explicit decisions and evidence;
2. separate game revision from presence/pause/recovery-hold semantics;
3. freeze the protocol generation/runtime validation pipeline;
4. freeze transaction, retry, deduplication, and disconnect linearization semantics;
5. define canonical state encoding and checksums;
6. strengthen the rule effect algebra and ADR alternatives/pivot criteria;
7. update PRD requirements, milestones, and test cases so the decisions are asserted rather than listed as unresolved.

After those changes, the overall architecture is likely approvable without changing the recommended stack.

## Verdict

**ITERATE**

The plan has a strong architecture and verification foundation, but unresolved setup decisions and underspecified cross-boundary consistency contracts prevent safe full execution handoff. These are bounded, repairable plan issues; they do not justify `BLOCK`, but they must be resolved before Architect approval and before sequential Critic review.
