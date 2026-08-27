// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), Appendix I, Ivits:
// "Ability: During setup, do not place mines. Instead, after all other players have placed
// mines..., place your planetary institute on any red planet. You can have only one federation
// during the whole game, but... you will be able to grow that federation to gain new federation
// tokens. After you have formed a federation, to take the 'Form a Federation' action again, you
// must connect planets to that federation instead of forming a new federation. The power values
// of the structures on those planets must bring the total power value of that federation to at
// least to 7X, where X is the number of federation tokens you own plus one... To build a
// satellite during this action, you must spend one Q.I.C. instead of discarding one power.
// Planetary Institute: As a special action, place a space station on an accessible space that
// does not contain a planet or another space station... each space station counts as having a
// power value of one for its federation. A space station is not a structure, so placing one
// does not allow opponents to charge power... it can be used as a 'starting point' when
// determining the accessibility of a planet."

use gaia_engine::game_state::{
    BoardState, FactionId, FederationToken, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure,
    Planet, PlanetType, Sector, Structure, StructureType,
};
use gaia_engine::map::MapEngine;
use gaia_engine::rules::actions::{FederationTokenChoice, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn empty_hex(coord: HexCoord) -> Hex {
    Hex {
        coord,
        planet: None,
        space_tile_kind: None,
        structures: vec![],
        satellites: vec![],
    }
}

fn structure_hex(coord: HexCoord, owner: u8, kind: StructureType) -> Hex {
    Hex {
        coord,
        planet: None,
        space_tile_kind: None,
        structures: vec![PlacedStructure { owner, kind }],
        satellites: vec![],
    }
}

// ── Space Station placement ─────────────────────────────────────────────────────

fn board_with_pi_and_empty_neighbor() -> BoardState {
    let pi = HexCoord::new(0, 0);
    let empty = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    hexes.insert(pi, structure_hex(pi, 0, StructureType::PlanetaryInstitute));
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

fn state_with_ivits_pi() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Ivits);
            p.resources.qic = 3;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            }];
        })
        .with_player(1)
        .with_board(board_with_pi_and_empty_neighbor())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn ivits_can_place_a_space_station_within_range() {
    let mut state = state_with_ivits_pi();
    let target = HexCoord::new(1, 0);
    let qic_before = state.players[0].resources.qic;

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::IvitsPlaceSpaceStation { coord: target },
    )
    .unwrap_or_else(|e| panic!("space station placement should succeed: {e}"));

    assert!(state.players[0]
        .structures
        .iter()
        .any(|s| s.hex == target && s.kind == StructureType::SpaceStation));
    let hex = state
        .board
        .hexes
        .get(&target)
        .unwrap_or_else(|| panic!("target hex should exist"));
    assert!(hex
        .structures
        .iter()
        .any(|s| s.owner == 0 && s.kind == StructureType::SpaceStation));
    // Adjacent to the PI (range 1, nav level 0) — no QIC needed for range.
    assert_eq!(state.players[0].resources.qic, qic_before);
    assert!(state.players[0].faction_special_action_used_this_round);
    assert!(events
        .iter()
        .any(|e| matches!(e, GameEvent::SpaceStationPlaced { player: 0, hex } if *hex == target)));
}

#[test]
fn ivits_space_station_requires_planetary_institute() {
    let mut state = state_with_ivits_pi();
    state.players[0].structures.clear(); // no PI built yet

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::IvitsPlaceSpaceStation {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn ivits_cannot_place_a_space_station_on_a_planet() {
    let mut state = state_with_ivits_pi();
    if let Some(hex) = state.board.hexes.get_mut(&HexCoord::new(1, 0)) {
        hex.planet = Some(Planet {
            planet_type: PlanetType::Terra,
            is_gaia_formed: false,
            owner: None,
        });
    }

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::IvitsPlaceSpaceStation {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn ivits_cannot_place_two_space_stations_on_the_same_hex() {
    let mut state = state_with_ivits_pi();
    let target = HexCoord::new(1, 0);
    if let Some(hex) = state.board.hexes.get_mut(&target) {
        hex.structures.push(PlacedStructure {
            owner: 1,
            kind: StructureType::SpaceStation,
        });
    }

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::IvitsPlaceSpaceStation { coord: target },
    );
    assert!(result.is_err());
}

#[test]
fn federation_power_counts_a_space_station_as_one() {
    let coord = HexCoord::new(0, 0);
    let mut hexes = HashMap::new();
    hexes.insert(coord, structure_hex(coord, 0, StructureType::SpaceStation));
    let board = BoardState {
        sectors: vec![],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };

    assert_eq!(MapEngine::federation_power(&board, 0, &[coord]), 1);
}

// ── Federation: first formation and growth ──────────────────────────────────────

/// One straight chain of 7 hexes: `a`-`b`-`c` (power 3+2+2 = 7, the first federation) directly
/// adjacent to `d`-`e`-`f`-`g` (power 1+2+2+2 = 7, the growth — `d` is a Space Station, counted
/// as power 1). No satellite is needed here since `c` and `d` are already adjacent; see
/// `ivits_growth_satellites_cost_qic_instead_of_power` for a bridged growth.
fn ivits_federation_board() -> BoardState {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(2, 0);
    let d = HexCoord::new(3, 0);
    let e = HexCoord::new(4, 0);
    let f = HexCoord::new(5, 0);
    let g = HexCoord::new(6, 0);
    let mut hexes = HashMap::new();
    hexes.insert(a, structure_hex(a, 0, StructureType::PlanetaryInstitute));
    hexes.insert(b, structure_hex(b, 0, StructureType::TradingStation));
    hexes.insert(c, structure_hex(c, 0, StructureType::TradingStation));
    hexes.insert(d, structure_hex(d, 0, StructureType::SpaceStation));
    hexes.insert(e, structure_hex(e, 0, StructureType::TradingStation));
    hexes.insert(f, structure_hex(f, 0, StructureType::TradingStation));
    hexes.insert(g, structure_hex(g, 0, StructureType::TradingStation));
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: a,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn ivits_federation_state() -> gaia_engine::game_state::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Ivits);
            p.vp = 10;
            p.resources.power.bowl1 = 4;
            p.resources.qic = 4;
        })
        .with_player(1)
        .with_board(ivits_federation_board())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1), FederationToken(2)];
    state
}

#[test]
fn ivits_first_federation_uses_the_flat_minimum() {
    let mut state = ivits_federation_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![
                HexCoord::new(0, 0),
                HexCoord::new(1, 0),
                HexCoord::new(2, 0),
            ],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("first Ivits federation at exactly 7 power should succeed: {e}"));

    assert_eq!(state.players[0].federation_tokens.len(), 1);
}

#[test]
fn ivits_second_federation_requires_7x_and_connects_to_the_existing_network() {
    let mut state = ivits_federation_state();
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![
                HexCoord::new(0, 0),
                HexCoord::new(1, 0),
                HexCoord::new(2, 0),
            ],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    // Growth hexes d/e/f/g (power 1+2+2+2 = 7, including the Space Station's power 1) bring the
    // cumulative federation power to exactly 7 + 7 = 14 = 7*(1+1) — the exact threshold for a
    // second federation token, checked as a whole-federation total, not a "new hexes only" one.
    let growth_hexes = vec![
        HexCoord::new(3, 0),
        HexCoord::new(4, 0),
        HexCoord::new(5, 0),
        HexCoord::new(6, 0),
    ];

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: growth_hexes.clone(),
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 2 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_ok(),
        "growth to exactly 7*2=14 total power should succeed: {result:?}"
    );
    assert_eq!(state.players[0].federation_tokens.len(), 2);
    for coord in growth_hexes {
        assert!(state.players[0].federated_hexes.contains(&coord));
    }
}

#[test]
fn ivits_second_federation_rejects_when_disconnected_from_the_existing_network() {
    let mut state = ivits_federation_state();
    // Detach `d` from `c` so the growth hexes form their own isolated island.
    state.board.hexes.remove(&HexCoord::new(3, 0));
    state
        .board
        .hexes
        .insert(HexCoord::new(3, 0), empty_hex(HexCoord::new(3, 0)));

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![
                HexCoord::new(0, 0),
                HexCoord::new(1, 0),
                HexCoord::new(2, 0),
            ],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![
                HexCoord::new(4, 0),
                HexCoord::new(5, 0),
                HexCoord::new(6, 0),
            ],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 2 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn ivits_growth_satellites_cost_qic_instead_of_power() {
    // First federation: PI + 2 Trading Stations, directly adjacent (power 3+2+2=7). Growth: 4
    // more structures (power 2+2+2+2=8) 2 spaces from the first federation, bridged by exactly 1
    // satellite — cumulative power 15 clears the 7*(1+1)=14 threshold with room to spare; this
    // test only cares that the satellite itself is paid for in QIC, not the exact margin.
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(2, 0);
    let bridge = HexCoord::new(3, 0);
    let d = HexCoord::new(4, 0);
    let e = HexCoord::new(5, 0);
    let f = HexCoord::new(6, 0);
    let g = HexCoord::new(7, 0);
    let mut hexes = HashMap::new();
    hexes.insert(a, structure_hex(a, 0, StructureType::PlanetaryInstitute));
    hexes.insert(b, structure_hex(b, 0, StructureType::TradingStation));
    hexes.insert(c, structure_hex(c, 0, StructureType::TradingStation));
    hexes.insert(bridge, empty_hex(bridge));
    hexes.insert(d, structure_hex(d, 0, StructureType::TradingStation));
    hexes.insert(e, structure_hex(e, 0, StructureType::TradingStation));
    hexes.insert(f, structure_hex(f, 0, StructureType::TradingStation));
    hexes.insert(g, structure_hex(g, 0, StructureType::ResearchLab));
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: a,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Ivits);
            p.vp = 10;
            p.resources.power.bowl1 = 4;
            p.resources.qic = 4;
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    // Kind 6 ("6 VP + 2 knowledge") deliberately doesn't touch QIC or power, so the growth
    // call's own token reward can't mask or offset the satellite cost being asserted below.
    state.research_board.federation_tokens = vec![FederationToken(1), FederationToken(6)];

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![a, b, c],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let qic_before = state.players[0].resources.qic;
    let power_before = state.players[0].resources.power.bowl1;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![d, e, f, g],
            satellite_hexes: vec![bridge],
            token: FederationTokenChoice::Supply { kind: 6 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("growth with a bridging satellite should succeed: {e}"));

    // The bridging satellite cost 1 QIC, not 1 power, during this growth action.
    assert_eq!(state.players[0].resources.qic, qic_before - 1);
    assert_eq!(state.players[0].resources.power.bowl1, power_before);
    let bridge_hex = state
        .board
        .hexes
        .get(&bridge)
        .unwrap_or_else(|| panic!("bridge hex should exist"));
    assert_eq!(bridge_hex.satellites, vec![0]);
}
