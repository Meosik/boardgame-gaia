use std::collections::HashSet;
use std::sync::Arc;
use tokio::sync::RwLock;

use crate::error::ServerResult;
use crate::event_bus::EventBus;
use crate::repository::GameRepository;
use crate::room::manager::{Room, RoomManager, RoomState};
use crate::room::session::SessionManager;

#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::PgPool,
    pub rooms: Arc<RwLock<RoomManager>>,
    pub sessions: Arc<SessionManager>,
    pub event_bus: Arc<EventBus>,
}

impl AppState {
    pub fn new(db: sqlx::PgPool) -> Self {
        Self {
            sessions: Arc::new(SessionManager::new(db.clone())),
            db,
            rooms: Arc::new(RwLock::new(RoomManager::new())),
            event_bus: Arc::new(EventBus::new()),
        }
    }

    /// Rehydrates a room from the DB into the in-memory `RoomManager` if it
    /// isn't already there — the only path that makes "restart recovery"
    /// real rather than aspirational. Only rooms that have committed at
    /// least one revision (reached faction selection or later, so a
    /// `game_snapshots` row exists) can be rehydrated this way: the player
    /// roster and nicknames for a room that's still in the lobby aren't
    /// durably persisted yet (a known gap — see README), so a pure-lobby room
    /// lost from memory (e.g. a restart before anyone readied up) stays lost.
    /// No-op (not an error) if the room genuinely doesn't exist, or exists
    /// but has nothing to rehydrate from yet — callers see a normal
    /// `RoomNotFound` from whatever they do next.
    pub async fn ensure_room_loaded(&self, room_code: &str) -> ServerResult<()> {
        {
            let rooms = self.rooms.read().await;
            if rooms.get_room(room_code).is_some() {
                return Ok(());
            }
        }

        let repo = GameRepository::new(self.db.clone());
        let Some((host_player, state_str, seed, _row_revision, setup_json)) =
            repo.load_room_row(room_code).await?
        else {
            return Ok(());
        };
        let setup = serde_json::from_value(setup_json).ok();

        let Some((revision, game_state)) = repo.load_latest_snapshot(room_code).await? else {
            return Ok(());
        };

        let players = game_state
            .players
            .iter()
            .map(|p| (p.player_id, p.nickname.clone(), true))
            .collect();

        let room = Room {
            code: room_code.to_string(),
            host_player,
            players,
            state: RoomState::from_db_str(&state_str),
            game_state: Some(game_state),
            setup,
            seed,
            revision: revision as u64,
            connected: HashSet::new(),
            paused: false,
        };

        let mut rooms = self.rooms.write().await;
        rooms.insert_if_absent(room_code.to_string(), room);
        Ok(())
    }
}
