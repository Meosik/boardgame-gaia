/// End-to-end integration test covering the official **sequential faction
/// selection** flow (PD-001: clockwise player order, one board-side pick per
/// turn, no bidding) driven entirely over the real WebSocket server harness,
/// through to game start — over the gaia-protocol envelope wire format
/// (`CommandEnvelope`/`ServerEnvelope`): every mutating command carries a
/// `command_id` and `expected_revision`, and gets a direct
/// `command_accepted`/`command_rejected` reply plus a room-wide `snapshot`
/// broadcast (see `gaia-server/src/protocol.rs`, `coordinator.rs`).
///
/// This is the closest equivalent to a browser E2E test achievable with the
/// tooling in this repo (no Playwright/Cypress here — see
/// `.omc/autopilot/spec.md`). It exercises the network/server layer that
/// connects faction-selection completion to the resulting `snapshot`
/// broadcast, complementing the engine-only coverage in
/// `gaia-engine/tests/setup_policy.rs`.
///
/// Sequential selection requires all four seats (`handle_player_ready` in
/// `gaia-server/src/handlers/websocket.rs` only starts selection once
/// `room.player_count() == 4`), so this test drives a full four-player room.
///
/// Requires a reachable Postgres instance (`DATABASE_URL`, see
/// `gaia-server/.env` / `docker-compose.dev.yml` — `postgres` service).
use axum_test::TestWebSocket;
use serde_json::{json, Value};

use gaia_engine::game_state::FactionId;
use gaia_engine::{GamePhase, GameState};

use super::harness::{
    next_command_id, receive_until, receive_until_revision, send_command_and_await_accept,
    spawn_test_app, RoomCleanupGuard,
};

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn sequential_faction_selection_reaches_game_started_action_phase() {
    let server = spawn_test_app().await;

    // ── Create room (host) via REST, exactly like the real client flow ─────
    let create_resp = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Host", "seed": "sequential-faction-selection-e2e-seed" }))
        .await;
    create_resp.assert_status(axum::http::StatusCode::CREATED);
    let create_body = create_resp.json::<Value>();
    let room_code = create_body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
    // Deletes the room row (and, via ON DELETE CASCADE, its snapshots/events)
    // when this test ends — including on panic — so repeated runs don't
    // leak rows into a shared dev database.
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let host_id = create_body["player_id"]
        .as_u64()
        .expect("create-room response should contain a numeric player_id");
    let host_token = create_body["session_token"]
        .as_str()
        .expect("create-room response should contain a string session_token")
        .to_string();
    let factions: Vec<FactionId> = create_body["game_setup"]["factions"]
        .as_array()
        .expect("game_setup.factions present in create-room response")
        .iter()
        .map(|f| serde_json::from_value(f.clone()).expect("each offered faction should parse"))
        .collect();
    assert!(
        factions.len() >= 8,
        "need at least 4 individually-offered board pairs for a 4-player game, got {factions:?}"
    );

    // ── Host connects over WS and joins using its REST session token — this
    //    resolves to the *existing* host player (id from create_room) via the
    //    reconnect/session-validate path, rather than adding a duplicate room
    //    member. ───────────────────────────────────────────────────────────
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
    assert_eq!(host_joined["player_id"].as_u64(), Some(host_id));
    let mut revision = host_joined["revision"]
        .as_u64()
        .expect("room_joined should carry the room's current revision");

    // ── Three more players connect over WS and join fresh — no REST call
    //    needed, since the WS JoinRoom path itself registers a new room
    //    member when no session token is supplied. ─────────────────────────
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
        let joined = receive_until(&mut ws, "room_joined").await;
        let player_id = joined["player_id"]
            .as_u64()
            .expect("room_joined should contain a numeric player_id");
        guests.push((player_id, ws));
    }
    let guest_ids: Vec<u64> = guests.iter().map(|(id, _)| *id).collect();
    for id in &guest_ids {
        assert_ne!(*id, host_id, "guest id must not collide with the host's id");
    }

    // ── All four players ready up, in turn, tracking the shared revision
    //    this test drives centrally. `handle_player_ready` starts sequential
    //    faction selection once all four seats are ready
    //    (`gaia-server/src/handlers/websocket.rs`). ──────────────────────────
    let mut cmd_id = 0u32;
    revision = send_command_and_await_accept(
        &mut host_ws,
        &room_code,
        &next_command_id("fsf", &mut cmd_id),
        revision,
        json!({ "type": "player_ready", "ready": true }),
    )
    .await;
    for (_, ws) in guests.iter_mut() {
        revision = send_command_and_await_accept(
            ws,
            &room_code,
            &next_command_id("fsf", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }

    // ── Sequential selection round: each of the four players picks one
    //    available faction board-side, strictly in clockwise room-join order
    //    (host, P2, P3, P4) per PD-001/PD-002. Picking indices 0, 2, 4, 6
    //    from the initially-offered faction list always lands on distinct
    //    board pairs, mirroring `gaia-engine/tests/setup_policy.rs`. ────────
    let picks = [
        (host_id, factions[0]),
        (guest_ids[0], factions[2]),
        (guest_ids[1], factions[4]),
        (guest_ids[2], factions[6]),
    ];
    for (picking_id, faction) in picks {
        let ws = if picking_id == host_id {
            &mut host_ws
        } else {
            &mut guests
                .iter_mut()
                .find(|(id, _)| *id == picking_id)
                .expect("picking player id must be a known room member")
                .1
        };
        revision = send_command_and_await_accept(
            ws,
            &room_code,
            &next_command_id("fsf", &mut cmd_id),
            revision,
            json!({
                "type": "place_setup_action",
                "action": { "type": "SelectFaction", "faction": faction },
            }),
        )
        .await;
    }

    // ── Assert: every connection eventually observes a `snapshot` at the
    //    final revision with the game in `ActionPhase { active_player: 0 }`
    //    — the exact transition performed when the final `SelectFaction`
    //    command completes setup. Each connection also received earlier
    //    snapshot broadcasts for *other* players' commands along the way
    //    (this test only ever awaits its own `command_accepted`), so this
    //    scans past those rather than assuming the final snapshot is next. ─
    let host_snapshot = receive_until_revision(&mut host_ws, revision).await;
    assert_snapshot_reached_action_phase(&host_snapshot, "host", revision);
    for (i, (_, ws)) in guests.iter_mut().enumerate() {
        let snap = receive_until_revision(ws, revision).await;
        assert_snapshot_reached_action_phase(&snap, &format!("guest[{i}]"), revision);
    }
}

fn assert_snapshot_reached_action_phase(snapshot: &Value, label: &str, expected_revision: u64) {
    assert_eq!(
        snapshot["revision"].as_u64(),
        Some(expected_revision),
        "[{label}] snapshot should be at the revision the last accepted command reported"
    );
    let game_state: GameState =
        serde_json::from_value(snapshot["state"].clone()).unwrap_or_else(|e| {
            panic!("[{label}] snapshot state should deserialize into GameState: {e}")
        });
    assert_eq!(
        game_state.phase,
        GamePhase::ActionPhase { active_player: 0 },
        "[{label}] game should start in ActionPhase with active_player 0"
    );
    assert!(
        game_state.players.iter().all(|p| p.faction.is_some()),
        "[{label}] every player should have an assigned faction once selection completes"
    );
}
