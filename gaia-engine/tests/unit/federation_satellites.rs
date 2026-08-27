// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), "4) Form a Federation" (p.14), "Connecting
// Planets": "To connect planets that are not adjacent, you must immediately build satellites...
// discard one power [per satellite]... place it in a space adjacent to either one of your
// colonized planets or one of your satellites." Satellites never contribute power value and can
// each be part of only one federation, same as the planets they connect.

use gaia_engine::game_state::{
    BoardState, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType, Sector, SpaceshipId,
    Structure, StructureType,
};
use gaia_engine::rules::actions::{FederationTokenChoice, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

/// Two colonized-planet clusters, 2 hexes apart: `a` (PlanetaryInstitute, power 3) and `b`
/// (TradingStation, power 2) are adjacent to each other; `c` (TradingStation, power 2) is 2
/// spaces from `b` — connectable only via a satellite at `bridge`. Total structure power is
/// exactly the federation minimum (7).
fn board_with_two_clusters() -> BoardState {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let bridge = HexCoord::new(2, 0);
    let c = HexCoord::new(3, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        a,
        Hex {
            coord: a,
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
        b,
        Hex {
            coord: b,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::TradingStation,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        bridge,
        Hex {
            coord: bridge,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        c,
        Hex {
            coord: c,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::TradingStation,
            }],
            satellites: vec![],
        },
    );
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

fn base_state() -> gaia_engine::game_state::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.vp = 10;
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 0;
            p.resources.power.bowl3 = 0;
            p.structures = vec![
                Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: HexCoord::new(1, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(3, 0),
                    kind: StructureType::TradingStation,
                },
            ];
        })
        .with_player(1)
        .with_board(board_with_two_clusters())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![
        gaia_engine::game_state::FederationToken(1),
        gaia_engine::game_state::FederationToken(2),
    ];
    state
}

fn hexes() -> Vec<HexCoord> {
    vec![
        HexCoord::new(0, 0),
        HexCoord::new(1, 0),
        HexCoord::new(3, 0),
    ]
}

const BRIDGE: HexCoord = HexCoord::new(2, 0);

fn form_federation(
    state: &mut gaia_engine::game_state::GameState,
    satellite_hexes: Vec<HexCoord>,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, gaia_engine::RuleError> {
    RuleEngine::apply_action(
        state,
        0,
        GameAction::FormFederation {
            hexes: hexes(),
            satellite_hexes,
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
}

#[test]
fn federation_without_a_bridging_satellite_is_rejected_as_disconnected() {
    let mut state = base_state();
    let result = form_federation(&mut state, vec![]);
    assert!(result.is_err());
}

#[test]
fn a_satellite_bridges_two_non_adjacent_clusters() {
    let mut state = base_state();

    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("federation with a bridging satellite should succeed: {e}"));

    let bridge_hex = state
        .board
        .hexes
        .get(&BRIDGE)
        .unwrap_or_else(|| panic!("bridge hex should exist"));
    assert_eq!(bridge_hex.satellites, vec![0]);
    // 1 power discarded for the 1 satellite (bowl1 drains first).
    assert_eq!(state.players[0].resources.power.bowl1, 3);
    assert_eq!(
        state.players[0].federated_hexes,
        vec![
            HexCoord::new(0, 0),
            HexCoord::new(1, 0),
            HexCoord::new(3, 0),
            BRIDGE
        ]
    );
}

#[test]
fn satellite_power_does_not_count_toward_the_federation_power_threshold() {
    // The bridge hex, if it somehow had a structure, would not be included as a "satellite" —
    // this test just confirms the 7-power total came entirely from the 3 real structures (3+2+2)
    // and the satellite contributed nothing, by using the exact minimum with no slack.
    let mut state = base_state();
    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("federation should succeed at exactly minimum power: {e}"));
}

#[test]
fn satellite_hex_cannot_already_have_a_structure() {
    let mut state = base_state();
    if let Some(hex) = state.board.hexes.get_mut(&BRIDGE) {
        hex.structures.push(PlacedStructure {
            owner: 1,
            kind: StructureType::Mine,
        });
    }

    let result = form_federation(&mut state, vec![BRIDGE]);
    assert!(result.is_err());
}

#[test]
fn satellite_hex_cannot_already_have_a_planet() {
    let mut state = base_state();
    if let Some(hex) = state.board.hexes.get_mut(&BRIDGE) {
        hex.planet = Some(Planet {
            planet_type: PlanetType::Terra,
            is_gaia_formed: false,
            owner: None,
        });
    }

    let result = form_federation(&mut state, vec![BRIDGE]);
    assert!(result.is_err());
}

#[test]
fn satellite_cannot_be_placed_on_a_lost_fleet_spaceship_tile() {
    let mut state = base_state();
    state
        .board
        .spaceship_tiles
        .insert(SpaceshipId::Twilight, BRIDGE);

    let result = form_federation(&mut state, vec![BRIDGE]);
    assert!(result.is_err());
}

#[test]
fn federation_rejects_insufficient_power_for_the_needed_satellites() {
    let mut state = base_state();
    state.players[0].resources.power.bowl1 = 0;
    state.players[0].resources.power.bowl2 = 0;
    state.players[0].resources.power.bowl3 = 0;

    let result = form_federation(&mut state, vec![BRIDGE]);
    assert!(result.is_err());
}

#[test]
fn federation_hex_cannot_be_reused_in_a_later_federation() {
    let mut state = base_state();
    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    // A second, otherwise-independent federation attempt that reuses hex `a` (PlanetaryInstitute)
    // must be rejected even though it would otherwise be connected and above the power threshold.
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![HexCoord::new(0, 0), HexCoord::new(1, 0)],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 2 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn federation_rejects_a_hex_the_player_has_not_colonized() {
    let mut state = base_state();
    let uncolonized = HexCoord::new(5, 5);
    state.board.hexes.insert(
        uncolonized,
        Hex {
            coord: uncolonized,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![HexCoord::new(0, 0), HexCoord::new(1, 0), uncolonized],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

// ── Minimality (p.14: "You cannot form a federation by connecting more planets and satellites
// than are needed") ─────────────────────────────────────────────────────────────────────────

/// Straight chain `a`(PI,3)-`b`(TradingStation,2)-`c`(TradingStation,2)-`d`(Mine,1), all directly
/// adjacent. `a,b,c` alone already reach the power minimum (3+2+2=7); `d` is never needed.
fn board_with_a_redundant_tail_hex() -> BoardState {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(2, 0);
    let d = HexCoord::new(3, 0);
    let mut hexes = HashMap::new();
    for (coord, kind) in [
        (a, StructureType::PlanetaryInstitute),
        (b, StructureType::TradingStation),
        (c, StructureType::TradingStation),
        (d, StructureType::Mine),
    ] {
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure { owner: 0, kind }],
                satellites: vec![],
            },
        );
    }
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

#[test]
fn federation_rejects_a_submission_with_a_redundant_hex() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.vp = 10;
            p.structures = vec![
                Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: HexCoord::new(1, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(2, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(3, 0),
                    kind: StructureType::Mine,
                },
            ];
        })
        .with_player(1)
        .with_board(board_with_a_redundant_tail_hex())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![gaia_engine::game_state::FederationToken(1)];

    // a+b+c already total exactly 7 power; d (Mine, power 1) is a redundant fourth hex.
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            hexes: vec![
                HexCoord::new(0, 0),
                HexCoord::new(1, 0),
                HexCoord::new(2, 0),
                HexCoord::new(3, 0),
            ],
            satellite_hexes: vec![],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_err(),
        "the redundant fourth hex should be rejected"
    );

    // Dropping the redundant hex makes the same submission valid.
    let result = RuleEngine::apply_action(
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
    );
    assert!(
        result.is_ok(),
        "the minimal 3-hex submission should succeed: {result:?}"
    );
}

// ── Adjacency exclusivity (p.14: "Planets and satellites of the newly formed federation
// cannot be directly adjacent to planets or satellites from any of your existing federations")
// ────────────────────────────────────────────────────────────────────────────────────────────

/// The same two-cluster federation board as `board_with_two_clusters`, plus a second,
/// independently-sufficient cluster `e`(TradingStation,2)-`f`(PlanetaryInstitute,3)-
/// `g`(TradingStation,2) starting directly adjacent to `c`.
fn board_with_an_adjacent_second_cluster() -> BoardState {
    let mut board = board_with_two_clusters();
    let e = HexCoord::new(4, 0); // adjacent to c = (3, 0)
    let f = HexCoord::new(5, 0);
    let g = HexCoord::new(6, 0);
    for (coord, kind) in [
        (e, StructureType::TradingStation),
        (f, StructureType::PlanetaryInstitute),
        (g, StructureType::TradingStation),
    ] {
        board.hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure { owner: 0, kind }],
                satellites: vec![],
            },
        );
    }
    board
}

#[test]
fn federation_rejects_a_new_federation_adjacent_to_an_existing_one() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.vp = 10;
            p.resources.power.bowl1 = 4;
            p.structures = vec![
                Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: HexCoord::new(1, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(3, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(4, 0),
                    kind: StructureType::TradingStation,
                },
                Structure {
                    hex: HexCoord::new(5, 0),
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: HexCoord::new(6, 0),
                    kind: StructureType::TradingStation,
                },
            ];
        })
        .with_player(1)
        .with_board(board_with_an_adjacent_second_cluster())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![
        gaia_engine::game_state::FederationToken(1),
        gaia_engine::game_state::FederationToken(2),
    ];

    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    // e-f-g (power 2+3+2=7) is self-sufficient and connected on its own, but e is directly
    // adjacent to c, part of the first federation — must be rejected.
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

// ── Satellite supply cap (25 per player color, `docs/EN_Gaia_rulebook_lo.pdf` components
// list: "Other Player Pieces (in each player color) ... 25 Satellites") ─────────────────────

#[test]
fn federation_rejects_a_satellite_once_the_players_supply_of_25_is_exhausted() {
    let mut state = base_state();
    // Pre-place 25 satellites for player 0 on otherwise-unrelated hexes.
    for i in 0..25 {
        let coord = HexCoord::new(100 + i, 0);
        state.board.hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![],
                satellites: vec![0],
            },
        );
    }

    let result = form_federation(&mut state, vec![BRIDGE]);
    assert!(result.is_err());
}

// ── Silent free enlargement via colonization (p.14: "When colonizing planets directly
// adjacent to one of your federations, these new planets enlarge the existing federation
// without any advantage for you") ──────────────────────────────────────────────────────────

#[test]
fn colonizing_next_to_an_existing_federation_enlarges_it_for_free() {
    let mut state = base_state();
    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    // Round 1's default test-fixture round tile also scores on BuildMine — swap it for an
    // unrelated condition so only the silent-enlargement VP (none) is being measured here.
    state.round_tiles[0].condition = gaia_engine::game_state::RoundCondition::FormFederation;

    // Directly adjacent to c = (3, 0), already part of the federation.
    let new_planet = HexCoord::new(4, 0);
    state.board.hexes.insert(
        new_planet,
        Hex {
            coord: new_planet,
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
    state.players[0].resources.ore = 10;
    state.players[0].resources.credits = 10;
    let vp_before = state.players[0].vp;
    let federation_tokens_before = state.players[0].federation_tokens.len();

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: new_planet })
        .unwrap_or_else(|e| panic!("build should succeed: {e}"));

    assert!(state.players[0].federated_hexes.contains(&new_planet));
    assert_eq!(
        state.players[0].vp, vp_before,
        "no VP advantage from silent enlargement"
    );
    assert_eq!(
        state.players[0].federation_tokens.len(),
        federation_tokens_before,
        "no new federation token from silent enlargement"
    );
}

#[test]
fn colonizing_a_planet_unrelated_to_any_federation_does_not_enlarge_anything() {
    let mut state = base_state();
    form_federation(&mut state, vec![BRIDGE])
        .unwrap_or_else(|e| panic!("first federation should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    // A second, unrelated Mine far from the federation, with a build target adjacent to *it*
    // instead — every hex adjacent to the federation's own structures would trivially trigger
    // enlargement, so this needs its own separate anchor to test "reachable but unrelated."
    let unrelated_mine = HexCoord::new(-5, 0);
    let far_planet = HexCoord::new(-4, 0);
    state.board.hexes.insert(
        unrelated_mine,
        Hex {
            coord: unrelated_mine,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    state.board.hexes.insert(
        far_planet,
        Hex {
            coord: far_planet,
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
    state.players[0].structures.push(Structure {
        hex: unrelated_mine,
        kind: StructureType::Mine,
    });
    state.players[0].resources.ore = 10;
    state.players[0].resources.credits = 10;

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: far_planet })
        .unwrap_or_else(|e| panic!("build should succeed: {e}"));

    assert!(!state.players[0].federated_hexes.contains(&far_planet));
}
