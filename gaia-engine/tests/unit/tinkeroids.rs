// Lost Fleet expansion rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`), Appendix I, Tinkeroids:
// "Ability: You start the game with your Planetary Institute instead of 2 mines ... When you
// terraform a standard planet, you will require 3 terraforming steps for 3 of the base-game
// planet types, and 1 terraforming step for the other base-game planet types (see 'Choosing
// Your Faction' on page 7). Making a Gaia planet habitable costs you 2 Q.I.C.s. The Tinkeroids
// have 6 different Tinkering tiles to use: 3 of the tiles are to be used in rounds 1-3, and the
// rest in rounds 4-6. At the start of each round choose 1 Tinkering tile that corresponds to
// that round. Place it on your Faction board. At the end of the round, remove that tile from
// play (each tile is only used once). Planetary Institute: Once per round, you may use the
// action on your current Tinkering tile as an ACTION." p.7, "Choosing Your Faction": "3 base-game
// planet types (which always includes their opponents' base-game types) will require 3 steps,
// and the others will require just 1." Tile effects confirmed against the scans at
// `gaia-frontend/src/assets/tinkering_tiles/`.

use gaia_engine::game_state::{
    BoardState, FactionId, GameEvent, GamePhase, GameState, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, Sector, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn board_with_pi_and_planet(planet_type: PlanetType, is_gaia_formed: bool) -> BoardState {
    let pi = HexCoord::new(0, 0);
    let planet_coord = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        pi,
        Hex {
            coord: pi,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::PlanetaryInstitute,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        planet_coord,
        Hex {
            coord: planet_coord,
            planet: Some(Planet {
                planet_type,
                is_gaia_formed,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: pi,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn tinkeroids_state(
    round: u8,
    opponent_faction: Option<FactionId>,
    planet_type: PlanetType,
) -> GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Tinkeroids);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.resources.qic = 5;
            p.resources.power.bowl1 = 4;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            }];
        })
        .with_player_fn(1, |p| {
            p.faction = opponent_faction;
        })
        .with_board(board_with_pi_and_planet(planet_type, false))
        .with_round(round)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn tinkeroids_round_1_resource_tile_grants_qic_and_marks_used() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    let qic_before = state.players[0].resources.qic;

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 2,
            coord: None,
        },
    )
    .unwrap_or_else(|e| panic!("tile 2 should be usable in round 1: {e}"));

    assert_eq!(state.players[0].resources.qic, qic_before + 1);
    assert!(state.players[0].tinkeroids_tiles_used.contains(&2));
    assert!(state.players[0].faction_special_action_used_this_round);
    assert!(events
        .iter()
        .any(|e| matches!(e, GameEvent::ResourceChanged { player: 0, .. })));
}

#[test]
fn tinkeroids_cannot_use_a_tile_outside_its_round_range() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 4,
            coord: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn tinkeroids_cannot_reuse_a_tile_that_was_already_used() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    state.players[0].tinkeroids_tiles_used.push(2);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 2,
            coord: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn tinkeroids_requires_planetary_institute() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    state.players[0].structures.clear(); // no PI built (shouldn't happen in practice — Tinkeroids
                                         // start with one — but confirms the gate is real)

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 2,
            coord: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn tinkeroids_build_mine_tile_waives_terraforming_ore_cost() {
    // No opponent faction is set, so the target's terraforming distance is the "cheap" 1-step
    // case — tile 1's 1 free terraforming step covers it entirely, leaving only the flat
    // 1-ore Mine build cost (`MINE_ORE_COST`), not the additional terraforming ore.
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 1,
            coord: Some(HexCoord::new(1, 0)),
        },
    )
    .unwrap_or_else(|e| panic!("tile 1 build should succeed: {e}"));

    assert_eq!(state.players[0].resources.ore, ore_before - 1);
    assert!(state.players[0].tinkeroids_tiles_used.contains(&1));
}

#[test]
fn tinkeroids_build_mine_tile_requires_a_coord() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 1,
            coord: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn tinkeroids_resource_tile_rejects_an_unneeded_coord() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 2,
            coord: Some(HexCoord::new(1, 0)),
        },
    );
    assert!(result.is_err());
}

#[test]
fn tinkeroids_charge_power_tile_moves_bowl1_to_bowl2() {
    let mut state = tinkeroids_state(1, None, PlanetType::Terra);
    state.players[0].resources.power.bowl1 = 4;
    state.players[0].resources.power.bowl2 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TinkeroidsUseTile {
            tile: 3,
            coord: None,
        },
    )
    .unwrap_or_else(|e| panic!("tile 3 should succeed: {e}"));

    assert_eq!(state.players[0].resources.power.bowl1, 0);
    assert_eq!(state.players[0].resources.power.bowl2, 4);
}

#[test]
fn tinkeroids_terraforming_cost_depends_on_opponents_home_types() {
    // Player 1 is Terrans (home = Terra), so Terra costs the Tinkeroids player 3 terraforming
    // steps; Swamp — a type no opponent here is homed to — costs only 1.
    let mut expensive = tinkeroids_state(1, Some(FactionId::Terrans), PlanetType::Terra);
    let ore_before = expensive.players[0].resources.ore;
    RuleEngine::apply_action(
        &mut expensive,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build on the expensive type should succeed: {e}"));
    // 3 terraforming steps at research level 0 (3*3=9 ore) plus the flat 1-ore Mine build
    // cost (`MINE_ORE_COST`) = 10 ore total.
    assert_eq!(expensive.players[0].resources.ore, ore_before - 10);

    let mut cheap = tinkeroids_state(1, Some(FactionId::Terrans), PlanetType::Swamp);
    let ore_before = cheap.players[0].resources.ore;
    RuleEngine::apply_action(
        &mut cheap,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build on the cheap type should succeed: {e}"));
    // 1 terraforming step at research level 0 (1*3=3 ore) plus the flat 1-ore Mine build cost
    // (`MINE_ORE_COST`) = 4 ore total.
    assert_eq!(cheap.players[0].resources.ore, ore_before - 4);
}

#[test]
fn tinkeroids_gaia_planet_costs_two_qic() {
    let mut state = tinkeroids_state(1, None, PlanetType::Transdim);
    if let Some(hex) = state.board.hexes.get_mut(&HexCoord::new(1, 0)) {
        if let Some(planet) = hex.planet.as_mut() {
            planet.is_gaia_formed = true;
        }
    }
    let qic_before = state.players[0].resources.qic;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build on a Gaia planet should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, qic_before - 2);
}
