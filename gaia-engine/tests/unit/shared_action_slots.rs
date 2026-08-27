use gaia_engine::game_state::{
    BoardState, FactionId, GamePhase, Hex, HexCoord, Planet, PlanetType, Sector,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

/// Rulebook Appendix III: power-action board slots are shared across all
/// players — once one player takes a slot, no one (including that same
/// player) can take it again until Clean-up. (The QIC-action board is gone
/// entirely under this project's always-Lost-Fleet ruleset — see README.)
fn base_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl3 = 10;
        })
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl3 = 10;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn power_action_slot_is_shared_across_players() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|e| panic!("player 0's power action should succeed: {e}"));

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::PowerAction { id: 1, coord: None },
    );
    assert!(result.is_err());
}

#[test]
fn power_action_slot_rejects_the_same_player_reusing_it_too() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 20;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|e| panic!("first power action should succeed: {e}"));

    // advance_turn moved the active player on; force it back to 0 to isolate
    // the slot-exclusivity check from turn-order enforcement.
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    );
    assert!(result.is_err());
}

#[test]
fn different_power_action_ids_remain_independently_available() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|e| panic!("player 0's power action (id 1) should succeed: {e}"));

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::PowerAction { id: 3, coord: None },
    );
    assert!(result.is_ok(), "id 3 should still be free: {result:?}");
}

#[test]
fn power_action_slots_reset_at_the_next_round() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|e| panic!("power action should succeed: {e}"));

    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));
    state.players[0].resources.power.bowl3 = 10;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    );
    assert!(
        result.is_ok(),
        "slot should be free again next round: {result:?}"
    );
}

// ── Resource-gain power actions (ids 1, 3, 4, 5, 7) ─────────────────────────
//
// Confirmed against gaia-frontend/src/assets/boards/research_board.jpg,
// since the rulebook prose doesn't print these — the previously-shipped
// costs/effects here were fabricated and did not match the real board.

#[test]
fn power_action_1_costs_7_for_3_knowledge() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 7;
    state.players[0].resources.knowledge = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl3, 0);
    assert_eq!(player.resources.knowledge, 3);
}

#[test]
fn power_action_3_costs_4_for_2_ore() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 4;
    state.players[0].resources.ore = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 3, coord: None },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 2);
}

#[test]
fn power_action_4_costs_4_for_7_credits() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 4;
    state.players[0].resources.credits = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 4, coord: None },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.credits, 7);
}

#[test]
fn power_action_5_costs_4_for_2_knowledge() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 4;
    state.players[0].resources.knowledge = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 5, coord: None },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.knowledge, 2);
}

#[test]
fn power_action_7_adds_two_fresh_tokens_to_bowl1() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 3;
    state.players[0].resources.power.bowl1 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 7, coord: None },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl3, 0);
    // Not a charge (which would move an *existing* token forward) — 2 brand
    // new tokens enter bowl1.
    assert_eq!(player.resources.power.bowl1, 2);
}

// ── Terraforming-step power actions (ids 2, 6) ──────────────────────────────
//
// These immediately perform a "build a mine" action with free terraforming
// steps (rulebook Appendix III) instead of a plain resource gain.

fn board_with_target(target: HexCoord, anchor: HexCoord, target_type: PlanetType) -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        target,
        Hex {
            coord: target,
            planet: Some(Planet {
                planet_type: target_type,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        anchor,
        Hex {
            coord: anchor,
            planet: None,
            space_tile_kind: None,
            structures: vec![gaia_engine::game_state::PlacedStructure {
                owner: 0,
                kind: gaia_engine::game_state::StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

/// Terrans (home planet Terra) building on Volcanic — 2 ring steps away, so
/// at research level 0 (3 ore/step) full terraforming would cost 6 ore.
fn terraform_test_state() -> gaia_engine::game_state::GameState {
    let target = HexCoord::new(1, 0);
    let anchor = HexCoord::new(0, 0);
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.resources.power.bowl3 = 10;
            p.structures = vec![gaia_engine::game_state::Structure {
                hex: HexCoord::new(0, 0),
                kind: gaia_engine::game_state::StructureType::Mine,
            }];
        })
        .with_player(1)
        .with_board(board_with_target(target, anchor, PlanetType::Volcanic))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn power_action_2_waives_both_terraforming_steps() {
    let mut state = terraform_test_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction {
            id: 2,
            coord: Some(HexCoord::new(1, 0)),
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl3, 5); // paid the 5-power cost
    assert_eq!(player.resources.ore, 9); // only the base 1-ore mine cost
    assert_eq!(player.resources.credits, 13); // base 2-credit mine cost
    assert!(player
        .structures
        .iter()
        .any(|s| s.hex == HexCoord::new(1, 0)));
}

#[test]
fn power_action_6_waives_one_of_two_terraforming_steps() {
    let mut state = terraform_test_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction {
            id: 6,
            coord: Some(HexCoord::new(1, 0)),
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl3, 7); // paid the 3-power cost
                                                 // 1 remaining terraforming step at level 0 (3 ore/step) + base mine ore (1).
    assert_eq!(player.resources.ore, 6);
    assert_eq!(player.resources.credits, 13); // base 2-credit mine cost
}

#[test]
fn power_action_2_requires_a_target_coord() {
    let mut state = terraform_test_state();

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 2, coord: None },
    );
    assert!(result.is_err());
}
