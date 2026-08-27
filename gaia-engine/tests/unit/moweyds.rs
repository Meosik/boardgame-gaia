// Lost Fleet expansion rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`), Appendix I, Moweyds:
// "Ability: You start the game with 1 mine instead of 2, which you place during the second
// stage of placement. You start the game with an Exploration Shuttle on T F Mars. When
// terraforming a standard planet, you will require 3 terraforming steps for 3 of the base-game
// planet types, and 1 terraforming step for the other base-game planet types. Planetary
// Institute: Once per round, you may place a Power Ring onto a planet that contains one of your
// buildings and does not already have a Power Ring (if you need to, you may lift up the
// structure on the planet, put the Power Ring on the planet and then put the structure on top).
// The power value of your structure on this planet increases by 2." Components list: "6 Power
// Rings (for the Moweyds faction)".

use gaia_engine::game_state::{
    BoardState, FactionId, FederationToken, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure,
    Planet, PlanetType, Sector, Structure, StructureType,
};
use gaia_engine::rules::actions::{FederationTokenChoice, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn structure_hex(coord: HexCoord, owner: u8, kind: StructureType) -> Hex {
    Hex {
        coord,
        planet: None,
        space_tile_kind: None,
        structures: vec![PlacedStructure { owner, kind }],
        satellites: vec![],
    }
}

fn empty_hex(coord: HexCoord) -> Hex {
    Hex {
        coord,
        planet: None,
        space_tile_kind: None,
        structures: vec![],
        satellites: vec![],
    }
}

fn moweyds_board() -> BoardState {
    let pi = HexCoord::new(0, 0);
    let mine = HexCoord::new(1, 0);
    let empty = HexCoord::new(2, 0);
    let mut hexes = HashMap::new();
    hexes.insert(pi, structure_hex(pi, 0, StructureType::PlanetaryInstitute));
    hexes.insert(mine, structure_hex(mine, 0, StructureType::Mine));
    hexes.insert(empty, empty_hex(empty));
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

fn moweyds_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Moweyds);
            p.structures = vec![
                Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: HexCoord::new(1, 0),
                    kind: StructureType::Mine,
                },
            ];
        })
        .with_player(1)
        .with_board(moweyds_board())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn moweyds_can_place_a_power_ring_on_its_own_structure() {
    let mut state = moweyds_state();
    let target = HexCoord::new(1, 0);

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::MoweydsPlacePowerRing { coord: target },
    )
    .unwrap_or_else(|e| panic!("power ring placement should succeed: {e}"));

    assert!(state.players[0].moweyds_power_ring_hexes.contains(&target));
    assert!(state.players[0].faction_special_action_used_this_round);
    assert!(events
        .iter()
        .any(|e| matches!(e, GameEvent::PowerRingPlaced { player: 0, hex } if *hex == target)));
}

#[test]
fn moweyds_requires_planetary_institute() {
    let mut state = moweyds_state();
    state.players[0]
        .structures
        .retain(|s| s.kind != StructureType::PlanetaryInstitute);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::MoweydsPlacePowerRing {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn moweyds_cannot_place_a_ring_on_a_hex_without_its_own_structure() {
    let mut state = moweyds_state();

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::MoweydsPlacePowerRing {
            coord: HexCoord::new(2, 0), // empty hex
        },
    );
    assert!(result.is_err());
}

#[test]
fn moweyds_cannot_place_two_rings_on_the_same_hex() {
    let mut state = moweyds_state();
    let target = HexCoord::new(1, 0);
    state.players[0].moweyds_power_ring_hexes.push(target);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::MoweydsPlacePowerRing { coord: target },
    );
    assert!(result.is_err());
}

#[test]
fn moweyds_power_ring_supply_is_capped_at_six() {
    let mut state = moweyds_state();
    // Seed 6 already-placed rings (their coords don't need to be real board hexes — the supply
    // check runs before the target-hex checks).
    state.players[0].moweyds_power_ring_hexes = (10..16).map(|q| HexCoord::new(q, 0)).collect();

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::MoweydsPlacePowerRing {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn moweyds_power_ring_increases_federation_power() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(2, 0);
    let hexes = vec![a, b, c];
    let board = {
        let mut hexes_map = HashMap::new();
        hexes_map.insert(a, structure_hex(a, 0, StructureType::PlanetaryInstitute));
        hexes_map.insert(b, structure_hex(b, 0, StructureType::TradingStation));
        hexes_map.insert(c, structure_hex(c, 0, StructureType::Mine));
        BoardState {
            sectors: vec![Sector {
                id: 1,
                rotation: 0,
                origin: a,
            }],
            hexes: hexes_map,
            lost_planet: None,
            spaceship_tiles: HashMap::new(),
        }
    };
    let federation_state = || {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(FactionId::Moweyds);
                p.structures = vec![
                    Structure {
                        hex: a,
                        kind: StructureType::PlanetaryInstitute,
                    },
                    Structure {
                        hex: b,
                        kind: StructureType::TradingStation,
                    },
                    Structure {
                        hex: c,
                        kind: StructureType::Mine,
                    },
                ];
                p.resources.power.bowl1 = 4;
            })
            .with_player(1)
            .with_board(board.clone())
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        state.research_board.federation_tokens = vec![FederationToken(1), FederationToken(2)];
        state
    };

    let mut without_ring = federation_state();
    let result = RuleEngine::apply_action(
        &mut without_ring,
        0,
        GameAction::FormFederation {
            hexes: hexes.clone(),
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_err(),
        "3 (PI) + 2 (Trading Station) + 1 (Mine) = 6 power without the ring should fall short \
         of the 7 threshold"
    );

    let mut with_ring = federation_state();
    RuleEngine::apply_action(
        &mut with_ring,
        0,
        GameAction::MoweydsPlacePowerRing { coord: c },
    )
    .unwrap_or_else(|e| panic!("power ring placement should succeed: {e}"));
    with_ring.phase = GamePhase::ActionPhase { active_player: 0 };

    let result = RuleEngine::apply_action(
        &mut with_ring,
        0,
        GameAction::FormFederation {
            hexes,
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_ok(),
        "3 + 2 + (1 + 2 ring) = 8 power with the ring should clear the threshold: {result:?}"
    );
}

#[test]
fn moweyds_power_ring_increases_chargeable_power_for_opponents() {
    let target = HexCoord::new(1, 0);
    let anchor = HexCoord::new(0, 0);
    let moweyds_hex = HexCoord::new(2, 0); // distance 1 from target

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
    hexes.insert(anchor, structure_hex(anchor, 0, StructureType::Mine));
    hexes.insert(
        moweyds_hex,
        structure_hex(moweyds_hex, 1, StructureType::Mine),
    );
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };

    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.structures = vec![Structure {
                hex: anchor,
                kind: StructureType::Mine,
            }];
        })
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Moweyds);
            p.moweyds_power_ring_hexes = vec![moweyds_hex];
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target })
        .unwrap_or_else(|e| panic!("build should succeed: {e}"));

    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(queue.len(), 1);
            assert_eq!(queue[0].player, 1);
            // Mine's base power value 1 + the Power Ring's +2 = 3.
            assert_eq!(queue[0].max_power, 3);
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }
}

#[test]
fn moweyds_gaia_planet_costs_two_qic() {
    let planet = HexCoord::new(1, 0);
    let mut board = moweyds_board();
    board.hexes.insert(
        planet,
        Hex {
            coord: planet,
            planet: Some(Planet {
                planet_type: PlanetType::Transdim,
                is_gaia_formed: true,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Moweyds);
            p.resources.qic = 5;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            }];
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let qic_before = state.players[0].resources.qic;

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: planet })
        .unwrap_or_else(|e| panic!("build on a Gaia planet should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, qic_before - 2);
}
