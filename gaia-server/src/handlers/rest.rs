use axum::{
    extract::{Path, State},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};

use gaia_engine::{
    game_state::{FactionId, GameState, PlayerId},
    MapEngine, SetupMode,
};

use crate::{
    coordinator,
    error::{ServerError, ServerResult},
    messages::LobbyPlayer,
    services::{
        dev_game::build_dev_game_state, game_setup::GameSetupService, reconnect::ReconnectService,
    },
    state::AppState,
};

// ── Request / Response types ──────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct CreateRoomRequest {
    pub nickname: String,
    pub seed: Option<String>,
    #[serde(default)]
    pub setup_mode: SetupMode,
    /// Room title for the lobby list; blank falls back to the host's nickname.
    pub name: Option<String>,
    /// Optional join password. Absent or blank leaves the room open to anyone with the code.
    pub password: Option<String>,
}

#[derive(Serialize)]
pub struct CreateRoomResponse {
    pub room_code: String,
    pub player_id: PlayerId,
    pub session_token: String,
    pub game_setup: serde_json::Value,
    pub players: Vec<LobbyPlayer>,
    pub host_player_id: PlayerId,
}

#[derive(Deserialize)]
pub struct JoinRoomRequest {
    pub nickname: String,
    pub session_token: Option<String>,
    /// Required only for a room created with a password.
    pub password: Option<String>,
}

#[derive(Serialize)]
pub struct JoinRoomResponse {
    pub player_id: PlayerId,
    pub session_token: String,
    pub room_code: String,
    pub game_setup: serde_json::Value,
    pub players: Vec<LobbyPlayer>,
    pub host_player_id: PlayerId,
    /// Present once the game has started — lets a reconnecting client resync
    /// immediately over REST rather than waiting for the first WS broadcast.
    pub game_state: Option<serde_json::Value>,
}

#[derive(Deserialize)]
pub struct RegenerateRequest {
    pub session_token: String,
    pub seed: Option<String>,
}

#[derive(Deserialize)]
pub struct CreateDevGameRequest {
    #[serde(default)]
    pub full_setup: bool,
    pub nickname: Option<String>,
    pub setup_mode: Option<SetupMode>,
    pub faction: Option<FactionId>,
    pub seed: Option<String>,
    /// Three AI opponents play their own seats (requires the AI pool, see `crate::ai`)
    /// instead of the controller manually playing all four seats.
    #[serde(default)]
    pub ai_opponents: bool,
    /// AI difficulty for `ai_opponents` games: `easy`, `normal` or `hard` (default: server's).
    pub ai_level: Option<String>,
}

#[derive(Serialize)]
pub struct CreateDevGameResponse {
    pub room_code: String,
    pub player_id: PlayerId,
    pub session_token: String,
    pub game_setup: serde_json::Value,
    pub game_state: GameState,
    pub players: Vec<LobbyPlayer>,
    pub host_player_id: PlayerId,
}

// ── Handlers ──────────────────────────────────────────────────────────────────

pub async fn create_room(
    State(app): State<AppState>,
    Json(req): Json<CreateRoomRequest>,
) -> ServerResult<(StatusCode, Json<CreateRoomResponse>)> {
    let (code, player_id, setup) = GameSetupService::create_room(
        &app,
        &req.nickname,
        req.seed,
        req.setup_mode,
        req.name.as_deref(),
        req.password.as_deref(),
    )
    .await?;

    let session_token = app.sessions.create_session(player_id, &code).await?;

    // Ensure the event bus channel exists for this room
    app.event_bus.get_or_create(&code).await;

    let (players, host_player_id) = {
        let rooms = app.rooms.read().await;
        let room = rooms
            .get_room(&code)
            .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
        (lobby_players(room), room.host_player)
    };

    Ok((
        StatusCode::CREATED,
        Json(CreateRoomResponse {
            room_code: code,
            player_id,
            session_token,
            game_setup: serde_json::to_value(&setup).unwrap_or(serde_json::Value::Null),
            players,
            host_player_id,
        }),
    ))
}

/// Local UI-development shortcut: one authenticated controller manually plays all four seats.
/// It skips invitations, bidding, and faction selection, then follows the normal placement,
/// booster, action, and pending-decision order without automated opponents.
/// Resource spending, invalid-action rejection, and snapshots use the normal live game paths.
/// Release builds expose it only when the operator explicitly opts in with `GAIA_DEV_MODE=1`.
pub async fn create_dev_game(
    State(app): State<AppState>,
    Json(req): Json<CreateDevGameRequest>,
) -> ServerResult<(StatusCode, Json<CreateDevGameResponse>)> {
    let explicitly_enabled = std::env::var("GAIA_DEV_MODE").is_ok_and(|value| value == "1");
    // Games against AI seats are a player feature wherever the AI pool is configured; the
    // manual four-seat controller stays a DEV-only tool.
    let ai_game = req.ai_opponents && !req.full_setup && app.ai.is_some();
    if !cfg!(debug_assertions) && !explicitly_enabled && !ai_game {
        return Err(ServerError::RoomNotFound(
            "dev game endpoint disabled".into(),
        ));
    }

    let seed = req.seed.unwrap_or_else(|| {
        if req.full_setup || req.ai_opponents {
            uuid::Uuid::new_v4().to_string()
        } else {
            "gaia-ui-dev".to_string()
        }
    });
    let nickname = req.nickname.as_deref().unwrap_or("DEV");
    // AI games start with the setup auction (the human bids against the AI seats, see
    // crate::ai_bidding); `setup_mode: Sequential` keeps the earlier random faction assignment.
    let ai_bidding = req.ai_opponents
        && !req.full_setup
        && matches!(
            req.setup_mode.unwrap_or(SetupMode::Bidding),
            SetupMode::Bidding
        );
    let setup_mode = if req.full_setup {
        req.setup_mode.unwrap_or(SetupMode::Bidding)
    } else if ai_bidding {
        SetupMode::Bidding
    } else {
        SetupMode::Sequential
    };
    let (faction, ai_bot_factions) = if req.ai_opponents && !ai_bidding {
        let (human, bots) = crate::services::dev_game::ai_game_factions(&seed, req.faction);
        (human, Some(bots))
    } else {
        (req.faction.unwrap_or(FactionId::Terrans), None)
    };
    let (code, player_id, setup) =
        GameSetupService::create_room(&app, nickname, Some(seed.clone()), setup_mode, None, None)
            .await?;
    let bot_player_ids = {
        let mut rooms = app.rooms.write().await;
        rooms.alloc_virtual_player_ids(3)
    };
    let mut game_state = if req.full_setup {
        let mut players = vec![(player_id, nickname.to_string())];
        players.extend(
            bot_player_ids
                .iter()
                .enumerate()
                .map(|(index, id)| (*id, format!("DEV {}", index + 2))),
        );
        MapEngine::init_game_state(&code, &seed, &players, &setup)
    } else if ai_bidding {
        let mut players = vec![(player_id, nickname.to_string())];
        players.extend(
            bot_player_ids
                .iter()
                .enumerate()
                .map(|(index, id)| (*id, format!("AI · {}", index + 1))),
        );
        MapEngine::init_game_state_with_bidding(&code, &seed, &players, &setup)
            .map_err(|error| ServerError::Internal(format!("AI bidding setup: {error}")))?
    } else if let Some(bot_factions) = ai_bot_factions {
        crate::services::dev_game::build_game_state_with_factions(
            &code,
            &seed,
            player_id,
            &bot_player_ids,
            &setup,
            faction,
            bot_factions,
        )?
    } else {
        build_dev_game_state(&code, &seed, player_id, &bot_player_ids, &setup, faction)?
    };

    let ai_opponents = req.ai_opponents && !req.full_setup;
    if ai_opponents && app.ai.is_none() {
        return Err(ServerError::Internal(
            "AI opponents are not configured on this server".into(),
        ));
    }
    if let Some(level) = &req.ai_level {
        if !crate::ai::LEVELS.contains(&level.as_str()) {
            return Err(ServerError::InvalidAction(format!(
                "unknown AI level {level}"
            )));
        }
    }
    if ai_opponents {
        for player in &mut game_state.players {
            player.nickname = player.nickname.replace("BOT ·", "AI ·");
        }
    } else {
        game_state.dev_controller = Some(player_id);
        for player in &mut game_state.players {
            player.nickname = player.nickname.replace("BOT ·", "DEV ·");
        }
    }

    let (players, host_player_id) = {
        let mut rooms = app.rooms.write().await;
        let room = rooms
            .get_room_mut(&code)
            .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
        room.state = if req.full_setup {
            crate::room::manager::RoomState::Lobby
        } else {
            crate::room::manager::RoomState::FactionSelection
        };
        room.game_state = Some(game_state.clone());
        room.dev_human_player = Some(player_id);
        room.ai_level = if ai_opponents {
            req.ai_level.clone()
        } else {
            None
        };
        for (_, _, ready) in &mut room.players {
            *ready = !req.full_setup;
        }
        (lobby_players(room), room.host_player)
    };

    let session_token = app.sessions.create_session(player_id, &code).await?;
    app.event_bus.get_or_create(&code).await;
    if ai_opponents {
        // An AI seat may place the first starting structure.
        crate::ai::spawn_driver(app.clone(), code.clone());
    }

    Ok((
        StatusCode::CREATED,
        Json(CreateDevGameResponse {
            room_code: code,
            player_id,
            session_token,
            game_setup: serde_json::to_value(&setup).unwrap_or(serde_json::Value::Null),
            game_state,
            players,
            host_player_id,
        }),
    ))
}

pub async fn join_room(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<JoinRoomRequest>,
) -> ServerResult<Json<JoinRoomResponse>> {
    // Reconnect path. If a client explicitly supplies a session token, it
    // must validate for this requested room; otherwise falling through would
    // silently create an extra seat for a mistyped/expired token.
    if let Some(token) = &req.session_token {
        let (player_id, room_code) = ReconnectService::validate_session(&app, token).await?;
        if room_code != code {
            return Err(ServerError::InvalidSession);
        }
        app.ensure_room_loaded(&room_code).await?;
        let (game_setup, game_state, players, host_player_id) = {
            let rooms = app.rooms.read().await;
            let room = rooms
                .get_room(&room_code)
                .ok_or_else(|| ServerError::RoomNotFound(room_code.clone()))?;
            (
                room.setup
                    .as_ref()
                    .and_then(|setup| serde_json::to_value(setup).ok())
                    .unwrap_or(serde_json::Value::Null),
                room.game_state.as_ref().map(|gs| gs.serialize()),
                lobby_players(room),
                room.host_player,
            )
        };
        return Ok(Json(JoinRoomResponse {
            player_id,
            session_token: token.clone(),
            room_code,
            game_setup,
            players,
            host_player_id,
            game_state,
        }));
    }

    let player_id = {
        let mut rooms = app.rooms.write().await;
        rooms.join_room(&code, &req.nickname, req.password.as_deref())?
    };

    let session_token = app.sessions.create_session(player_id, &code).await?;

    let (game_setup, players, host_player_id) = {
        let rooms = app.rooms.read().await;
        let room = rooms
            .get_room(&code)
            .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
        (
            room.setup
                .as_ref()
                .and_then(|setup| serde_json::to_value(setup).ok())
                .unwrap_or(serde_json::Value::Null),
            lobby_players(room),
            room.host_player,
        )
    };

    Ok(Json(JoinRoomResponse {
        player_id,
        session_token,
        room_code: code,
        game_setup,
        players,
        host_player_id,
        game_state: None,
    }))
}

pub async fn get_room(
    State(app): State<AppState>,
    Path(code): Path<String>,
) -> ServerResult<Json<serde_json::Value>> {
    app.ensure_room_loaded(&code).await?;
    let rooms = app.rooms.read().await;
    let room = rooms
        .get_room(&code)
        .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;

    Ok(Json(serde_json::json!({
        "code":         room.code,
        "player_count": room.display_players().len(),
        "state":        format!("{:?}", room.state),
        "host_player_id": room.host_player,
        "players":      room.players.iter()
            .map(|(id, nick, ready)| serde_json::json!({ "id": id, "player_id": id, "nickname": nick, "ready": ready }))
            .collect::<Vec<_>>(),
    })))
}

/// Read-only preview of the board/tiles the current `room.setup`/`room.seed` would produce if the
/// game started right now — lets the waiting room show the randomized layout (and let the host
/// reroll via the existing `regenerate_setup` seed controls) before anyone readies up. Reuses
/// `MapEngine::init_game_state` directly rather than a separate preview-only builder, since that's
/// the one real code path that actually assembles Deep Space/Interspace positions; the 4
/// placeholder players are fine because the board/tile layout never depends on real player
/// identity or count (this project is always exactly 4-player) — this also means the preview
/// works even before all 4 seats are filled. Pure computation: never touches `room.state`/
/// `room.game_state`, so the room stays in `Lobby` regardless of how often this is called.
const PREVIEW_PLAYERS: [(PlayerId, &str); 4] = [(0, ""), (1, ""), (2, ""), (3, "")];

pub async fn preview_board(
    State(app): State<AppState>,
    Path(code): Path<String>,
) -> ServerResult<Json<serde_json::Value>> {
    app.ensure_room_loaded(&code).await?;
    let (room_code, seed, setup) = {
        let rooms = app.rooms.read().await;
        let room = rooms
            .get_room(&code)
            .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
        let setup = room
            .setup
            .clone()
            .ok_or_else(|| ServerError::Internal("setup missing".into()))?;
        (room.code.clone(), room.seed.clone(), setup)
    };

    let players: Vec<(PlayerId, String)> = PREVIEW_PLAYERS
        .iter()
        .map(|(id, nickname)| (*id, (*nickname).to_string()))
        .collect();
    let state = MapEngine::init_game_state(&room_code, &seed, &players, &setup);

    Ok(Json(serde_json::json!({
        "seed": seed,
        "board": state.board,
        "round_tiles": state.round_tiles,
        "final_scoring_tiles": state.final_scoring_tiles,
        "spaceship_boards": state.spaceship_boards,
        "research_board": state.research_board,
    })))
}

pub async fn regenerate_setup(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<RegenerateRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player_id, session_room_code) =
        ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room_code != code {
        return Err(ServerError::InvalidSession);
    }

    // No client envelope on the REST path — mint a provisional command_id
    // and use the room's current revision as "expected" (same rationale as
    // `coordinator::apply_command_auto_revision`, but this call also needs
    // the resulting `GameSetup` value, which `CommandOutcome` doesn't carry,
    // so it's inlined here as a single-attempt call instead of the retrying
    // helper).
    let expected_revision = coordinator::current_revision(&app, &code).await?;
    let command_id = coordinator::fresh_command_id();
    GameSetupService::regenerate_setup(
        &app,
        &code,
        player_id,
        req.seed,
        command_id,
        expected_revision,
    )
    .await
    .map_err(coordinator::command_error_to_server_error)?;

    let setup = {
        let rooms = app.rooms.read().await;
        rooms
            .get_room(&code)
            .and_then(|r| r.setup.clone())
            .ok_or_else(|| ServerError::Internal("setup missing after regenerate".into()))?
    };

    Ok(Json(
        serde_json::to_value(&setup).unwrap_or(serde_json::Value::Null),
    ))
}

pub async fn health() -> StatusCode {
    StatusCode::OK
}

/// Public room browser — every room still open to `join_room` right now. Lobby-only
/// rooms aren't durably persisted (see `AppState::ensure_room_loaded`), so this reads
/// straight off the in-memory `RoomManager` rather than the DB.
pub async fn list_rooms(
    State(app): State<AppState>,
) -> Json<Vec<crate::room::manager::RoomSummary>> {
    let rooms = app.rooms.read().await;
    Json(rooms.list_rooms())
}

fn lobby_players(room: &crate::room::manager::Room) -> Vec<LobbyPlayer> {
    room.display_players()
        .iter()
        .map(|(player_id, nickname, ready)| LobbyPlayer {
            player_id: *player_id,
            nickname: nickname.clone(),
            ready: *ready,
        })
        .collect()
}
