use gaia_engine::game_state::{
    BoardState, FederationToken, GamePhase, Hex, HexCoord, PlacedStructure, Sector, SpaceshipBoard,
    SpaceshipId, Structure, StructureType, TechTile,
};
use gaia_engine::rules::actions::{FederationTokenChoice, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), "4) Form a Federation" (p.14) and the p.2
// components image's 19-token catalog; Lost Fleet expansion (`docs/GP_Exp_Rule_EN_V1_Web.pdf`,
// "4) Action: Form a Federation" + Appendix VI) for the 4 spaceship-tied tokens.

/// 3 mutually-adjacent hexes with structures totaling exactly `FEDERATION_MIN_POWER` (7): a
/// Planetary Institute (3) + 2 Trading Stations (2 each), all owned by player 0.
fn board_with_federation_structures() -> BoardState {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(0, 1);
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
    // A build-target hex for the Lost Fleet free-build token tests: Volcanic, adjacent to `a`.
    let target = HexCoord::new(-1, 0);
    hexes.insert(
        target,
        Hex {
            coord: target,
            planet: Some(gaia_engine::game_state::Planet {
                planet_type: gaia_engine::game_state::PlanetType::Volcanic,
                is_gaia_formed: false,
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
            origin: a,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn base_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.ore = 15;
            p.resources.credits = 15;
            p.resources.knowledge = 15;
            p.resources.qic = 15;
            p.resources.power.bowl3 = 10;
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
                    hex: HexCoord::new(0, 1),
                    kind: StructureType::TradingStation,
                },
            ];
        })
        .with_player_fn(1, |p| {
            p.vp = 10;
        })
        .with_board(board_with_federation_structures())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

fn federation_hexes() -> Vec<HexCoord> {
    vec![
        HexCoord::new(0, 0),
        HexCoord::new(1, 0),
        HexCoord::new(0, 1),
    ]
}

fn form_federation(
    state: &mut gaia_engine::game_state::GameState,
    kind: u8,
    bonus_build_coord: Option<HexCoord>,
    bonus_tech_tile: Option<TechTile>,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, gaia_engine::RuleError> {
    RuleEngine::apply_action(
        state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Supply { kind },
            bonus_build_coord,
            bonus_tech_tile,
        },
    )
}

// ── Base-game supply tokens (ids 1-7) ─────────────────────────────────────────

#[test]
fn kind_1_grants_flat_12_vp() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(1)];
    let vp_before = state.players[0].vp;

    form_federation(&mut state, 1, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 12);
    assert!(state.research_board.federation_tokens.is_empty());
    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(1)]);
}

#[test]
fn kind_2_grants_8_vp_plus_1_qic() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(2)];
    let vp_before = state.players[0].vp;
    let qic_before = state.players[0].resources.qic;

    form_federation(&mut state, 2, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 8);
    assert_eq!(state.players[0].resources.qic, qic_before + 1);
}

#[test]
fn kind_3_grants_8_vp_plus_2_power_as_fresh_bowl1_tokens() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(3)];
    let vp_before = state.players[0].vp;
    let bowl1_before = state.players[0].resources.power.bowl1;

    form_federation(&mut state, 3, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 8);
    assert_eq!(state.players[0].resources.power.bowl1, bowl1_before + 2);
}

#[test]
fn kind_4_grants_7_vp_plus_2_ore() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(4)];
    let vp_before = state.players[0].vp;
    let ore_before = state.players[0].resources.ore;

    form_federation(&mut state, 4, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 7);
    assert_eq!(state.players[0].resources.ore, ore_before + 2);
}

#[test]
fn kind_5_grants_7_vp_plus_6_credits() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(5)];
    let vp_before = state.players[0].vp;
    let credits_before = state.players[0].resources.credits;

    form_federation(&mut state, 5, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 7);
    assert_eq!(state.players[0].resources.credits, credits_before + 6);
}

#[test]
fn kind_6_grants_6_vp_plus_2_knowledge() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(6)];
    let vp_before = state.players[0].vp;
    let knowledge_before = state.players[0].resources.knowledge;

    form_federation(&mut state, 6, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 6);
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 2);
}

#[test]
fn kind_7_grants_1_ore_1_knowledge_2_credits_no_vp() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(7)];
    let vp_before = state.players[0].vp;
    let ore_before = state.players[0].resources.ore;
    let knowledge_before = state.players[0].resources.knowledge;
    let credits_before = state.players[0].resources.credits;

    form_federation(&mut state, 7, None, None).unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before);
    assert_eq!(state.players[0].resources.ore, ore_before + 1);
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 1);
    assert_eq!(state.players[0].resources.credits, credits_before + 2);
}

#[test]
fn supply_pool_depletes_and_rejects_an_unavailable_kind() {
    let mut state = base_state();
    state.research_board.federation_tokens = vec![FederationToken(1)];

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Supply { kind: 2 }, // not in the (single-entry) pool
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

// ── Lost Fleet spaceship-tied tokens (ids 8-15, one physical token each) ─────

fn state_with_spaceship_token(kind: u8) -> gaia_engine::game_state::GameState {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.spaceship_boards = vec![SpaceshipBoard {
        id: SpaceshipId::Twilight,
        explorers: vec![Some(0), None, None, None],
        artifact_pool: vec![],
        tech_tiles: vec![],
        federation_token: Some(FederationToken(kind)),
    }];
    state
}

#[test]
fn kind_9_grants_flat_12_vp_via_spaceship_path() {
    let mut state = state_with_spaceship_token(9);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 12);
    let board = &state.spaceship_boards[0];
    assert!(board.federation_token.is_none());
}

#[test]
fn kind_8_grants_8_vp_plus_8_credits() {
    let mut state = state_with_spaceship_token(8);
    let vp_before = state.players[0].vp;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 8);
    assert_eq!(state.players[0].resources.credits, credits_before + 8);
}

#[test]
fn kind_10_grants_4_vp_plus_4_knowledge() {
    let mut state = state_with_spaceship_token(10);
    let vp_before = state.players[0].vp;
    let knowledge_before = state.players[0].resources.knowledge;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 4);
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 4);
}

#[test]
fn kind_11_grants_4_vp_plus_2_ore_plus_1_qic() {
    let mut state = state_with_spaceship_token(11);
    let vp_before = state.players[0].vp;
    let ore_before = state.players[0].resources.ore;
    let qic_before = state.players[0].resources.qic;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 4);
    assert_eq!(state.players[0].resources.ore, ore_before + 2);
    assert_eq!(state.players[0].resources.qic, qic_before + 1);
}

#[test]
fn kind_13_grants_7_vp_plus_2_fresh_power_tokens_to_bowl3() {
    let mut state = state_with_spaceship_token(13);
    let vp_before = state.players[0].vp;
    let bowl3_before = state.players[0].resources.power.bowl3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 7);
    // Fresh tokens directly into bowl3 ("Area III") — confirmed via the physical token photo,
    // same fresh-grant style as the base game's kind-3 "+2 power" (bowl1), not a charge.
    assert_eq!(state.players[0].resources.power.bowl3, bowl3_before + 2);
}

#[test]
fn spaceship_token_requires_the_ship_explored() {
    let mut state = state_with_spaceship_token(9);
    state.players[0].explored_ships.clear(); // hasn't actually explored Twilight

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn spaceship_token_requires_it_not_already_claimed() {
    let mut state = state_with_spaceship_token(8);
    state.spaceship_boards[0].federation_token = None; // already claimed by someone else

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn kind_15_grants_a_free_build_of_unlimited_range() {
    let mut state = state_with_spaceship_token(15);
    // Move the build target far out of normal range so only "unlimited range" can reach it.
    let far = HexCoord::new(-40, 0);
    state.board.hexes.insert(
        far,
        Hex {
            coord: far,
            planet: Some(gaia_engine::game_state::Planet {
                planet_type: gaia_engine::game_state::PlanetType::Volcanic,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: Some(far),
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    let built = state.players[0]
        .structures
        .iter()
        .any(|s| s.hex == far && s.kind == StructureType::Mine);
    assert!(built, "expected a Mine built at the far hex");
    // No mine ore cost (free build) but terraforming ore for Volcanic still applies.
    assert!(state.players[0].resources.ore <= ore_before);
}

#[test]
fn kind_15_requires_a_bonus_build_coord() {
    let mut state = state_with_spaceship_token(15);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn kind_15_bonus_build_advances_the_turn_exactly_once() {
    let mut state = state_with_spaceship_token(15);
    let target = HexCoord::new(-1, 0);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: Some(target),
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    // 2 players; exactly one advance_turn() should move active_player from 0 to 1.
    match state.phase {
        GamePhase::ActionPhase { active_player } => assert_eq!(active_player, 1),
        other => panic!("expected ActionPhase, got {other:?}"),
    }
}

#[test]
fn kind_14_grants_a_free_build_with_up_to_3_terraform_steps() {
    let mut state = state_with_spaceship_token(14);
    let target = HexCoord::new(-1, 0); // Volcanic, adjacent to the federation hexes
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: Some(target),
            bonus_tech_tile: None,
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    let built = state.players[0]
        .structures
        .iter()
        .any(|s| s.hex == target && s.kind == StructureType::Mine);
    assert!(built);
    // Free build: the base 1-ore mine cost still applies (`MINE_ORE_COST`, unaffected by
    // `free_terraform_steps`), but no additional terraforming ore — Volcanic is within the 3
    // free terraforming steps this token grants.
    assert_eq!(state.players[0].resources.ore, ore_before - 1);
}

#[test]
fn kind_12_grants_a_standard_tech_tile_of_choice() {
    let mut state = state_with_spaceship_token(12);
    let chosen = TechTile(3);
    let tiles_before = state.research_board.tech_tiles.len();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: Some(chosen.clone()),
        },
    )
    .unwrap_or_else(|e| panic!("should succeed: {e}"));

    assert!(state.players[0].tech_tiles.contains(&chosen));
    assert_eq!(state.research_board.tech_tiles.len(), tiles_before - 1);
}

#[test]
fn kind_12_requires_choosing_an_available_tech_tile() {
    let mut state = state_with_spaceship_token(12);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: federation_hexes(),
            token: FederationTokenChoice::Spaceship {
                ship: SpaceshipId::Twilight,
            },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(result.is_err());
}
