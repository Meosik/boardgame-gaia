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
use serde_json::json;

use super::harness::{spawn_test_app, RoomCleanupGuard};

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn create_room_returns_201_with_code_and_setup() {
    let server = spawn_test_app().await;

    // Act
    let response = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Alice" }))
        .await;

    // Assert
    response.assert_status(StatusCode::CREATED);
    let body = response.json::<serde_json::Value>();
    let room_code = body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    let _cleanup = RoomCleanupGuard::new(room_code);

    assert!(body["player_id"].as_u64().is_some());
    assert!(body["session_token"].as_str().is_some());
    assert!(body["game_setup"].is_object());
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn join_room_increments_player_count() {
    let server = spawn_test_app().await;

    // Create room
    let create_resp = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Alice" }))
        .await;
    let body = create_resp.json::<serde_json::Value>();
    let code = body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    let _cleanup = RoomCleanupGuard::new(code.clone());

    // Join
    let join_resp = server
        .post(&format!("/api/rooms/{code}/join"))
        .json(&json!({ "nickname": "Bob" }))
        .await;
    join_resp.assert_status_ok();

    // Check room state
    let room_resp = server.get(&format!("/api/rooms/{code}")).await;
    let room = room_resp.json::<serde_json::Value>();
    assert_eq!(room["player_count"].as_u64(), Some(2));
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn room_full_after_four_players() {
    let server = spawn_test_app().await;

    let create_resp = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "P1" }))
        .await;
    let code = create_resp.json::<serde_json::Value>()["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    let _cleanup = RoomCleanupGuard::new(code.clone());

    for name in &["P2", "P3", "P4"] {
        server
            .post(&format!("/api/rooms/{code}/join"))
            .json(&json!({ "nickname": name }))
            .await;
    }

    // 5th join must fail
    let fifth = server
        .post(&format!("/api/rooms/{code}/join"))
        .json(&json!({ "nickname": "P5" }))
        .await;
    fifth.assert_status(StatusCode::CONFLICT);
}
