use super::*;
use crate::game_state::{
    AcademyType, AdvancedTechTile, BoardState, FederationToken, Hex, PlacedStructure, Planet,
    Sector, Structure, TechTile,
};
use crate::randomizer::{Randomizer, ADVANCED_TECH_TILE_IDS};
use crate::test_utils::builders::GameStateBuilder;
use std::path::Path;

const STANDARD_IDS: [u8; 12] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

fn add_structure_hex(
    hexes: &mut HashMap<HexCoord, Hex>,
    structures: &mut Vec<Structure>,
    coord: HexCoord,
    kind: StructureType,
    planet_type: PlanetType,
    is_gaia_formed: bool,
) {
    hexes.insert(
        coord,
        Hex {
            coord,
            planet: Some(Planet {
                planet_type,
                is_gaia_formed,
                owner: Some(0),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure { owner: 0, kind }],
            satellites: vec![],
        },
    );
    structures.push(Structure { hex: coord, kind });
}

/// A single fixture with stable, independently countable values for every counter used by a
/// Standard or Advanced Tech tile:
/// - 2 Trading Stations
/// - 3 Federation tokens (1 green + 2 gray)
/// - 2 ordinary sectors and 2 Deep Space sectors
/// - 2 Gaia planets
/// - 3 Mines (2 on the board + 1 Artifact Mine)
/// - 2 large buildings
/// - 3 planet types (Terra, Gaia, Asteroid)
/// - 1 asteroid (the Artifact Mine)
fn counted_state() -> GameState {
    let mut hexes = HashMap::new();
    let mut structures = Vec::new();
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(0, 0),
        StructureType::TradingStation,
        PlanetType::Terra,
        false,
    );
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(1, 0),
        StructureType::TradingStation,
        PlanetType::Terra,
        false,
    );
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(10, 0),
        StructureType::Mine,
        PlanetType::Swamp,
        true,
    );
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(20, 0),
        StructureType::Mine,
        PlanetType::Desert,
        true,
    );
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(30, 0),
        StructureType::PlanetaryInstitute,
        PlanetType::Terra,
        false,
    );
    add_structure_hex(
        &mut hexes,
        &mut structures,
        HexCoord::new(0, 1),
        StructureType::Academy(AcademyType::Science),
        PlanetType::Terra,
        false,
    );

    let board = BoardState {
        sectors: vec![
            Sector {
                id: 1,
                rotation: 0,
                origin: HexCoord::new(0, 0),
            },
            Sector {
                id: 2,
                rotation: 0,
                origin: HexCoord::new(10, 0),
            },
            Sector {
                id: 11,
                rotation: 0,
                origin: HexCoord::new(20, 0),
            },
            Sector {
                id: 12,
                rotation: 0,
                origin: HexCoord::new(30, 0),
            },
        ],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };

    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.resources.ore = 4;
            player.resources.credits = 10;
            player.resources.knowledge = 3;
            player.resources.qic = 1;
            player.structures = structures;
            player.artifact_mines = vec![PlanetType::Asteroid];
            player.federation_tokens = vec![FederationToken(1)];
            player.gray_federation_tokens = vec![FederationToken(2), FederationToken(3)];
        })
        .with_board(board)
        .build()
}

fn resources(state: &GameState) -> (u8, u8, u8, u8) {
    let resources = &state.players[0].resources;
    (
        resources.ore,
        resources.credits,
        resources.knowledge,
        resources.qic,
    )
}

fn awarded_vp(events: &[GameEvent]) -> i32 {
    events
        .iter()
        .filter_map(|event| match event {
            GameEvent::VpAwarded { amount, .. } => Some(*amount),
            _ => None,
        })
        .sum()
}

#[test]
fn technology_catalog_matches_assets_and_setup_pools() {
    let asset_dir = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../gaia-frontend/src/assets/tech_tiles/rendered");
    for id in STANDARD_IDS {
        assert!(
            asset_dir.join(format!("std_{id:02}.webp")).is_file(),
            "missing rendered Standard Tech tile {id}"
        );
    }
    for id in ADVANCED_TECH_TILE_IDS {
        assert!(
            asset_dir.join(format!("adv_{id:02}.webp")).is_file(),
            "missing rendered Advanced Tech tile {id}"
        );
    }

    let setup = Randomizer::generate_setup("tech-tile-audit")
        .unwrap_or_else(|error| panic!("audit setup should be valid: {error}"));
    let mut base_standard_ids = setup.tech_tile_slot_ids;
    base_standard_ids.sort_unstable();
    assert_eq!(base_standard_ids, (2..=10).collect::<Vec<_>>());

    let mut spaceship_standard_ids = MapEngine::initial_spaceship_boards("tech-tile-audit")
        .into_iter()
        .flat_map(|board| board.tech_tiles)
        .map(|tile| tile.0)
        .collect::<Vec<_>>();
    spaceship_standard_ids.sort_unstable();
    spaceship_standard_ids.dedup();
    assert_eq!(spaceship_standard_ids, vec![11, 12, 13]);
}

#[test]
fn standard_immediate_reward_branches_match_all_tile_faces() {
    let cases = [
        (4, (1, 0, 0, 1), 0),
        (7, (0, 0, 0, 0), 7),
        (9, (0, 0, 3, 0), 0),
        (13, (1, 0, 3, 0), 0),
    ];
    for (id, expected_resources, expected_vp) in cases {
        let mut state = counted_state();
        let before_resources = resources(&state);
        let before_vp = state.players[0].vp;
        let events = apply_tech_tile_immediate_reward(&mut state, 0, id);
        let after_resources = resources(&state);
        assert_eq!(
            (
                after_resources.0 - before_resources.0,
                after_resources.1 - before_resources.1,
                after_resources.2 - before_resources.2,
                after_resources.3 - before_resources.3,
            ),
            expected_resources,
            "Standard Tech tile {id} resource result"
        );
        assert_eq!(state.players[0].vp - before_vp, expected_vp, "tile {id}");
        assert_eq!(awarded_vp(&events), expected_vp, "tile {id} event");
    }

    for id in [2, 3, 5, 6, 8, 10, 11, 12] {
        let mut state = counted_state();
        let before_resources = resources(&state);
        let before_vp = state.players[0].vp;
        let events = apply_tech_tile_immediate_reward(&mut state, 0, id);
        assert_eq!(
            resources(&state),
            before_resources,
            "Standard Tech tile {id}"
        );
        assert_eq!(state.players[0].vp, before_vp, "Standard Tech tile {id}");
        assert!(events.is_empty(), "Standard Tech tile {id}");
    }
}

#[test]
fn advanced_immediate_reward_branches_match_all_tile_faces() {
    let cases = [
        (1, (0, 0, 0, 0), 8),
        (2, (0, 0, 0, 0), 15),
        (5, (2, 0, 0, 0), 0),
        (6, (0, 0, 0, 0), 4),
        (9, (0, 0, 0, 0), 4),
        (10, (0, 0, 0, 0), 6),
        (12, (0, 0, 0, 0), 8),
        (13, (0, 0, 0, 0), 12),
    ];
    for (id, expected_resources, expected_vp) in cases {
        let mut state = counted_state();
        let before_resources = resources(&state);
        let before_vp = state.players[0].vp;
        let events = apply_advanced_tech_tile_immediate_reward(&mut state, 0, id);
        let after_resources = resources(&state);
        assert_eq!(
            (
                after_resources.0 - before_resources.0,
                after_resources.1 - before_resources.1,
                after_resources.2 - before_resources.2,
                after_resources.3 - before_resources.3,
            ),
            expected_resources,
            "Advanced Tech tile {id} resource result"
        );
        assert_eq!(state.players[0].vp - before_vp, expected_vp, "tile {id}");
        assert_eq!(awarded_vp(&events), expected_vp, "tile {id} event");
    }

    for id in [3, 4, 7, 8, 11, 14, 15, 16, 17, 19, 20, 21, 22] {
        let mut state = counted_state();
        let before_resources = resources(&state);
        let before_vp = state.players[0].vp;
        let events = apply_advanced_tech_tile_immediate_reward(&mut state, 0, id);
        assert_eq!(
            resources(&state),
            before_resources,
            "Advanced Tech tile {id}"
        );
        assert_eq!(state.players[0].vp, before_vp, "Advanced Tech tile {id}");
        assert!(events.is_empty(), "Advanced Tech tile {id}");
    }
}

#[test]
fn recurring_event_reward_branches_match_all_trigger_tiles() {
    let cases = [
        (RoundCondition::BuildMineOnGaia, 6),
        (RoundCondition::UpgradeTradingStation, 6),
        (RoundCondition::BuildMine, 6),
        (RoundCondition::ResearchAdvance, 4),
        (RoundCondition::TerraformingStep, 4),
        (RoundCondition::FormFederation, 0),
    ];
    for (condition, expected_vp) in cases {
        let mut state = counted_state();
        state.players[0].tech_tiles = vec![TechTile(8)];
        state.players[0].advanced_tech_tiles = vec![
            AdvancedTechTile(3),
            AdvancedTechTile(4),
            AdvancedTechTile(8),
            AdvancedTechTile(17),
        ];
        let before_vp = state.players[0].vp;
        let events = check_tech_tile_event_bonus(&mut state, 0, &condition, 2);
        assert_eq!(
            state.players[0].vp - before_vp,
            expected_vp,
            "{condition:?}"
        );
        assert_eq!(awarded_vp(&events), expected_vp, "{condition:?} event");
        let repeated = check_tech_tile_event_bonus(&mut state, 0, &condition, 2);
        assert_eq!(state.players[0].vp - before_vp, expected_vp * 2, "{condition:?} repeated");
        assert_eq!(awarded_vp(&repeated), expected_vp, "{condition:?} repeated event");
    }

    let mut covered = counted_state();
    covered.players[0].tech_tiles = vec![TechTile(8)];
    covered.players[0].covered_tech_tiles = vec![TechTile(8)];
    let before_vp = covered.players[0].vp;
    let events = check_tech_tile_event_bonus(&mut covered, 0, &RoundCondition::BuildMineOnGaia, 1);
    assert_eq!(covered.players[0].vp, before_vp);
    assert!(events.is_empty());

    let mut zero_units = counted_state();
    zero_units.players[0].advanced_tech_tiles = vec![AdvancedTechTile(4)];
    let before_vp = zero_units.players[0].vp;
    let events = check_tech_tile_event_bonus(&mut zero_units, 0, &RoundCondition::BuildMine, 0);
    assert_eq!(zero_units.players[0].vp, before_vp);
    assert!(events.is_empty());
}

#[test]
fn pass_reward_branches_match_all_pass_tiles() {
    let cases = [(7, 6), (11, 9), (14, 2), (15, 4), (19, 3)];
    for (id, expected_vp) in cases {
        let mut state = counted_state();
        state.players[0].structures.extend([
            Structure {
                hex: HexCoord::new(40, 0),
                kind: StructureType::ResearchLab,
            },
            Structure {
                hex: HexCoord::new(41, 0),
                kind: StructureType::ResearchLab,
            },
        ]);
        state.players[0].advanced_tech_tiles = vec![AdvancedTechTile(id)];
        let before_vp = state.players[0].vp;
        let events = apply_tech_tile_pass_bonus(&mut state, 0);
        assert_eq!(state.players[0].vp - before_vp, expected_vp, "tile {id}");
        assert_eq!(awarded_vp(&events), expected_vp, "tile {id} event");
        let repeated = apply_tech_tile_pass_bonus(&mut state, 0);
        assert_eq!(state.players[0].vp - before_vp, expected_vp * 2, "tile {id} repeated pass");
        assert_eq!(awarded_vp(&repeated), expected_vp, "tile {id} repeated event");
    }

    for id in STANDARD_IDS {
        let mut state = counted_state();
        state.players[0].tech_tiles = vec![TechTile(id)];
        let before_vp = state.players[0].vp;
        let events = apply_tech_tile_pass_bonus(&mut state, 0);
        assert_eq!(state.players[0].vp, before_vp, "Standard Tech tile {id}");
        assert!(events.is_empty(), "Standard Tech tile {id}");
    }
}

fn effect_values(effect: Option<TechTileSpecialActionEffect>) -> Option<(u8, u8, u8, u8, u8)> {
    effect.map(|effect| {
        (
            effect.ore,
            effect.credits,
            effect.knowledge,
            effect.qic,
            effect.charge_power,
        )
    })
}

#[test]
fn special_action_branches_match_all_action_tiles() {
    assert_eq!(
        effect_values(tech_tile_special_action_effect(10)),
        Some((0, 0, 0, 0, 4))
    );
    for id in STANDARD_IDS.into_iter().filter(|id| *id != 10) {
        assert_eq!(effect_values(tech_tile_special_action_effect(id)), None);
    }

    let advanced_cases = [
        (20, (0, 0, 3, 0, 0)),
        (21, (3, 0, 0, 0, 0)),
        (22, (0, 5, 0, 1, 0)),
    ];
    for (id, expected) in advanced_cases {
        assert_eq!(
            effect_values(advanced_tech_tile_special_action_effect(id)),
            Some(expected),
            "Advanced Tech tile {id}"
        );
    }
    for id in ADVANCED_TECH_TILE_IDS
        .into_iter()
        .filter(|id| ![20, 21, 22].contains(id))
    {
        assert_eq!(
            effect_values(advanced_tech_tile_special_action_effect(id)),
            None,
            "Advanced Tech tile {id}"
        );
    }

    let mut covered = counted_state();
    covered.players[0].tech_tiles = vec![TechTile(10)];
    covered.players[0].covered_tech_tiles = vec![TechTile(10)];
    assert!(RuleEngine::apply_action(
        &mut covered,
        0,
        GameAction::TechTileSpecialAction {
            tile: TechTileRef::Standard { tile: TechTile(10) },
        },
    )
    .is_err());
}

#[test]
fn income_range_and_power_value_branches_honor_covering() {
    let income_cases = [(2, (1, 0, 0), 1), (3, (0, 4, 0), 0), (5, (0, 1, 1), 0)];
    for (id, expected_resources, expected_charge) in income_cases {
        let mut state = counted_state();
        state.players[0].tech_tiles = vec![TechTile(id)];
        state.players[0].resources.power.bowl1 = 2;
        state.players[0].resources.power.bowl2 = 0;
        let before = resources(&state);
        let power_charge = apply_tech_tile_income(&mut state.players[0]);
        let after = resources(&state);
        assert_eq!(
            (after.0 - before.0, after.1 - before.1, after.2 - before.2),
            expected_resources,
            "Standard Tech tile {id}"
        );
        assert_eq!(power_charge, expected_charge, "Standard Tech tile {id}");
        assert_eq!(
            state.players[0].resources.power.bowl2, expected_charge,
            "Standard Tech tile {id} power charge"
        );
    }

    let mut covered_income = counted_state();
    covered_income.players[0].tech_tiles = vec![TechTile(2)];
    covered_income.players[0].covered_tech_tiles = vec![TechTile(2)];
    let before = resources(&covered_income);
    let before_power = covered_income.players[0].resources.power.clone();
    assert_eq!(apply_tech_tile_income(&mut covered_income.players[0]), 0);
    assert_eq!(resources(&covered_income), before);
    assert_eq!(covered_income.players[0].resources.power, before_power);

    let mut ongoing = counted_state();
    ongoing.players[0].tech_tiles = vec![TechTile(6), TechTile(12)];
    assert_eq!(player_nav_range(&ongoing.players[0], 0), 2);
    assert_eq!(
        tech_tile_large_building_power_bonus(&ongoing, 0, StructureType::PlanetaryInstitute),
        1
    );
    assert_eq!(
        tech_tile_large_building_power_bonus(&ongoing, 0, StructureType::Academy(AcademyType::Qic)),
        1
    );
    assert_eq!(
        tech_tile_large_building_power_bonus(&ongoing, 0, StructureType::Mine),
        0
    );

    ongoing.players[0].covered_tech_tiles = vec![TechTile(6), TechTile(12)];
    assert_eq!(player_nav_range(&ongoing.players[0], 0), 1);
    assert_eq!(
        tech_tile_large_building_power_bonus(&ongoing, 0, StructureType::PlanetaryInstitute),
        0
    );
}

#[test]
fn advanced_qic_bonus_and_special_action_usage_branches_are_exact() {
    let mut without_tile = counted_state();
    let before_vp = without_tile.players[0].vp;
    assert!(apply_advanced_tech_qic_action_bonus(&mut without_tile, 0).is_empty());
    assert_eq!(without_tile.players[0].vp, before_vp);

    let mut with_tile = counted_state();
    with_tile.players[0].advanced_tech_tiles = vec![AdvancedTechTile(16)];
    let before_vp = with_tile.players[0].vp;
    let events = apply_advanced_tech_qic_action_bonus(&mut with_tile, 0);
    assert_eq!(with_tile.players[0].vp - before_vp, 4);
    assert_eq!(awarded_vp(&events), 4);

    for (id, expected_delta) in [(20, (0, 0, 3, 0)), (21, (3, 0, 0, 0)), (22, (0, 5, 0, 1))] {
        let mut state = counted_state();
        state.players[0].advanced_tech_tiles = vec![AdvancedTechTile(id)];
        let before = resources(&state);
        RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::TechTileSpecialAction {
                tile: TechTileRef::Advanced {
                    tile: AdvancedTechTile(id),
                },
            },
        )
        .unwrap_or_else(|error| panic!("Advanced Tech tile {id} action failed: {error}"));
        let after = resources(&state);
        assert_eq!(
            (
                after.0 - before.0,
                after.1 - before.1,
                after.2 - before.2,
                after.3 - before.3,
            ),
            expected_delta,
            "Advanced Tech tile {id}"
        );

        state.phase = GamePhase::ActionPhase { active_player: 0 };
        assert!(
            RuleEngine::apply_action(
                &mut state,
                0,
                GameAction::TechTileSpecialAction {
                    tile: TechTileRef::Advanced {
                        tile: AdvancedTechTile(id),
                    },
                },
            )
            .is_err(),
            "Advanced Tech tile {id} must be limited to once per round"
        );
        finish_round_transition(&mut state, 1);
        assert!(state.players[0]
            .advanced_tech_tile_special_actions_used_this_round
            .is_empty());
    }

    let mut reset = counted_state();
    reset.players[0].tech_tile_special_actions_used_this_round = vec![10];
    reset.players[0].advanced_tech_tile_special_actions_used_this_round = vec![20];
    finish_round_transition(&mut reset, 1);
    assert!(reset.players[0]
        .tech_tile_special_actions_used_this_round
        .is_empty());
    assert!(reset.players[0]
        .advanced_tech_tile_special_actions_used_this_round
        .is_empty());
}
