use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    response::Response,
};
use tokio::select;

use gaia_engine::{error::RuleError, MapEngine, RuleEngine};
use gaia_protocol::Revision;

use crate::{
    coordinator::{self, CommandResult},
    messages::LobbyPlayer,
    messages::{OutboundMessage, RemovalReason, ServerMessage},
    protocol::{self, ClientCommand, ClientFrame},
    room::manager::{Room, RoomState},
    services::{
        dev_game::DevGameService, faction_selection::FactionSelectionService,
        game_action::GameActionService, game_setup::GameSetupService, undo::UndoService,
    },
    state::AppState,
};

pub async fn ws_handler(
    ws: WebSocketUpgrade,
    Path(room_code): Path<String>,
    State(app): State<AppState>,
) -> Response {
    ws.max_message_size(protocol::MAX_CLIENT_FRAME_BYTES)
        .on_upgrade(move |socket| handle_socket(socket, room_code, app))
}

async fn handle_socket(mut socket: WebSocket, room_code: String, app: AppState) {
    // Subscribe to room broadcasts before processing the first message.
    let mut rx = app.event_bus.subscribe(&room_code).await;

    // The first message MUST be JoinRoom to obtain player_id.
    let player_id = match socket.recv().await {
        Some(Ok(Message::Text(text))) => {
            match protocol::decode_client_frame(&text) {
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
                            Ok(Some((pid, token_room_code))) if token_room_code == room_code => {
                                Some((pid, token.clone()))
                            }
                            Ok(Some(_)) | Ok(None) => {
                                send_error(
                                    &mut socket,
                                    "INVALID_SESSION",
                                    "session invalid or expired",
                                )
                                .await;
                                return;
                            }
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
                                // No password here: this fallback join is for a client with no
                                // session token, and a locked room is meant to be entered through
                                // the REST join that checks it. Locked rooms therefore fail closed.
                                match rooms.join_room(&room_code, &nickname, None) {
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
                    let (setup, revision, snapshot_view, member_nickname) = {
                        let rooms = app.rooms.read().await;
                        match rooms.get_room(&room_code) {
                            Some(r) => (
                                r.setup.clone(),
                                r.revision,
                                Some(coordinator::room_snapshot_view(r)),
                                r.nickname_of(pid).map(str::to_owned),
                            ),
                            None => (None, 0, None, None),
                        }
                    };
                    let Some(nickname) = member_nickname else {
                        send_error(&mut socket, "INVALID_SESSION", "session invalid or expired")
                            .await;
                        return;
                    };
                    if let Some(setup) = setup {
                        let msg = ServerMessage::RoomJoined {
                            room_code: room_code.clone(),
                            player_id: pid,
                            session_token: token,
                            game_setup: Box::new(setup),
                            revision,
                        };
                        send_msg(&mut socket, &msg.into()).await;
                    }
                    // Directly catch this connection up on the room's actual
                    // current state — `RoomJoined` above only carries the
                    // lobby-phase `game_setup`, so without this a client that
                    // (re)connects after the game has already started (every
                    // setup-stage transition opens a brand new WebSocket
                    // connection, not just a true reconnect) would otherwise
                    // see nothing but its own client-guessed placeholder
                    // state until someone else's unrelated action happens to
                    // broadcast the real one.
                    if let (Ok(revision), Some(view)) = (Revision::new(revision), snapshot_view) {
                        send_msg(&mut socket, &protocol::snapshot(revision, view).into()).await;
                    }

                    // Broadcast player and lobby state to room
                    let (player_count, lobby_state) = {
                        let rooms = app.rooms.read().await;
                        let room = rooms.get_room(&room_code);
                        (
                            room.map(|r| r.display_players().len()).unwrap_or(0),
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
                Err(error) => {
                    send_error(&mut socket, error.code(), &error.to_string()).await;
                    return;
                }
                Ok(ClientFrame::Command(_) | ClientFrame::QueryValidActions) => {
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
    let frame = match protocol::decode_client_frame(text) {
        Ok(f) => f,
        Err(e) => {
            send_error(socket, e.code(), &e.to_string()).await;
            return;
        }
    };

    let envelope = match frame {
        ClientFrame::Command(envelope) => envelope,
        ClientFrame::JoinRoom { .. } => {
            send_error(socket, "PROTOCOL", "already joined").await;
            return;
        }
        ClientFrame::QueryValidActions => {
            handle_query_valid_actions(app, room_code, player_id, socket).await;
            return;
        }
    };

    if let Err(error) = envelope.validate_compatibility(protocol::SCHEMA_HASH) {
        let current = coordinator::current_revision(app, room_code)
            .await
            .unwrap_or(Revision::ZERO);
        let (code, message_key) = protocol::compatibility_rejection_reason(&error);
        send_msg(
            socket,
            &protocol::command_rejected(
                Some(envelope.command_id.clone()),
                current,
                code,
                message_key,
            )
            .into(),
        )
        .await;
        return;
    }

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
        ClientCommand::LeaveRoom => {
            handle_remove_player(
                app,
                room_code,
                player_id,
                player_id,
                RemovalReason::Left,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::KickPlayer { player_id: target } => {
            handle_remove_player(
                app,
                room_code,
                player_id,
                target,
                RemovalReason::Kicked,
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
        ClientCommand::TriggerDevPowerCharge { coord } => {
            DevGameService::trigger_power_charge(
                app,
                room_code,
                player_id,
                coord,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::UndoFreeAction => {
            UndoService::undo_free_action(
                app,
                room_code,
                player_id,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::RequestTurnUndo => {
            UndoService::request_turn_undo(
                app,
                room_code,
                player_id,
                command_id.clone(),
                expected_revision,
            )
            .await
        }
        ClientCommand::RespondTurnUndo { approve } => {
            UndoService::respond_turn_undo(
                app,
                room_code,
                player_id,
                approve,
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

/// Answers `ClientFrame::QueryValidActions` directly off the live in-memory room — a pure read,
/// so unlike every `ClientCommand` there's no candidate-clone/DB-commit/revision-advance dance,
/// just `RuleEngine::get_valid_actions` against the room's current `game_state`.
async fn handle_query_valid_actions(
    app: &AppState,
    room_code: &str,
    player_id: u8,
    socket: &mut WebSocket,
) {
    let rooms = app.rooms.read().await;
    let Some(room) = rooms.get_room(room_code) else {
        drop(rooms);
        send_error(socket, "ROOM_NOT_FOUND", "room not found").await;
        return;
    };
    let Some(game_state) = room.game_state.as_ref() else {
        let revision = room.revision;
        drop(rooms);
        send_msg(
            socket,
            &ServerMessage::ValidActions {
                actions: vec![],
                revision,
            }
            .into(),
        )
        .await;
        return;
    };
    let acting_player = crate::services::dev_game::acting_player(room, player_id);
    let actions = RuleEngine::get_valid_actions(game_state, acting_player);
    let revision = room.revision;
    drop(rooms);
    send_msg(
        socket,
        &ServerMessage::ValidActions { actions, revision }.into(),
    )
    .await;
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

            let manual_control = crate::services::dev_game::is_manual_controller(room, player_id);
            if room.all_ready() && (room.player_count() == 4 || manual_control) {
                let setup = room
                    .setup
                    .as_ref()
                    .ok_or_else(|| RuleError::ActionNotAllowed("setup missing".into()))?;
                let players: Vec<(u8, String)> = room
                    .display_players()
                    .iter()
                    .map(|(id, nickname, _)| (*id, nickname.clone()))
                    .collect();
                let mut game_state = match setup.setup_mode {
                    gaia_engine::SetupMode::Sequential => {
                        MapEngine::init_game_state(room_code, &room.seed, &players, setup)
                    }
                    gaia_engine::SetupMode::Bidding => MapEngine::init_game_state_with_bidding(
                        room_code, &room.seed, &players, setup,
                    )?,
                };
                if manual_control {
                    game_state.dev_controller = Some(player_id);
                }
                room.game_state = Some(game_state);
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

/// Frees a seat — the same operation whether someone left or the host removed them, so both
/// commands share it and differ only in who may ask and what the broadcast says.
///
/// Lobby-only: a started room's roster is rebuilt from its snapshot on rehydrate, so a mid-game
/// removal would reappear on the next load. Leaving mid-game stays the existing
/// disconnect/`RoomPaused` path, which keeps the seat for the player to come back to.
async fn handle_remove_player(
    app: &AppState,
    room_code: &str,
    actor: u8,
    target: u8,
    reason: RemovalReason,
    command_id: gaia_protocol::CommandId,
    expected_revision: Revision,
) -> CommandResult {
    let outcome =
        coordinator::apply_command(app, room_code, command_id, expected_revision, |room| {
            if room.state != RoomState::Lobby {
                return Err(RuleError::WrongPhase);
            }
            if actor != target && !room.is_host(actor) {
                return Err(RuleError::ActionNotAllowed(
                    "only the host can remove another player".into(),
                ));
            }
            room.remove_player(target)
                .map_err(|_| RuleError::ActionNotAllowed("player not found".into()))?;
            Ok(Vec::new())
        })
        .await?;

    coordinator::broadcast_snapshot(app, room_code, outcome.revision).await;
    app.event_bus
        .broadcast(
            room_code,
            ServerMessage::PlayerRemoved {
                player_id: target,
                reason,
            },
        )
        .await;

    // Nobody left to play, and no snapshot to rehydrate a lobby room from, so drop it rather
    // than leaving an empty row in the browser for someone to walk into.
    let emptied = {
        let mut rooms = app.rooms.write().await;
        match rooms.get_room(room_code) {
            Some(room) if room.player_count() == 0 => {
                rooms.remove_room(room_code);
                true
            }
            _ => false,
        }
    };
    if !emptied {
        let lobby_state = {
            let rooms = app.rooms.read().await;
            rooms.get_room(room_code).map(lobby_state_message)
        };
        if let Some(lobby_state) = lobby_state {
            app.event_bus.broadcast(room_code, lobby_state).await;
        }
    }

    Ok(outcome)
}

fn lobby_state_message(room: &Room) -> ServerMessage {
    ServerMessage::LobbyState {
        players: room
            .display_players()
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
