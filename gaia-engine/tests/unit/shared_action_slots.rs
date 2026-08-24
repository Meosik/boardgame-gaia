use gaia_engine::game_state::{FactionId, GamePhase};
use gaia_engine::rules::actions::{GameAction, QicActionKind};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

/// Rulebook Appendix III: power-action and QIC-action board slots are
/// shared across all players — once one player takes a slot, no one
/// (including that same player) can take it again until Clean-up.
fn base_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl3 = 10;
            p.resources.qic = 10;
        })
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl3 = 10;
            p.resources.qic = 10;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn power_action_slot_is_shared_across_players() {
    let mut state = base_state();

    RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 })
        .unwrap_or_else(|e| panic!("player 0's power action should succeed: {e}"));

    let result = RuleEngine::apply_action(&mut state, 1, GameAction::PowerAction { id: 1 });
    assert!(result.is_err());
}

#[test]
fn power_action_slot_rejects_the_same_player_reusing_it_too() {
    let mut state = base_state();
    // Give player 0 two turns' worth of power for this scenario.
    state.players[0].resources.power.bowl3 = 20;

    RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 })
        .unwrap_or_else(|e| panic!("first power action should succeed: {e}"));

    // advance_turn moved the active player on; force it back to 0 to isolate
    // the slot-exclusivity check from turn-order enforcement.
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let result = RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 });
    assert!(result.is_err());
}

#[test]
fn different_power_action_ids_remain_independently_available() {
    let mut state = base_state();

    RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 })
        .unwrap_or_else(|e| panic!("player 0's power action (id 1) should succeed: {e}"));

    let result = RuleEngine::apply_action(&mut state, 1, GameAction::PowerAction { id: 2 });
    assert!(result.is_ok(), "id 2 should still be free: {result:?}");
}

#[test]
fn power_action_slots_reset_at_the_next_round() {
    let mut state = base_state();

    RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 })
        .unwrap_or_else(|e| panic!("power action should succeed: {e}"));

    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));
    state.players[1].resources.power.bowl3 = 10;

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::PowerAction { id: 1 });
    assert!(
        result.is_ok(),
        "slot should be free again next round: {result:?}"
    );
}

#[test]
fn qic_action_slot_is_shared_across_players() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::QicAction {
            kind: QicActionKind::GainOre,
        },
    )
    .unwrap_or_else(|e| panic!("player 0's QIC action should succeed: {e}"));

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::QicAction {
            kind: QicActionKind::GainOre,
        },
    );
    assert!(result.is_err());
}

#[test]
fn qic_action_slot_identity_ignores_coord_payload() {
    use gaia_engine::game_state::HexCoord;

    let mut state = base_state();
    state.board.hexes.clear();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::QicAction {
            kind: QicActionKind::ColoniseLostPlanet {
                coord: HexCoord::new(0, 0),
            },
        },
    )
    .unwrap_or_else(|e| panic!("first colonise action should succeed: {e}"));

    // Same *kind* (ColoniseLostPlanet), different coord — still the same
    // shared slot, so this must be rejected regardless of target.
    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::QicAction {
            kind: QicActionKind::ColoniseLostPlanet {
                coord: HexCoord::new(5, 5),
            },
        },
    );
    assert!(result.is_err());
}

#[test]
fn different_qic_action_kinds_remain_independently_available() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::QicAction {
            kind: QicActionKind::GainOre,
        },
    )
    .unwrap_or_else(|e| panic!("player 0's GainOre should succeed: {e}"));

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::QicAction {
            kind: QicActionKind::ResearchStep,
        },
    );
    assert!(
        result.is_ok(),
        "ResearchStep should still be free: {result:?}"
    );
}
