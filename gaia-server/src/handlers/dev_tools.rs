//! Temporary controls for authenticated, manually controlled DEV rooms only.
use axum::{
    extract::{Path, State},
    Json,
};
use gaia_engine::{error::RuleError, GamePhase};
use gaia_protocol::{CommandId, Revision};
use serde::Deserialize;
use serde_json::{json, Value};

use crate::{
    coordinator,
    error::{ServerError, ServerResult},
    services::{dev_game::is_manual_controller, reconnect::ReconnectService},
    state::AppState,
};

#[derive(Deserialize)]
pub struct DevToolRequest {
    pub session_token: String,
    pub command_id: CommandId,
    pub expected_revision: Revision,
}

pub async fn refill(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<DevToolRequest>,
) -> ServerResult<Json<Value>> {
    let player = authenticate(&app, &code, &req.session_token).await?;
    let result =
        coordinator::apply_command(&app, &code, req.command_id, req.expected_revision, |room| {
            if !is_manual_controller(room, player) {
                return Err(RuleError::ActionNotAllowed(
                    "manual DEV controller only".into(),
                ));
            }
            let state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
            if !matches!(state.phase, GamePhase::ActionPhase { .. }) {
                return Err(RuleError::WrongPhase);
            }
            for player in &mut state.players {
                let resources = &mut player.resources;
                resources.ore = 250;
                resources.credits = 250;
                resources.knowledge = 250;
                resources.qic = 250;
                resources.power.bowl1 = 10;
                resources.power.bowl2 = 10;
                resources.power.bowl3 = 10;
                // Leave Gaia commitments untouched.
            }
            Ok(vec![])
        })
        .await
        .map_err(coordinator::command_error_to_server_error)?;
    coordinator::broadcast_snapshot(&app, &code, result.revision).await;
    Ok(Json(json!({ "revision": result.revision })))
}

pub async fn delete(
    State(app): State<AppState>,
    Path(code): Path<String>,
    Json(req): Json<DevToolRequest>,
) -> ServerResult<Json<Value>> {
    let player = authenticate(&app, &code, &req.session_token).await?;
    let mut rooms = app.rooms.write().await;
    let room = rooms
        .get_room(&code)
        .ok_or_else(|| ServerError::RoomNotFound(code.clone()))?;
    if !is_manual_controller(room, player) {
        return Err(ServerError::Unauthorised);
    }
    if room.revision != req.expected_revision.get() {
        return Err(ServerError::InvalidAction(
            "방 상태가 변경됐습니다. 다시 눌러 주세요.".into(),
        ));
    }
    // FK cascades remove snapshots, events, commands and sessions atomically.
    // Hold the same lock as game commands; only evict memory after DB success.
    sqlx::query("DELETE FROM rooms WHERE code = $1")
        .bind(&code)
        .execute(&app.db)
        .await?;
    rooms.remove_room(&code);
    app.event_bus.remove(&code).await;
    Ok(Json(json!({ "deleted": true })))
}

async fn authenticate(app: &AppState, code: &str, token: &str) -> ServerResult<u8> {
    if !cfg!(debug_assertions) && !std::env::var("GAIA_DEV_MODE").is_ok_and(|v| v == "1") {
        return Err(ServerError::Unauthorised);
    }
    let (player, session_room) = ReconnectService::validate_session(app, token).await?;
    if session_room != code {
        return Err(ServerError::InvalidSession);
    }
    app.ensure_room_loaded(code).await?;
    let rooms = app.rooms.read().await;
    let room = rooms
        .get_room(code)
        .ok_or_else(|| ServerError::RoomNotFound(code.into()))?;
    if !is_manual_controller(room, player) {
        return Err(ServerError::Unauthorised);
    }
    Ok(player)
}
