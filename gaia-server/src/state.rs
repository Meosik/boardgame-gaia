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
        let Some((host_player, state_str, seed, _row_revision, setup_json, ai_options)) =
            repo.load_room_row(room_code).await?
        else {
            return Ok(());
        };
        let setup = serde_json::from_value(setup_json).ok();

        let Some((revision, mut game_state)) = repo.load_latest_snapshot(room_code).await? else {
            return Ok(());
        };

        // A game against AI seats saved before `GameState::ai_game` existed has no mark, so its
        // AI seats would not play on. The owner can name such a room in `GAIA_AI_RESUME_ROOMS`;
        // the mark is then written here and saved with the game's next snapshots.
        if let Some(pool) = &self.ai {
            let unmarked = game_state.ai_game.is_none()
                && game_state.dev_controller.is_none()
                && game_state.tutorial.is_none();
            let named = std::env::var("GAIA_AI_RESUME_ROOMS")
                .ok()
                .and_then(|rooms| resumed_ai_mark(&rooms, room_code, host_player));
            if let (true, Some(mut mark)) = (unmarked, named) {
                mark.teacher = pool.pin_teacher().await;
                log::info!(
                    "AI room {room_code}: resumed from GAIA_AI_RESUME_ROOMS (human seat {}, level {}, teacher {})",
                    mark.human,
                    mark.level.as_deref().unwrap_or("server default"),
                    mark.teacher.as_deref().unwrap_or("built into the image")
                );
                game_state.ai_game = Some(mark);
            }
        }

        let room = rehydrated_room(
            room_code,
            host_player,
            &state_str,
            seed,
            revision as u64,
            setup,
            game_state,
            ai_options,
        );

        let mut rooms = self.rooms.write().await;
        rooms.insert_if_absent(room_code.to_string(), room);
        Ok(())
    }
}

/// The AI-game mark for a room the owner names in `GAIA_AI_RESUME_ROOMS`: a comma-separated
/// list of `CODE` or `CODE:level` (`crate::ai::LEVELS`; no level = the server's default). It
/// is for games against AI seats saved before `GameState::ai_game` existed. The human seat is
/// the room's host, as in every AI game; an entry with an unknown level is ignored.
fn resumed_ai_mark(
    rooms: &str,
    room_code: &str,
    host_player: gaia_engine::game_state::PlayerId,
) -> Option<gaia_engine::game_state::AiGameMark> {
    rooms.split(',').find_map(|entry| {
        let (code, level) = match entry.trim().split_once(':') {
            Some((code, level)) => (code.trim(), Some(level.trim())),
            None => (entry.trim(), None),
        };
        if code != room_code {
            return None;
        }
        let level = level.filter(|level| !level.is_empty());
        if level.is_some_and(|level| !crate::ai::LEVELS.contains(&level)) {
            log::warn!("GAIA_AI_RESUME_ROOMS: unknown AI level in {entry:?}, room not resumed");
            return None;
        }
        Some(gaia_engine::game_state::AiGameMark {
            human: host_player,
            level: level.map(str::to_string),
            teacher: None,
        })
    })
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
///
/// `ai_options` is what the room's row says the member chose for an AI game (the teacher
/// plays every seat, the review of AI turns); it counts only for a game with the AI mark.
#[allow(clippy::too_many_arguments)]
fn rehydrated_room(
    room_code: &str,
    host_player: gaia_engine::game_state::PlayerId,
    state_str: &str,
    seed: String,
    revision: u64,
    setup: Option<gaia_engine::GameSetup>,
    game_state: gaia_engine::game_state::GameState,
    ai_options: crate::room::manager::AiOptions,
) -> Room {
    let dev_controller = game_state
        .dev_controller
        .filter(|controller| *controller == host_player);
    let ai_game = game_state
        .ai_game
        .clone()
        .filter(|mark| mark.human == host_player && dev_controller.is_none());
    let sole_member = dev_controller.or(ai_game.as_ref().map(|mark| mark.human));
    let ai_options = ai_game.as_ref().map(|_| ai_options).unwrap_or_default();
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
        // From the room's row: the review switch and "the teacher plays every seat" stay as
        // the member left them. The turn in progress and a wait at a finished turn do not
        // come back; the AI seats wait again at the end of their next turn.
        ai_review: ai_options.review,
        ai_all_seats: ai_options.all_seats,
        ai_turn: None,
        ai_hold: None,
        ai_rejected: None,
        setup_choices: Vec::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::room::manager::AiOptions;
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
        loaded_with(host, game, AiOptions::default())
    }

    fn loaded_with(host: u8, game: GameState, options: AiOptions) -> Room {
        rehydrated_room("AIROOM", host, "in_game", "restart-test".into(), 12, None, game, options)
    }

    #[test]
    fn an_ai_game_keeps_what_its_member_chose_after_a_restart() {
        let mark = AiGameMark {
            human: 7,
            level: Some("hard".into()),
            teacher: None,
        };
        let chosen = AiOptions {
            all_seats: true,
            review: true,
        };
        let room = loaded_with(7, saved_game(Some(mark.clone())), chosen);
        // The teacher still plays every seat and the AI turns are still looked at; the member
        // is still the room's only member.
        assert!(room.ai_all_seats);
        assert!(room.ai_review);
        assert_eq!(room.ai_options(), chosen);
        assert_eq!(room.dev_human_player, Some(7));
        assert_eq!(room.players.len(), 1);

        // A row written before the column existed ('{}') and one with a single key.
        let old: AiOptions = serde_json::from_str("{}").unwrap();
        assert_eq!(old, AiOptions::default());
        let room = loaded_with(7, saved_game(Some(mark.clone())), old);
        assert!(!room.ai_all_seats && !room.ai_review);
        let review_only: AiOptions = serde_json::from_str(r#"{"review":true}"#).unwrap();
        let room = loaded_with(7, saved_game(Some(mark.clone())), review_only);
        assert!(!room.ai_all_seats && room.ai_review);

        // The options belong to an AI game: without the mark, or with a mark that does not
        // name the room's host, the room is an ordinary one.
        let room = loaded_with(7, saved_game(None), chosen);
        assert!(!room.ai_all_seats && !room.ai_review);
        let room = loaded_with(8, saved_game(Some(mark)), chosen);
        assert!(!room.ai_all_seats && !room.ai_review);
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

    #[test]
    fn a_room_the_owner_names_gets_the_ai_game_mark() {
        let mark = resumed_ai_mark("OTHER, AIROOM:hard", "AIROOM", 7);
        assert_eq!(
            mark,
            Some(AiGameMark {
                human: 7,
                level: Some("hard".into()),
                teacher: None,
            })
        );
        // No level = the server's default; other rooms, unknown levels and an empty list: none.
        assert_eq!(
            resumed_ai_mark("AIROOM", "AIROOM", 7),
            Some(AiGameMark {
                human: 7,
                level: None,
                teacher: None,
            })
        );
        assert_eq!(resumed_ai_mark("OTHER:hard", "AIROOM", 7), None);
        assert_eq!(resumed_ai_mark("AIROOM:godlike", "AIROOM", 7), None);
        assert_eq!(resumed_ai_mark("", "AIROOM", 7), None);

        // A game saved without the mark, given it, loads like one created with it.
        let mut game = saved_game(None);
        game.ai_game = mark;
        let room = loaded(7, game);
        assert_eq!(room.dev_human_player, Some(7));
        assert_eq!(room.ai_level.as_deref(), Some("hard"));
        assert_eq!(room.players.len(), 1);
        assert!(crate::ai::is_ai_room(&room));
    }
}
