//! Per-room command coordinator: the single place that serializes command
//! handling, deduplicates by `command_id`, checks `expected_revision`, and
//! atomically persists the resulting state before broadcasting it.
//!
//! Follows the PRD "Concurrency and transaction flow": authenticate/pause
//! check -> idempotency check -> revision check -> pure engine mutation ->
//! atomic DB commit -> only-after-commit in-memory swap. The existing global
//! `AppState.rooms` `RwLock` is the serialization boundary — this is a single
//! self-hosted-process deployment, so a per-room actor/mailbox would be
//! premature; the lock already gives correct (if coarse) serialization.
use serde_json::json;

use gaia_engine::error::RuleError;
use gaia_engine::game_state::GameEvent;

use gaia_protocol::{CommandId, Revision};

use crate::{
    error::ServerError, protocol, repository::GameRepository, room::manager::Room, state::AppState,
};

pub struct CommandOutcome {
    pub revision: Revision,
    pub events: Vec<GameEvent>,
}

#[derive(Debug, thiserror::Error)]
pub enum CommandError {
    #[error("room not found: {0}")]
    RoomNotFound(String),
    #[error("room is paused: waiting for players to reconnect")]
    Paused,
    #[error("revision conflict: expected {expected}, room is at {current}")]
    RevisionConflict { expected: u64, current: u64 },
    #[error(transparent)]
    Rule(#[from] RuleError),
    #[error(transparent)]
    Server(#[from] ServerError),
}

pub type CommandResult = Result<CommandOutcome, CommandError>;

/// Applies one client-issued command to a room, end-to-end.
///
/// `mutate` receives a clone of the room and must either mutate it in place
/// (engine calls, `room.state` transitions, etc.) and return the resulting
/// events, or return a `RuleError` to reject the command without any effect.
/// The clone is only swapped into the live room after the DB transaction
/// commits — a DB failure leaves the live room untouched.
pub async fn apply_command(
    app: &AppState,
    room_code: &str,
    command_id: CommandId,
    expected_revision: Revision,
    mutate: impl FnOnce(&mut Room) -> Result<Vec<GameEvent>, RuleError>,
) -> CommandResult {
    app.ensure_room_loaded(room_code)
        .await
        .map_err(CommandError::Server)?;

    let repo = GameRepository::new(app.db.clone());

    // Idempotency: a command_id we've already committed (accepted or
    // rejected) replays its recorded outcome instead of reprocessing.
    if let Some(stored) = repo
        .find_processed_command(room_code, command_id.as_str())
        .await
        .map_err(CommandError::Server)?
    {
        return decode_stored_outcome(&stored);
    }

    let mut rooms = app.rooms.write().await;
    let room = rooms
        .get_room_mut(room_code)
        .ok_or_else(|| CommandError::RoomNotFound(room_code.to_string()))?;

    if room.paused {
        return Err(CommandError::Paused);
    }

    if room.revision != expected_revision.get() {
        return Err(CommandError::RevisionConflict {
            expected: expected_revision.get(),
            current: room.revision,
        });
    }

    let mut candidate = room.clone();
    let events = match mutate(&mut candidate) {
        Ok(events) => events,
        Err(rule_error) => {
            let result = json!({
                "accepted": false,
                "code": rule_error_code(&rule_error),
                "message": rule_error.to_string(),
            });
            repo.record_rejected_command(
                room_code,
                command_id.as_str(),
                room.revision as i64,
                &result,
            )
            .await
            .map_err(CommandError::Server)?;
            return Err(CommandError::Rule(rule_error));
        }
    };

    // `commit_*` always advances by exactly 1 on success — deterministic, so
    // it's safe to compute now and store it alongside the outcome for replay.
    let next_revision = room.revision + 1;
    let result = json!({ "accepted": true, "revision": next_revision, "events": &events });

    let room_state_str = candidate.state.as_db_str();
    let setup_json = serde_json::to_value(&candidate.setup).map_err(ServerError::from)?;
    let committed = match candidate.game_state.as_ref() {
        Some(state) => {
            let round = state.round;
            repo.commit_command(
                room_code,
                room.revision as i64,
                round,
                state,
                &events,
                None,
                command_id.as_str(),
                &result,
                room_state_str,
                &setup_json,
            )
            .await
        }
        None => {
            repo.commit_lobby_command(
                room_code,
                room.revision as i64,
                command_id.as_str(),
                &result,
                room_state_str,
                &setup_json,
            )
            .await
        }
    }
    .map_err(CommandError::Server)?;

    let Some(new_revision_raw) = committed else {
        // Only reachable if something else advanced `rooms.revision` in the
        // DB without going through this same in-memory-locked path (e.g. a
        // second server process) — the in-memory check above already
        // prevents this under normal single-process operation.
        return Err(CommandError::RevisionConflict {
            expected: expected_revision.get(),
            current: room.revision,
        });
    };

    let new_revision = Revision::new(new_revision_raw as u64)
        .map_err(|_| ServerError::Internal("revision overflow".into()))?;

    candidate.revision = new_revision.get();
    *room = candidate;

    Ok(CommandOutcome {
        revision: new_revision,
        events,
    })
}

/// Same as `apply_command`, but for call sites that don't have a real
/// client-supplied `expected_revision` yet (pre-envelope-migration: every
/// current service call site) — reads the room's current revision and
/// retries on `RevisionConflict` with a fresh read, since there's no client
/// on the other end deciding whether a conflict is worth retrying. Genuine
/// client commands (once the envelope carries a real `expected_revision`)
/// must NOT use this: a stale revision from a real client is a real conflict
/// the client needs to see, not something to silently paper over.
pub async fn apply_command_auto_revision(
    app: &AppState,
    room_code: &str,
    mut mutate: impl FnMut(&mut Room) -> Result<Vec<GameEvent>, RuleError>,
) -> CommandResult {
    const MAX_ATTEMPTS: u32 = 8;
    let mut last_conflict = None;
    for _ in 0..MAX_ATTEMPTS {
        let expected_revision = current_revision(app, room_code).await?;
        let command_id = fresh_command_id();
        match apply_command(app, room_code, command_id, expected_revision, &mut mutate).await {
            Err(CommandError::RevisionConflict { expected, current }) => {
                last_conflict = Some(CommandError::RevisionConflict { expected, current });
                continue;
            }
            other => return other,
        }
    }
    Err(last_conflict.unwrap_or(CommandError::RevisionConflict {
        expected: 0,
        current: 0,
    }))
}

pub struct TransitionOutcome {
    pub revision: Revision,
}

/// Applies a server-initiated transition (round advance, game end — no
/// client `command_id`/`expected_revision` behind it) the same way as
/// `apply_command`: mutate a clone, only swap it in after the DB commit.
/// Requires `room.game_state` to already exist (`mutate` runs after cloning,
/// so it may still consume/replace it, but the room must have one before the
/// call — these transitions only happen mid-game).
pub async fn apply_server_transition(
    app: &AppState,
    room_code: &str,
    mutate: impl FnOnce(&mut Room),
) -> Result<TransitionOutcome, CommandError> {
    app.ensure_room_loaded(room_code)
        .await
        .map_err(CommandError::Server)?;

    let mut rooms = app.rooms.write().await;
    let room = rooms
        .get_room_mut(room_code)
        .ok_or_else(|| CommandError::RoomNotFound(room_code.to_string()))?;

    let mut candidate = room.clone();
    mutate(&mut candidate);

    let state = candidate.game_state.as_ref().ok_or_else(|| {
        ServerError::Internal("server transition requires an existing game state".into())
    })?;
    let round = state.round;
    let room_state_str = candidate.state.as_db_str();
    let setup_json = serde_json::to_value(&candidate.setup)
        .map_err(|e| CommandError::Server(ServerError::from(e)))?;

    let repo = GameRepository::new(app.db.clone());
    let committed = repo
        .commit_server_transition(
            room_code,
            room.revision as i64,
            round,
            state,
            room_state_str,
            &setup_json,
        )
        .await
        .map_err(CommandError::Server)?;

    let Some(new_revision_raw) = committed else {
        return Err(CommandError::RevisionConflict {
            expected: room.revision,
            current: room.revision,
        });
    };

    let new_revision = Revision::new(new_revision_raw as u64)
        .map_err(|_| ServerError::Internal("revision overflow".into()))?;
    candidate.revision = new_revision.get();
    *room = candidate;

    Ok(TransitionOutcome {
        revision: new_revision,
    })
}

fn decode_stored_outcome(stored: &serde_json::Value) -> CommandResult {
    let accepted = stored
        .get("accepted")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);
    if accepted {
        let events: Vec<GameEvent> = stored
            .get("events")
            .cloned()
            .map(serde_json::from_value)
            .transpose()
            .map_err(|e| CommandError::Server(ServerError::Serialise(e)))?
            .unwrap_or_default();
        let revision_raw = stored.get("revision").and_then(|v| v.as_u64()).unwrap_or(0);
        let revision = Revision::new(revision_raw).map_err(|_| {
            CommandError::Server(ServerError::Internal("stored revision overflow".into()))
        })?;
        Ok(CommandOutcome { revision, events })
    } else {
        let message = stored
            .get("message")
            .and_then(|v| v.as_str())
            .unwrap_or("command was previously rejected")
            .to_string();
        Err(CommandError::Server(ServerError::InvalidAction(message)))
    }
}

fn rule_error_code(error: &RuleError) -> &'static str {
    match error {
        RuleError::NotYourTurn => "NOT_YOUR_TURN",
        RuleError::WrongPhase => "WRONG_PHASE",
        RuleError::InsufficientResources(_) => "INSUFFICIENT_RESOURCES",
        _ => "ACTION_NOT_ALLOWED",
    }
}

/// Reads a room's current revision — used by callers that don't yet have a
/// client-supplied `expected_revision` to pass through (pre-envelope-migration
/// call sites treat "whatever the room is at right now" as expected).
pub async fn current_revision(app: &AppState, room_code: &str) -> Result<Revision, ServerError> {
    app.ensure_room_loaded(room_code).await?;
    let rooms = app.rooms.read().await;
    let room = rooms
        .get_room(room_code)
        .ok_or_else(|| ServerError::RoomNotFound(room_code.to_string()))?;
    Revision::new(room.revision).map_err(|_| ServerError::Internal("revision overflow".into()))
}

/// Mints a fresh `CommandId` for call sites that don't yet have one from a
/// client-supplied envelope (see `current_revision`) — a uuid v4 in simple
/// (no-hyphen) form always fits `CommandId`'s ASCII/64-char rule.
pub fn fresh_command_id() -> CommandId {
    CommandId::parse(&uuid::Uuid::new_v4().simple().to_string())
        .unwrap_or_else(|_| unreachable!("uuid simple output is always valid CommandId input"))
}

/// Broadcasts a `Snapshot` envelope with the room's current state — a lobby
/// view before a `GameState` exists, the full serialized `GameState` after.
/// No-op (silently) if the room has since vanished from memory; callers
/// already have their own room-not-found handling for the primary operation.
pub async fn broadcast_snapshot(app: &AppState, room_code: &str, revision: Revision) {
    let view = {
        let rooms = app.rooms.read().await;
        let Some(room) = rooms.get_room(room_code) else {
            return;
        };
        room.game_state
            .as_ref()
            .map(|gs| gs.serialize())
            .unwrap_or_else(|| lobby_view(room))
    };
    app.event_bus
        .broadcast(room_code, protocol::snapshot(revision, view))
        .await;
}

fn lobby_view(room: &Room) -> serde_json::Value {
    json!({
        "phase": "lobby",
        "state": room.state.as_db_str(),
        "players": room.players.iter().map(|(id, nick, ready)| json!({
            "player_id": id, "nickname": nick, "ready": ready,
        })).collect::<Vec<_>>(),
        "setup": room.setup,
    })
}

pub fn command_error_to_server_error(error: CommandError) -> ServerError {
    match error {
        CommandError::RoomNotFound(code) => ServerError::RoomNotFound(code),
        CommandError::Paused => ServerError::InvalidAction("room is paused".into()),
        CommandError::RevisionConflict { expected, current } => ServerError::InvalidAction(
            format!("revision conflict: expected {expected}, room is at {current}"),
        ),
        CommandError::Rule(rule_error) => ServerError::InvalidAction(rule_error.to_string()),
        CommandError::Server(server_error) => server_error,
    }
}
