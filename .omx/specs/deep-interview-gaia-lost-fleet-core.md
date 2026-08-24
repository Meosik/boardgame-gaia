# Gaia Lost Fleet Core Rebuild — Clarified Specification

## Mission

Rebuild Gaia as a complete, server-authoritative, four-player online implementation of the base game plus Lost Fleet. Existing application code and technology choices are reference material only and may be replaced.

## Source-of-truth order

1. Official rulebooks under `docs/`
2. Explicit decisions in this specification
3. Verified game data and rule tests
4. Legacy requirements and code only as non-authoritative reference

When legacy material conflicts with an official rulebook, follow the official rulebook unless a newer explicit product decision overrides it.

## In scope

- Exactly four guest players
- Room creation and room-code joining
- Deterministic, shareable setup generation
- Base game and Lost Fleet boards, factions, actions, phases, scoring, and special rules
- Server-authoritative action validation and state transitions
- Real-time synchronized browser gameplay
- Complete setup, all six rounds, and final scoring
- Durable state sufficient to restore the exact current game
- Session-based reconnection
- Automatic pause whenever a participating player disconnects; resume after that player reconnects
- Reproducible local execution
- Automated rule, protocol, integration, reconnection, and browser end-to-end tests

## Explicit non-goals

- LLM coaching
- MCTS or any AI player
- Spectator mode or user-facing replay UI
- User accounts, public lobby, or matchmaking
- Player replacement during a game
- CI/CD, monitoring, or production deployment automation

Internal history may still be used for correctness and recovery.

## Decision boundaries

- The existing Rust/Axum/React/PostgreSQL architecture is not mandatory.
- Technology alternatives must be compared against rule correctness, deterministic testing, contract safety, multiplayer recovery, local operability, and maintainability.
- Existing assets, game data, utilities, and tests may be reused only after validation against authoritative rules and new contracts.
- Known legacy client/server schemas need not remain compatible.
- One authoritative state-transition path must serve live play, tests, and recovery.

## Acceptance criteria

1. Four independent clients can create/join one room and complete setup.
2. The generated base and Lost Fleet map is valid and deterministic for the same seed.
3. Every client action uses one versioned contract and is validated by the authoritative engine.
4. All base and Lost Fleet factions and rule-changing abilities are executable rather than stubbed.
5. A four-player game can complete all phases of all six rounds and produce correct final scores.
6. Illegal actions are rejected without partial state mutation.
7. Disconnecting any player pauses actions; valid reconnection restores exact state and resumes play.
8. Restart/recovery is proven against durable state, not only in-memory sessions.
9. Rule unit/property tests, contract tests, server integration tests, and browser end-to-end tests pass.
10. A documented local command starts the system and runs the verified end-to-end scenario.

## Planning obligations

- Produce a PRD and test specification.
- Evaluate the stack rather than defaulting to the legacy implementation.
- Identify rulebook/data conflicts before implementation.
- Define verified delivery milestones without shrinking the final completion contract.
- Obtain sequential architecture and adversarial plan approvals before implementation.

## Residual risks

- Asset licensing and redistribution have not been established.
- Browser support and visual fidelity targets may use conservative defaults.
- The rule surface is large; milestones are allowed, but Autopilot completion remains the entire accepted game.
