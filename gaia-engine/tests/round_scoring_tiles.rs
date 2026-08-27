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
