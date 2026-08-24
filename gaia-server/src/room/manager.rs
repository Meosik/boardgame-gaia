use std::collections::{HashMap, HashSet};

use gaia_engine::{game_state::PlayerId, GameSetup, GameState, Randomizer};

use crate::error::{ServerError, ServerResult};

// ── Room ──────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum RoomState {
    Lobby,
    FactionSelection,
    InGame,
    Ended,
}

impl RoomState {
    /// The string stored in `rooms.state` — matches the literals every
    /// `update_room_state`/`commit_*` call site used to pass by hand.
    pub fn as_db_str(&self) -> &'static str {
        match self {
            Self::Lobby => "lobby",
            Self::FactionSelection => "faction_selection",
            Self::InGame => "in_game",
            Self::Ended => "ended",
        }
    }

    pub fn from_db_str(value: &str) -> Self {
        match value {
            "faction_selection" => Self::FactionSelection,
            "in_game" => Self::InGame,
            "ended" => Self::Ended,
            _ => Self::Lobby,
        }
    }
}

#[derive(Debug, Clone)]
pub struct Room {
    pub code: String,
    pub host_player: PlayerId,
    /// (player_id, nickname, is_ready)
    pub players: Vec<(PlayerId, String, bool)>,
    pub state: RoomState,
    pub game_state: Option<GameState>,
    pub setup: Option<GameSetup>,
    pub seed: String,
    /// Monotonic command revision — mirrors `rooms.revision` in the DB and is
    /// only ever advanced by `coordinator::apply_command` after a committed
    /// transaction, never mutated directly.
    pub revision: u64,
    /// Seats with a live WebSocket connection right now.
    pub connected: HashSet<PlayerId>,
    /// Set once gameplay has started and a required seat disconnects; cleared
    /// once all seats are reconnected. Never changes `revision`.
    pub paused: bool,
}

impl Room {
    pub fn player_count(&self) -> usize {
        self.players.len()
    }

    pub fn is_host(&self, player_id: PlayerId) -> bool {
        self.host_player == player_id
    }

    pub fn nickname_of(&self, player_id: PlayerId) -> Option<&str> {
        self.players
            .iter()
            .find(|(id, _, _)| *id == player_id)
            .map(|(_, n, _)| n.as_str())
    }

    pub fn set_ready(&mut self, player_id: PlayerId, ready: bool) -> ServerResult<()> {
        let Some((_, _, is_ready)) = self.players.iter_mut().find(|(id, _, _)| *id == player_id)
        else {
            return Err(ServerError::PlayerNotFound);
        };
        *is_ready = ready;
        Ok(())
    }

    pub fn all_ready(&self) -> bool {
        !self.players.is_empty() && self.players.iter().all(|(_, _, ready)| *ready)
    }

    /// Marks a seat as connected and recomputes `paused`. Only rooms with a
    /// live game (`state == InGame`) can be paused — the lobby has no
    /// gameplay to interrupt.
    pub fn mark_connected(&mut self, player_id: PlayerId) {
        self.connected.insert(player_id);
        self.recompute_paused();
    }

    /// Marks a seat as disconnected and recomputes `paused`.
    pub fn mark_disconnected(&mut self, player_id: PlayerId) {
        self.connected.remove(&player_id);
        self.recompute_paused();
    }

    fn recompute_paused(&mut self) {
        self.paused = self.state == RoomState::InGame
            && self
                .players
                .iter()
                .any(|(id, _, _)| !self.connected.contains(id));
    }

    /// Seats required for gameplay that currently have no live connection.
    pub fn missing_seats(&self) -> Vec<PlayerId> {
        self.players
            .iter()
            .map(|(id, _, _)| *id)
            .filter(|id| !self.connected.contains(id))
            .collect()
    }
}

// ── RoomManager ───────────────────────────────────────────────────────────────

pub struct RoomManager {
    rooms: HashMap<String, Room>,
    next_player_id: u8,
}

impl Default for RoomManager {
    fn default() -> Self {
        Self::new()
    }
}

impl RoomManager {
    pub fn new() -> Self {
        Self {
            rooms: HashMap::new(),
            next_player_id: 1,
        }
    }

    /// Creates a new room, returning (room_code, host_player_id).
    /// If `seed` is `Some("")` or whitespace-only the caller already validated it;
    /// an empty/whitespace seed is replaced by a random UUID.
    pub fn create_room(
        &mut self,
        host_nickname: &str,
        seed: Option<String>,
    ) -> ServerResult<(String, PlayerId)> {
        let seed = seed.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
        let code = generate_room_code();
        let player_id = self.alloc_player_id();
        let setup = Randomizer::generate_setup(&seed)?;
        let room = Room {
            code: code.clone(),
            host_player: player_id,
            players: vec![(player_id, host_nickname.to_string(), false)],
            state: RoomState::Lobby,
            game_state: None,
            setup: Some(setup),
            seed,
            revision: 0,
            connected: HashSet::new(),
            paused: false,
        };
        self.rooms.insert(code.clone(), room);
        Ok((code, player_id))
    }

    /// Joins an existing room. Returns the new player's id.
    pub fn join_room(&mut self, code: &str, nickname: &str) -> ServerResult<PlayerId> {
        let room = self
            .rooms
            .get_mut(code)
            .ok_or_else(|| ServerError::RoomNotFound(code.to_string()))?;
        if room.state != RoomState::Lobby {
            return Err(ServerError::RoomAlreadyStarted);
        }
        if room.player_count() >= 4 {
            return Err(ServerError::RoomFull);
        }
        let player_id = self.next_player_id;
        self.next_player_id = self.next_player_id.wrapping_add(1);
        room.players.push((player_id, nickname.to_string(), false));
        Ok(player_id)
    }

    /// Inserts a rehydrated room (see `AppState::ensure_room_loaded`) unless
    /// one already exists for this code — e.g. a concurrent request rehydrated
    /// it first, or it was never actually evicted. Never overwrites live state.
    pub fn insert_if_absent(&mut self, code: String, room: Room) {
        self.rooms.entry(code).or_insert(room);
    }

    pub fn get_room(&self, code: &str) -> Option<&Room> {
        self.rooms.get(code)
    }

    pub fn get_room_mut(&mut self, code: &str) -> Option<&mut Room> {
        self.rooms.get_mut(code)
    }

    pub fn remove_room(&mut self, code: &str) {
        self.rooms.remove(code);
    }

    fn alloc_player_id(&mut self) -> PlayerId {
        let id = self.next_player_id;
        self.next_player_id = self.next_player_id.wrapping_add(1);
        id
    }
}

fn generate_room_code() -> String {
    use std::fmt::Write;
    let n = uuid::Uuid::new_v4().as_u128();
    let mut s = String::with_capacity(6);
    let _ = write!(s, "{:06X}", n & 0xFF_FFFF);
    s
}
