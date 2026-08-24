use axum::{
    extract::{Path, State},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};

use gaia_engine::game_state::PlayerId;

use crate::{
    coordinator,
    error::{ServerError, ServerResult},
    messages::LobbyPlayer,
    services::{game_setup::GameSetupService, reconnect::ReconnectService},
    state::AppState,
};

// ── Request / Response types ──────────────────────────────────────────────────

#[derive(Deserialize)]
pub struct CreateRoomRequest {
    pub nickname: String,
    pub seed: Option<String>,
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

// ── Handlers ──────────────────────────────────────────────────────────────────

pub async fn create_room(
    State(app): State<AppState>,
    Json(req): Json<CreateRoomRequest>,
) -> ServerResult<(StatusCode, Json<CreateRoomResponse>)> {
    let (code, player_id, setup) =
        GameSetupService::create_room(&app, &req.nickname, req.seed).await?;

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

pub async fn join_room(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<JoinRoomRequest>,
) -> ServerResult<Json<JoinRoomResponse>> {
    // Reconnect path
    if let Some(token) = &req.session_token {
        if let Ok((player_id, room_code)) = ReconnectService::validate_session(&app, token).await {
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
    }

    let player_id = {
        let mut rooms = app.rooms.write().await;
        rooms.join_room(&code, &req.nickname)?
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
        "player_count": room.player_count(),
        "state":        format!("{:?}", room.state),
        "host_player_id": room.host_player,
        "players":      room.players.iter()
            .map(|(id, nick, ready)| serde_json::json!({ "id": id, "player_id": id, "nickname": nick, "ready": ready }))
            .collect::<Vec<_>>(),
    })))
}

pub async fn regenerate_setup(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<RegenerateRequest>,
) -> ServerResult<Json<serde_json::Value>> {
    let (player_id, _) = ReconnectService::validate_session(&app, &req.session_token).await?;

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

fn lobby_players(room: &crate::room::manager::Room) -> Vec<LobbyPlayer> {
    room.players
        .iter()
        .map(|(player_id, nickname, ready)| LobbyPlayer {
            player_id: *player_id,
            nickname: nickname.clone(),
            ready: *ready,
        })
        .collect()
}
