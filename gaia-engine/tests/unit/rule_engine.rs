use gaia_engine::error::RuleError;
use gaia_engine::game_state::{GamePhase, ResearchTrack};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn action_phase_state() -> gaia_engine::GameState {
    GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn wrong_phase_returns_error() {
    let state = GameStateBuilder::new()
        .with_player(0)
        .with_phase(GamePhase::IncomePhase)
        .build();
    let result = RuleEngine::validate_action(&state, 0, &GameAction::Pass { booster_id: None });
    assert!(matches!(result, Err(RuleError::WrongPhase)));
}

#[test]
fn not_your_turn_returns_error() {
    let state = action_phase_state();
    // active_player is 0, so player 1 cannot act
    let result = RuleEngine::validate_action(&state, 1, &GameAction::Pass { booster_id: None });
    assert!(matches!(result, Err(RuleError::NotYourTurn)));
}

#[test]
fn pass_is_valid_when_your_turn() {
    let state = action_phase_state();
    let result = RuleEngine::validate_action(&state, 0, &GameAction::Pass { booster_id: None });
    assert!(result.is_ok());
}

#[test]
fn already_passed_returns_error() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.passed = true;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let result = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::ResearchAdvance {
            track: ResearchTrack::Science,
        },
    );
    assert!(matches!(result, Err(RuleError::AlreadyPassed)));
}

#[test]
fn research_insufficient_knowledge_returns_error() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.knowledge = 1;
        }) // need 4
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let result = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::ResearchAdvance {
            track: ResearchTrack::Science,
        },
    );
    assert!(matches!(result, Err(RuleError::InsufficientResources(_))));
}

#[test]
fn research_at_max_level_returns_error() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.knowledge = 10;
            p.research_tracks.science = 5; // max
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let result = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::ResearchAdvance {
            track: ResearchTrack::Science,
        },
    );
    assert!(matches!(result, Err(RuleError::ActionNotAllowed(_))));
}

#[test]
fn apply_pass_marks_player_passed() {
    let mut state = action_phase_state();
    let events = RuleEngine::apply_action(&mut state, 0, GameAction::Pass { booster_id: None });
    assert!(events.is_ok());
    let player = state.player(0);
    assert!(player.is_some_and(|p| p.passed));
}

#[test]
fn apply_research_deducts_knowledge() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.knowledge = 7;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(result.is_ok());
    let player = state.player(0);
    assert_eq!(player.map(|p| p.resources.knowledge), Some(3)); // 7 - 4 = 3
}

#[test]
fn apply_research_increments_track_level() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.knowledge = 10;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    )
    .ok();
    let player = state.player(0);
    assert_eq!(player.map(|p| p.research_tracks.navigation), Some(1));
}

#[test]
fn get_valid_actions_wrong_phase_is_empty() {
    let state = GameStateBuilder::new()
        .with_player(0)
        .with_phase(GamePhase::FinalScoring)
        .build();
    let actions = RuleEngine::get_valid_actions(&state, 0);
    assert!(actions.is_empty());
}

#[test]
fn get_valid_actions_includes_pass() {
    let state = action_phase_state();
    let actions = RuleEngine::get_valid_actions(&state, 0);
    assert!(actions.iter().any(|a| matches!(a, GameAction::Pass { .. })));
}
