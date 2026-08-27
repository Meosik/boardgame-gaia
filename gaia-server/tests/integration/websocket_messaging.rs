/// WebSocket connection, protocol validation, and message-routing tests.
///
/// Requires a reachable PostgreSQL instance (`DATABASE_URL`, see
/// `gaia-server/.env` / `docker-compose.dev.yml` — `postgres` service).
use std::time::Duration;

use axum::http::StatusCode;
use axum_test::{TestServer, TestWebSocket};
use serde_json::{json, Value};

use gaia_server::protocol::SCHEMA_HASH;

use super::harness::{
    command_msg, next_command_id, receive_until, send_command_and_await_accept, spawn_test_app,
    RoomCleanupGuard,
};

struct JoinedPlayer {
    id: u64,
    token: String,
    ws: TestWebSocket,
}

async fn create_room(server: &TestServer, seed_prefix: &str) -> (String, u64, String) {
    let response = server
        .post("/api/rooms")
        .json(&json!({
            "nickname": "Host",
            "seed": format!("{seed_prefix}-{}", uuid::Uuid::new_v4()),
        }))
        .await;
    response.assert_status(StatusCode::CREATED);

    let body = response.json::<Value>();
    let room_code = body["room_code"]
        .as_str()
        .expect("room_code present")
        .to_string();
    let player_id = body["player_id"].as_u64().expect("player_id present");
    let session_token = body["session_token"]
        .as_str()
        .expect("session_token present")
        .to_string();

    (room_code, player_id, session_token)
}

async fn join_ws(
    server: &TestServer,
    room_code: &str,
    nickname: &str,
    session_token: Option<String>,
) -> JoinedPlayer {
    let mut ws = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    ws.send_json(&json!({
        "type": "join_room",
        "room_code": room_code,
        "nickname": nickname,
        "session_token": session_token,
    }))
    .await;

    let joined = receive_until(&mut ws, "room_joined").await;
    JoinedPlayer {
        id: joined["player_id"].as_u64().expect("player_id present"),
        token: joined["session_token"]
            .as_str()
            .expect("session_token present")
            .to_string(),
        ws,
    }
}

async fn create_and_join_four(server: &TestServer) -> (String, Vec<JoinedPlayer>, u64) {
    let (room_code, host_id, host_token) = create_room(server, "ws-four").await;

    let mut host = join_ws(server, &room_code, "Host", Some(host_token.clone())).await;
    assert_eq!(host.id, host_id);
    host.token = host_token;

    let mut players = vec![host];
    for nickname in ["P2", "P3", "P4"] {
        players.push(join_ws(server, &room_code, nickname, None).await);
    }

    players[0]
        .ws
        .send_json(&command_msg(
            &room_code,
            "probe-revision",
            0,
            json!({ "type": "player_ready", "ready": true }),
        ))
        .await;
    let accepted = receive_until(&mut players[0].ws, "command_accepted").await;
    assert_eq!(accepted["command_id"].as_str(), Some("probe-revision"));
    let revision = accepted["revision"].as_u64().expect("revision present");

    (room_code, players, revision)
}

async fn receive_message_type(ws: &mut TestWebSocket, expected_type: &str) -> Value {
    for _ in 0..20 {
        let msg = tokio::time::timeout(Duration::from_secs(5), ws.receive_json::<Value>())
            .await
            .unwrap_or_else(|_| panic!("timed out waiting for a `{expected_type}` message"));
        if msg["type"] == expected_type {
            return msg;
        }
    }
    panic!("did not receive a `{expected_type}` message within 20 messages");
}

async fn receive_error(ws: &mut TestWebSocket) -> Value {
    receive_message_type(ws, "error").await
}

fn assert_error(message: &Value, code: &str, text_fragment: &str) {
    assert_eq!(message["type"].as_str(), Some("error"));
    assert_eq!(message["code"].as_str(), Some(code));
    assert!(
        message["message"]
            .as_str()
            .unwrap_or_default()
            .contains(text_fragment),
        "error message should contain `{text_fragment}`: {message}"
    );
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn ws_rejects_invalid_first_frames_and_join_mismatches() {
    let server = spawn_test_app().await;
    let (room_code, _, _) = create_room(&server, "ws-first-frame").await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());

    let mut command_first = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    command_first
        .send_json(&command_msg(
            &room_code,
            "first-command",
            0,
            json!({ "type": "player_ready", "ready": true }),
        ))
        .await;
    assert_error(
        &receive_error(&mut command_first).await,
        "PROTOCOL",
        "first message must be JoinRoom",
    );

    let mut malformed = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    malformed.send_text("{not-json").await;
    assert_error(
        &receive_error(&mut malformed).await,
        "PARSE_ERROR",
        "invalid client frame",
    );

    let mut unknown = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    unknown.send_json(&json!({ "type": "unknown_frame" })).await;
    assert_error(
        &receive_error(&mut unknown).await,
        "PARSE_ERROR",
        "invalid client frame",
    );

    let mut mismatched_join = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    mismatched_join
        .send_json(&json!({
            "type": "join_room",
            "room_code": "OTHER1",
            "nickname": "Mismatch",
            "session_token": Value::Null,
        }))
        .await;
    assert_error(
        &receive_error(&mut mismatched_join).await,
        "PROTOCOL",
        "room code mismatch",
    );

    let missing_room_code = format!("Z{:05}", uuid::Uuid::new_v4().as_u128() & 0xFFFFF);
    let mut missing_room = server
        .get_websocket(&format!("/ws/{missing_room_code}"))
        .await
        .into_websocket()
        .await;
    missing_room
        .send_json(&json!({
            "type": "join_room",
            "room_code": missing_room_code,
            "nickname": "Nobody",
            "session_token": Value::Null,
        }))
        .await;
    assert_error(
        &receive_error(&mut missing_room).await,
        "JOIN_FAILED",
        "room not found",
    );

    let mut blank_nickname = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    blank_nickname
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "   ",
            "session_token": Value::Null,
        }))
        .await;
    assert_error(
        &receive_error(&mut blank_nickname).await,
        "JOIN_FAILED",
        "nickname must not be empty",
    );

    let mut invalid_session = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    invalid_session
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "Invalid session",
            "session_token": "not-a-valid-session-token",
        }))
        .await;
    assert_error(
        &receive_error(&mut invalid_session).await,
        "INVALID_SESSION",
        "session invalid or expired",
    );

    let (other_room_code, _, other_room_token) = create_room(&server, "ws-other-room").await;
    let _other_cleanup = RoomCleanupGuard::new(other_room_code);
    let mut cross_room_session = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    cross_room_session
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "Cross-room session",
            "session_token": other_room_token,
        }))
        .await;
    assert_error(
        &receive_error(&mut cross_room_session).await,
        "INVALID_SESSION",
        "session invalid or expired",
    );
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn ws_validates_post_join_protocol_and_command_outcomes() {
    let server = spawn_test_app().await;
    let (room_code, _, host_token) = create_room(&server, "ws-command-branches").await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let mut host = join_ws(&server, &room_code, "Host", Some(host_token)).await;

    host.ws
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "HostAgain",
            "session_token": host.token,
        }))
        .await;
    assert_error(
        &receive_error(&mut host.ws).await,
        "PROTOCOL",
        "already joined",
    );

    let mut wrong_room = command_msg(
        &room_code,
        "wrong-room",
        0,
        json!({ "type": "player_ready", "ready": true }),
    );
    wrong_room["room_id"] = json!("WRONG1");
    host.ws.send_json(&wrong_room).await;
    assert_error(
        &receive_error(&mut host.ws).await,
        "PROTOCOL",
        "room_id mismatch",
    );

    let mut unsupported_version = command_msg(
        &room_code,
        "bad-version",
        0,
        json!({ "type": "player_ready", "ready": true }),
    );
    unsupported_version["protocol_version"] = json!(gaia_protocol::PROTOCOL_VERSION + 1);
    host.ws.send_json(&unsupported_version).await;
    let rejected = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(rejected["command_id"].as_str(), Some("bad-version"));
    assert_eq!(
        rejected["rejection"]["code"].as_str(),
        Some("UNSUPPORTED_PROTOCOL_VERSION")
    );

    let mut bad_schema = command_msg(
        &room_code,
        "bad-schema",
        0,
        json!({ "type": "player_ready", "ready": true }),
    );
    bad_schema["schema_hash"] =
        json!("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");
    host.ws.send_json(&bad_schema).await;
    let rejected = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(rejected["command_id"].as_str(), Some("bad-schema"));
    assert_eq!(
        rejected["rejection"]["code"].as_str(),
        Some("SCHEMA_HASH_MISMATCH")
    );

    host.ws
        .send_json(&command_msg(
            &room_code,
            "ready-accepted",
            0,
            json!({ "type": "player_ready", "ready": true }),
        ))
        .await;
    let accepted = receive_until(&mut host.ws, "command_accepted").await;
    assert_eq!(accepted["command_id"].as_str(), Some("ready-accepted"));
    let current_revision = accepted["revision"].as_u64().expect("revision present");
    assert_eq!(current_revision, 1);

    host.ws
        .send_json(&command_msg(
            &room_code,
            "stale-ready",
            0,
            json!({ "type": "player_ready", "ready": false }),
        ))
        .await;
    let rejected = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(rejected["command_id"].as_str(), Some("stale-ready"));
    assert_eq!(
        rejected["rejection"]["code"].as_str(),
        Some("REVISION_CONFLICT")
    );
    assert_eq!(rejected["revision"].as_u64(), Some(current_revision));
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn ws_join_capacity_started_and_reconnect_branches() {
    let server = spawn_test_app().await;
    let (room_code, mut players, mut revision) = create_and_join_four(&server).await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());

    let mut fifth = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    fifth
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "P5",
            "session_token": Value::Null,
        }))
        .await;
    assert_error(
        &receive_error(&mut fifth).await,
        "JOIN_FAILED",
        "room is full",
    );

    let mut cmd_id = 0u32;
    for player in players.iter_mut().skip(1) {
        revision = send_command_and_await_accept(
            &mut player.ws,
            &room_code,
            &next_command_id("start-ready", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }
    assert_eq!(revision, 4);

    let mut tokenless_started_join = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    tokenless_started_join
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "Late",
            "session_token": Value::Null,
        }))
        .await;
    assert_error(
        &receive_error(&mut tokenless_started_join).await,
        "JOIN_FAILED",
        "room already started",
    );

    let rejoin_id = players[1].id;
    let rejoin_token = players[1].token.clone();
    let disconnected = players.remove(1);
    disconnected.ws.close().await;

    let mut reconnect = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    reconnect
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "P2 reconnect",
            "session_token": rejoin_token,
        }))
        .await;
    let rejoined = receive_until(&mut reconnect, "room_joined").await;
    assert_eq!(rejoined["player_id"].as_u64(), Some(rejoin_id));
    assert_eq!(rejoined["revision"].as_u64(), Some(revision));
    assert!(rejoined["session_token"].as_str().is_some());

    let snapshot = receive_until(&mut reconnect, "snapshot").await;
    assert_eq!(snapshot["revision"].as_u64(), Some(revision));
    let schema_hash = SCHEMA_HASH.to_string();
    assert_eq!(snapshot["schema_hash"].as_str(), Some(schema_hash.as_str()));
}
