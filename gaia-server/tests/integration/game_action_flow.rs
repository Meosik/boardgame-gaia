/// End-to-end rejection coverage for game-action commands.
///
/// The successful `place_game_action` path, including room-wide snapshots,
/// round transitions, and `game_ended`, is exercised by
/// `full_game_playthrough.rs`. This file keeps the complementary public
/// failure branch focused and cheap: a syntactically valid game action sent
/// while the room is still in the lobby must be rejected without consuming a
/// revision.
use serde_json::{json, Value};

use super::harness::{command_msg, receive_until, spawn_test_app, RoomCleanupGuard};

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn game_action_in_lobby_is_rejected_without_advancing_revision() {
    let server = spawn_test_app().await;
    let create = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Host", "seed": "game-action-wrong-phase" }))
        .await;
    create.assert_status(axum::http::StatusCode::CREATED);
    let body = create.json::<Value>();
    let room_code = body["room_code"]
        .as_str()
        .expect("create response contains room_code")
        .to_string();
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let token = body["session_token"]
        .as_str()
        .expect("create response contains session_token");

    let mut ws = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    ws.send_json(&json!({
        "type": "join_room",
        "room_code": room_code,
        "nickname": "Host",
        "session_token": token,
    }))
    .await;
    let joined = receive_until(&mut ws, "room_joined").await;
    let revision = joined["revision"]
        .as_u64()
        .expect("room_joined contains revision");

    ws.send_json(&command_msg(
        &room_code,
        "wrong-phase-game-action",
        revision,
        json!({
            "type": "place_game_action",
            "action": { "type": "Pass", "booster_id": null },
        }),
    ))
    .await;

    let rejected = receive_until(&mut ws, "command_rejected").await;
    assert_eq!(rejected["rejection"]["code"].as_str(), Some("WRONG_PHASE"));
    assert_eq!(
        rejected["revision"].as_u64(),
        Some(revision),
        "a rejected action must not consume a room revision"
    );
}
