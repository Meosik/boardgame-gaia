use std::collections::{HashMap, HashSet};

use gaia_engine::{game_state::PlayerId, GameSetup, GameState, Randomizer, SetupMode};
use serde::Serialize;
use sha2::{Digest, Sha256};

use crate::error::{ServerError, ServerResult};

// ── Room ──────────────────────────────────────────────────────────────────────

/// Long enough for a descriptive title, short enough to stay on one line in the lobby list.
const ROOM_NAME_MAX_CHARS: usize = 24;

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
    /// Title shown in the room list. Blank input falls back to the host's nickname.
    pub name: String,
    /// SHA-256 of an optional room password. `None` means anyone with the code can join; the
    /// plaintext is never stored, matching how session tokens are kept.
    pub password_hash: Option<String>,
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
    /// The only interactive seat in a local development sandbox. The game state may contain
    /// virtual opponents so setup order, adjacency, and opponent-dependent costs can be tested,
    /// but those opponents are advanced automatically and are not room members.
    pub dev_human_player: Option<PlayerId>,
    /// Main actions taken by each virtual seat in the current DEV round. This is server-only
    /// harness state; ordinary rooms leave it empty.
    pub dev_bot_action_counts: HashMap<PlayerId, u8>,
    pub dev_bot_action_round: u8,
}

impl Room {
    /// Show all locally controlled seats without treating them as separate authenticated members.
    pub fn display_players(&self) -> Vec<(PlayerId, String, bool)> {
        if let Some(state) = self
            .game_state
            .as_ref()
            .filter(|state| state.dev_controller == Some(self.host_player))
        {
            let ready = self
                .players
                .iter()
                .find(|(id, _, _)| *id == self.host_player)
                .is_some_and(|(_, _, ready)| *ready);
            return state
                .players
                .iter()
                .map(|player| (player.player_id, player.nickname.clone(), ready))
                .collect();
        }
        self.players.clone()
    }

    pub fn player_count(&self) -> usize {
        self.players.len()
    }

    /// An unlocked room accepts any join; a locked one only the matching password.
    pub fn password_matches(&self, password: Option<&str>) -> bool {
        match &self.password_hash {
            None => true,
            Some(expected) => hash_room_password(password).as_deref() == Some(expected.as_str()),
        }
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

/// One row of the public room browser (`GET /api/rooms`) — only ever built from rooms
/// still in `Lobby`, since a room in any later state has already rejected `join_room`.
#[derive(Debug, Clone, Serialize)]
pub struct RoomSummary {
    pub code: String,
    pub name: String,
    pub host_nickname: String,
    pub player_count: usize,
    /// Whether joining needs the room's password, never the password itself.
    pub has_password: bool,
    /// How this room picks factions, so the list can say so before anyone joins.
    pub setup_mode: Option<SetupMode>,
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
        setup_mode: SetupMode,
        name: Option<&str>,
        password: Option<&str>,
    ) -> ServerResult<(String, PlayerId)> {
        let host_nickname = host_nickname.trim();
        if host_nickname.is_empty() {
            return Err(ServerError::InvalidNickname);
        }
        let seed = seed.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
        let code = generate_room_code();
        let player_id = self.alloc_player_id();
        let setup = match setup_mode {
            SetupMode::Sequential => Randomizer::generate_setup(&seed)?,
            SetupMode::Bidding => Randomizer::generate_bidding_setup(&seed)?,
        };
        let room = Room {
            code: code.clone(),
            name: room_name(name, host_nickname),
            password_hash: hash_room_password(password),
            host_player: player_id,
            players: vec![(player_id, host_nickname.to_string(), false)],
            state: RoomState::Lobby,
            game_state: None,
            setup: Some(setup),
            seed,
            revision: 0,
            connected: HashSet::new(),
            paused: false,
            dev_human_player: None,
            dev_bot_action_counts: HashMap::new(),
            dev_bot_action_round: 0,
        };
        self.rooms.insert(code.clone(), room);
        Ok((code, player_id))
    }

    /// Joins an existing room. Returns the new player's id.
    pub fn join_room(
        &mut self,
        code: &str,
        nickname: &str,
        password: Option<&str>,
    ) -> ServerResult<PlayerId> {
        let nickname = nickname.trim();
        if nickname.is_empty() {
            return Err(ServerError::InvalidNickname);
        }
        let room = self
            .rooms
            .get_mut(code)
            .ok_or_else(|| ServerError::RoomNotFound(code.to_string()))?;
        if room.state != RoomState::Lobby {
            return Err(ServerError::RoomAlreadyStarted);
        }
        if !room.password_matches(password) {
            return Err(ServerError::InvalidRoomPassword);
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

    /// Every currently joinable room, newest first — rooms not in `Lobby` are omitted
    /// since `join_room` would reject them anyway (started game or already ended).
    pub fn list_rooms(&self) -> Vec<RoomSummary> {
        let mut rooms: Vec<&Room> = self
            .rooms
            .values()
            .filter(|room| room.state == RoomState::Lobby)
            .collect();
        rooms.sort_by_key(|room| std::cmp::Reverse(room.host_player));
        rooms
            .into_iter()
            .map(|room| RoomSummary {
                code: room.code.clone(),
                name: room.name.clone(),
                host_nickname: room
                    .nickname_of(room.host_player)
                    .unwrap_or("")
                    .to_string(),
                player_count: room.player_count(),
                has_password: room.password_hash.is_some(),
                setup_mode: room.setup.as_ref().map(|setup| setup.setup_mode),
            })
            .collect()
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

    pub fn alloc_virtual_player_ids(&mut self, count: usize) -> Vec<PlayerId> {
        (0..count).map(|_| self.alloc_player_id()).collect()
    }
}

/// Room titles are free text, so they are trimmed and length-capped; a blank one becomes the
/// host's name rather than leaving an unlabelled row in the lobby list.
fn room_name(name: Option<&str>, host_nickname: &str) -> String {
    match name.map(str::trim).filter(|value| !value.is_empty()) {
        Some(value) => value.chars().take(ROOM_NAME_MAX_CHARS).collect(),
        None => format!("{host_nickname}님의 방"),
    }
}

/// Room passwords are shared throwaway secrets, but they still never sit in memory as plaintext —
/// the same reasoning as `SessionManager`'s token hashing.
fn hash_room_password(password: Option<&str>) -> Option<String> {
    password
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(|value| format!("{:x}", Sha256::digest(value.as_bytes())))
}

fn generate_room_code() -> String {
    use std::fmt::Write;
    let n = uuid::Uuid::new_v4().as_u128();
    let mut s = String::with_capacity(6);
    let _ = write!(s, "{:06X}", n & 0xFF_FFFF);
    s
}

#[cfg(test)]
mod tests {
    use super::RoomManager;
    use gaia_engine::SetupMode;

    #[test]
    fn bidding_room_persists_mode_and_four_offered_factions() {
        let mut rooms = RoomManager::new();
        let (code, _) = rooms
            .create_room(
                "Host",
                Some("server-bidding-room".to_string()),
                SetupMode::Bidding,
                None,
                None,
            )
            .unwrap_or_else(|error| panic!("bidding room should be created: {error}"));

        let setup = rooms
            .get_room(&code)
            .and_then(|room| room.setup.as_ref())
            .unwrap_or_else(|| panic!("created room should retain its setup"));
        assert_eq!(setup.setup_mode, SetupMode::Bidding);
        assert_eq!(setup.factions.len(), 4);
    }

    #[test]
    fn list_rooms_omits_rooms_that_join_room_would_reject() {
        let mut rooms = RoomManager::new();
        let (open_code, _) = rooms
            .create_room("Host", Some("list-rooms-open".to_string()), SetupMode::Bidding, None, None)
            .unwrap_or_else(|error| panic!("room should be created: {error}"));
        let (started_code, _) = rooms
            .create_room("Host2", Some("list-rooms-started".to_string()), SetupMode::Bidding, None, None)
            .unwrap_or_else(|error| panic!("room should be created: {error}"));
        rooms.get_room_mut(&started_code).unwrap_or_else(|| panic!("created room should exist")).state = super::RoomState::InGame;

        let listed = rooms.list_rooms();
        assert!(listed.iter().any(|room| room.code == open_code));
        assert!(!listed.iter().any(|room| room.code == started_code));
        let open = listed.iter().find(|room| room.code == open_code).unwrap_or_else(|| panic!("joinable room should be listed"));
        assert_eq!(open.host_nickname, "Host");
        assert_eq!(open.player_count, 1);
        assert_eq!(open.name, "Host님의 방");
        assert!(!open.has_password);
        assert_eq!(open.setup_mode, Some(SetupMode::Bidding));
    }

    #[test]
    fn a_blank_title_becomes_the_host_name_and_a_long_one_is_capped() {
        let mut rooms = RoomManager::new();
        let (default_code, _) = rooms
            .create_room("호스트", Some("name-default".to_string()), SetupMode::Bidding, Some("   "), None)
            .unwrap_or_else(|error| panic!("room should be created: {error}"));
        let (named_code, _) = rooms
            .create_room("호스트", Some("name-long".to_string()), SetupMode::Bidding, Some(&"가".repeat(40)), None)
            .unwrap_or_else(|error| panic!("room should be created: {error}"));

        let name_of = |code: &str| rooms.get_room(code).map(|room| room.name.clone()).unwrap_or_default();
        assert_eq!(name_of(&default_code), "호스트님의 방");
        assert_eq!(name_of(&named_code).chars().count(), 24);
    }

    #[test]
    fn a_locked_room_admits_only_the_matching_password() {
        let mut rooms = RoomManager::new();
        let (code, _) = rooms
            .create_room("Host", Some("locked-room".to_string()), SetupMode::Bidding, Some("우리끼리"), Some(" hunter2 "))
            .unwrap_or_else(|error| panic!("room should be created: {error}"));

        assert!(matches!(rooms.join_room(&code, "Guest", None), Err(crate::error::ServerError::InvalidRoomPassword)));
        assert!(matches!(rooms.join_room(&code, "Guest", Some("nope")), Err(crate::error::ServerError::InvalidRoomPassword)));
        // Surrounding whitespace is trimmed on both sides, as it is for the nickname.
        assert!(rooms.join_room(&code, "Guest", Some("hunter2")).is_ok());

        let listed = rooms.list_rooms();
        let room = listed.iter().find(|room| room.code == code).unwrap_or_else(|| panic!("locked room should still be listed"));
        assert_eq!(room.name, "우리끼리");
        assert!(room.has_password, "the list must say a room is locked");
        assert_eq!(room.player_count, 2);
    }

    #[test]
    fn an_open_room_ignores_a_supplied_password() {
        let mut rooms = RoomManager::new();
        let (code, _) = rooms
            .create_room("Host", Some("open-room".to_string()), SetupMode::Bidding, None, None)
            .unwrap_or_else(|error| panic!("room should be created: {error}"));

        assert!(rooms.join_room(&code, "Guest", Some("anything")).is_ok());
    }
}
