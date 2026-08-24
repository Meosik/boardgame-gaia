//! The revisioned wire protocol: every command that mutates room state
//! (lobby readiness, setup regeneration, faction selection, in-game actions)
//! travels wrapped in `gaia_protocol::CommandEnvelope`/`ServerEnvelope`,
//! carrying a client-chosen `command_id` (for idempotent replay) and
//! `expected_revision` (for optimistic concurrency) — see `coordinator.rs`.
//!
//! Connection-lifecycle signaling that isn't a room-state command (join
//! acks, membership roster, presence/pause) stays on the plainer
//! `messages::ServerMessage` — see that module's doc comment.
use serde::{Deserialize, Serialize};

use gaia_engine::{
    game_state::{GameEvent, PlayerId},
    rules::actions::{GameAction, SetupAction},
};
use gaia_protocol::{CommandEnvelope, Digest32, ServerEnvelope};

/// Fixed for now — automatic schema-hash derivation (to catch a client/server
/// build mismatch) is out of scope until multi-version rollout is a real
/// concern. Bump by hand on a breaking wire-format change.
pub const SCHEMA_HASH: Digest32 = Digest32::from_bytes([0u8; 32]);

/// The union of every command that advances a room's revision.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientCommand {
    /// Toggle this player's lobby ready state.
    PlayerReady { ready: bool },
    /// Host-only: regenerate the randomised game setup.
    RegenerateSetup { seed: Option<String> },
    /// Faction choice during the setup phase.
    PlaceSetupAction { action: SetupAction },
    /// In-game action.
    PlaceGameAction { action: GameAction },
}

/// Top-level shape of every client->server WebSocket frame. `Join` precedes
/// having a revision to track (it establishes identity), so it stays outside
/// the envelope; the room's current revision comes back in the join
/// acknowledgement (`messages::ServerMessage::RoomJoined`) for the client to
/// bootstrap `expected_revision` tracking from.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ClientFrame {
    JoinRoom {
        room_code: String,
        nickname: String,
        session_token: Option<String>,
    },
    Command(CommandEnvelope<ClientCommand>),
}

/// State broadcast after every accepted command — either a lobby-phase view
/// (before a `GameState` exists) or the full serialized `GameState`, both as
/// opaque JSON; the client tells them apart by shape.
pub type Envelope = ServerEnvelope<serde_json::Value, GameEvent>;

pub fn command_accepted(
    command_id: gaia_protocol::CommandId,
    revision: gaia_protocol::Revision,
) -> Envelope {
    Envelope::CommandAccepted {
        protocol_version: gaia_protocol::PROTOCOL_VERSION,
        schema_hash: SCHEMA_HASH,
        command_id,
        revision,
    }
}

pub fn command_rejected(
    command_id: Option<gaia_protocol::CommandId>,
    revision: gaia_protocol::Revision,
    code: &str,
    message: &str,
) -> Envelope {
    Envelope::CommandRejected {
        protocol_version: gaia_protocol::PROTOCOL_VERSION,
        schema_hash: SCHEMA_HASH,
        command_id,
        revision,
        rejection: gaia_protocol::ProtocolRejection {
            code: code.to_string(),
            message_key: message.to_string(),
        },
    }
}

pub fn snapshot(revision: gaia_protocol::Revision, state: serde_json::Value) -> Envelope {
    Envelope::Snapshot {
        protocol_version: gaia_protocol::PROTOCOL_VERSION,
        schema_hash: SCHEMA_HASH,
        revision,
        state,
    }
}

pub fn control(control: gaia_protocol::ControlProjection) -> Envelope {
    Envelope::Control {
        protocol_version: gaia_protocol::PROTOCOL_VERSION,
        schema_hash: SCHEMA_HASH,
        control,
    }
}

/// Maps a `coordinator::CommandError` to the `(code, message)` pair a
/// `CommandRejected` carries — the current room revision (needed for the
/// envelope's `revision` field) is the caller's responsibility to supply,
/// since only the caller still holds it after a revision-conflict error.
pub fn rejection_reason(error: &crate::coordinator::CommandError) -> (&'static str, String) {
    use crate::coordinator::CommandError;
    match error {
        CommandError::RoomNotFound(_) => ("ROOM_NOT_FOUND", error.to_string()),
        CommandError::Paused => ("ROOM_PAUSED", error.to_string()),
        CommandError::RevisionConflict { .. } => ("REVISION_CONFLICT", error.to_string()),
        CommandError::Rule(rule_error) => (rule_error_code(rule_error), rule_error.to_string()),
        CommandError::Server(_) => ("INTERNAL", error.to_string()),
    }
}

fn rule_error_code(error: &gaia_engine::error::RuleError) -> &'static str {
    use gaia_engine::error::RuleError;
    match error {
        RuleError::NotYourTurn => "NOT_YOUR_TURN",
        RuleError::WrongPhase => "WRONG_PHASE",
        RuleError::InsufficientResources(_) => "INSUFFICIENT_RESOURCES",
        _ => "ACTION_NOT_ALLOWED",
    }
}

/// Best-effort seat index (0-3, this codebase's rooms are always 4 seats) for
/// `gaia_protocol::SeatId`, which is a fixed-size seat slot rather than this
/// codebase's globally-allocated `PlayerId`. Falls back to seat 0 if the
/// player somehow isn't in the roster — callers only use this for
/// best-effort presence display, never as an authorization check.
pub fn seat_id_for(
    players: &[(PlayerId, String, bool)],
    player_id: PlayerId,
) -> gaia_protocol::SeatId {
    let index = players
        .iter()
        .position(|(id, _, _)| *id == player_id)
        .unwrap_or(0);
    gaia_protocol::SeatId::new(index.min(3) as u8)
        .unwrap_or_else(|_| unreachable!("index.min(3) is always in 0..=3"))
}
