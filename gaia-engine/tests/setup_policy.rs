use gaia_engine::error::RuleError;
use gaia_engine::game_state::{FactionId, GameEvent, GamePhase, SetupPhase};
use gaia_engine::rules::actions::SetupAction;
use gaia_engine::{MapEngine, Randomizer, RuleEngine, SetupPolicy};

fn available_factions() -> Vec<FactionId> {
    FactionId::all()
}

#[test]
fn selection_starts_with_the_first_player_in_clockwise_order() {
    let state = SetupPolicy::initialize(vec![7, 3, 9, 1], available_factions());

    assert_eq!(state.current_player(), Some(7));
    assert_eq!(state.player_order, vec![7, 3, 9, 1]);
    assert!(state.assignments.is_empty());
}

#[test]
fn only_the_current_player_can_select() {
    let mut state = SetupPolicy::initialize(vec![7, 3, 9, 1], available_factions());

    let result = SetupPolicy::select_faction(&mut state, 3, FactionId::Terrans);

    assert!(matches!(result, Err(RuleError::NotYourTurn)));
    assert!(state.assignments.is_empty());
}

#[test]
fn choosing_one_board_side_removes_both_sides() {
    let mut state = SetupPolicy::initialize(vec![7, 3, 9, 1], available_factions());

    let result = SetupPolicy::select_faction(&mut state, 7, FactionId::Terrans);

    assert!(matches!(
        result,
        Ok(GameEvent::FactionSelected {
            player: 7,
            faction: FactionId::Terrans
        })
    ));
    assert!(!state.available_factions.contains(&FactionId::Terrans));
    assert!(!state.available_factions.contains(&FactionId::Lantids));

    let result = SetupPolicy::select_faction(&mut state, 3, FactionId::Lantids);
    assert!(matches!(
        result,
        Err(RuleError::ActionNotAllowed(ref msg)) if msg.contains("unavailable")
    ));
}

#[test]
fn four_selections_complete_setup_without_changing_clockwise_order() {
    let setup = match Randomizer::generate_setup("sequential-faction-selection") {
        Ok(setup) => setup,
        Err(e) => panic!("fixture seed should produce a setup: {e:?}"),
    };
    let players = vec![
        (7, "P1".to_string()),
        (3, "P2".to_string()),
        (9, "P3".to_string()),
        (1, "P4".to_string()),
    ];
    let mut game = MapEngine::init_game_state("ROOM", &players, &setup);

    assert_eq!(
        game.phase,
        GamePhase::Setup(SetupPhase::FactionSelection { active_player: 7 })
    );
    assert_eq!(game.turn_order, vec![7, 3, 9, 1]);

    for (player, faction) in [
        (7, FactionId::Terrans),
        (3, FactionId::Xenos),
        (9, FactionId::Taklons),
        (1, FactionId::HadschHallas),
    ] {
        let result = RuleEngine::apply_setup_action(
            &mut game,
            player,
            SetupAction::SelectFaction { faction },
        );
        assert!(
            result.is_ok(),
            "selection should follow the fixed player order: {result:?}"
        );
    }

    assert_eq!(game.phase, GamePhase::Setup(SetupPhase::Complete));
    assert_eq!(game.turn_order, vec![7, 3, 9, 1]);
    assert_eq!(game.players[0].faction, Some(FactionId::Terrans));
    assert_eq!(game.players[1].faction, Some(FactionId::Xenos));
    assert_eq!(game.players[2].faction, Some(FactionId::Taklons));
    assert_eq!(game.players[3].faction, Some(FactionId::HadschHallas));
}
