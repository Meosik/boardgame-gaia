use std::collections::{HashMap, HashSet};
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
    /// Live AI seats; `None` unless `GAIA_AI_DIR` is configured (see `crate::ai`).
    pub ai: Option<Arc<crate::ai::AiPool>>,
}

impl AppState {
    pub fn new(db: sqlx::PgPool) -> Self {
        Self {
            sessions: Arc::new(SessionManager::new(db.clone())),
            db,
            rooms: Arc::new(RwLock::new(RoomManager::new())),
            event_bus: Arc::new(EventBus::new()),
            ai: crate::ai::AiConfig::from_env().map(|config| {
                log::info!(
                    "AI seats enabled: {} worker(s), level {}",
                    config.workers,
                    config.level
                );
                Arc::new(crate::ai::AiPool::new(config))
            }),
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

        let room = rehydrated_room(
            room_code,
            host_player,
            &state_str,
            seed,
            revision as u64,
            setup,
            game_state,
        );

        let mut rooms = self.rooms.write().await;
        rooms.insert_if_absent(room_code.to_string(), room);
        Ok(())
    }
}

/// The in-memory room of a saved game (`AppState::ensure_room_loaded`).
///
/// A game with virtual seats has one room member, its host: the local test controller's
/// (`dev_controller`) or the human seat of a game against AI seats (`ai_game`). Both marks are
/// written into the snapshot by the endpoint that created the game, never inferred from names,
/// and count only when they name the room's host. The other seats of such a game are not
/// members, so the room is not paused waiting for them to connect, and for an AI game the
/// level and the teacher version come back too — its AI seats play on after a server restart.
/// A game saved before `ai_game` existed has no mark and is loaded as an ordinary room.
fn rehydrated_room(
    room_code: &str,
    host_player: gaia_engine::game_state::PlayerId,
    state_str: &str,
    seed: String,
    revision: u64,
    setup: Option<gaia_engine::GameSetup>,
    game_state: gaia_engine::game_state::GameState,
) -> Room {
    let dev_controller = game_state
        .dev_controller
        .filter(|controller| *controller == host_player);
    let ai_game = game_state
        .ai_game
        .clone()
        .filter(|mark| mark.human == host_player && dev_controller.is_none());
    let sole_member = dev_controller.or(ai_game.as_ref().map(|mark| mark.human));
    let players = game_state
        .players
        .iter()
        .filter(|player| sole_member.is_none_or(|member| player.player_id == member))
        .filter(|player| game_state.tutorial.is_none() || player.player_id == host_player)
        .map(|p| (p.player_id, p.nickname.clone(), state_str != "lobby"))
        .collect();

    Room {
        code: room_code.to_string(),
        // Titles and passwords live only in memory: a rehydrated room has already left the
        // lobby (it has a snapshot), so neither is still in play for joining.
        name: format!("방 {room_code}"),
        password_hash: None,
        host_player,
        players,
        state: RoomState::from_db_str(state_str),
        game_state: Some(game_state),
        setup,
        seed,
        revision,
        connected: HashSet::new(),
        paused: false,
        dev_human_player: sole_member,
        dev_bot_action_counts: HashMap::new(),
        dev_bot_action_round: 0,
        ai_level: ai_game.as_ref().and_then(|mark| mark.level.clone()),
        ai_teacher: ai_game.and_then(|mark| mark.teacher),
        ai_stalled: None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use gaia_engine::game_state::{AiGameMark, FactionId, GameState};
    use gaia_engine::Randomizer;

    /// A game of seat 7 against three virtual seats, as saved (through JSON) and loaded again.
    fn saved_game(mark: Option<AiGameMark>) -> GameState {
        let setup = Randomizer::generate_setup("restart-test")
            .unwrap_or_else(|error| panic!("setup should be generated: {error}"));
        let mut state = crate::services::dev_game::build_game_state_with_factions(
            "AIROOM",
            "restart-test",
            7,
            &[8, 9, 10],
            &setup,
            FactionId::Terrans,
            vec![FactionId::Xenos, FactionId::Taklons, FactionId::HadschHallas],
            false,
        )
        .unwrap_or_else(|error| panic!("game should be built: {error}"));
        state.ai_game = mark;
        let saved = serde_json::to_string(&state)
            .unwrap_or_else(|error| panic!("the game is saved: {error}"));
        // A game without the mark has no such key at all, like one saved before it existed.
        assert_eq!(saved.contains("\"ai_game\""), state.ai_game.is_some());
        serde_json::from_str(&saved).unwrap_or_else(|error| panic!("the game is loaded: {error}"))
    }

    fn loaded(host: u8, game: GameState) -> Room {
        rehydrated_room("AIROOM", host, "in_game", "restart-test".into(), 12, None, game)
    }

    #[test]
    fn an_ai_game_keeps_its_ai_seats_after_a_restart() {
        let mark = AiGameMark {
            human: 7,
            level: Some("hard".into()),
            teacher: Some("v3".into()),
        };
        let mut room = loaded(7, saved_game(Some(mark.clone())));

        // The human seat is the room's only member, with the level and teacher of the game.
        assert_eq!(room.dev_human_player, Some(7));
        assert_eq!(room.ai_level.as_deref(), Some("hard"));
        assert_eq!(room.ai_teacher.as_deref(), Some("v3"));
        assert_eq!(
            room.players.iter().map(|(id, _, _)| *id).collect::<Vec<_>>(),
            vec![7]
        );
        assert!(crate::ai::is_ai_room(&room));
        // So the room runs as soon as that seat is back, not waiting for the AI seats.
        room.state = RoomState::InGame;
        room.mark_connected(7);
        assert!(!room.paused);

        // A mark that does not name the room's host is not trusted.
        let room = loaded(8, saved_game(Some(mark)));
        assert_eq!(room.dev_human_player, None);
        assert_eq!(room.players.len(), 4);
    }

    #[test]
    fn a_game_saved_without_the_mark_is_loaded_as_an_ordinary_room() {
        let room = loaded(7, saved_game(None));
        assert_eq!(room.dev_human_player, None);
        assert_eq!(room.ai_level, None);
        assert_eq!(room.ai_teacher, None);
        assert_eq!(room.players.len(), 4);
        assert!(!crate::ai::is_ai_room(&room));
    }
}
