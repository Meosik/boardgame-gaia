/// Focused regression test for a bug reported via live browser testing: a
/// 4-player room in **Bidding** setup mode never transitioned past "비딩을
/// 시작하는 중..." even once all 4 seats readied up.
///
/// No existing integration test exercised this exact path over the real
/// server + database: `faction_selection_flow.rs`/`full_game_playthrough.rs`
/// both use `SetupMode::Sequential`, and `room/manager.rs`'s own bidding test
/// only calls `RoomManager::create_room` directly — it never drives
/// `handle_player_ready`'s `room.player_count() == 4` transition through
/// `coordinator::apply_command` and its DB commit, which is exactly where a
/// real bug (e.g. a JSON round-trip failure on the new `GameState` shape) or
/// a real crash on the previously-buggy client (`FactionSelectView`'s
/// infinite render loop) could each independently explain the reported
/// symptom. This test isolates the *server's* half of that path.
///
/// Requires a reachable Postgres instance (`DATABASE_URL`, see
/// `gaia-server/.env` / `docker-compose.dev.yml` — `postgres` service).
use axum_test::TestWebSocket;
use serde_json::{json, Value};

use gaia_engine::game_state::SetupPhase;
use gaia_engine::GamePhase;

use super::harness::{
    next_command_id, receive_until, receive_until_revision, send_command_and_await_accept,
    spawn_test_app, RoomCleanupGuard,
};

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn all_four_players_ready_starts_bidding() {
    let server = spawn_test_app().await;

    let create_resp = server
        .post("/api/rooms")
        .json(&json!({
            "nickname": "Host",
            "seed": "bidding-room-start-e2e-seed",
            "setup_mode": "bidding",
        }))
        .await;
    create_resp.assert_status(axum::http::StatusCode::CREATED);
    let create_body = create_resp.json::<Value>();
    assert_eq!(
        create_body["game_setup"]["setup_mode"], "bidding",
        "room should actually be created in bidding mode"
    );
    let room_code = create_body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let _host_id = create_body["player_id"]
        .as_u64()
        .expect("create-room response should contain a numeric player_id");
    let host_token = create_body["session_token"]
        .as_str()
        .expect("create-room response should contain a string session_token")
        .to_string();

    let mut host_ws = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    host_ws
        .send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": "Host",
            "session_token": host_token,
        }))
        .await;
    let host_joined = receive_until(&mut host_ws, "room_joined").await;
    let mut revision = host_joined["revision"]
        .as_u64()
        .expect("room_joined should carry the room's current revision");

    let mut guests: Vec<(u64, TestWebSocket)> = Vec::new();
    for nickname in ["P2", "P3", "P4"] {
        let mut ws = server
            .get_websocket(&format!("/ws/{room_code}"))
            .await
            .into_websocket()
            .await;
        ws.send_json(&json!({
            "type": "join_room",
            "room_code": room_code,
            "nickname": nickname,
            "session_token": Value::Null,
        }))
        .await;
        receive_until(&mut ws, "room_joined").await;
        guests.push((0, ws));
    }

    // All 4 seats ready up in turn, exactly what the browser's "준비 완료"
    // button sends. The 4th one is the one that should flip
    // `RoomState::Lobby` -> `RoomState::FactionSelection` server-side.
    let mut cmd_id = 0u32;
    revision = send_command_and_await_accept(
        &mut host_ws,
        &room_code,
        &next_command_id("brs", &mut cmd_id),
        revision,
        json!({ "type": "player_ready", "ready": true }),
    )
    .await;
    for (_, ws) in guests.iter_mut() {
        revision = send_command_and_await_accept(
            ws,
            &room_code,
            &next_command_id("brs", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }

    // The 4th `player_ready` should have produced a `snapshot` broadcast
    // carrying a real `GameState` already in `SetupPhase::Bidding`. Observed
    // on `host_ws` specifically since it wasn't the sender of that last
    // command (P4 was) — and matched by revision, not just "first snapshot
    // seen", since `host_ws` also received (and hasn't drained) the 3
    // earlier snapshot broadcasts from its own and the other guests' ready
    // toggles.
    let snapshot = receive_until_revision(&mut host_ws, revision).await;
    let game_state: gaia_engine::GameState = serde_json::from_value(snapshot["state"].clone())
        .unwrap_or_else(|error| {
            panic!("snapshot state should deserialize into GameState: {error}")
        });
    assert_eq!(
        game_state.phase,
        GamePhase::Setup(SetupPhase::Bidding {
            active_player: game_state.turn_order[0]
        }),
        "room should enter the Bidding setup phase once all 4 seats are ready, got {:?}",
        game_state.phase,
    );
}
