use std::collections::HashMap;

use gaia_engine::game_state::{
    BoardState, FactionId, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType,
    RoundCondition, RoundTile, Sector, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

const PLAYER: u8 = 0;
const ANCHOR: HexCoord = HexCoord::new(0, 0);
const TARGET: HexCoord = HexCoord::new(1, 0);

fn board_with_planet(target_type: PlanetType, is_gaia_formed: bool) -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        ANCHOR,
        Hex {
            coord: ANCHOR,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: PLAYER,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        TARGET,
        Hex {
            coord: TARGET,
            planet: Some(Planet {
                planet_type: target_type,
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
            origin: ANCHOR,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn board_with_adjacent_deep_space_planets() -> BoardState {
    let first = HexCoord::new(0, 0);
    let second = HexCoord::new(2, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        first,
        Hex {
            coord: first,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: Some(PLAYER),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: PLAYER,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        second,
        Hex {
            coord: second,
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
    let bridge = HexCoord::new(1, 0);
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
    BoardState {
        sectors: vec![
            Sector {
                id: 11,
                rotation: 0,
                origin: first,
            },
            Sector {
                id: 12,
                rotation: 0,
                origin: second,
            },
        ],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn build_state(
    tile_id: u8,
    target_type: PlanetType,
    is_gaia_formed: bool,
) -> gaia_engine::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(PLAYER, |player| {
            player.faction = Some(FactionId::Terrans);
            player.resources.ore = 30;
            player.resources.credits = 30;
            player.resources.qic = 10;
            player.structures = vec![Structure {
                hex: ANCHOR,
                kind: StructureType::Mine,
            }];
        })
        .with_board(board_with_planet(target_type, is_gaia_formed))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.round = 1;
    state.round_tiles[0] = RoundTile::from_id(tile_id);
    state
}

#[test]
fn all_twelve_tiles_have_the_defined_condition_and_vp() {
    let expected = [
        (RoundCondition::BuildMine, 2),
        (RoundCondition::TerraformingStep, 2),
        (RoundCondition::BuildMineOnGaia, 4),
        (RoundCondition::UpgradeTradingStation, 3),
        (RoundCondition::FormFederation, 5),
        (RoundCondition::UpgradeLargeBuilding, 5),
        (RoundCondition::BuildMineOnGaia, 3),
        (RoundCondition::UpgradeTradingStation, 4),
        (RoundCondition::ResearchAdvance, 2),
        (RoundCondition::BuildMineOnNewPlanetType, 3),
        (RoundCondition::BuildMineInNewSector, 3),
        (RoundCondition::UpgradeResearchLab, 4),
    ];

    for (index, (condition, vp)) in expected.into_iter().enumerate() {
        let tile = RoundTile::from_id((index + 1) as u8);
        assert_eq!(
            tile.condition,
            condition,
            "wrong condition for tile {}",
            index + 1
        );
        assert_eq!(tile.vp_per_unit, vp, "wrong VP for tile {}", index + 1);
    }
}

#[test]
fn terraforming_tile_scores_once_per_step_used() {
    // Terrans: Terra -> Volcanic is two steps around the planet ring.
    let mut state = build_state(2, PlanetType::Volcanic, false);
    let vp_before = state.player(PLAYER).map_or(0, |player| player.vp);

    RuleEngine::apply_action(&mut state, PLAYER, GameAction::Build { coord: TARGET })
        .unwrap_or_else(|error| panic!("build should be valid: {error}"));

    assert_eq!(
        state.player(PLAYER).map_or(0, |player| player.vp),
        vp_before + 4
    );
}

#[test]
fn new_sector_tile_scores_a_mine_in_a_different_deep_space_sector() {
    let first = HexCoord::new(0, 0);
    let target = HexCoord::new(2, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(PLAYER, |player| {
            player.faction = Some(FactionId::Terrans);
            player.resources.ore = 30;
            player.resources.credits = 30;
            player.research_tracks.navigation = 2;
            player.structures = vec![Structure {
                hex: first,
                kind: StructureType::Mine,
            }];
        })
        .with_board(board_with_adjacent_deep_space_planets())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.round_tiles[0] = RoundTile::from_id(11);
    let vp_before = state.player(PLAYER).map_or(0, |player| player.vp);

    RuleEngine::apply_action(&mut state, PLAYER, GameAction::Build { coord: target })
        .unwrap_or_else(|error| panic!("deep-space build should be valid: {error}"));

    assert_eq!(
        state.player(PLAYER).map_or(0, |player| player.vp),
        vp_before + 3
    );
}

#[test]
fn gaia_mine_tile_only_scores_a_gaia_planet() {
    let mut gaia_state = build_state(3, PlanetType::Transdim, true);
    let gaia_vp = gaia_state.player(PLAYER).map_or(0, |player| player.vp);
    RuleEngine::apply_action(&mut gaia_state, PLAYER, GameAction::Build { coord: TARGET })
        .unwrap_or_else(|error| panic!("Gaia build should be valid: {error}"));
    assert_eq!(
        gaia_state.player(PLAYER).map_or(0, |player| player.vp),
        gaia_vp + 4
    );

    let mut normal_state = build_state(3, PlanetType::Terra, false);
    let normal_vp = normal_state.player(PLAYER).map_or(0, |player| player.vp);
    RuleEngine::apply_action(
        &mut normal_state,
        PLAYER,
        GameAction::Build { coord: TARGET },
    )
    .unwrap_or_else(|error| panic!("normal build should be valid: {error}"));
    assert_eq!(
        normal_state.player(PLAYER).map_or(0, |player| player.vp),
        normal_vp
    );
}

#[test]
fn trading_station_tile_only_scores_that_upgrade_target() {
    let mut state = build_state(4, PlanetType::Terra, false);
    let vp_before = state.player(PLAYER).map_or(0, |player| player.vp);

    RuleEngine::apply_action(
        &mut state,
        PLAYER,
        GameAction::Upgrade {
            tech_tile_choice: None,
            coord: ANCHOR,
            to: StructureType::TradingStation,
        },
    )
    .unwrap_or_else(|error| panic!("trading-station upgrade should be valid: {error}"));

    assert_eq!(
        state.player(PLAYER).map_or(0, |player| player.vp),
        vp_before + 3
    );
}

#[test]
fn new_sector_tile_does_not_score_an_interspace_mine() {
    let mut state = build_state(11, PlanetType::Terra, false);
    // This gap is within radius two of Deep Space but outside its three-hex footprint.
    // It must not be treated as a previously uncolonized sector.
    state.board.sectors = vec![Sector {
        id: 11,
        origin: HexCoord::new(2, -1),
        rotation: 0,
    }];
    let before = state.players[0].vp;
    let events = RuleEngine::apply_action(&mut state, PLAYER, GameAction::Build { coord: TARGET })
        .unwrap_or_else(|error| panic!("mine build should succeed: {error}"));
    assert_eq!(state.players[0].vp, before);
    assert!(!events.iter().any(|event| matches!(
        event,
        gaia_engine::game_state::GameEvent::VpAwarded {
            reason: gaia_engine::game_state::VpReason::RoundTile { tile_id: 11 },
            ..
        }
    )));
}

#[test]
fn new_sector_tile_scores_only_the_first_mine_in_a_standard_sector() {
    for (origin, expected_vp) in [(ANCHOR, 0), (HexCoord::new(3, 0), 3)] {
        let mut state = build_state(11, PlanetType::Terra, false);
        state.board.sectors[0].origin = origin;
        let before = state.players[0].vp;
        RuleEngine::apply_action(&mut state, PLAYER, GameAction::Build { coord: TARGET })
            .unwrap_or_else(|error| panic!("mine build should succeed: {error}"));
        assert_eq!(state.players[0].vp - before, expected_vp);
    }
}
