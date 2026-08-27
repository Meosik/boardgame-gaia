/// Integration tests for room creation and join flows, driven over the real
/// HTTP layer against a live (migrated) Postgres pool via the shared
/// [`harness::spawn_test_app`] helper.
///
/// These tests require a running PostgreSQL instance.
/// Set DATABASE_URL in the environment; otherwise they are skipped via
/// `#[ignore]`.
///
/// Run with: cargo test -p gaia-server --test integration_tests room_lifecycle -- --ignored
use axum::http::StatusCode;
use axum_test::{TestServer, TestWebSocket};
use serde_json::{json, Value};

use super::harness::{
    next_command_id, receive_until, send_command_and_await_accept, spawn_test_app, RoomCleanupGuard,
};

struct CreatedRoom {
    code: String,
    host_id: u64,
    host_token: String,
    setup: Value,
}

struct RestPlayer {
    id: u64,
    nickname: String,
    token: String,
}

struct WsPlayer {
    ws: TestWebSocket,
}

async fn create_room(server: &TestServer, nickname: &str, setup_mode: Option<&str>) -> CreatedRoom {
    let mut payload = json!({ "nickname": nickname });
    if let Some(setup_mode) = setup_mode {
        payload["setup_mode"] = json!(setup_mode);
    }

    let response = server.post("/api/rooms").json(&payload).await;
    response.assert_status(StatusCode::CREATED);
    let body = response.json::<Value>();
    let code = body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    let host_id = body["player_id"]
        .as_u64()
        .expect("create-room response should contain a numeric player_id");
    let host_token = body["session_token"]
        .as_str()
        .expect("create-room response should contain a string session_token")
        .to_string();
    let setup = body["game_setup"].clone();

    CreatedRoom {
        code,
        host_id,
        host_token,
        setup,
    }
}

async fn join_room(server: &TestServer, code: &str, nickname: &str) -> RestPlayer {
    let response = server
        .post(&format!("/api/rooms/{code}/join"))
        .json(&json!({ "nickname": nickname }))
        .await;
    response.assert_status_ok();
    let body = response.json::<Value>();
    RestPlayer {
        id: body["player_id"]
            .as_u64()
            .expect("join-room response should contain a numeric player_id"),
        nickname: nickname.to_string(),
        token: body["session_token"]
            .as_str()
            .expect("join-room response should contain a string session_token")
            .to_string(),
    }
}

async fn join_existing_player_ws(
    server: &TestServer,
    code: &str,
    nickname: &str,
    token: &str,
) -> WsPlayer {
    let mut ws = server
        .get_websocket(&format!("/ws/{code}"))
        .await
        .into_websocket()
        .await;
    ws.send_json(&json!({
        "type": "join_room",
        "room_code": code,
        "nickname": nickname,
        "session_token": token,
    }))
    .await;
    let joined = receive_until(&mut ws, "room_joined").await;
    assert_eq!(joined["room_code"].as_str(), Some(code));
    WsPlayer { ws }
}

async fn create_full_room(server: &TestServer) -> (CreatedRoom, Vec<RestPlayer>) {
    let created = create_room(server, "Host", Some("sequential")).await;
    let players = vec![
        RestPlayer {
            id: created.host_id,
            nickname: "Host".to_string(),
            token: created.host_token.clone(),
        },
        join_room(server, &created.code, "P2").await,
        join_room(server, &created.code, "P3").await,
        join_room(server, &created.code, "P4").await,
    ];
    (created, players)
}

async fn start_room(server: &TestServer) -> (CreatedRoom, Vec<RestPlayer>) {
    let (created, players) = create_full_room(server).await;
    assert_eq!(
        players.iter().map(|player| player.id).collect::<Vec<_>>(),
        (created.host_id..created.host_id + 4).collect::<Vec<_>>(),
        "full room should assign contiguous REST player ids"
    );

    let mut ws_players = Vec::with_capacity(players.len());
    for player in &players {
        ws_players.push(
            join_existing_player_ws(server, &created.code, &player.nickname, &player.token).await,
        );
    }

    let mut revision = 0;
    let mut cmd_id = 0u32;
    for player in &mut ws_players {
        revision = send_command_and_await_accept(
            &mut player.ws,
            &created.code,
            &next_command_id("room-lifecycle-ready", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }
    assert_eq!(revision, 4);

    (created, players)
}

fn assert_error(body: Value, expected: &str) {
    assert_eq!(body["error"].as_str(), Some(expected), "body: {body}");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn health_returns_200() {
    let server = spawn_test_app().await;

    let response = server.get("/health").await;

    response.assert_status_ok();
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn create_room_accepts_sequential_and_bidding_modes() {
    let server = spawn_test_app().await;

    let sequential = create_room(&server, "SequentialHost", Some("sequential")).await;
    let _cleanup_sequential = RoomCleanupGuard::new(sequential.code.clone());
    assert_eq!(sequential.setup["setup_mode"].as_str(), Some("sequential"));
    assert!(
        sequential.setup["factions"]
            .as_array()
            .is_some_and(|factions| factions.len() >= 4),
        "sequential setup should offer at least four factions: {}",
        sequential.setup
    );

    let bidding = create_room(&server, "BiddingHost", Some("bidding")).await;
    let _cleanup_bidding = RoomCleanupGuard::new(bidding.code.clone());
    assert_eq!(bidding.setup["setup_mode"].as_str(), Some("bidding"));
    assert_eq!(bidding.setup["factions"].as_array().map(Vec::len), Some(4));
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn create_room_rejects_malformed_setup_mode() {
    let server = spawn_test_app().await;

    let response = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "BadMode", "setup_mode": "draft" }))
        .await;

    response.assert_status(StatusCode::UNPROCESSABLE_ENTITY);
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn create_and_join_reject_blank_nicknames_and_missing_room() {
    let server = spawn_test_app().await;

    let blank_host = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "   " }))
        .await;
    blank_host.assert_status(StatusCode::UNPROCESSABLE_ENTITY);
    assert_error(blank_host.json::<Value>(), "INVALID_NICKNAME");

    let created = create_room(&server, "Host", Some("sequential")).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());
    let blank_guest = server
        .post(&format!("/api/rooms/{}/join", created.code))
        .json(&json!({ "nickname": "\t\n" }))
        .await;
    blank_guest.assert_status(StatusCode::UNPROCESSABLE_ENTITY);
    assert_error(blank_guest.json::<Value>(), "INVALID_NICKNAME");

    let missing = server
        .post("/api/rooms/NOPE00/join")
        .json(&json!({ "nickname": "Guest" }))
        .await;
    missing.assert_status(StatusCode::NOT_FOUND);
    assert_error(missing.json::<Value>(), "ROOM_NOT_FOUND");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn get_room_returns_lobby_state_and_404_for_missing_room() {
    let server = spawn_test_app().await;
    let created = create_room(&server, "Host", Some("sequential")).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());

    let found = server.get(&format!("/api/rooms/{}", created.code)).await;
    found.assert_status_ok();
    let room = found.json::<Value>();
    assert_eq!(room["code"].as_str(), Some(created.code.as_str()));
    assert_eq!(room["player_count"].as_u64(), Some(1));
    assert_eq!(room["state"].as_str(), Some("Lobby"));
    assert_eq!(room["host_player_id"].as_u64(), Some(created.host_id));

    let missing = server.get("/api/rooms/NOPE00").await;
    missing.assert_status(StatusCode::NOT_FOUND);
    assert_error(missing.json::<Value>(), "ROOM_NOT_FOUND");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn preview_board_returns_layout_and_404_for_missing_room() {
    let server = spawn_test_app().await;
    let created = create_room(&server, "Host", Some("sequential")).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());

    let preview = server
        .get(&format!("/api/rooms/{}/preview_board", created.code))
        .await;
    preview.assert_status_ok();
    let body = preview.json::<Value>();
    assert!(body["board"].is_object(), "preview should include board");
    assert!(
        body["round_tiles"]
            .as_array()
            .is_some_and(|tiles| tiles.len() == 6),
        "preview should include six round tiles: {body}"
    );
    assert!(
        body["final_scoring_tiles"]
            .as_array()
            .is_some_and(|tiles| tiles.len() == 2),
        "preview should include two final scoring tiles: {body}"
    );
    assert!(
        body["spaceship_boards"].is_array(),
        "preview should include spaceship boards"
    );
    assert_eq!(
        body["research_board"]["tech_tile_slots"]
            .as_array()
            .map(Vec::len),
        Some(9),
        "preview should include the nine physical Standard Tech positions"
    );

    let repeated = server
        .get(&format!("/api/rooms/{}/preview_board", created.code))
        .await;
    repeated.assert_status_ok();
    assert_eq!(
        body["board"],
        repeated.json::<Value>()["board"],
        "every client in one room must receive the same deterministic Interspace layout"
    );

    let missing = server.get("/api/rooms/NOPE00/preview_board").await;
    missing.assert_status(StatusCode::NOT_FOUND);
    assert_error(missing.json::<Value>(), "ROOM_NOT_FOUND");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn join_room_covers_new_player_reconnect_and_invalid_session() {
    let server = spawn_test_app().await;
    let created = create_room(&server, "Host", Some("sequential")).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());

    let bob = server
        .post(&format!("/api/rooms/{}/join", created.code))
        .json(&json!({ "nickname": "Bob" }))
        .await;
    bob.assert_status_ok();
    let bob_body = bob.json::<Value>();
    assert_eq!(bob_body["room_code"].as_str(), Some(created.code.as_str()));
    assert_eq!(bob_body["players"].as_array().map(Vec::len), Some(2));
    let bob_token = bob_body["session_token"].as_str().expect("bob token");

    let reconnect = server
        .post(&format!("/api/rooms/{}/join", created.code))
        .json(&json!({ "nickname": "Bob", "session_token": bob_token }))
        .await;
    reconnect.assert_status_ok();
    let reconnect_body = reconnect.json::<Value>();
    assert_eq!(reconnect_body["player_id"], bob_body["player_id"]);
    assert_eq!(reconnect_body["session_token"].as_str(), Some(bob_token));
    assert_eq!(reconnect_body["players"].as_array().map(Vec::len), Some(2));

    let invalid = server
        .post(&format!("/api/rooms/{}/join", created.code))
        .json(&json!({ "nickname": "Mallory", "session_token": "not-a-valid-session" }))
        .await;
    invalid.assert_status(StatusCode::UNAUTHORIZED);
    assert_error(invalid.json::<Value>(), "INVALID_SESSION");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn join_room_rejects_full_room_and_already_started_room() {
    let server = spawn_test_app().await;

    let (full, _) = create_full_room(&server).await;
    let _cleanup_full = RoomCleanupGuard::new(full.code.clone());
    let fifth = server
        .post(&format!("/api/rooms/{}/join", full.code))
        .json(&json!({ "nickname": "P5" }))
        .await;
    fifth.assert_status(StatusCode::CONFLICT);
    assert_error(fifth.json::<Value>(), "ROOM_FULL");

    let (started, _) = start_room(&server).await;
    let _cleanup_started = RoomCleanupGuard::new(started.code.clone());
    let late = server
        .post(&format!("/api/rooms/{}/join", started.code))
        .json(&json!({ "nickname": "Late" }))
        .await;
    late.assert_status(StatusCode::CONFLICT);
    assert_error(late.json::<Value>(), "ALREADY_STARTED");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn regenerate_setup_covers_host_non_host_and_invalid_session() {
    let server = spawn_test_app().await;
    let created = create_room(&server, "Host", Some("sequential")).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());
    let guest = join_room(&server, &created.code, "Guest").await;
    let mut guest_ws =
        join_existing_player_ws(&server, &created.code, &guest.nickname, &guest.token).await;
    send_command_and_await_accept(
        &mut guest_ws.ws,
        &created.code,
        "ready-before-reroll",
        0,
        json!({ "type": "player_ready", "ready": true }),
    )
    .await;

    let regenerated = server
        .post(&format!("/api/rooms/{}/regenerate", created.code))
        .json(&json!({ "session_token": created.host_token, "seed": "regen-success" }))
        .await;
    regenerated.assert_status_ok();
    let setup = regenerated.json::<Value>();
    assert_eq!(setup["seed"].as_str(), Some("regen-success"));
    assert_eq!(setup["setup_mode"].as_str(), Some("sequential"));

    let room = server.get(&format!("/api/rooms/{}", created.code)).await;
    room.assert_status_ok();
    assert!(room.json::<Value>()["players"]
        .as_array()
        .expect("room players")
        .iter()
        .all(|player| player["ready"].as_bool() == Some(false)));

    let non_host = server
        .post(&format!("/api/rooms/{}/regenerate", created.code))
        .json(&json!({ "session_token": guest.token, "seed": "regen-forbidden" }))
        .await;
    non_host.assert_status(StatusCode::FORBIDDEN);
    assert_error(non_host.json::<Value>(), "UNAUTHORISED");

    let invalid = server
        .post(&format!("/api/rooms/{}/regenerate", created.code))
        .json(&json!({ "session_token": "not-a-valid-session", "seed": "regen-invalid" }))
        .await;
    invalid.assert_status(StatusCode::UNAUTHORIZED);
    assert_error(invalid.json::<Value>(), "INVALID_SESSION");
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn regenerate_setup_rejects_after_room_started() {
    let server = spawn_test_app().await;
    let (created, _) = start_room(&server).await;
    let _cleanup = RoomCleanupGuard::new(created.code.clone());

    let response = server
        .post(&format!("/api/rooms/{}/regenerate", created.code))
        .json(&json!({ "session_token": created.host_token, "seed": "regen-after-start" }))
        .await;

    response.assert_status(StatusCode::CONFLICT);
    assert_error(response.json::<Value>(), "ALREADY_STARTED");
}
