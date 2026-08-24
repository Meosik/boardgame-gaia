# Gaia

Server-authoritative, four-player browser implementation of **Gaia Project** with the **Lost Fleet** expansion.

> **Current status:** architecture foundation and legacy cleanup are in progress. The repository builds and its available tests pass. Room control revision, command idempotency, atomic PostgreSQL command storage, and restart/reconnect recovery are implemented over the gaia-protocol envelope. The round loop now actually completes end to end (Gaia phase, Income phase, and the round→round phase transition were previously unwired — a round-2 game was stuck forever) and round-tile VP is now applied instead of only broadcast; the complete official setup, full six-round rules engine, and browser E2E acceptance scenario are still not finished — see "Known migration work".

## Product scenario

1. A host creates a guest room and receives a short room code plus an opaque seat-recovery token.
2. Exactly three additional guests join. A fifth player cannot claim a seat.
3. The server creates a deterministic Lost Fleet setup from a versioned seed.
4. Players choose factions sequentially in official player order. The first release uses clockwise turn order; legacy bidding is not part of the target product.
5. The final player may rotate Space Sector tiles through persisted setup commands before confirming the board. Lost Fleet spaceship tiles must be at least four axial-hex spaces apart.
6. The authoritative Rust engine validates every setup and gameplay command. Rejected commands cannot partially mutate state.
7. Players complete Income, Gaia, Action, and Clean-up phases for rounds 1–6. The same pure transition path serves live play, tests, and recovery.
8. If any required player disconnects, gameplay pauses without changing the gameplay revision. Reconnection uses the seat token and returns an authoritative snapshot before play resumes.
9. PostgreSQL atomically stores accepted command identity, events/audit data, the new revision, and authoritative post-state. Restart recovery never depends on live sockets.
10. After round 6, the server applies official final scoring and publishes the terminal result to all four clients.

## Architecture

```text
gaia-frontend (React/Vite)
        | REST + versioned WebSocket
gaia-server (Axum/Tokio coordinator)
        | strict envelopes from gaia-protocol
gaia-engine (pure deterministic rules)
        |
PostgreSQL (authoritative durable state)
```

- `gaia-protocol`: strict command IDs, JavaScript-safe revisions, seat IDs, digests, and versioned envelopes.
- `gaia-engine`: domain state and deterministic rule transitions. Existing legacy rules/data remain under replacement.
- `gaia-server`: room/session transport, persistence, and browser delivery.
- `gaia-frontend`: browser UI and WebSocket client.
- `.omx/plans`: current PRD, test specification, architecture review, and cleanup plan.

AI coaching, MCTS, Qdrant, and Ollama were removed because they are explicit non-goals for the core game.

## Local development

Prerequisites:

- Rust 1.95.0 (`rust-toolchain.toml`)
- Node.js 24.19.0 (`.nvmrc`)
- Docker with Compose

Start PostgreSQL:

```bash
docker compose -f docker-compose.dev.yml up -d
cp gaia-server/.env.example gaia-server/.env
cargo run -p gaia-server
```

In another terminal:

```bash
cd gaia-frontend
npm ci
npm run dev
```

Build the combined server/client image:

```bash
docker compose up --build
```

## Verification

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

cd gaia-frontend
npm ci
npm test -- --run
npm run build

docker compose config
docker compose -f docker-compose.dev.yml config
```

The database/WebSocket integration cases are marked ignored in the default test run because they require PostgreSQL. They were verified against the development Compose database during repository preparation, but must become self-provisioning before release acceptance.

## Known migration work

- All 18 factions' starting resource bowls (ore/credits/knowledge/QIC/power) in `gaia-engine/data/factions.toml` are now confirmed against the physical faction board scans (transcribed directly by the project owner, since the rulebook only prints faction abilities in prose, not the boards' numeric bowls). Starting research-track levels (`starting_track_bonuses`) are likewise confirmed against `gaia-frontend/src/assets/faction_boards/` — 12 of the 18 factions start with one research track (two for Darkanians) at level 1 instead of 0, a detail the rulebook prose never mentions either.
- Per-structure round income (Mine/TradingStation/ResearchLab base+table, Academy(Science), PlanetaryInstitute power charge) is wired into `apply_income_phase` (`gaia-engine/src/rules/engine.rs`, `apply_structure_income`). Values are universal across factions (Mine: 1 ore base + `[1,1,0,1,1,1,1,1]`; TradingStation: 0 credits base + `[3,4,4,5]`; ResearchLab: 1 knowledge base + `[1,1,1]`; Academy(Science): 2 knowledge/round; PlanetaryInstitute: charge 4 power/round) unless a faction's `factions.toml` entry overrides them — confirmed overrides: Firaks' ResearchLab base (2 knowledge), Bescods' TradingStation/ResearchLab income swap (TradingStation pays knowledge, ResearchLab pays credits), Nevlas' ResearchLab income (2/2/2 power instead of knowledge), Itars' Academy(Science) (3 knowledge/round), Space Giants' PlanetaryInstitute charge (6 power/round). All 18 factions' data is transcribed from the physical faction boards.

  PlanetaryInstitute's per-round bonus power token (universal: +1/round, entering bowl1 fresh; Lantids: 0; Ambas/Bescods: +2/round) is implemented, including the order choice it creates: since the fresh token can itself get swept into the same round's power charge if it enters bowl1 before the charge is applied, a player with both effects must choose which happens first. `apply_income_phase` defers any such player into `GamePhase::IncomeOrderPending` (queue-front processing, like `ChargePowerPending`) instead of applying the charge immediately; each queued player resolves their own entry with `GameAction::ChooseIncomeOrder { charge_first }`, and the round only finishes (round increments, `ActionPhase` reopens) once the queue drains. PlanetaryInstitute's per-round bonus *resource* (Xenos: 1 QIC instead of a power token; Gleens: 1 ore instead; Ivits: 1 QIC alongside its normal power token) is also implemented (`FactionData.planetary_institute_bonus_resource`), applied directly since it has no charge-order interaction. Per-faction PlanetaryInstitute abilities beyond income (e.g. Ambas' PI↔Mine swap) are still `FactionAbility` territory and remain deferred.

  Academy(Qic)'s action — "gain 1 Q.I.C." (rulebook p.13), requires a built Academy(Qic) — is implemented as `GameAction::AcademyQicAction`, including BalTaks' override (gain 4 credits instead, `factions.toml`'s `academy_qic_action`). Per rulebook p.15 ("Special Actions": free, but limited to once per round via an action token, reset at Clean-up), it's capped at once per round via `PlayerState.academy_qic_action_used_this_round`, reset in `finish_round_transition` alongside `passed`; the frontend button disables itself accordingly.

  The shared power-action and QIC-action boards (rulebook Appendix III: "each of these actions can be taken only once per round," exclusive across *all* players, not just per-player like Academy(Qic) above) are likewise now enforced: `GameState.used_power_actions`/`used_qic_action_slots` (`Vec<u8>`) track which board slot ids were taken this round — `validate_power_action`/`validate_qic_action` reject a slot already in either list, `apply_power_action`/`apply_qic_action` push onto them, and `finish_round_transition` clears both alongside the Academy(Qic) flag. A `QicActionKind`'s slot identity (`qic_action_slot_id`) ignores its coord payload, so e.g. two different `BuildSatellite` targets still contend for the same shared slot. The frontend's `PowerAction`/`QicAction` pickers disable already-taken slots the same way the Academy(Qic) button does.
- The `FactionAbility` system is now wired into the engine (setup completion seeds starting resources; `on_build`/`special_action`/`final_scoring`/`passive_income`/`gaia_phase_power_destination` hooks are called; a per-faction terraforming-cost override point exists), and **Darkanians**, **Space Giants**, and (Gaia-phase power destination only) **Terrans** have real implementations. **Tinkeroids** and **Moweyds** still use the inert stub: their abilities (Tinkering tiles, Power Ring, the randomized 3-vs-1 terraforming split) depend on the Exploration board / Deep Space spatial subsystem, which isn't built yet — Deep Space sector positions are still a `(0,0)` placeholder in `Randomizer::build_deep_space_layout`. The other 13 base-game factions also remain stubs; most of their abilities depend on foundational mechanics below that don't exist yet (free actions, a Brainstone-like resource type, once-per-round flag resets, an `on_upgrade` hook, interactive starting-structure placement).
- Where on the board a player places their faction's starting structures isn't modeled as an interactive setup step yet — the engine seeds starting resources on setup completion but not board placement.
- The round loop now actually completes (`RuleEngine::advance_to_next_round`): Gaia phase (Transdim→Gaia planet conversion, Gaia-area power re-entering the cycle) and Income phase (current research-track-level income, `passive_income` hook) are wired, and `gaia-server`'s round transition calls it — previously the game got stuck in `RoundScoring` forever after round 1, and round-tile VP was computed and broadcast but never actually added to `player.vp`.
- **Passive Action: Charge Power** (rulebook p.16-17, the standard base-game reactive power mechanic — not a faction ability) is implemented: `GameAction::Build`/`Upgrade` pause into a new `GamePhase::ChargePowerPending` queue (clockwise order, opponent structures within range 2), and each queued opponent submits `GameAction::ChargePower { accept }` — all-or-nothing, with the chargeable amount auto-capped by the qualifying structure's power value, available power tokens, and available VP (both documented rulebook exceptions). Still missing: round booster and tech tile effects, a Brainstone-like resource type, an `on_upgrade` faction-ability hook, interactive starting-structure placement, and the "free action" distinction (QIC actions currently consume the main turn action like everything else) — most of the remaining 13 base-game factions' abilities depend on one or more of these.
- `gaia-frontend`'s `GameAction`/`GamePhase`/`GameState` TypeScript types and `ActionPanel` now match the current `gaia_engine::rules::actions::GameAction` enum exactly (they had drifted to an entirely different, older action-name scheme — `BuildMine`/`UpgradeStructure`/etc. — that didn't correspond to any current wire variant, so Build/Upgrade/Pass didn't actually work from the browser despite UI existing for them). The browser can now submit every `GameAction` variant, including `ChargePower`/`ChooseIncomeOrder` (rendered as their own full-panel prompts when `GamePhase` is `ChargePowerPending`/`IncomeOrderPending`) and `AcademyQicAction`. There is still no server-side "valid targets" query (`RuleEngine::get_valid_actions` isn't exposed over the wire) — the client lets the player pick any hex for a coord-taking action and relies on the server's existing `command_rejected` reply (now surfaced as an error banner in `App.tsx`) to reject illegal targets, rather than pre-filtering/highlighting them. `FormFederation`'s multi-hex picker, the `Upgrade`/`PowerAction`/`QicAction` sub-choice pickers, and the Pass booster picker are all new. `gaia-frontend/src/tests/ActionPanel.test.tsx` covers turn-gating, the Build confirm flow, Pass, `AcademyQicAction` visibility/disabled state, both new passive-action prompts, and disabled shared power/QIC action slots.
- The lobby-phase player roster (nicknames/ready flags) isn't durably persisted yet — only rooms that have reached faction selection or later (and so have a `game_snapshots` row) can be rehydrated after a restart; see `AppState::ensure_room_loaded`.
- Review and upgrade the Vite/Vitest major versions; see `docs/DEPENDENCY-AUDIT.md`.
- Replace or license scanned board-game art before any public distribution.

## Repository transfer safety

- Do not commit `.env`, `target`, `node_modules`, frontend `dist`, or local `.omx/.omc/.claude` runtime state; `.gitignore` excludes them.
- This project does not currently declare a redistribution license.
- The rulebook PDFs and scanned/component artwork have unresolved redistribution rights. Keep the destination repository private or remove/replace those files before public publication.
- No remote is configured and this preparation does not push or publish anything.
