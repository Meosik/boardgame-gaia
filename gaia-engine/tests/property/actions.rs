use gaia_engine::game_state::GamePhase;
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use proptest::prelude::*;

proptest! {
    #[test]
    fn pass_always_valid_when_your_turn(vp in 0i32..=100) {
        let state = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.vp = vp; })
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        let result = RuleEngine::validate_action(&state, 0, &GameAction::Pass { booster_id: None });
        prop_assert!(result.is_ok(), "Pass should always be valid when it's your turn");
    }

    #[test]
    fn apply_pass_marks_player_passed(vp in 0i32..=100) {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.vp = vp; })
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        let result = RuleEngine::apply_action(&mut state, 0, GameAction::Pass { booster_id: None });
        prop_assert!(result.is_ok());
        prop_assert!(state.player(0).is_some_and(|p| p.passed));
    }

    #[test]
    fn valid_actions_always_apply_without_error(knowledge in 0u8..=20u8) {
        let state = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.resources.knowledge = knowledge; })
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        let valid = RuleEngine::get_valid_actions(&state, 0);
        for action in valid {
            let mut test_state = state.clone();
            let result = RuleEngine::apply_action(&mut test_state, 0, action);
            prop_assert!(result.is_ok(), "valid action from get_valid_actions must apply without error");
        }
    }
}
