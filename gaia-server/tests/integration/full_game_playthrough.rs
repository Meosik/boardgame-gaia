/// End-to-end integration test that drives an entire 4-player game — setup,
/// all 6 rounds, and final scoring — over the real WebSocket server, and
/// asserts the browser-facing `game_ended` message the frontend's
/// `GameOverScreen` consumes actually arrives with a sane payload.
///
/// This is the closest equivalent to "play the game in a browser to the end"
/// achievable with the tooling in this repo (no Playwright/Cypress here —
/// see `faction_selection_flow.rs`'s header comment). Every player simply
/// passes each round (picking whatever booster is available) rather than
/// building/researching — the goal is exercising the full round-loop and
/// game-end wiring end to end, not covering every action type (those are
/// covered individually elsewhere).
///
/// Requires a reachable Postgres instance (`DATABASE_URL`, see
/// `gaia-server/.env` / `docker-compose.dev.yml` — `postgres` service).
use std::time::Duration;

use axum_test::TestWebSocket;
use serde_json::{json, Value};

use gaia_engine::game_state::{FactionId, HexCoord, PlayerId, SetupPhase};
use gaia_engine::{data::load_factions, GamePhase, GameState};

use super::harness::{
    command_msg, next_command_id, receive_until, spawn_test_app, RoomCleanupGuard,
};

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn a_full_four_player_game_reaches_game_ended_with_real_scores() {
    let server = spawn_test_app().await;

    // ── Create room (host) via REST, exactly like the real client flow ─────
    let create_resp = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Host", "seed": "full-game-playthrough-e2e-seed" }))
        .await;
    create_resp.assert_status(axum::http::StatusCode::CREATED);
    let create_body = create_resp.json::<Value>();
    let room_code = create_body["room_code"]
        .as_str()
        .expect("create-room response should contain a string room_code")
        .to_string();
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

    let mut cmd_id = 0u32;
    revision = send_and_await(
        &mut host_ws,
        &room_code,
        &next_command_id("fgp", &mut cmd_id),
        revision,
        json!({ "type": "player_ready", "ready": true }),
    )
    .await;
    for (_, ws) in guests.iter_mut() {
        revision = send_and_await(
            ws,
            &room_code,
            &next_command_id("fgp", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }

    // ── Sequential faction selection (same as faction_selection_flow.rs) ──
    let picks = [
        (host_id, factions[0]),
        (guest_ids[0], factions[2]),
        (guest_ids[1], factions[4]),
        (guest_ids[2], factions[6]),
    ];
    for (picking_id, faction) in picks {
        let ws = ws_for(&mut host_ws, &mut guests, host_id, picking_id);
        revision = send_and_await(
            ws,
            &room_code,
            &next_command_id("fgp", &mut cmd_id),
            revision,
            json!({
                "type": "place_setup_action",
                "action": { "type": "SelectFaction", "faction": faction },
            }),
        )
        .await;
    }

    // ── Drive everything from here — starting-structure/booster setup,
    //    every round's income/Gaia pending decisions, and all 6 rounds of
    //    play — through one generic phase-driven loop. Every acting player
    //    just does the minimum legal thing (place on an open home planet,
    //    take the first available booster, resolve pending decisions with
    //    no side effects, and otherwise Pass) — the point is exercising the
    //    full round-to-game-end pipeline end to end, not full rules coverage. ─
    // `host_ws` never sent the last pick (`guest_ids[2]` did), so it's a
    // valid observer here — but it may also be holding several *older*,
    // still-unread snapshot broadcasts from the earlier picks in this same
    // loop (each `send_and_await` above only consumed
    // `command_accepted` on the sender's own connection, not the resulting
    // broadcast on every other connection) — drain fully rather than take
    // the first snapshot found, or this picks up a stale revision.
    let mut game_state = match drain_until_settled(&mut host_ws).await {
        Settled::GameEnded(msg) => {
            panic!("game ended unexpectedly during faction selection: {msg:?}")
        }
        Settled::Snapshot(snapshot) => {
            revision = snapshot["revision"]
                .as_u64()
                .expect("snapshot should carry a revision");
            snapshot_game_state(&snapshot, "after faction selection")
        }
    };

    let game_ended = loop {
        let (active_player, command) = decide_next_command(&game_state);

        let ws = ws_for(&mut host_ws, &mut guests, host_id, u64::from(active_player));
        // The accepted revision is intentionally discarded here — the
        // subsequent `drain_until_settled` observation below is what
        // actually advances `revision`/`game_state`, since a Pass that ends
        // a round can trigger further server-initiated snapshots beyond
        // this one command's own.
        send_and_await(
            ws,
            &room_code,
            &next_command_id("fgp", &mut cmd_id),
            revision,
            command,
        )
        .await;

        // Observe on a connection other than the sender, since the sender
        // may consume the room-wide broadcast before its own acknowledgement
        // (same reasoning as faction_selection_flow.rs).
        let observer_id = if active_player == host_id as PlayerId {
            guest_ids[0]
        } else {
            host_id
        };
        let observer = ws_for(&mut host_ws, &mut guests, host_id, observer_id);

        match drain_until_settled(observer).await {
            Settled::GameEnded(msg) => break msg,
            Settled::Snapshot(snapshot) => {
                revision = snapshot["revision"]
                    .as_u64()
                    .expect("snapshot should carry a revision");
                game_state = snapshot_game_state(&snapshot, "mid-playthrough");
            }
        }
    };

    // ── Assert the exact payload App.tsx/GameOverScreen consume ───────────
    assert_eq!(game_ended["type"], "game_ended");
    let final_scores = game_ended["final_scores"]
        .as_array()
        .expect("game_ended should carry a final_scores array");
    assert_eq!(
        final_scores.len(),
        4,
        "final_scores should have one entry per player, got {final_scores:?}"
    );
    let scored_players: std::collections::HashSet<u64> = final_scores
        .iter()
        .map(|pair| {
            pair.as_array()
                .and_then(|p| p.first())
                .and_then(Value::as_u64)
                .unwrap_or_else(|| {
                    panic!("each final_scores entry should be a [player_id, vp] pair, got {pair:?}")
                })
        })
        .collect();
    assert_eq!(
        scored_players,
        [host_id, guest_ids[0], guest_ids[1], guest_ids[2]]
            .into_iter()
            .collect(),
        "final_scores should cover exactly the 4 seated players"
    );
    let winner = game_ended["winner"]
        .as_u64()
        .expect("game_ended should carry a numeric winner");
    assert!(
        scored_players.contains(&winner),
        "winner {winner} should be one of the seated players {scored_players:?}"
    );
    println!(
        "Full 4-player playthrough reached game_ended: final_scores={:?}, winner={}",
        final_scores, winner
    );
}

/// Like `harness::send_command_and_await_accept`, but skips through a much
/// larger backlog of non-matching messages (2000, vs. the shared helper's
/// 40) before giving up. A full 6-round, 4-player playthrough sends far more
/// commands than the shorter setup-only flows the shared helper was written
/// for, and a player who goes many turns without being chosen as the
/// round-loop's observer (see `drain_until_settled` below) can accumulate a
/// sizeable backlog of still-unread broadcast `snapshot`s on their own
/// connection by the time they're next the sender — harmless to skip past,
/// but enough to blow through the shared helper's tighter bound.
async fn send_and_await(
    ws: &mut TestWebSocket,
    room_code: &str,
    command_id: &str,
    revision: u64,
    command: Value,
) -> u64 {
    ws.send_json(&command_msg(room_code, command_id, revision, command))
        .await;
    let accepted = receive_until_type(ws, "command_accepted").await;
    assert_eq!(
        accepted["command_id"], command_id,
        "command_accepted should echo back the command_id it acknowledges"
    );
    accepted["revision"]
        .as_u64()
        .expect("command_accepted should carry the new revision")
}

async fn receive_until_type(ws: &mut TestWebSocket, expected_type: &str) -> Value {
    for _ in 0..2000 {
        let msg = tokio::time::timeout(Duration::from_secs(5), ws.receive_json::<Value>())
            .await
            .unwrap_or_else(|_| panic!("timed out waiting for a `{expected_type}` message"));
        if msg["type"] == expected_type {
            return msg;
        }
    }
    panic!("did not receive a `{expected_type}` message within 2000 messages");
}

/// Picks the acting player's websocket by matching `player_id` against the
/// host's REST id or one of the three guests' ids.
fn ws_for<'a>(
    host_ws: &'a mut TestWebSocket,
    guests: &'a mut [(u64, TestWebSocket)],
    host_id: u64,
    player_id: u64,
) -> &'a mut TestWebSocket {
    if player_id == host_id {
        host_ws
    } else {
        &mut guests
            .iter_mut()
            .find(|(id, _)| *id == player_id)
            .unwrap_or_else(|| panic!("player id {player_id} must be a known room member"))
            .1
    }
}

fn snapshot_game_state(snapshot: &Value, label: &str) -> GameState {
    serde_json::from_value(snapshot["state"].clone())
        .unwrap_or_else(|error| panic!("[{label}] snapshot should deserialize: {error}"))
}

/// The one legal, side-effect-minimal action for whichever phase the game is
/// currently paused in, and the `PlayerId` who must submit it.
fn decide_next_command(game_state: &GameState) -> (PlayerId, Value) {
    match &game_state.phase {
        GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. }) => {
            let coord = open_home_planet(game_state, *active_player);
            (
                *active_player,
                json!({
                    "type": "place_setup_action",
                    "action": { "type": "PlaceStartingStructure", "coord": coord },
                }),
            )
        }
        GamePhase::Setup(SetupPhase::StartingBoosters { active_player, .. }) => {
            let booster_id = game_state
                .boosters
                .first()
                .unwrap_or_else(|| panic!("an initial booster should remain"))
                .0;
            (
                *active_player,
                json!({
                    "type": "place_setup_action",
                    "action": { "type": "SelectStartingBooster", "booster_id": booster_id },
                }),
            )
        }
        GamePhase::IncomeOrderPending { queue, .. } => {
            let entry = queue
                .first()
                .unwrap_or_else(|| panic!("income-order queue should not be empty"));
            (
                entry.player,
                json!({
                    "type": "place_game_action",
                    "action": { "type": "ChooseIncomeOrder", "charge_first": true },
                }),
            )
        }
        GamePhase::GaiaDecisionPending { queue, .. } => {
            let entry = queue
                .first()
                .unwrap_or_else(|| panic!("Gaia-decision queue should not be empty"));
            (
                entry.player,
                json!({
                    "type": "place_game_action",
                    "action": { "type": "FinishGaiaDecision" },
                }),
            )
        }
        GamePhase::ChargePowerPending { queue, .. } => {
            let entry = queue
                .first()
                .unwrap_or_else(|| panic!("charge-power queue should not be empty"));
            (
                entry.player,
                json!({
                    "type": "place_game_action",
                    "action": { "type": "ChargePower", "accept": false },
                }),
            )
        }
        GamePhase::ActionPhase { active_player } => {
            let player = *game_state
                .turn_order
                .get(*active_player)
                .unwrap_or_else(|| panic!("active_player index {active_player} out of range"));
            let booster_id = if game_state.round < 6 {
                Some(
                    game_state
                        .boosters
                        .first()
                        .unwrap_or_else(|| panic!("a booster should remain available to pass with"))
                        .0,
                )
            } else {
                None
            };
            (
                player,
                json!({
                    "type": "place_game_action",
                    "action": { "type": "Pass", "booster_id": booster_id },
                }),
            )
        }
        other => panic!("decide_next_command: unhandled phase {other:?}"),
    }
}

fn open_home_planet(game_state: &GameState, player_id: PlayerId) -> HexCoord {
    let faction = game_state
        .player(player_id)
        .and_then(|player| player.faction)
        .unwrap_or_else(|| panic!("placement player {player_id} should have a faction"));
    let home_planet = load_factions()
        .factions
        .into_iter()
        .find(|data| data.faction_id() == Some(faction))
        .and_then(|data| data.home_planet_type())
        .unwrap_or_else(|| panic!("{faction:?} should have a home planet"));
    game_state
        .board
        .hexes
        .values()
        .find(|hex| {
            hex.planet.as_ref().is_some_and(|planet| {
                planet.planet_type == home_planet
                    && !planet.is_gaia_formed
                    && planet.owner.is_none()
                    && hex.structures.is_empty()
            })
        })
        .map(|hex| hex.coord)
        .unwrap_or_else(|| {
            panic!(
                "an open {home_planet:?} planet should exist for player {player_id} ({faction:?})"
            )
        })
}

enum Settled {
    Snapshot(Value),
    GameEnded(Value),
}

/// Drains `ws` until no new message arrives for a short idle window,
/// returning the last `snapshot` seen — or short-circuiting the moment a
/// `game_ended` broadcast shows up (the server tears down the room's event
/// bus entry right after sending it, so there's nothing further to wait for).
async fn drain_until_settled(ws: &mut TestWebSocket) -> Settled {
    let mut latest_snapshot: Option<Value> = None;
    for _ in 0..200 {
        match tokio::time::timeout(Duration::from_millis(1500), ws.receive_json::<Value>()).await {
            Ok(msg) => {
                if msg["type"] == "game_ended" {
                    return Settled::GameEnded(msg);
                }
                if msg["type"] == "snapshot" {
                    latest_snapshot = Some(msg);
                }
                // Other broadcasts (round_ended, player_joined, ...) are
                // ignored — the next snapshot/game_ended is authoritative.
            }
            Err(_) => break, // no message within the idle window — settled.
        }
    }
    Settled::Snapshot(latest_snapshot.unwrap_or_else(|| {
        panic!("drain_until_settled observed no snapshot at all before going quiet")
    }))
}
