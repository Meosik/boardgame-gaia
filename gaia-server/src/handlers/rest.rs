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
    /// The player looks at every AI turn of an `ai_opponents` game: the AI seats wait after
    /// each of their turns until the player continues (`crate::ai`, `Room::ai_review`).
    #[serde(default)]
    pub ai_review: bool,
    /// The three AI seats' factions for an `ai_opponents` game (default: drawn from the seed).
    /// Naming these or `faction` skips the setup auction, see `dev_game::ai_game_setup`.
    #[serde(default)]
    pub ai_factions: Option<Vec<FactionId>>,
    /// The human's place in the turn order (1 = first, the default, to 4) of an `ai_opponents`
    /// game with fixed factions; the AI seats keep their order. The setup auction decides the
    /// order itself, so the two do not go together.
    #[serde(default)]
    pub human_seat: Option<u8>,
    /// The teacher plays every seat of an `ai_opponents` game, the creator's own too: the
    /// creator has no seat to play and looks at the AI turns (`Room::ai_all_seats`, with
    /// `ai_review` they wait after each one). `faction` and `human_seat` then only name the
    /// fourth faction and its place. Needs fixed factions, like `human_seat`: the setup
    /// auction is not played this way.
    #[serde(default)]
    pub ai_all_seats: bool,
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

/// Creates the fixed round-one teaching scenario with three scripted seats.
pub async fn create_tutorial_game(
    State(app): State<AppState>,
) -> ServerResult<(StatusCode, Json<CreateDevGameResponse>)> {
    let (code, player_id, setup, game_state) = {
        let mut rooms = app.rooms.write().await;
        let (code, player_id) = rooms.create_room(
            "나",
            Some(gaia_engine::tutorial::SEED.into()),
            SetupMode::Sequential,
            None,
            None,
        )?;
        let bots = rooms.alloc_virtual_player_ids(3);
        let game_state =
            gaia_engine::tutorial::initial_state(&code, [player_id, bots[0], bots[1], bots[2]])
                .map_err(|error| ServerError::Internal(error.to_string()))?;
        let room = rooms
            .get_room_mut(&code)
            .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
        let setup = room
            .setup
            .clone()
            .ok_or_else(|| ServerError::Internal("tutorial setup missing".into()))?;
        // Mark it before releasing the lock so it never appears as an open lobby room.
        room.state = crate::room::manager::RoomState::InGame;
        room.game_state = Some(game_state.clone());
        (code, player_id, setup, game_state)
    };
    crate::repository::GameRepository::new(app.db.clone())
        .save_room(&code, gaia_engine::tutorial::SEED, player_id, &setup)
        .await?;
    crate::coordinator::apply_server_transition(&app, &code, |room| {
        room.state = crate::room::manager::RoomState::InGame;
        room.game_state = Some(game_state.clone());
        Ok(())
    })
    .await
    .map_err(crate::coordinator::command_error_to_server_error)?;
    let session_token = app.sessions.create_session(player_id, &code).await?;
    app.event_bus.get_or_create(&code).await;
    let players = {
        let rooms = app.rooms.read().await;
        lobby_players(
            rooms
                .get_room(&code)
                .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?,
        )
    };
    Ok((
        StatusCode::CREATED,
        Json(CreateDevGameResponse {
            room_code: code,
            player_id,
            session_token,
            game_setup: serde_json::to_value(&setup)?,
            game_state,
            players,
            host_player_id: player_id,
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
    // crate::ai_bidding); `setup_mode: Sequential` or a named faction skips it and seats fixed
    // factions (the earlier seeded assignment unless the request names them).
    let ai_game_request = req.ai_opponents && !req.full_setup;
    if req.ai_factions.is_some() && !ai_game_request {
        return Err(ServerError::InvalidAction(
            "ai_factions needs ai_opponents without full_setup".into(),
        ));
    }
    let ai_fixed_factions = if ai_game_request {
        crate::services::dev_game::ai_game_setup(
            &seed,
            req.setup_mode,
            req.faction,
            req.ai_factions.as_deref(),
        )
        .map_err(ServerError::InvalidAction)?
    } else {
        None
    };
    let ai_bidding = ai_game_request && ai_fixed_factions.is_none();
    if req.human_seat.is_some() && ai_fixed_factions.is_none() {
        return Err(ServerError::InvalidAction(
            "human_seat needs an AI game with fixed factions (setup_mode sequential)".into(),
        ));
    }
    if req.ai_all_seats && ai_fixed_factions.is_none() {
        return Err(ServerError::InvalidAction(
            "ai_all_seats needs an AI game with fixed factions (setup_mode sequential)".into(),
        ));
    }
    if req.human_seat.is_some_and(|seat| !(1..=4).contains(&seat)) {
        return Err(ServerError::InvalidAction(
            "human_seat must be 1 to 4".into(),
        ));
    }
    let setup_mode = if req.full_setup {
        req.setup_mode.unwrap_or(SetupMode::Bidding)
    } else if ai_bidding {
        SetupMode::Bidding
    } else {
        SetupMode::Sequential
    };
    let (faction, ai_bot_factions) = match ai_fixed_factions {
        Some((human, bots)) => (human, Some(bots)),
        None => (req.faction.unwrap_or(FactionId::Terrans), None),
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
        let mut state = crate::services::dev_game::build_game_state_with_factions(
            &code,
            &seed,
            player_id,
            &bot_player_ids,
            &setup,
            faction,
            bot_factions,
            false,
        )?;
        if let Some(seat) = req.human_seat {
            crate::services::dev_game::seat_human_at(&mut state, player_id, seat)?;
        }
        state
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

    // The teacher version stays with the game until it ends (`crate::ai`). The first game of a
    // newly promoted version waits here for that version's worker to start once.
    let ai_teacher = match &app.ai {
        Some(pool) if ai_opponents => pool.pin_teacher().await,
        _ => None,
    };
    if ai_opponents {
        log::info!(
            "AI room {code}: teacher {}",
            ai_teacher.as_deref().unwrap_or("built into the image")
        );
        // Saved with every snapshot of the game: a room loaded again after a server restart
        // takes its human seat, level and teacher from it (`AppState::ensure_room_loaded`).
        game_state.ai_game = Some(gaia_engine::game_state::AiGameMark {
            human: player_id,
            level: req.ai_level.clone(),
            teacher: ai_teacher.clone(),
        });
    }

    let (players, host_player_id, ai_options) = {
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
        room.ai_teacher = ai_teacher;
        room.ai_review = ai_opponents && req.ai_review;
        room.ai_all_seats = ai_opponents && req.ai_all_seats;
        for (_, _, ready) in &mut room.players {
            *ready = !req.full_setup;
        }
        (lobby_players(room), room.host_player, room.ai_options())
    };
    if ai_opponents {
        // In the room's row, so a room loaded again after a server restart still has the
        // teacher on every seat and the review switch (`AppState::ensure_room_loaded`).
        crate::repository::GameRepository::new(app.db.clone())
            .save_ai_options(&code, ai_options)
            .await?;
        if ai_options.all_seats {
            log::info!("AI room {code}: the teacher plays every seat (member {player_id})");
        }
    }

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
        // The other seats are played by the teacher workers: the game screen offers hints.
        "ai_game":      app.ai.is_some() && crate::ai::is_ai_room(room),
        "players":      room.players.iter()
            .map(|(id, nick, ready)| serde_json::json!({ "id": id, "player_id": id, "nickname": nick, "ready": ready }))
            .collect::<Vec<_>>(),
    })))
}

#[derive(Deserialize)]
pub struct AiHintRequest {
    pub session_token: String,
    /// The room revision the player is looking at; the answer is only for that position.
    pub expected_revision: u64,
}

/// What the teacher would play for the human seat of an AI game right now (`crate::ai::hint`).
/// Read-only: nothing is applied and the revision does not change. The reply repeats the
/// revision it belongs to, so the client can drop an answer for a position it has left.
pub async fn ai_hint(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiHintRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    use crate::ai::HintError;
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    match crate::ai::hint(&app, &code, player, req.expected_revision).await {
        Ok(decision) => Ok(Json(serde_json::json!({
            "revision": req.expected_revision,
            "decision": decision,
        }))),
        Err(HintError::NotAnAiGame) => Err(ServerError::InvalidAction(
            "teacher hints are for the human seat of an AI game".into(),
        )),
        Err(HintError::NotYourDecision) => Err(ServerError::NotYourTurn),
        Err(HintError::Stale) => Err(ServerError::InvalidAction(
            "the position changed while the teacher was thinking".into(),
        )),
        Err(HintError::NoAnswer) => Err(ServerError::Internal(
            "the teacher gave no answer".into(),
        )),
    }
}

#[derive(Deserialize)]
pub struct AiRetryRequest {
    pub session_token: String,
}

/// Lets the AI seats of an AI game try again after they stopped because the teacher gave no
/// usable move (`crate::ai::retry`). Asked by the game's human seat; the move, if the teacher
/// has one now, arrives as an ordinary snapshot.
pub async fn ai_retry(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiRetryRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    crate::ai::retry(&app, &code, player).await.map_err(|_| {
        ServerError::InvalidAction("only the human seat of an AI game restarts its AI seats".into())
    })?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

/// The player has looked at the AI turn the AI seats wait at and lets them play on
/// (`crate::ai::continue_after_hold`). Asked by the game's human seat; harmless when nothing
/// waits.
pub async fn ai_continue(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiRetryRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    crate::ai::continue_after_hold(&app, &code, player)
        .await
        .map_err(|_| {
            ServerError::InvalidAction("only the human seat of an AI game continues its AI seats".into())
        })?;
    Ok(Json(serde_json::json!({ "ok": true })))
}

/// The player rejects the finished AI turn the AI seats wait at (`crate::ai::reject_turn`): the
/// room goes back to that turn's first position and the seat plays it again without the move
/// that ended it. Asked by the game's human seat for the revision it is looking at; the
/// restored position and the new move arrive as ordinary snapshots.
///
/// With `turn_start_revision` an earlier AI turn is rejected instead (one of `ai_turns`): the
/// room goes back to that turn's first position and everything played since is gone.
pub async fn ai_reject(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiRejectRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    use crate::ai::RejectError;
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    let rejected = crate::ai::reject_turn(
        &app,
        &code,
        player,
        req.expected_revision,
        req.turn_start_revision,
    )
    .await;
    match rejected {
        Ok(()) => Ok(Json(serde_json::json!({ "ok": true }))),
        Err(RejectError::NotAnAiGame) => Err(ServerError::InvalidAction(
            "only the human seat of an AI game rejects an AI turn".into(),
        )),
        Err(RejectError::NothingHeld) => Err(ServerError::InvalidAction(
            "no finished AI turn waits at this position".into(),
        )),
        Err(RejectError::Server(error)) => Err(ServerError::Internal(error)),
    }
}

#[derive(Deserialize)]
pub struct AiRejectRequest {
    pub session_token: String,
    /// The room revision the player is looking at.
    pub expected_revision: u64,
    /// The first revision of an earlier AI turn to reject (`turn.start_revision` of an entry
    /// of `ai_turns`); absent = the turn the AI seats wait at.
    #[serde(default)]
    pub turn_start_revision: Option<u64>,
}

/// The finished AI turns of an AI game that can still be rejected, oldest first
/// (`crate::ai::past_turns`), for the game's human seat. Kept in memory only: the turns played
/// before the last server restart are not listed.
pub async fn ai_turns(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiRetryRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    crate::ai::past_turns(&app, &code, player)
        .await
        .map(Json)
        .map_err(|_| {
            ServerError::InvalidAction("only the human seat of an AI game lists its AI turns".into())
        })
}

/// The human seat of an AI game takes back its latest setup choice — a starting structure or
/// the starting booster (`crate::ai::redo_setup_choice`): the room goes back to the position
/// that choice was made at, and what the AI seats did after it is played again. Asked for the
/// revision the player is looking at; the restored position arrives as an ordinary snapshot.
pub async fn setup_redo(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiHintRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    use crate::ai::SetupRedoError;
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    match crate::ai::redo_setup_choice(&app, &code, player, req.expected_revision).await {
        Ok(()) => Ok(Json(serde_json::json!({ "ok": true }))),
        Err(SetupRedoError::NotAnAiGame) => Err(ServerError::InvalidAction(
            "only the human seat of an AI game takes back a setup choice".into(),
        )),
        Err(SetupRedoError::NothingToRedo) => Err(ServerError::InvalidAction(
            "no setup choice can be taken back at this position".into(),
        )),
        Err(SetupRedoError::Server(error)) => Err(ServerError::Internal(error)),
    }
}

#[derive(Deserialize)]
pub struct AiReviewRequest {
    pub session_token: String,
    /// `true` = the AI seats wait after each of their turns until the player continues.
    pub enabled: bool,
}

/// Turns the review of AI turns on or off for an AI game (`crate::ai::set_review`). Asked by
/// the game's human seat; the new setting arrives with a snapshot (`ai_review`).
pub async fn ai_review(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<AiReviewRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player, session_room) = ReconnectService::validate_session(&app, &req.session_token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(&code).await?;
    crate::ai::set_review(&app, &code, player, req.enabled)
        .await
        .map_err(|_| {
            ServerError::InvalidAction("only the human seat of an AI game sets its AI turn review".into())
        })?;
    Ok(Json(serde_json::json!({ "ok": true, "enabled": req.enabled })))
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
