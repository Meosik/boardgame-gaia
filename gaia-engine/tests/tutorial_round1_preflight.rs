use gaia_engine::{
    game_state::ResourceKind, rules::actions::GameAction, test_utils::builders::GameStateBuilder,
    RuleEngine, RuleError,
};

// Lost Fleet p.10, "Power and Q.I.C. Actions": the three Research-board QIC
// spaces are covered. The round-one tutorial must use a spaceship QIC action.
#[test]
fn lost_fleet_has_no_research_board_qic_actions() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.resources.qic = 30;
            player.resources.power.bowl3 = 12;
        })
        .build();

    let actions = RuleEngine::get_valid_actions(&state, 0);
    assert!(actions
        .iter()
        .all(|action| { !matches!(action, GameAction::PowerAction { id, .. } if *id > 7) }));
    for id in 8..=10 {
        let before = state.serialize();
        let result =
            RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id, coord: None });
        assert_eq!(
            result.err(),
            Some(RuleError::InsufficientResources(ResourceKind::Power))
        );
        assert_eq!(state.serialize(), before);
    }
}
