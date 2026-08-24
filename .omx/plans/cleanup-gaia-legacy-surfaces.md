# Cleanup Plan: Gaia Legacy Surfaces

**Date:** 2026-08-19  
**Mode:** direct execution; existing Autopilot artifacts remain preserved

## Target outcome

Remove services and application paths that are explicit non-goals for the four-player base + Lost Fleet rebuild, without deleting setup behavior until its official replacement exists.

## Behavior lock

Before editing:

- `cargo test --workspace`
- `npm test -- --run` in `gaia-frontend`
- `npm run build` in `gaia-frontend`

After editing, rerun the same checks plus Rust format/Clippy and Docker Compose configuration validation.

## Pass 1: safe deletion

- Remove `gaia-ai`, Qdrant, and Ollama services from the core repository topology.
- Remove coaching request/response protocol variants, server proxy code/configuration, client store state/actions, and UI.
- Remove dependencies and environment variables used only by coaching.
- Preserve PostgreSQL, the Rust server/engine, the React client, and game assets pending licensing disposition.

## Pass 2: replacement before deletion

- Implement and test official sequential faction selection, clockwise order, persisted sector rotation, and initial-placement state.
- Only then remove legacy bidding engine/state/actions/UI/tests.
- Replace fictitious Lost Fleet factions with the four official factions through verified data migrations before deleting legacy identifiers.
- Switch server/client traffic to `gaia-protocol` before deleting legacy message DTOs.

## Constraints

- No new external dependencies.
- No behavior-preserving wrapper around removed AI functionality.
- No silent removal of the only currently wired setup flow.
- Keep each deletion reversible through a temporary archive because this project directory is not tracked as its own Git repository.

## Stop condition

Pass 1 is complete when no production source or Compose file references AI coaching, Qdrant, or Ollama and all available Rust/frontend/Compose checks pass. Pass 2 remains explicitly pending until its replacement tests exist.

## Pass 1 result

- Removed the AI/coaching application path and its Rust, TypeScript, dependency, environment, and Compose surfaces.
- Removed obsolete local team/bootstrap and preview scratch files; retained asset-preparation scripts because they document how currently bundled runtime images were derived.
- Removed orphaned Qdrant and Ollama containers after the Compose topology was reduced.
- Verified Rust format/Clippy/tests, all database-backed server integration tests, frontend tests/build, Compose configuration, and the combined Docker image.
- Kept legacy bidding and faction identifiers only because their official sequential-selection replacement is not implemented yet.
