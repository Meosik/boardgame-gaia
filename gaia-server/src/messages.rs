//! Connection-lifecycle / room-roster signaling that isn't a revisioned
//! command: join acknowledgements, membership roster, presence/pause, and
//! informational round/game-end summaries. Everything that mutates room
//! state (and needs `command_id`/`expected_revision`/idempotent replay)
//! travels through `protocol::Envelope` instead — see that module.
use gaia_engine::{game_state::PlayerId, rules::actions::GameAction, GameSetup};
use serde::Serialize;

use crate::protocol::Envelope;

#[derive(Debug, Clone, Serialize)]
pub struct LobbyPlayer {
    pub player_id: PlayerId,
    pub nickname: String,
    pub ready: bool,
}

/// Why a seat disappeared from the roster, so a client can tell being removed by the host from
/// someone else simply leaving.
#[derive(Debug, Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RemovalReason {
    Left,
    Kicked,
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ServerMessage {
    /// Successful room join — sent only to the joining player.
    RoomJoined {
        room_code: String,
        player_id: PlayerId,
        session_token: String,
        game_setup: Box<GameSetup>,
        /// The room's current revision, for the client to bootstrap
        /// `expected_revision` tracking from.
        revision: u64,
    },
    /// A player joined the lobby — broadcast to all in room.
    PlayerJoined {
        player_id: PlayerId,
        nickname: String,
        player_count: usize,
    },
    /// A player left the lobby or was removed by the host — broadcast to everyone still in the
    /// room, including the player it names, whose client uses it to return to the room list.
    /// A `LobbyState` with the new roster follows, unless the room emptied and was dropped.
    PlayerRemoved {
        player_id: PlayerId,
        reason: RemovalReason,
    },
    /// Full lobby player state — broadcast whenever membership or readiness changes.
    LobbyState {
        players: Vec<LobbyPlayer>,
        host_player_id: PlayerId,
    },
    /// Round ended with per-player scores.
    RoundEnded {
        round: u8,
        scores: Vec<(PlayerId, i32)>,
    },
    /// Final game ended. `winners` holds every player tied for the highest score (ties share
    /// the win, matching `GamePhase::Ended` — this broadcast mirrors that authoritative state,
    /// which is also reachable straight from a snapshot for clients that missed this message).
    GameEnded {
        final_scores: Vec<(PlayerId, i32)>,
        winners: Vec<PlayerId>,
    },
    /// Reply to `ClientFrame::QueryValidActions` — every `GameAction` the requesting player could
    /// currently submit and have accepted (`RuleEngine::get_valid_actions`), bound to `revision`
    /// so the client can discard a response that arrives after room state has already moved on.
    /// A pure read: unlike `ClientCommand`, it never advances the revision itself. Exists so the
    /// frontend can ask the engine what's legal instead of re-implementing each action's
    /// eligibility rules by hand (the source of several UI/engine drift bugs so far).
    ValidActions {
        actions: Vec<GameAction>,
        revision: u64,
    },
    /// A required seat disconnected/reconnected mid-game — broadcast
    /// whenever `paused` flips. Never accompanies a revision change.
    RoomPaused {
        paused: bool,
        missing_seats: Vec<PlayerId>,
    },
    /// Server-side error.
    Error { code: String, message: String },
}

impl ServerMessage {
    pub fn error(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self::Error {
            code: code.into(),
            message: message.into(),
        }
    }
}

/// Everything that can travel over a room's broadcast channel: lobby/roster
/// signaling and revisioned command envelopes share one channel per room, so
/// a single WS connection's outbound stream can carry both. `untagged`
/// passes each variant's own `type`-tagged serialization straight through —
/// this wrapper is invisible on the wire.
#[derive(Debug, Clone, Serialize)]
#[serde(untagged)]
pub enum OutboundMessage {
    Lobby(ServerMessage),
    Command(Envelope),
}

impl From<ServerMessage> for OutboundMessage {
    fn from(msg: ServerMessage) -> Self {
        Self::Lobby(msg)
    }
}

impl From<Envelope> for OutboundMessage {
    fn from(envelope: Envelope) -> Self {
        Self::Command(envelope)
    }
}
