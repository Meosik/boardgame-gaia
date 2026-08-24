# Gaia rebuild: technology-stack evidence memo

Date: 2026-08-14  
Scope: `lost-fleet-core`, full-game E2E, no AI/spectator-replay/auth-matchmaking/production-ops, and pause-until-reconnect. This memo compares implementation stacks; it does not approve implementation.

## Current local baseline

- The repository already separates a Rust `gaia-engine` from an Axum/Tokio/SQLx `gaia-server`, with a React/TypeScript/Vite client (`Cargo.toml`, `gaia-engine/Cargo.toml`, `gaia-server/Cargo.toml`, `gaia-frontend/package.json`).
- The current Compose file also starts Qdrant, Ollama, and a Python AI service. Those are outside the newly stated scope and should not shape the rebuild stack (`docker-compose.yml`).
- Prior analysis found the existing wire contracts and recovery implementation inconsistent. Therefore the useful local evidence is language/tool familiarity and domain data, not compatibility with current protocol code.

## Primary-source facts that constrain the decision

1. **Rust can own both the domain model and the JSON wire model.** Serde supports explicit tagged enum representations suitable for command/event messages, including `#[serde(tag = "...")]` and rename policies ([Serde enum representations](https://serde.rs/enum-representations.html), [Serde container attributes](https://serde.rs/container-attrs.html)). `ts-rs` generates TypeScript declarations from Rust structs/enums, understands common Serde attributes, and recommends generating bindings through tests ([ts-rs README](https://github.com/Aleph-Alpha/ts-rs#readme)). Its current README also declares MSRV 1.88, so the Rust toolchain must be pinned and checked rather than assumed.
2. **TypeScript is expressive but compile-time-only.** Discriminated unions plus `never` support exhaustive handling of network message variants ([TypeScript narrowing and exhaustiveness](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#exhaustiveness-checking)). However, TypeScript erases its types and emits plain JavaScript with no retained type information, so every WebSocket/HTTP/database boundary still needs runtime parsing and validation ([TypeScript erased types](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html#erased-types)).
3. **WebSocket reconnect is an application protocol concern in every stack.** RFC 6455 defines loss as failure/closure of the underlying connection and recommends delayed reconnect after abnormal closure; it does not restore application state ([RFC 6455, section 7.2.3](https://datatracker.ietf.org/doc/html/rfc6455#section-7.2.3)). Axum provides the server upgrade/socket primitive ([Axum `WebSocketUpgrade`](https://docs.rs/axum/latest/axum/extract/ws/struct.WebSocketUpgrade.html)); Node's maintained `ws` package likewise provides server/client primitives and heartbeat guidance ([ws README](https://github.com/websockets/ws#how-to-detect-and-close-broken-connections)). Neither substitutes for resume tokens, sequence numbers, idempotency, or replay logic.
4. **Durability is principally a PostgreSQL design choice, not a Rust-vs-TS choice.** PostgreSQL WAL is the mechanism that makes committed changes recoverable after a crash ([PostgreSQL WAL introduction](https://www.postgresql.org/docs/current/wal-intro.html)). Serializable transactions make successfully committed concurrent effects equivalent to some serial order, but applications must retry serialization failures ([PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html#XACT-SERIALIZABLE)). SQLx exposes commit/rollback transactions and rolls back an unfinished transaction on drop ([SQLx `Transaction`](https://docs.rs/sqlx/latest/sqlx/struct.Transaction.html)); equivalent transaction discipline is available from Node PostgreSQL clients.
5. **Wasm shares executable Rust logic but adds a second target and interop boundary.** `wasm-bindgen` can expose Rust types/functions as JavaScript bindings ([exported Rust types](https://wasm-bindgen.github.io/wasm-bindgen/reference/types/exported-rust-types.html)), but generated shims translate values on both sides ([exporting Rust to JS](https://wasm-bindgen.github.io/wasm-bindgen/contributing/design/exporting-rust.html)). Rust documents `wasm32-unknown-unknown` as Tier 2 with unsupported `std` facilities such as filesystem and native threads; Rust's own suite does not test this target in CI ([Rust wasm32 target support](https://doc.rust-lang.org/stable/rustc/platform-support/wasm32-unknown-unknown.html)). The `wasm-bindgen-test` browser harness is explicitly described as experimental ([wasm-bindgen test guide](https://wasm-bindgen.github.io/wasm-bindgen/wasm-bindgen-test/index.html)).
6. **The requested full-game E2E can be stack-neutral.** Playwright's primary repository documents Chromium/Firefox/WebKit execution, browser isolation, auto-waiting, and web-first assertions ([Playwright README](https://github.com/microsoft/playwright#readme)); its official Docker image includes browsers and system dependencies but requires version pinning to the test package ([Playwright Docker](https://playwright.dev/docs/docker)).
7. **Small local Compose is operationally sufficient.** Docker documents that dependency order alone does not imply readiness; `service_healthy` plus health checks is the intended readiness gate ([Docker Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)). For this scope the minimum topology is browser build/static server + authoritative app server + PostgreSQL, with an optional test container/profile.

## Comparative evaluation

Scores are planning judgments (5 = strongest fit for this stated scope), derived from the facts above and the local baseline—not external benchmark claims.

| Criterion | Rust authoritative engine/server + generated TS | TypeScript full-stack authoritative server | Rust shared engine via Wasm + server |
|---|---:|---:|---:|
| Deterministic domain modeling | **5** | 4 | **5** |
| WebSocket/session recovery | 4 | 4 | 4 |
| Durable persistence | 5 | 5 | 5 |
| Browser integration | 4 | **5** | 3 |
| Unit/property/integration/E2E tooling | **5** | **5** | 3 |
| Small local Docker operation | 4 | **5** | 3 |
| Maintenance risk (higher score = lower risk) | **4** | 4 | 2 |

### A. Rust authoritative engine/server + generated TypeScript contracts

**Strengths**

- Best fit for an authoritative, pure command reducer: algebraic enums, explicit integer types, and exhaustive `match` make invalid state transitions harder to express. This is helpful, but determinism still requires architecture rules: injected seeded RNG, no wall clock/I/O in the engine, canonical ordering, and no outcome dependence on randomized `HashMap` iteration (Rust documents that `HashMap` is randomly seeded: [std `HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html)).
- One Rust source of truth can generate TS command/event/state declarations. Contract drift becomes a CI failure if generated bindings are checked in and `cargo test` regenerates/diffs them.
- It reuses current Rust/PostgreSQL/React familiarity without reusing the broken protocol implementation.

**Costs/risks**

- Generated declarations are not runtime validators. The Rust server validates inbound JSON through Serde; the browser should minimally validate envelope/version/discriminant before trusting server messages.
- Cross-language debugging and code generation add a build step. Unsupported Serde attributes or wide integers need explicit review; `ts-rs` documents both warnings and `i64/u64` mapping configuration.
- Rust compile times and a smaller contributor pool may slow UI-adjacent iteration.

### B. TypeScript full-stack authoritative server

**Strengths**

- Fastest browser/server iteration and truly shared source types/packages; no code-generation boundary.
- Discriminated unions can model commands/events and enforce exhaustive handlers during type checking.
- Node has a stable built-in test runner ([Node `node:test`](https://nodejs.org/api/test.html)), and Playwright/Vitest integration is straightforward.

**Costs/risks**

- Shared compile-time types do not validate network or persisted data because types are erased. A runtime schema must be authoritative, versioned, and applied at every untrusted boundary; otherwise this option can recreate the current “types agree in editors but payloads fail at runtime” class of defect.
- JavaScript `number` requires discipline for counters/IDs and prohibits relying on floating arithmetic for rule outcomes. Determinism also needs seeded RNG and stable sorting; language unification does not provide those properties automatically.
- Replaces rather than leverages the current Rust domain skill/assets. The rewrite benefit must outweigh loss of Rust's stronger compile-time domain constraints.

### C. Wasm/shared Rust engine variant

Interpretation: the Rust engine runs natively on the authoritative server and a second build of the same crate runs in the browser for local previews/validation.

**Strengths**

- Maximizes executable rule sharing and enables instant client-side previews while the server remains authoritative.
- Native-vs-Wasm differential tests can reveal platform assumptions in a well-isolated pure engine.

**Costs/risks**

- Adds a Wasm target, generated JS glue, initialization/lifecycle concerns, browser caching/version skew, and another test matrix before the base game works.
- Browser execution does not eliminate wire contracts: authoritative commands/results, reconnect snapshots, and persistence still cross JSON/binary boundaries.
- Client-side validation cannot be trusted for authority and can disclose hidden state if the Wasm API is given the full server state.
- The official target/test limitations make it the highest-maintenance option for an MVP whose acceptance criterion is a complete server-authoritative game, not offline play.

## Bounded recommendation for `ralplan`

Choose **A: a native Rust authoritative engine/server with generated TypeScript contracts**, and explicitly **defer Wasm**. This recommendation is bounded to the current scope and team baseline; it should be revisited only if offline play, complex local move previews, or a reusable embedded engine becomes a confirmed requirement.

Planning guardrails:

1. Make `engine` a pure deterministic reducer: `apply(state, command, deterministic_context) -> events/error`; inject a versioned seed/PRNG; use integers for rule quantities; canonicalize every externally observed ordering.
2. Define one versioned Rust protocol crate containing tagged `ClientCommand`, `ServerEvent`, resume envelope, and public/private view DTOs. Generate checked-in TS declarations in CI; add golden JSON round-trip fixtures so generated static types and actual Serde encoding cannot diverge.
3. Treat a WebSocket as disposable transport. Give every game a monotonic `game_seq`, every command a unique `command_id`, and each no-auth player seat an opaque reconnect capability. On disconnect, durably mark the game paused; on reconnect, authenticate the seat capability and return a snapshot at sequence N plus later events (or one current snapshot) before resuming.
4. Commit accepted command identity, resulting event(s), new sequence/version, and snapshot/update in one PostgreSQL transaction. Serialize commands per game with an optimistic version check or row lock; retry only well-defined transaction conflicts. Recovery must be reconstructible from persisted data, never from in-memory sockets.
5. Test in layers: Rust unit + property/state-machine tests with persisted failing seeds; protocol golden fixtures; server/PostgreSQL integration tests; then Playwright full-game E2E covering two browser contexts, disconnect/pause, reconnect/resync, and completion/scoring. Rust's standard test support is built in ([Rust testing chapter](https://doc.rust-lang.org/book/ch11-00-testing.html)); `proptest` supports explicit/persisted RNG seeds ([proptest test runner](https://docs.rs/proptest/latest/proptest/test_runner/)).
6. Keep local Compose to PostgreSQL + one app image serving the built browser client (or one frontend dev service only in a dev profile). Remove Qdrant/Ollama/AI from the core topology. Pin Rust, Node, PostgreSQL, and Playwright image/tool versions; gate app startup on PostgreSQL health.

**Decision trade-off:** this chooses stronger authoritative-domain constraints and current repository skill reuse over the shortest single-language iteration loop. It rejects Wasm for phase 1 because it adds target/interoperability risk without advancing the stated full-game/reconnect acceptance criteria.
