use axum_test::TestServer;
use gaia_engine::{GameAction, GamePhase, RuleEngine, SetupAction, SetupPhase};
use gaia_protocol::{CommandId, Revision};
use gaia_server::{
    handlers::rest::CreateDevGameRequest,
    services::{faction_selection::FactionSelectionService, game_action::GameActionService},
    state::AppState,
};

use super::harness::RoomCleanupGuard;

#[tokio::test]
#[ignore = "requires PostgreSQL"]
async fn manual_dev_controller_places_every_mine_and_passes_every_seat_across_six_rounds() {
    let _ = dotenvy::from_path(concat!(env!("CARGO_MANIFEST_DIR"), "/.env"));
    let pool = sqlx::PgPool::connect(&std::env::var("DATABASE_URL").expect("test DB URL"))
        .await
        .expect("connect test DB");
    let app = AppState::new(pool);
    let _server =
        TestServer::new(gaia_server::router::build_router(app.clone())).expect("test server");
    let (_, axum::Json(created)) = gaia_server::handlers::rest::create_dev_game(
        axum::extract::State(app.clone()),
        axum::Json(CreateDevGameRequest {
            full_setup: false,
            nickname: None,
            setup_mode: None,
            faction: None,
            seed: Some("manual-dev-regression".into()),
        }),
    )
    .await
    .expect("create manual DEV game");
    let code = created.room_code;
    let _cleanup = RoomCleanupGuard::new(&code);
    let controller = created.player_id;
    let mut revision = 0;
    let mut placements = 0;
    loop {
        let state = app
            .rooms
            .read()
            .await
            .get_room(&code)
            .expect("room")
            .game_state
            .clone()
            .expect("state");
        let action = match state.phase {
            GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. }) => {
                let action = state
                    .board
                    .hexes
                    .keys()
                    .find_map(|coord| {
                        let action = SetupAction::PlaceStartingStructure { coord: *coord };
                        RuleEngine::apply_setup_action(
                            &mut state.clone(),
                            active_player,
                            action.clone(),
                        )
                        .ok()
                        .map(|_| action)
                    })
                    .expect("legal starting coordinate");
                placements += 1;
                action
            }
            GamePhase::Setup(SetupPhase::StartingBoosters { .. }) => {
                SetupAction::SelectStartingBooster {
                    booster_id: state.boosters[0].0,
                }
            }
            GamePhase::ActionPhase { .. } => break,
            phase => panic!("unexpected setup phase: {phase:?}"),
        };
        let outcome = FactionSelectionService::process_setup_action(
            &app,
            &code,
            controller,
            action,
            CommandId::parse(&format!("manual-setup-{revision}")).expect("command ID"),
            Revision::new(revision).expect("revision"),
        )
        .await
        .expect("controller should act for current setup seat");
        revision = outcome.revision.get();
        if revision == 1 {
            // Simulate losing all in-memory Room metadata after one human placement.
            app.rooms.write().await.remove_room(&code);
            app.ensure_room_loaded(&code)
                .await
                .expect("restore DEV room");
            let rooms = app.rooms.read().await;
            let room = rooms.get_room(&code).expect("restored room");
            assert_eq!(room.dev_human_player, Some(controller));
            assert_eq!(
                room.players.len(),
                1,
                "virtual seats must not block reconnect presence"
            );
        }
    }
    assert_eq!(
        placements, 9,
        "Terrans 2 + Xenos 3 + Taklons 2 + Hadsch Hallas 2 must all be manual"
    );
    let mut passes = 0;
    let mut undo_checked = false;
    for _ in 0..80 {
        let state = app
            .rooms
            .read()
            .await
            .get_room(&code)
            .expect("room")
            .game_state
            .clone()
            .expect("state");
        let active = match &state.phase {
            GamePhase::ActionPhase { active_player } => state.turn_order[*active_player],
            GamePhase::IncomeOrderPending { queue, .. } => queue[0].player,
            GamePhase::GaiaDecisionPending { queue, .. } => queue[0].player,
            GamePhase::Ended { .. } => break,
            phase => panic!("unexpected round phase: {phase:?}"),
        };
        let mut action = RuleEngine::get_valid_actions(&state, active)
            .into_iter()
            .find(|action| {
                matches!(
                    action,
                    GameAction::Pass { .. }
                        | GameAction::ChooseIncomeOrder {
                            charge_first: false
                        }
                        | GameAction::FinishGaiaDecision
                )
            })
            .expect("manual pass or pending decision");
        if matches!(action, GameAction::Pass { .. }) {
            passes += 1;
            action = GameAction::Pass {
                booster_id: (state.round < 6).then(|| state.boosters[0].0),
            };
        }
        GameActionService::process_action(
            &app,
            &code,
            controller,
            action,
            CommandId::parse(&format!("manual-action-{revision}")).expect("command ID"),
            Revision::new(revision).expect("revision"),
        )
        .await
        .expect("controller should act for current game seat");
        revision = app
            .rooms
            .read()
            .await
            .get_room(&code)
            .expect("room")
            .revision;
        if passes == 2 && !undo_checked {
            gaia_server::services::undo::UndoService::request_turn_undo(
                &app,
                &code,
                controller,
                CommandId::parse("manual-undo-other-seat").expect("command ID"),
                Revision::new(revision).expect("revision"),
            )
            .await
            .expect("controller can undo previous seat without approval");
            let rooms = app.rooms.read().await;
            let room = rooms.get_room(&code).expect("room");
            let restored = room.game_state.as_ref().expect("state");
            assert_eq!(restored.phase, state.phase);
            assert!(restored.undo_state.pending_request.is_none());
            assert!(!restored.player(active).expect("acting seat").passed);
            revision = room.revision;
            passes -= 1;
            undo_checked = true;
        }
    }
    let rooms = app.rooms.read().await;
    let state = rooms
        .get_room(&code)
        .expect("room")
        .game_state
        .as_ref()
        .expect("state");
    assert!(undo_checked);
    assert_eq!(
        passes, 24,
        "each of four seats must be passed manually in every round"
    );
    assert!(matches!(state.phase, GamePhase::Ended { .. }));
}

#[tokio::test]
#[ignore = "requires PostgreSQL"]
async fn full_dev_setup_keeps_randomizer_and_bidding_interactive() {
    use super::harness::{command_msg, receive_until, receive_until_revision, spawn_test_app};
    use serde_json::{json, Value};
    let server = spawn_test_app().await;
    for mode in ["bidding", "sequential"] {
        let response = server.post("/api/dev-games").json(&json!({
            "nickname": "Module test", "full_setup": true, "setup_mode": mode, "seed": "manual-full-start"
        })).await;
        response.assert_status(axum::http::StatusCode::CREATED);
        let body = response.json::<Value>();
        let code = body["room_code"].as_str().expect("room");
        let _cleanup = RoomCleanupGuard::new(code);
        let controller = body["player_id"].as_u64().expect("controller") as u8;
        assert_eq!(body["players"].as_array().expect("roster").len(), 4);
        assert!(body["game_state"]["players"]
            .as_array()
            .expect("players")
            .iter()
            .all(|p| p["faction"].is_null()));
        let mut ws = server
            .get_websocket(&format!("/ws/{code}"))
            .await
            .into_websocket()
            .await;
        ws.send_json(&json!({"type":"join_room","room_code":code,"nickname":"Module test","session_token":body["session_token"]})).await;
        receive_until(&mut ws, "room_joined").await;
        let lobby = receive_until_revision(&mut ws, 0).await;
        assert_eq!(
            lobby["state"]["phase"], "lobby",
            "must not skip randomizer preview"
        );
        let reroll = server
            .post(&format!("/api/rooms/{code}/regenerate"))
            .json(&json!({
                "session_token":body["session_token"], "seed":"manual-full-reroll"
            }))
            .await;
        reroll.assert_status_ok();
        assert_eq!(reroll.json::<Value>()["setup_mode"], mode);
        let lobby = receive_until_revision(&mut ws, 1).await;
        assert_eq!(lobby["state"]["phase"], "lobby");
        assert_eq!(lobby["state"]["setup"]["seed"], "manual-full-reroll");
        let preview = server
            .get(&format!("/api/rooms/{code}/preview_board"))
            .await;
        preview.assert_status_ok();
        ws.send_json(&command_msg(
            code,
            "full-ready",
            1,
            json!({"type":"player_ready","ready":true}),
        ))
        .await;
        let mut frame = receive_until_revision(&mut ws, 2).await;
        assert!(frame["state"]["phase"]["Setup"][if mode == "bidding" {
            "Bidding"
        } else {
            "FactionSelection"
        }]
        .is_object());
        let mut revision = 2;
        let mut choices = 0;
        let mut placements = 0;
        let mut booster_choices = 0;
        for index in 0..100 {
            let state: gaia_engine::GameState =
                serde_json::from_value(frame["state"].clone()).expect("state");
            assert_eq!(state.dev_controller, Some(controller));
            let (actor, action) = match state.phase {
                GamePhase::Setup(SetupPhase::Bidding { active_player }) => {
                    (active_player, SetupAction::PassBid)
                }
                GamePhase::Setup(SetupPhase::BiddingChoice { winner }) => {
                    choices += 1;
                    let bidding = state.bidding.as_ref().expect("bidding");
                    (
                        winner,
                        SetupAction::ChooseBidReward {
                            faction: bidding.available_factions[0],
                            turn_position: bidding.available_turn_positions[0],
                        },
                    )
                }
                GamePhase::Setup(SetupPhase::FactionSelection { active_player }) => {
                    choices += 1;
                    (
                        active_player,
                        SetupAction::SelectFaction {
                            faction: state
                                .faction_selection
                                .as_ref()
                                .expect("selection")
                                .available_factions[0],
                        },
                    )
                }
                GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. }) => {
                    placements += 1;
                    let action = state
                        .board
                        .hexes
                        .keys()
                        .find_map(|coord| {
                            let action = SetupAction::PlaceStartingStructure { coord: *coord };
                            RuleEngine::apply_setup_action(
                                &mut state.clone(),
                                active_player,
                                action.clone(),
                            )
                            .ok()
                            .map(|_| action)
                        })
                        .expect("legal placement");
                    (active_player, action)
                }
                GamePhase::Setup(SetupPhase::StartingBoosters { active_player, .. }) => {
                    booster_choices += 1;
                    (
                        active_player,
                        SetupAction::SelectStartingBooster {
                            booster_id: state.boosters[0].0,
                        },
                    )
                }
                GamePhase::Setup(ref phase) => panic!("unexpected setup phase: {phase:?}"),
                _ => {
                    assert_eq!(state.round, 1);
                    assert!(
                        state.players.iter().all(|player| {
                            player.resources.ore < 30
                                && player.resources.credits < 50
                                && player.resources.knowledge < 30
                                && player.resources.qic < 20
                                && player.resources.power.bowl3 < 20
                        }),
                        "all manual DEV seats must retain normal setup and income resources"
                    );
                    break;
                }
            };
            let mut expected_state = state.clone();
            RuleEngine::apply_setup_action(&mut expected_state, actor, action.clone())
                .expect("legal manual choice");
            let expected_resources = if expected_state.phase
                == GamePhase::Setup(SetupPhase::Complete)
            {
                RuleEngine::start_first_round(&mut expected_state).expect("normal first income");
                Some(
                    expected_state
                        .players
                        .iter()
                        .map(|player| player.resources.clone())
                        .collect::<Vec<_>>(),
                )
            } else {
                None
            };
            ws.send_json(&command_msg(
                code,
                &format!("full-step-{index}"),
                revision,
                json!({"type":"place_setup_action","action":action}),
            ))
            .await;
            revision += 1;
            frame = receive_until_revision(&mut ws, revision).await;
            if let Some(expected) = expected_resources {
                let actual: gaia_engine::GameState =
                    serde_json::from_value(frame["state"].clone()).expect("state");
                assert_eq!(
                    actual
                        .players
                        .iter()
                        .map(|player| player.resources.clone())
                        .collect::<Vec<_>>(),
                    expected,
                    "DEV must preserve every seat's normal RuleEngine setup and first income"
                );
            }
        }
        // Standard bidding assigns the sole remaining faction/seat automatically.
        assert_eq!(choices, if mode == "bidding" { 3 } else { 4 });
        assert!(placements >= 7, "no initial placements were automated");
        assert_eq!(booster_choices, 4);
    }
}

#[tokio::test]
#[ignore = "requires PostgreSQL"]
async fn manual_dev_tools_refill_persist_and_delete_only_owned_sandbox() {
    let _ = dotenvy::from_path(concat!(env!("CARGO_MANIFEST_DIR"), "/.env"));
    let pool = sqlx::PgPool::connect(&std::env::var("DATABASE_URL").expect("test DB URL"))
        .await.expect("DB");
    let app = AppState::new(pool.clone());
    let server = TestServer::new(gaia_server::router::build_router(app.clone())).expect("server");
    let created: serde_json::Value = server.post("/api/dev-games")
        .json(&serde_json::json!({"seed":"dev-tools-test"})).await.json();
    let code = created["room_code"].as_str().expect("code");
    let _cleanup = RoomCleanupGuard::new(code);
    let token = created["session_token"].as_str().expect("token");
    // Isolate controls from setup; seed committed power to verify all three bowls refill while Gaia stays unchanged.
    {
        let mut rooms = app.rooms.write().await;
        let state = rooms.get_room_mut(code).expect("room").game_state.as_mut().expect("state");
        state.phase = GamePhase::ActionPhase { active_player: 0 };
        for player in &mut state.players {
            player.resources.power.bowl3 = 3;
            player.resources.power.gaia_bowl = 2;
        }
    }
    let req = serde_json::json!({
        "session_token":token, "command_id":"dev-refill-test", "expected_revision":0
    });
    server.post(&format!("/api/rooms/{code}/dev-refill")).json(&serde_json::json!({
        "session_token":"invalid", "command_id":"invalid-test", "expected_revision":0
    })).await.assert_status_unauthorized();
    server.post(&format!("/api/rooms/{code}/dev-refill")).json(&req).await.assert_status_ok();
    // Same command ID must not refill again or advance revision.
    server.post(&format!("/api/rooms/{code}/dev-refill")).json(&req).await.assert_status_ok();
    app.rooms.write().await.remove_room(code);
    app.ensure_room_loaded(code).await.expect("reload persisted resources");
    {
        let rooms = app.rooms.read().await;
        let room = rooms.get_room(code).expect("restored");
        assert_eq!(room.revision, 1);
        for p in &room.game_state.as_ref().expect("state").players {
            assert_eq!((p.resources.ore, p.resources.credits, p.resources.knowledge, p.resources.qic), (250,250,250,250));
            assert_eq!((p.resources.power.bowl1,p.resources.power.bowl2,p.resources.power.bowl3,p.resources.power.gaia_bowl), (10,10,10,2));
        }
    }
    // A valid session for a normal room is not DEV authority, even for its host.
    let ordinary: serde_json::Value = server.post("/api/rooms").json(&serde_json::json!({"nickname":"ordinary"})).await.json();
    let normal_code = ordinary["room_code"].as_str().expect("normal code");
    let _normal_cleanup = RoomCleanupGuard::new(normal_code);
    for tool in ["refill", "delete"] {
        server.post(&format!("/api/rooms/{normal_code}/dev-{tool}")).json(&serde_json::json!({
            "session_token":ordinary["session_token"], "command_id":format!("normal-{tool}"), "expected_revision":0
        })).await.assert_status_forbidden();
        server.post(&format!("/api/rooms/{normal_code}/dev-{tool}")).json(&req).await.assert_status_unauthorized();
    }
    server.post(&format!("/api/rooms/{code}/dev-delete")).json(&req).await.assert_status_unprocessable_entity();
    server.post(&format!("/api/rooms/{code}/dev-delete")).json(&serde_json::json!({
        "session_token":token, "command_id":"delete-test", "expected_revision":1
    })).await.assert_status_ok();
    assert!(app.rooms.read().await.get_room(code).is_none());
    assert!(app.sessions.validate(token).await.expect("session lookup").is_none());
    let remaining: (i64,) = sqlx::query_as("SELECT COUNT(*) FROM game_snapshots WHERE room_code=$1").bind(code).fetch_one(&pool).await.expect("snapshots");
    assert_eq!(remaining.0, 0);
    assert!(app.rooms.read().await.get_room(normal_code).is_some());
}
