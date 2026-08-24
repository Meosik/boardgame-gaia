use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    response::Response,
};
use tokio::select;

use gaia_engine::{error::RuleError, MapEngine};
use gaia_protocol::Revision;

use crate::{
    coordinator::{self, CommandResult},
    messages::LobbyPlayer,
    messages::{OutboundMessage, ServerMessage},
    protocol::{self, ClientCommand, ClientFrame},
    room::manager::{Room, RoomState},
    services::{
        faction_selection::FactionSelectionService, game_action::GameActionService,
        game_setup::GameSetupService,
    },
    state::AppState,
};

pub async fn ws_handler(
    ws: WebSocketUpgrade,
    Path(room_code): Path<String>,
    State(app): State<AppState>,
) -> Response {
    ws.on_upgrade(move |socket| handle_socket(socket, room_code, app))
}

async fn handle_socket(mut socket: WebSocket, room_code: String, app: AppState) {
    // Subscribe to room broadcasts before processing the first message.
    let mut rx = app.event_bus.subscribe(&room_code).await;

    // The first message MUST be JoinRoom to obtain player_id.
    let player_id = match socket.recv().await {
        Some(Ok(Message::Text(text))) => {
            match serde_json::from_str::<ClientFrame>(&text) {
                Ok(ClientFrame::JoinRoom {
                    room_code: requested_room_code,
                    nickname,
                    session_token,
                }) => {
                    if requested_room_code != room_code {
                        send_error(&mut socket, "PROTOCOL", "room code mismatch").await;
                        return;
                    }

                    // Rehydrate from the DB if this room isn't in memory yet
                    // (e.g. the server just restarted) — a no-op otherwise.
                    if let Err(e) = app.ensure_room_loaded(&room_code).await {
                        send_error(&mut socket, "INTERNAL", &e.to_string()).await;
                        return;
                    }

                    // Try reconnect path first — reuse the presented token's
                    // existing session rather than minting a new one.
                    let reconnected = match &session_token {
                        Some(token) => match app.sessions.validate(token).await {
                            Ok(Some((pid, _))) => Some((pid, token.clone())),
                            Ok(None) => None,
                            Err(e) => {
                                send_error(&mut socket, "INTERNAL", &e.to_string()).await;
                                return;
                            }
                        },
                        None => None,
                    };

                    let (pid, token) = match reconnected {
                        Some(pair) => pair,
                        None => {
                            let pid = {
                                let mut rooms = app.rooms.write().await;
                                match rooms.join_room(&room_code, &nickname) {
                                    Ok(p) => p,
                                    Err(e) => {
                                        send_error(&mut socket, "JOIN_FAILED", &e.to_string())
                                            .await;
                                        return;
                                    }
                                }
                            };
                            let token = match app.sessions.create_session(pid, &room_code).await {
                                Ok(t) => t,
                                Err(e) => {
                                    send_error(&mut socket, "INTERNAL", &e.to_string()).await;
                                    return;
                                }
                            };
                            (pid, token)
                        }
                    };

                    // Send RoomJoined to this player
                    let (setup, revision) = {
                        let rooms = app.rooms.read().await;
                        match rooms.get_room(&room_code) {
                            Some(r) => (r.setup.clone(), r.revision),
                            None => (None, 0),
                        }
                    };
                    if let Some(setup) = setup {
                        let msg = ServerMessage::RoomJoined {
                            room_code: room_code.clone(),
                            player_id: pid,
                            session_token: token,
                            game_setup: setup,
                            revision,
                        };
                        send_msg(&mut socket, &msg.into()).await;
                    }

                    // Broadcast player and lobby state to room
                    let (player_count, lobby_state) = {
                        let rooms = app.rooms.read().await;
                        let room = rooms.get_room(&room_code);
                        (
                            room.map(|r| r.player_count()).unwrap_or(0),
                            room.map(lobby_state_message),
                        )
                    };
                    app.event_bus
                        .broadcast(
                            &room_code,
                            ServerMessage::PlayerJoined {
                                player_id: pid,
                                nickname,
                                player_count,
                            },
                        )
                        .await;
                    if let Some(lobby_state) = lobby_state {
                        app.event_bus.broadcast(&room_code, lobby_state).await;
                    }

                    if let Some(paused_msg) = update_presence(&app, &room_code, pid, true).await {
                        app.event_bus.broadcast(&room_code, paused_msg).await;
                    }

                    pid
                }
                _ => {
                    send_error(&mut socket, "PROTOCOL", "first message must be JoinRoom").await;
                    return;
                }
            }
        }
        _ => return,
    };

    // Main message loop — interleave incoming client messages and room broadcasts.
    loop {
        select! {
            // Incoming from this client
            msg = socket.recv() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        handle_client_message(&app, &room_code, player_id, &text, &mut socket).await;
                    }
                    Some(Ok(Message::Close(_))) | None => break,
                    _ => {}
                }
            }
            // Broadcast from room
            broadcast = rx.recv() => {
                match broadcast {
                    Ok(server_msg) => send_msg(&mut socket, &server_msg).await,
                    Err(_) => break,  // channel closed (room ended)
                }
            }
        }
    }

    if let Some(paused_msg) = update_presence(&app, &room_code, player_id, false).await {
        app.event_bus.broadcast(&room_code, paused_msg).await;
    }
}

/// Marks a seat connected/disconnected and returns a `RoomPaused` broadcast
/// if — and only if — `paused` actually flipped as a result. Never touches
/// `revision` (pause/resume isn't a game-state mutation).
async fn update_presence(
    app: &AppState,
    room_code: &str,
    player_id: u8,
    connected: bool,
) -> Option<ServerMessage> {
    let mut rooms = app.rooms.write().await;
    let room = rooms.get_room_mut(room_code)?;
    let was_paused = room.paused;
    if connected {
        room.mark_connected(player_id);
    } else {
        room.mark_disconnected(player_id);
    }
    if room.paused == was_paused {
        return None;
    }
    Some(ServerMessage::RoomPaused {
        paused: room.paused,
        missing_seats: room.missing_seats(),
    })
}

async fn handle_client_message(
    app: &AppState,
    room_code: &str,
    player_id: u8,
    text: &str,
    socket: &mut WebSocket,
) {
    let frame = match serde_json::from_str::<ClientFrame>(text) {
        Ok(f) => f,
        Err(e) => {
            send_error(socket, "PARSE_ERROR", &e.to_string()).await;
            return;
        }
    };

    let envelope = match frame {
        ClientFrame::Command(envelope) => envelope,
        ClientFrame::JoinRoom { .. } => {
            send_error(socket, "PROTOCOL", "already joined").await;
            return;
        }
    };

    if envelope.room_id != room_code {
        send_error(socket, "PROTOCOL", "room_id mismatch").await;
        return;
    }

    let command_id = envelope.command_id.clone();
    let expected_revision = envelope.expected_revision;

    let result: CommandResult = match envelope.command {
        ClientCommand::PlayerReady { ready } => {
            handle_player_ready(
                app,
                room_code,
                player_id,
                ready,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::RegenerateSetup { seed } => {
            GameSetupService::regenerate_setup(
                app,
                room_code,
                player_id,
                seed,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::PlaceSetupAction { action } => {
            FactionSelectionService::process_setup_action(
                app,
                room_code,
                player_id,
                action,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::PlaceGameAction { action } => {
            GameActionService::process_action(
                app,
                room_code,
                player_id,
                action,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
    };

    match result {
        Ok(outcome) => {
            send_msg(
                socket,
                &protocol::command_accepted(command_id, outcome.revision).into(),
            )
            .await;
        }
        Err(error) => {
            let current = coordinator::current_revision(app, room_code)
                .await
                .unwrap_or(Revision::ZERO);
            let (code, message) = protocol::rejection_reason(&error);
            send_msg(
                socket,
                &protocol::command_rejected(Some(command_id), current, code, &message).into(),
            )
            .await;
        }
    }
}

async fn handle_player_ready(
    app: &AppState,
    room_code: &str,
    player_id: u8,
    ready: bool,
    command_id: gaia_protocol::CommandId,
    expected_revision: Revision,
) -> CommandResult {
    let outcome =
        coordinator::apply_command(app, room_code, command_id, expected_revision, |room| {
            if room.state != RoomState::Lobby {
                return Err(RuleError::WrongPhase);
            }
            room.set_ready(player_id, ready)
                .map_err(|_| RuleError::ActionNotAllowed("player not found".into()))?;

            if room.all_ready() && room.player_count() == 4 {
                let setup = room
                    .setup
                    .as_ref()
                    .ok_or_else(|| RuleError::ActionNotAllowed("setup missing".into()))?;
                let players: Vec<(u8, String)> = room
                    .players
                    .iter()
                    .map(|(id, nickname, _)| (*id, nickname.clone()))
                    .collect();
                room.game_state = Some(MapEngine::init_game_state(room_code, &players, setup));
                room.state = RoomState::FactionSelection;
            }

            Ok(Vec::new())
        })
        .await?;

    coordinator::broadcast_snapshot(app, room_code, outcome.revision).await;

    let lobby_state = {
        let rooms = app.rooms.read().await;
        rooms.get_room(room_code).map(lobby_state_message)
    };
    if let Some(lobby_state) = lobby_state {
        app.event_bus.broadcast(room_code, lobby_state).await;
    }

    Ok(outcome)
}

fn lobby_state_message(room: &Room) -> ServerMessage {
    ServerMessage::LobbyState {
        players: room
            .players
            .iter()
            .map(|(player_id, nickname, ready)| LobbyPlayer {
                player_id: *player_id,
                nickname: nickname.clone(),
                ready: *ready,
            })
            .collect(),
        host_player_id: room.host_player,
    }
}

async fn send_msg(socket: &mut WebSocket, msg: &OutboundMessage) {
    if let Ok(text) = serde_json::to_string(msg) {
        let _ = socket.send(Message::Text(text)).await;
    }
}

async fn send_error(socket: &mut WebSocket, code: &str, message: &str) {
    send_msg(socket, &ServerMessage::error(code, message).into()).await;
}
