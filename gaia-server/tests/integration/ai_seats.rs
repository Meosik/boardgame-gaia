//! A human seat plays a whole game against three live AI seats (`crate::ai`).
use std::time::{Duration, Instant};

use axum_test::TestServer;
use gaia_engine::{rules::engine::AiDecision, GamePhase, GameState, RuleEngine};
use gaia_protocol::{CommandId, Revision};
use gaia_server::{
    handlers::rest::CreateDevGameRequest,
    services::{faction_selection::FactionSelectionService, game_action::GameActionService},
    state::AppState,
};

use super::harness::RoomCleanupGuard;

async fn room_state(app: &AppState, code: &str) -> (GameState, u64) {
    let rooms = app.rooms.read().await;
    let room = rooms.get_room(code).expect("room");
    (room.game_state.clone().expect("state"), room.revision)
}

fn awaited_player(state: &GameState) -> Option<u8> {
    RuleEngine::decision_player(state).ok().flatten()
}

#[tokio::test]
#[ignore = "requires PostgreSQL and GAIA_AI_DIR (a built gaia-rl checkout)"]
async fn human_plays_a_full_game_against_three_ai_seats() {
    let _ = dotenvy::from_path(concat!(env!("CARGO_MANIFEST_DIR"), "/.env"));
    if std::env::var("GAIA_AI_DIR").is_err() {
        eprintln!("skipped: set GAIA_AI_DIR to a built gaia-rl directory to run AI seats");
        return;
    }
    let pool = sqlx::PgPool::connect(&std::env::var("DATABASE_URL").expect("test DB URL"))
        .await
        .expect("connect test DB");
    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("migrate");
    let app = AppState::new(pool);
    assert!(app.ai.is_some(), "AI pool must be configured");
    let _server = TestServer::new(gaia_server::router::build_router(app.clone())).expect("server");
    let (_, axum::Json(created)) = gaia_server::handlers::rest::create_dev_game(
        axum::extract::State(app.clone()),
        axum::Json(CreateDevGameRequest {
            full_setup: false,
            nickname: None,
            setup_mode: None,
            faction: None,
            seed: Some("ai-seats-regression".into()),
            ai_opponents: true,
        }),
    )
    .await
    .expect("create AI game");
    let code = created.room_code;
    let _cleanup = RoomCleanupGuard::new(&code);
    let human = created.player_id;

    let mut human_moves = 0;
    let started = Instant::now();
    loop {
        // Wait for the AI seats to hand the turn back (or finish the game).
        let wait = Instant::now();
        let (state, revision) = loop {
            let (state, revision) = room_state(&app, &code).await;
            if matches!(state.phase, GamePhase::Ended { .. })
                || awaited_player(&state) == Some(human)
            {
                break (state, revision);
            }
            assert!(
                wait.elapsed() < Duration::from_secs(300),
                "AI seats stalled: {:?}",
                state.phase
            );
            tokio::time::sleep(Duration::from_millis(50)).await;
        };
        if matches!(state.phase, GamePhase::Ended { .. }) {
            break;
        }
        assert!(
            started.elapsed() < Duration::from_secs(3600),
            "game took too long"
        );
        // The human always takes the first legal candidate (a deterministic stand-in).
        let decision = RuleEngine::ai_decisions(&state)
            .expect("human candidates")
            .remove(0);
        let command = CommandId::parse(&format!("human-{human_moves}")).expect("command id");
        let expected = Revision::new(revision).expect("revision");
        match decision {
            AiDecision::Setup(action) => {
                FactionSelectionService::process_setup_action(
                    &app, &code, human, action, command, expected,
                )
                .await
                .expect("human setup move");
            }
            AiDecision::Game(action) => {
                GameActionService::process_action(&app, &code, human, action, command, expected)
                    .await
                    .expect("human game move");
            }
        }
        human_moves += 1;
    }

    let (state, _) = room_state(&app, &code).await;
    let GamePhase::Ended { final_scores, .. } = &state.phase else {
        unreachable!()
    };
    let ai_actions = state
        .event_log
        .iter()
        .filter(|event| matches!(event, gaia_engine::game_state::GameEvent::ActionLog { player, .. } if *player != human))
        .count();
    println!("human moves {human_moves}, AI logged actions {ai_actions}, final scores {final_scores:?}, {:?}", started.elapsed());
    for player in &state.players {
        println!(
            "seat {} {:?} structures {} vp {}",
            player.player_id,
            player.faction,
            player.structures.len(),
            player.vp
        );
    }
    let (moves, fallbacks) = app.ai.as_ref().expect("pool").move_counts();
    println!("AI moves {moves}, fallback moves {fallbacks}");
    assert!(ai_actions > 30, "AI seats must have played the game");
    assert_eq!(fallbacks, 0, "every AI move must come from the teacher");
}
