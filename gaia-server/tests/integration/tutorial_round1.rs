use super::harness::{command_msg, receive_until, RoomCleanupGuard};
use axum_test::TestServerConfig;
use gaia_engine::{tutorial, GameAction, RuleError};
use gaia_protocol::{CommandId, Revision};
use gaia_server::{
    coordinator::CommandError, repository::GameRepository,
    services::game_action::GameActionService, state::AppState,
};
use serde_json::json;

#[tokio::test]
#[ignore = "requires DATABASE_URL"]
async fn tutorial_rejects_mismatches_replays_and_recovers_without_public_records() {
    let _ = dotenvy::from_path(concat!(env!("CARGO_MANIFEST_DIR"), "/.env"));
    let pool = sqlx::PgPool::connect(&std::env::var("DATABASE_URL").expect("test DB URL"))
        .await
        .expect("test DB");
    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("migrations");
    let app = AppState::new(pool);
    let server = TestServerConfig::builder()
        .http_transport()
        .build_server(gaia_server::router::build_router(app.clone()))
        .expect("server");
    let response = server.post("/api/tutorial-games").await;
    response.assert_status(axum::http::StatusCode::CREATED);
    let body: serde_json::Value = response.json();
    let code = body["room_code"].as_str().expect("code");
    let id = body["player_id"].as_u64().expect("player") as u8;
    let _cleanup = RoomCleanupGuard::new(code);
    let listed: serde_json::Value = server.get("/api/rooms").await.json();
    assert!(!listed.to_string().contains(code));
    let repo = GameRepository::new(app.db.clone());
    let (mut revision, mut snapshot) = repo
        .load_latest_snapshot(code)
        .await
        .expect("load")
        .expect("snapshot");
    assert_eq!(snapshot.tutorial.as_ref().expect("tutorial").step, 1);
    let wrong = [
        GameAction::AcademyQicAction,
        GameAction::Build {
            coord: gaia_engine::game_state::HexCoord::new(5, -6),
        },
    ];
    for (index, action) in wrong.into_iter().enumerate() {
        let before = snapshot.serialize();
        let result = GameActionService::process_action(
            &app,
            code,
            id,
            action,
            CommandId::parse(&format!("wrong-{index}")).expect("id"),
            Revision::new(revision as u64).expect("revision"),
        )
        .await;
        assert!(matches!(
            result,
            Err(CommandError::Rule(RuleError::TutorialStepMismatch(_)))
        ));
        let (after_revision, after) = repo
            .load_latest_snapshot(code)
            .await
            .expect("load")
            .expect("snapshot");
        assert_eq!(after_revision, revision);
        assert_eq!(after.serialize(), before);
        assert_eq!(
            app.rooms
                .read()
                .await
                .get_room(code)
                .expect("room")
                .game_state
                .as_ref()
                .expect("state")
                .serialize(),
            before
        );
    }
    for (index, step) in tutorial::steps().into_iter().enumerate() {
        let outcome = GameActionService::process_action(
            &app,
            code,
            id,
            step.action,
            CommandId::parse(&format!("tutorial-{index}")).expect("id"),
            Revision::new(revision as u64).expect("revision"),
        )
        .await
        .expect("step");
        revision = outcome.revision.get() as i64;
        let (_, saved) = repo
            .load_latest_snapshot(code)
            .await
            .expect("load")
            .expect("snapshot");
        snapshot = saved;
        assert_eq!(
            snapshot.tutorial.as_ref().expect("tutorial").step,
            if index + 1 == tutorial::steps().len() {
                tutorial::steps().len() + 2
            } else {
                index + 2
            }
        );
        if index == 0 {
            assert!(!snapshot
                .tutorial
                .as_ref()
                .expect("tutorial")
                .opponents
                .is_empty());
        }
        app.rooms.write().await.remove_room(code);
        app.ensure_room_loaded(code).await.expect("recover");
        let rooms = app.rooms.read().await;
        let restored = rooms.get_room(code).expect("room");
        assert_eq!(restored.players.len(), 1);
        assert_eq!(
            restored.game_state.as_ref().expect("state").serialize(),
            snapshot.serialize()
        );
        assert!(rooms.list_rooms().iter().all(|room| room.code != code));
    }
    assert_eq!(snapshot.round, 2);
    assert_eq!(
        snapshot.tutorial.as_ref().expect("tutorial").final_scores,
        Some(gaia_engine::ScoringEngine::calculate_final_scoring_breakdown(&snapshot))
    );
    assert!(repo
        .load_events_since(code, 0)
        .await
        .expect("events")
        .is_empty());
    let mut ws = server
        .get_websocket(&format!("/ws/{code}"))
        .await
        .into_websocket()
        .await;
    ws.send_json(&json!({ "type": "join_room", "room_code": code, "nickname": "나", "session_token": body["session_token"] })).await;
    let recovered = receive_until(&mut ws, "snapshot").await;
    assert_eq!(
        recovered["state"]["tutorial"]["step"],
        tutorial::steps().len() + 2
    );
    assert_eq!(recovered["revision"], revision);
    ws.send_json(&command_msg(
        code,
        "after-completion",
        revision as u64,
        json!({"type": "place_game_action", "action": {"type": "AcademyQicAction"}}),
    ))
    .await;
    let rejected = receive_until(&mut ws, "command_rejected").await;
    assert_eq!(rejected["rejection"]["code"], "TutorialStepMismatch");
    assert_eq!(
        repo.load_latest_snapshot(code)
            .await
            .expect("snapshot")
            .expect("saved")
            .0,
        revision
    );
}
