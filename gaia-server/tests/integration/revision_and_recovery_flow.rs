/// Integration tests for the room-control-revision machinery itself:
/// optimistic-concurrency rejection, command_id idempotent replay,
/// disconnect/reconnect pause without a revision change, and restart
/// recovery — the "coordinator-order tests" and "executable transaction
/// fixtures" the PRD's concurrency section calls for. Complements
/// `faction_selection_flow.rs`, which exercises the same envelope machinery
/// end-to-end but doesn't specifically probe these edge cases.
///
/// Requires a reachable Postgres instance (`DATABASE_URL`, see
/// `gaia-server/.env` / `docker-compose.dev.yml` — `postgres` service).
use axum_test::{TestServer, TestWebSocket};
use serde_json::{json, Value};

use gaia_engine::game_state::{HexCoord, SetupPhase};
use gaia_engine::{data::load_factions, GamePhase, GameState};

use super::harness::{
    next_command_id, receive_until, receive_until_revision, send_command_and_await_accept,
    spawn_test_app, RoomCleanupGuard,
};

struct Player {
    id: u64,
    token: String,
    ws: TestWebSocket,
}

/// Creates a room, joins 4 players over WS, and readies all of them up —
/// leaving the room in `FactionSelection` (a `GameState` exists, so
/// `game_snapshots` has a row; `room.paused` tracking doesn't engage until
/// `InGame`, see the pause test for the extra steps it takes to get there).
/// Returns `(room_code, players[0]=host..=3, revision)`.
async fn ready_up_four_players(server: &TestServer) -> (String, Vec<Player>, u64) {
    let create_resp = server
        .post("/api/rooms")
        .json(&json!({ "nickname": "Host", "seed": format!("revision-tests-{}", uuid::Uuid::new_v4()) }))
        .await;
    create_resp.assert_status(axum::http::StatusCode::CREATED);
    let create_body = create_resp.json::<Value>();
    let room_code = create_body["room_code"]
        .as_str()
        .expect("room_code present")
        .to_string();
    let host_id = create_body["player_id"]
        .as_u64()
        .expect("player_id present");
    let host_token = create_body["session_token"]
        .as_str()
        .expect("session_token present")
        .to_string();

    let mut host_ws = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    host_ws
        .send_json(&json!({
            "type": "join_room", "room_code": room_code, "nickname": "Host",
            "session_token": host_token,
        }))
        .await;
    let host_joined = receive_until(&mut host_ws, "room_joined").await;
    let mut revision = host_joined["revision"].as_u64().expect("revision present");

    let mut players = vec![Player {
        id: host_id,
        token: host_token,
        ws: host_ws,
    }];
    for nickname in ["P2", "P3", "P4"] {
        let mut ws = server
            .get_websocket(&format!("/ws/{room_code}"))
            .await
            .into_websocket()
            .await;
        ws.send_json(&json!({
            "type": "join_room", "room_code": room_code, "nickname": nickname,
            "session_token": Value::Null,
        }))
        .await;
        let joined = receive_until(&mut ws, "room_joined").await;
        let id = joined["player_id"].as_u64().expect("player_id present");
        let token = joined["session_token"]
            .as_str()
            .expect("session_token present")
            .to_string();
        players.push(Player { id, token, ws });
    }

    let mut cmd_id = 0u32;
    for player in players.iter_mut() {
        revision = send_command_and_await_accept(
            &mut player.ws,
            &room_code,
            &next_command_id("ready", &mut cmd_id),
            revision,
            json!({ "type": "player_ready", "ready": true }),
        )
        .await;
    }

    (room_code, players, revision)
}

async fn drive_to_action_phase(
    room_code: &str,
    players: &mut [Player],
    mut revision: u64,
    cmd_id: &mut u32,
) -> (u64, Value) {
    let faction_names = ["Terrans", "Xenos", "Taklons", "HadschHallas"];
    for (i, faction) in faction_names.iter().enumerate() {
        revision = send_command_and_await_accept(
            &mut players[i].ws,
            room_code,
            &next_command_id("pause", cmd_id),
            revision,
            json!({
                "type": "place_setup_action",
                "action": { "type": "SelectFaction", "faction": faction },
            }),
        )
        .await;
    }

    let mut snapshot = receive_until_revision(&mut players[0].ws, revision).await;
    let mut game_state = snapshot_game_state(&snapshot, "after faction selection");

    loop {
        let (active_player, command) = match &game_state.phase {
            GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. }) => {
                let coord = open_home_planet(&game_state, *active_player);
                (
                    *active_player,
                    json!({
                        "type": "place_setup_action",
                        "action": {
                            "type": "PlaceStartingStructure",
                            "coord": coord,
                        },
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
                        "action": {
                            "type": "SelectStartingBooster",
                            "booster_id": booster_id,
                        },
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
                        "action": {
                            "type": "ChooseIncomeOrder",
                            "charge_first": true,
                        },
                    }),
                )
            }
            GamePhase::ActionPhase { active_player: 0 } => return (revision, snapshot),
            ref phase => {
                panic!("unexpected phase while driving setup before disconnect: {phase:?}")
            }
        };

        let active_index = players
            .iter()
            .position(|player| player.id == u64::from(active_player))
            .unwrap_or_else(|| {
                panic!("active setup player {active_player} should have a websocket")
            });
        revision = send_command_and_await_accept(
            &mut players[active_index].ws,
            room_code,
            &next_command_id("pause", cmd_id),
            revision,
            command,
        )
        .await;

        let observer_index = if active_index == 0 { 1 } else { 0 };
        snapshot = receive_until_revision(&mut players[observer_index].ws, revision).await;
        game_state = snapshot_game_state(&snapshot, "during setup completion before disconnect");
    }
}

fn snapshot_game_state(snapshot: &Value, label: &str) -> GameState {
    serde_json::from_value(snapshot["state"].clone())
        .unwrap_or_else(|error| panic!("[{label}] snapshot should deserialize: {error}"))
}

fn open_home_planet(game_state: &GameState, player_id: u8) -> HexCoord {
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
            let matching_planets = game_state
                .board
                .hexes
                .values()
                .filter(|hex| {
                    hex.planet
                        .as_ref()
                        .is_some_and(|planet| planet.planet_type == home_planet)
                })
                .count();
            panic!(
                "an open {home_planet:?} planet should exist for player {player_id} ({faction:?}); \
                 board contains {matching_planets} matching planets"
            )
        })
}

fn assert_snapshot_reached_action_phase(snapshot: &Value, label: &str, expected_revision: u64) {
    assert_eq!(
        snapshot["revision"].as_u64(),
        Some(expected_revision),
        "[{label}] snapshot should be at the revision the last accepted command reported"
    );
    let game_state = snapshot_game_state(snapshot, label);
    assert_eq!(
        game_state.phase,
        GamePhase::ActionPhase { active_player: 0 },
        "[{label}] game should start in ActionPhase with active_player 0"
    );
    assert!(
        game_state
            .players
            .iter()
            .all(|player| player.faction.is_some()),
        "[{label}] every player should have an assigned faction once selection completes"
    );
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn revision_conflict_rejects_stale_expected_revision() {
    let server = spawn_test_app().await;
    let (room_code, mut players, revision) = ready_up_four_players(&server).await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let host = &mut players[0];

    // All four seats are ready, so the room is already in `FactionSelection`
    // (a `player_ready` command would now be rejected as `WrongPhase`) — use
    // a `place_setup_action` instead, which is valid here.
    let select_terrans = json!({
        "type": "place_setup_action",
        "action": { "type": "SelectFaction", "faction": "Terrans" },
    });

    // Send with a deliberately stale `expected_revision` (one behind).
    let stale = revision - 1;
    host.ws
        .send_json(&super::harness::command_msg(
            &room_code,
            "stale-cmd",
            stale,
            select_terrans.clone(),
        ))
        .await;
    let rejected = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(rejected["command_id"].as_str(), Some("stale-cmd"));
    assert_eq!(
        rejected["rejection"]["code"].as_str(),
        Some("REVISION_CONFLICT")
    );
    assert_eq!(
        rejected["revision"].as_u64(),
        Some(revision),
        "rejection should report the room's actual current revision, not the stale one sent"
    );

    // The room must be untouched: a follow-up command at the *correct*
    // revision should still land at exactly `revision + 1`, proving the
    // stale command neither mutated state nor consumed a revision slot.
    let mut cmd_id = 0u32;
    let next = send_command_and_await_accept(
        &mut host.ws,
        &room_code,
        &next_command_id("revconflict", &mut cmd_id),
        revision,
        select_terrans,
    )
    .await;
    assert_eq!(next, revision + 1);
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn duplicate_command_id_replays_recorded_result() {
    let server = spawn_test_app().await;
    let (room_code, mut players, revision) = ready_up_four_players(&server).await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());

    // First selector (host, whoever's turn it is per clockwise order — the
    // host always goes first, see `SetupPolicy::initialize`) picks Terrans
    // with a fixed command_id.
    let host = &mut players[0];
    let command_id = "select-terrans";
    let command = json!({
        "type": "place_setup_action",
        "action": { "type": "SelectFaction", "faction": "Terrans" },
    });
    host.ws
        .send_json(&super::harness::command_msg(
            &room_code,
            command_id,
            revision,
            command.clone(),
        ))
        .await;
    let first_accept = receive_until(&mut host.ws, "command_accepted").await;
    let accepted_revision = first_accept["revision"].as_u64().expect("revision present");
    assert_eq!(accepted_revision, revision + 1);

    // Resend the *exact same* envelope (same command_id, same — now stale —
    // expected_revision). If this were reprocessed instead of replayed, it
    // would be rejected as a revision conflict (or, worse, silently
    // re-applied and skip a player's turn). Idempotent replay must instead
    // return the original recorded outcome untouched.
    host.ws
        .send_json(&super::harness::command_msg(
            &room_code, command_id, revision, command,
        ))
        .await;
    let replay_accept = receive_until(&mut host.ws, "command_accepted").await;
    assert_eq!(
        replay_accept["revision"].as_u64(),
        Some(accepted_revision),
        "a replayed command_id must return the exact same recorded revision, not reprocess"
    );

    // Prove the mutation itself only happened once: the *second* player in
    // clockwise order must still be able to act at `accepted_revision` — if
    // the duplicate had actually reprocessed, the room would have advanced
    // to `accepted_revision + 1` and this would come back as a conflict.
    let mut cmd_id = 0u32;
    let p2 = &mut players[1];
    let p2_revision = send_command_and_await_accept(
        &mut p2.ws,
        &room_code,
        &next_command_id("dup", &mut cmd_id),
        accepted_revision,
        json!({
            "type": "place_setup_action",
            "action": { "type": "SelectFaction", "faction": "Xenos" },
        }),
    )
    .await;
    assert_eq!(p2_revision, accepted_revision + 1);
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn rejected_command_id_replays_original_rejection() {
    let server = spawn_test_app().await;
    let (room_code, mut players, revision) = ready_up_four_players(&server).await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    let host = &mut players[0];
    let command_id = "rejected-ready-replay";
    let command = json!({ "type": "player_ready", "ready": false });

    host.ws
        .send_json(&super::harness::command_msg(
            &room_code,
            command_id,
            revision,
            command.clone(),
        ))
        .await;
    let first = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(first["rejection"]["code"].as_str(), Some("WRONG_PHASE"));
    assert_eq!(first["revision"].as_u64(), Some(revision));

    host.ws
        .send_json(&super::harness::command_msg(
            &room_code, command_id, revision, command,
        ))
        .await;
    let replay = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(
        replay["rejection"], first["rejection"],
        "a rejected command replay must preserve its original code and message"
    );
    assert_eq!(replay["revision"].as_u64(), Some(revision));
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn disconnect_pauses_and_reconnect_resumes_without_revision_change() {
    let server = spawn_test_app().await;
    let (room_code, mut players, mut revision) = ready_up_four_players(&server).await;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());

    // Drive the whole sequential setup flow to a *verified* round-one
    // ActionPhase snapshot. Faction selection alone only enters interactive
    // setup (starting structures, boosters, and possible income decisions);
    // pause tracking only engages after gameplay is truly InGame.
    let mut cmd_id = 0u32;
    let (settled_revision, action_snapshot) =
        drive_to_action_phase(&room_code, &mut players, revision, &mut cmd_id).await;
    revision = settled_revision;
    assert_snapshot_reached_action_phase(&action_snapshot, "before disconnect", revision);
    let revision_before_disconnect = revision;

    // Disconnect P2 (a proper WS close, not just dropping the value, so the
    // server's `socket.recv()` observes `Message::Close` promptly).
    let p2_token = players[1].token.clone();
    let p2_id = players[1].id;
    let disconnected = players.remove(1);
    disconnected.ws.close().await;

    let host = &mut players[0];
    let paused_msg = receive_until(&mut host.ws, "room_paused").await;
    assert_eq!(paused_msg["paused"].as_bool(), Some(true));
    let missing: Vec<u64> = paused_msg["missing_seats"]
        .as_array()
        .expect("missing_seats is an array")
        .iter()
        .map(|v| v.as_u64().expect("seat id is a number"))
        .collect();
    assert_eq!(missing, vec![p2_id]);

    // Commands must be rejected while paused, and must not advance revision.
    host.ws
        .send_json(&super::harness::command_msg(
            &room_code,
            "while-paused",
            revision_before_disconnect,
            json!({
                "type": "place_game_action",
                "action": { "type": "Pass", "booster_id": 1 },
            }),
        ))
        .await;
    let rejected = receive_until(&mut host.ws, "command_rejected").await;
    assert_eq!(rejected["rejection"]["code"].as_str(), Some("ROOM_PAUSED"));

    // Reconnect P2 with its original session token — same seat, not a new one.
    let mut p2_ws = server
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    p2_ws
        .send_json(&json!({
            "type": "join_room", "room_code": room_code, "nickname": "P2",
            "session_token": p2_token,
        }))
        .await;
    let p2_rejoined = receive_until(&mut p2_ws, "room_joined").await;
    assert_eq!(p2_rejoined["player_id"].as_u64(), Some(p2_id));

    let resumed_msg = receive_until(&mut host.ws, "room_paused").await;
    assert_eq!(resumed_msg["paused"].as_bool(), Some(false));

    // The whole pause window must not have touched the revision.
    assert_eq!(
        p2_rejoined["revision"].as_u64(),
        Some(revision_before_disconnect),
        "revision must be unchanged across the entire disconnect/reconnect window"
    );
}

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn restart_recovery_reconstructs_committed_revision() {
    // First "process": creates the room and reaches FactionSelection (a
    // `game_snapshots` row now exists at `revision`).
    let server_before = spawn_test_app().await;
    let (room_code, players, revision) = ready_up_four_players(&server_before).await;
    let host_token = players[0].token.clone();
    let host_id = players[0].id;
    let _cleanup = RoomCleanupGuard::new(room_code.clone());
    drop(server_before);

    // A brand new `spawn_test_app()` call against the *same* Postgres
    // database is a fresh, empty in-memory `RoomManager`/`SessionManager` —
    // exactly what a real process restart leaves behind. Recovery must come
    // entirely from the DB: `AppState::ensure_room_loaded`, exercised here
    // via the REST `get_room` endpoint (which calls it before reading).
    let server_after = spawn_test_app().await;
    let recovered = server_after.get(&format!("/api/rooms/{room_code}")).await;
    recovered.assert_status_ok();
    let body = recovered.json::<Value>();
    assert_eq!(body["player_count"].as_u64(), Some(4));

    // Full round-trip through the WS reconnect path too — the room is no
    // longer in `Lobby` (it's in `FactionSelection`), so only a *token*-based
    // reconnect can succeed here (a fresh, tokenless join would be rejected
    // with `RoomAlreadyStarted`); the token itself is DB-persisted
    // (`sessions` table, see `SessionManager`) and so survives the "restart"
    // just as the room state does. The rebuilt roster the token resolves
    // against comes from the *snapshot's* `GameState.players`, not a
    // durably-stored lobby roster (a gap called out in the README), so this
    // is the realistic post-restart recovery path for an in-progress game.
    let mut ws = server_after
        .get_websocket(&format!("/ws/{room_code}"))
        .await
        .into_websocket()
        .await;
    ws.send_json(&json!({
        "type": "join_room", "room_code": room_code, "nickname": "Host",
        "session_token": host_token,
    }))
    .await;
    let joined = receive_until(&mut ws, "room_joined").await;
    assert_eq!(
        joined["player_id"].as_u64(),
        Some(host_id),
        "the persisted session token must resolve back to the same seat after a restart"
    );
    assert_eq!(
        joined["revision"].as_u64(),
        Some(revision),
        "the rehydrated room's revision must match what was committed before the restart"
    );
}
