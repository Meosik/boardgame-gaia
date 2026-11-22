use gaia_engine::error::RuleError;
use gaia_engine::game_state::{
    BoardState, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType, Sector,
    StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

/// Board with an unowned Terra planet at `target` (Build destination), a
/// builder anchor Mine at `anchor` (for reachability), and an opponent
/// structure of `opponent_kind` at `opponent_hex` owned by player 1.
fn board(
    target: HexCoord,
    anchor: HexCoord,
    opponent_hex: Option<(HexCoord, StructureType)>,
) -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        target,
        Hex {
            coord: target,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
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
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    if let Some((hex, kind)) = opponent_hex {
        hexes.insert(
            hex,
            Hex {
                coord: hex,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure { owner: 1, kind }],
                satellites: vec![],
            },
        );
    }
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

fn base_builder(opponent_hex: Option<(HexCoord, StructureType)>) -> GameStateBuilder {
    let target = HexCoord::new(1, 0);
    let anchor = HexCoord::new(0, 0);
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.structures = vec![gaia_engine::game_state::Structure {
                hex: anchor,
                kind: StructureType::Mine,
            }];
        })
        .with_player(1)
        .with_board(board(target, anchor, opponent_hex))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
}

fn build_target() -> GameAction {
    GameAction::Build {
        coord: HexCoord::new(1, 0),
    }
}

#[test]
fn no_eligible_charger_skips_charge_power_phase() {
    // Opponent structure at distance 3 — outside range 2.
    let mut state = base_builder(Some((HexCoord::new(4, 0), StructureType::Mine))).build();

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));

    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn eligible_charger_pauses_action_phase() {
    // Mine (power value 1) at distance 1 from the build target.
    let mut state = base_builder(Some((HexCoord::new(2, 0), StructureType::Mine))).build();

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));

    match &state.phase {
        GamePhase::ChargePowerPending {
            queue,
            resume_active_player,
        } => {
            assert_eq!(queue.len(), 1);
            assert_eq!(queue[0].player, 1);
            assert_eq!(queue[0].max_power, 1);
            assert_eq!(*resume_active_player, Some(1));
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }
}

#[test]
fn accepting_charges_power_and_spends_vp() {
    let mut state = base_builder(Some((HexCoord::new(2, 0), StructureType::Mine))).build();
    state.players[1].resources.power.bowl1 = 5;
    state.players[1].resources.power.bowl2 = 0;
    state.players[1].vp = 10;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    // Mine power value 1 → charge 1 power, cost 1 - 1 = 0 VP.
    assert_eq!(opponent.resources.power.bowl1, 4);
    assert_eq!(opponent.resources.power.bowl2, 1);
    assert_eq!(opponent.vp, 10);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn declining_leaves_state_unchanged() {
    let mut state = base_builder(Some((HexCoord::new(2, 0), StructureType::Mine))).build();
    state.players[1].resources.power.bowl1 = 5;
    let vp_before = state.players[1].vp;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: false })
        .unwrap_or_else(|e| panic!("decline should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(opponent.resources.power.bowl1, 5);
    assert_eq!(opponent.vp, vp_before);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn charging_full_planetary_institute_power_costs_two_vp() {
    let mut state = base_builder(Some((
        HexCoord::new(3, 0),
        StructureType::PlanetaryInstitute,
    )))
    .build();
    state.players[1].resources.power.bowl1 = 3;
    state.players[1].resources.power.bowl2 = 0;
    state.players[1].vp = 10;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    // PlanetaryInstitute power value 3 → charge 3, cost 3 - 1 = 2 VP.
    assert_eq!(opponent.resources.power.bowl1, 0);
    assert_eq!(opponent.resources.power.bowl2, 3);
    assert_eq!(opponent.vp, 8);
}

#[test]
fn charge_amount_capped_by_available_vp() {
    let mut state = base_builder(Some((
        HexCoord::new(3, 0),
        StructureType::PlanetaryInstitute,
    )))
    .build();
    state.players[1].resources.power.bowl1 = 3;
    state.players[1].resources.power.bowl2 = 0;
    state.players[1].vp = 1; // can only afford 1 VP → 2 power (cost = amount - 1)

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(opponent.resources.power.bowl1, 1);
    assert_eq!(opponent.resources.power.bowl2, 2);
    assert_eq!(opponent.vp, 0);
}

#[test]
fn charge_amount_capped_by_what_moves_every_token_to_area_three() {
    // Rulebook p.17, first exception and its example: with one token left in Area II the
    // Planetary Institute's 3 power charges only 1, for 0 VP.
    let mut state = base_builder(Some((
        HexCoord::new(3, 0),
        StructureType::PlanetaryInstitute,
    )))
    .build();
    state.players[1].resources.power.bowl1 = 0;
    state.players[1].resources.power.bowl2 = 1;
    state.players[1].resources.power.bowl3 = 5;
    state.players[1].vp = 10;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(opponent.resources.power.bowl1, 0);
    assert_eq!(opponent.resources.power.bowl2, 0);
    assert_eq!(opponent.resources.power.bowl3, 6);
    assert_eq!(opponent.vp, 10); // charged only 1 power → cost 0 VP
}

#[test]
fn a_token_in_area_one_takes_two_power_of_a_charge() {
    // One token in Area I is not "1 power left": moving it to Area III takes 2 power, so the
    // Planetary Institute's 3 power charges 2 for 1 VP (the cap is power, not tokens).
    let mut state = base_builder(Some((
        HexCoord::new(3, 0),
        StructureType::PlanetaryInstitute,
    )))
    .build();
    state.players[1].resources.power.bowl1 = 1;
    state.players[1].resources.power.bowl2 = 0;
    state.players[1].resources.power.bowl3 = 5;
    state.players[1].vp = 10;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(opponent.resources.power.bowl1, 0);
    assert_eq!(opponent.resources.power.bowl2, 0);
    assert_eq!(opponent.resources.power.bowl3, 6);
    assert_eq!(opponent.vp, 9); // charged 2 power → cost 1 VP
}

#[test]
fn two_tokens_spread_over_areas_one_and_two_take_the_full_three_power() {
    // Two tokens outside Area III (one each in I and II) take 3 power in all.
    let mut state = base_builder(Some((
        HexCoord::new(3, 0),
        StructureType::PlanetaryInstitute,
    )))
    .build();
    state.players[1].resources.power.bowl1 = 1;
    state.players[1].resources.power.bowl2 = 1;
    state.players[1].resources.power.bowl3 = 4;
    state.players[1].vp = 10;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("charge power should be valid: {e}"));

    let opponent = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(opponent.resources.power.bowl1, 0);
    assert_eq!(opponent.resources.power.bowl2, 0);
    assert_eq!(opponent.resources.power.bowl3, 6);
    assert_eq!(opponent.vp, 8); // charged 3 power → cost 2 VP
}

#[test]
fn passed_opponent_is_still_eligible() {
    let mut state = base_builder(Some((HexCoord::new(2, 0), StructureType::Mine))).build();
    state.players[1].passed = true;

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));

    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(queue.len(), 1);
            assert_eq!(queue[0].player, 1);
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }
}

/// Three seats with two charge offers queued (seat 1 ahead of seat 2) after a build of seat 0.
fn two_queued_offers() -> gaia_engine::game_state::GameState {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player_fn(1, |p| {
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 0;
            p.resources.power.bowl3 = 0;
            p.vp = 10;
        })
        .with_player_fn(2, |p| {
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 0;
            p.resources.power.bowl3 = 0;
            p.vp = 10;
        })
        .build();
    let offer = |player| gaia_engine::game_state::PendingCharge {
        player,
        hex: HexCoord::new(1, 0),
        max_power: 2,
    };
    state.phase = GamePhase::ChargePowerPending {
        queue: vec![offer(1), offer(2)],
        resume_active_player: Some(1),
    };
    state
}

#[test]
fn a_queued_player_answers_a_charge_offer_before_the_seat_ahead() {
    let mut state = two_queued_offers();

    RuleEngine::apply_action(&mut state, 2, GameAction::ChargePower { accept: true })
        .unwrap_or_else(|e| panic!("the second queued seat may answer first: {e}"));

    // Seat 2 charged its own offer; seat 1's offer is untouched and still waits.
    let second = state.player(2).unwrap_or_else(|| panic!("player 2 exists"));
    assert_eq!(second.resources.power.bowl2, 2);
    assert_eq!(second.vp, 9);
    let first = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(first.resources.power.bowl2, 0);
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(queue.len(), 1);
            assert_eq!(queue[0].player, 1);
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }

    // A seat that has answered has nothing left to answer.
    let again = RuleEngine::apply_action(&mut state, 2, GameAction::ChargePower { accept: true });
    assert!(matches!(again, Err(RuleError::NotYourTurn)));

    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: false })
        .unwrap_or_else(|e| panic!("the remaining seat answers: {e}"));
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn out_of_turn_charge_power_is_rejected() {
    let mut state = base_builder(Some((HexCoord::new(2, 0), StructureType::Mine))).build();

    RuleEngine::apply_action(&mut state, 0, build_target())
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));

    // Player 0 (the builder, not in the charge queue) tries to act.
    let result = RuleEngine::apply_action(&mut state, 0, GameAction::ChargePower { accept: false });
    assert!(matches!(result, Err(RuleError::NotYourTurn)));
}
