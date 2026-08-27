use gaia_engine::game_state::{
    AdvancedTechTile, ArtifactId, BoardState, BrainstoneLocation, FactionId, FederationToken,
    FinalScoringCondition, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType,
    ResearchTrack, RoundTile, Sector, SpaceshipBoard, SpaceshipId, Structure, StructureType,
    TechTile,
};
use gaia_engine::rules::actions::{GameAction, TechTileRef};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{RuleEngine, ScoringEngine};
use std::collections::HashMap;

// Lost Fleet expansion (`docs/GP_Exp_Rule_EN_V1_Web.pdf`), "11) Action: Explore a Lost Fleet
// Spaceship", "12) Action: Examine an Artifact", the Build-a-Mine special costs for
// Asteroid/ProtoPlanet planet types, and the Gleens/Space Giants Exploration Board special
// actions. Map placement here is a small hand-built fixture, independent of the real
// Interspace-tile variable setup (see `MapEngine::place_interspace_tiles`).

fn board_with_extras() -> BoardState {
    let anchor = HexCoord::new(0, 0);
    let asteroid = HexCoord::new(1, 0);
    let protoplanet = HexCoord::new(-1, 0);
    let ship_hex = HexCoord::new(0, 1);

    let mut hexes = HashMap::new();
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
    hexes.insert(
        asteroid,
        Hex {
            coord: asteroid,
            planet: Some(Planet {
                planet_type: PlanetType::Asteroid,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        protoplanet,
        Hex {
            coord: protoplanet,
            planet: Some(Planet {
                planet_type: PlanetType::ProtoPlanet,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        ship_hex,
        Hex {
            coord: ship_hex,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    let volcanic = HexCoord::new(0, -1); // adjacent to anchor
    hexes.insert(
        volcanic,
        Hex {
            coord: volcanic,
            planet: Some(Planet {
                planet_type: PlanetType::Volcanic,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    let player1_anchor = HexCoord::new(0, 2); // adjacent to ship_hex
    hexes.insert(
        player1_anchor,
        Hex {
            coord: player1_anchor,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 1,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );

    let mut spaceship_tiles = HashMap::new();
    spaceship_tiles.insert(SpaceshipId::Twilight, ship_hex);

    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: anchor,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles,
    }
}

fn empty_spaceship_board(id: SpaceshipId) -> SpaceshipBoard {
    SpaceshipBoard {
        id,
        explorers: vec![None; 4],
        artifact_pool: if id == SpaceshipId::Twilight {
            vec![ArtifactId(8)] // FlatVp7 — the simplest default for tests that don't care which
        } else {
            vec![]
        },
        federation_token: None,
    }
}

fn base_state() -> gaia_engine::game_state::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
            p.resources.ore = 15;
            p.resources.credits = 15;
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 4;
            p.vp = 10;
        })
        .with_player_fn(1, |p| {
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 2),
                kind: StructureType::Mine,
            }];
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 4;
            p.vp = 10;
        })
        .with_board(board_with_extras())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.spaceship_boards = SpaceshipId::all()
        .into_iter()
        .map(empty_spaceship_board)
        .collect();
    state
}

fn insert_empty_hex(state: &mut gaia_engine::game_state::GameState, coord: HexCoord) {
    state.board.hexes.insert(
        coord,
        Hex {
            coord,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
}

fn insert_planet_hex(
    state: &mut gaia_engine::game_state::GameState,
    coord: HexCoord,
    planet_type: PlanetType,
) {
    state.board.hexes.insert(
        coord,
        Hex {
            coord,
            planet: Some(Planet {
                planet_type,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
}

// ── Explore a Lost Fleet Spaceship ──────────────────────────────────────────────

#[test]
fn explore_spaceship_succeeds() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|e| panic!("explore should succeed: {e}"));

    assert_eq!(state.players[0].exploration_shuttles_available, 2);
    assert_eq!(state.players[0].vp, 5);
    assert!(state.players[0].explored_ships.contains(&0)); // Twilight = 0
    let Some(board) = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == SpaceshipId::Twilight)
    else {
        panic!("Twilight board should exist");
    };
    assert_eq!(board.explorers[0], Some(0));
    // First explorer charges no power.
    assert_eq!(state.players[0].resources.power.bowl3, 0);
}

#[test]
fn taklons_move_the_brainstone_to_gaia_when_exploring_a_spaceship() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Taklons);
    state.players[0].resources.power.brainstone = Some(BrainstoneLocation::Area3);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|error| panic!("Taklons exploration should succeed: {error}"));

    assert_eq!(
        state.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Gaia)
    );
}

#[test]
fn second_explorer_on_same_ship_charges_power() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|e| panic!("first explore should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|e| panic!("second explore should succeed: {e}"));

    // Slot index 1 (second explorer) charges 2 power, confirmed from a physical shuttle-slot
    // photo (slot table: [0, 2, 2, 3]). `apply_power_charge` moves existing tokens forward
    // (bowl1 -> bowl2 here, since player 1's bowl1 starts non-empty).
    assert_eq!(state.players[1].resources.power.bowl1, 2);
    assert_eq!(state.players[1].resources.power.bowl2, 6);
}

#[test]
fn third_and_fourth_explorer_charge_amounts_match_the_confirmed_slot_table() {
    let mut state = base_state();

    // Fill slots 0-2 directly with placeholder occupants (not via the action, and not player
    // 0) so this test exercises slot 3's charge amount in isolation — player 0 (who hasn't
    // explored yet) will land in the first open slot, index 3.
    if let Some(board) = state
        .spaceship_boards
        .iter_mut()
        .find(|b| b.id == SpaceshipId::Twilight)
    {
        board.explorers[0] = Some(1);
        board.explorers[1] = Some(1);
        board.explorers[2] = Some(1);
    }

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|e| panic!("fourth explore should succeed: {e}"));

    // Slot index 3 (fourth explorer) charges 3 power, per the confirmed [0, 2, 2, 3] table.
    assert_eq!(state.players[0].resources.power.bowl1, 1);
    assert_eq!(state.players[0].resources.power.bowl2, 7);
}

#[test]
fn cannot_explore_same_ship_twice() {
    let mut state = base_state();
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|e| panic!("first explore should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    );
    assert!(result.is_err());
}

#[test]
fn cannot_explore_out_of_range() {
    let mut state = base_state();
    // Rebellion has no map hex seeded at all in `board_with_extras` — unreachable.
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Rebellion,
        },
    );
    assert!(result.is_err());
}

#[test]
fn cannot_explore_with_no_shuttles_left() {
    let mut state = base_state();
    state.players[0].exploration_shuttles_available = 0;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    );
    assert!(result.is_err());
}

// ── Examine an Artifact ──────────────────────────────────────────────────────────

#[test]
fn examine_artifact_requires_twilight_explored() {
    let mut state = base_state();
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn examine_artifact_requires_enough_power() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.power.bowl1 = 1;
    state.players[0].resources.power.bowl2 = 1;
    state.players[0].resources.power.bowl3 = 1;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn examine_artifact_succeeds() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.power.bowl1 = 4;
    state.players[0].resources.power.bowl2 = 4;
    state.players[0].resources.power.bowl3 = 0;
    let vp_before = state.players[0].vp;
    let structures_before = state.players[0].structures.len();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    // 6 power discarded: bowl1 (4) then bowl2 (2 of 4) drained.
    assert_eq!(state.players[0].resources.power.bowl1, 0);
    assert_eq!(state.players[0].resources.power.bowl2, 2);
    assert_eq!(state.players[0].resources.power.bowl3, 0);
    // Artifact 8 grants 7 VP and counts as a current Build-a-Mine action, so the fixture's
    // round-1 BuildMine tile grants another 2 VP. The mine is virtual: it counts for objectives
    // and planet types without adding a board structure or consuming a physical piece.
    assert_eq!(state.players[0].vp, vp_before + 9);
    assert_eq!(state.players[0].structures.len(), structures_before);
    assert_eq!(state.players[0].artifact_mines, [PlanetType::ProtoPlanet]);
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostBuildings,),
        structures_before as u32 + 1
    );
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostPlanetTypes,),
        1
    );
    let Some(board) = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == SpaceshipId::Twilight)
    else {
        panic!("Twilight board should exist");
    };
    assert!(board.artifact_pool.is_empty());
}

#[test]
fn taklons_pay_the_additional_brainstone_cost_to_examine_an_artifact() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Taklons);
    state.players[0].explored_ships.push(0);
    state.players[0].resources.power.brainstone = Some(BrainstoneLocation::Area2);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|error| panic!("Taklons artifact action should succeed: {error}"));

    assert_eq!(
        state.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Gaia)
    );
}

#[test]
fn examine_artifact_rejects_when_pool_empty() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    let Some(board) = state
        .spaceship_boards
        .iter_mut()
        .find(|b| b.id == SpaceshipId::Twilight)
    else {
        panic!("Twilight board should exist");
    };
    board.artifact_pool.clear();

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

// ── Build a Mine: ProtoPlanet / Asteroid special costs ───────────────────────────

#[test]
fn build_on_protoplanet_grants_vp_and_flat_terraform_cost() {
    let mut state = base_state();
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(-1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("protoplanet build should succeed: {e}"));

    // Flat 3-step terraform at track level 0 (3 ore/step) = 9 ore, + 1 ore base mine cost = 10.
    assert_eq!(state.players[0].resources.ore, 15 - 10);
    assert_eq!(state.players[0].resources.credits, 15 - 2);
    // +6 VP for the Protoplanet colonization, plus the builder's default round tile 1
    // ("BuildMine", 2 VP/unit) which fires for any mine build, Protoplanet included.
    assert_eq!(state.players[0].vp, vp_before + 6 + 2);
}

#[test]
fn build_on_asteroid_requires_gaiaformer_and_is_free() {
    let mut state = base_state();
    state.players[0].gaiaformers_total = 1;
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("asteroid build should succeed: {e}"));

    assert_eq!(state.players[0].resources.ore, ore_before);
    assert_eq!(state.players[0].resources.credits, credits_before);
    assert_eq!(state.players[0].resources.spent_gaia_formers, 1);
}

#[test]
fn build_on_asteroid_rejected_without_gaiaformer() {
    let mut state = base_state();
    // gaiaformers_total defaults to 0 in the builder.

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

// ── Appendix II: SpaceshipCreditTerraform ─────────────────────────────────────────

#[test]
fn spaceship_credit_terraform_requires_an_explored_ship() {
    let mut state = base_state();
    // Player 0 hasn't explored any spaceship yet.

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceshipCreditTerraform {
            coord: HexCoord::new(0, -1),
        },
    );
    assert!(result.is_err());
}

#[test]
fn spaceship_credit_terraform_requires_tf_mars_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not T F Mars

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceshipCreditTerraform {
            coord: HexCoord::new(0, -1),
        },
    );
    assert!(result.is_err());
}

#[test]
fn spaceship_credit_terraform_succeeds() {
    let mut state = base_state();
    state.players[0].explored_ships.push(2); // T F Mars
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceshipCreditTerraform {
            coord: HexCoord::new(0, -1),
        },
    )
    .unwrap_or_else(|e| panic!("spaceship credit terraform should succeed: {e}"));

    // Terra -> Volcanic is 2 ring steps; 1 is free, so 1 remaining step at track level 0
    // (3 ore/step) = 3 ore, + 1 ore base mine cost = 4.
    assert_eq!(state.players[0].resources.ore, ore_before - 4);
    // 3 credits for the action itself, + 2 credits base mine cost = 5.
    assert_eq!(state.players[0].resources.credits, credits_before - 5);
    assert!(state.used_spaceship_actions.contains(&1));
}

#[test]
fn spaceship_credit_terraform_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(2); // T F Mars
    state.players[1].explored_ships.push(2);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceshipCreditTerraform {
            coord: HexCoord::new(0, -1),
        },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    // A different player attempting it — still rejected: `used_spaceship_actions` is checked
    // before reachability, so the action-space exclusivity (not the target hex) is what fails
    // here regardless of whether player 1 could otherwise reach this coord.
    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::SpaceshipCreditTerraform {
            coord: HexCoord::new(0, -1),
        },
    );
    assert!(result.is_err());
}

// ── Twilight: free TradingStation -> ResearchLab ──────────────────────────────

#[test]
fn twilight_free_research_lab_requires_twilight_specifically() {
    let mut state = base_state();
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(5, 5),
        kind: StructureType::TradingStation,
    });
    // Explored Rebellion (ship_id 1), not Twilight (ship_id 0).
    state.players[0].explored_ships.push(1);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightFreeResearchLab {
            coord: HexCoord::new(5, 5),
        },
    );
    assert!(result.is_err());
}

#[test]
fn twilight_free_research_lab_costs_3_power_and_2_ore_but_no_credits() {
    let mut state = base_state();
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(5, 5),
        kind: StructureType::TradingStation,
    });
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.power.bowl3 = 3;
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightFreeResearchLab {
            coord: HexCoord::new(5, 5),
        },
    )
    .unwrap_or_else(|e| panic!("free research lab upgrade should succeed: {e}"));

    // The action space costs 3 power + 2 ore to activate; the *upgrade itself* has no
    // additional cost beyond that (credits untouched — a normal TradingStation->ResearchLab
    // upgrade would also cost credits).
    assert_eq!(state.players[0].resources.power.bowl3, 0);
    assert_eq!(state.players[0].resources.ore, ore_before - 2);
    assert_eq!(state.players[0].resources.credits, credits_before);
    let upgraded = state.players[0]
        .structures
        .iter()
        .find(|s| s.hex == HexCoord::new(5, 5));
    assert_eq!(upgraded.map(|s| s.kind), Some(StructureType::ResearchLab));
    assert!(state.used_spaceship_actions.contains(&2));
}

#[test]
fn twilight_free_research_lab_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(5, 5),
        kind: StructureType::TradingStation,
    });
    state.players[1].structures.push(Structure {
        hex: HexCoord::new(6, 6),
        kind: StructureType::TradingStation,
    });
    state.players[0].explored_ships.push(0);
    state.players[1].explored_ships.push(0);
    state.players[0].resources.power.bowl3 = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightFreeResearchLab {
            coord: HexCoord::new(5, 5),
        },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::TwilightFreeResearchLab {
            coord: HexCoord::new(6, 6),
        },
    );
    assert!(result.is_err());
}

// ── Artifact effects (Appendix VII, ids 1-4 confirmed) ────────────────────────

fn set_artifact_pool(state: &mut gaia_engine::game_state::GameState, ids: &[u8]) {
    if let Some(board) = state
        .spaceship_boards
        .iter_mut()
        .find(|b| b.id == SpaceshipId::Twilight)
    {
        board.artifact_pool = ids.iter().copied().map(ArtifactId).collect();
    }
}

#[test]
fn artifact_1_grants_2_vp_per_deep_space_sector() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    // `board_with_extras`'s only sector (id 1) is Standard; `sector_id_at` resolves a hex to
    // whichever sector's origin is within range, so retagging it as id 11 (Deep Space, per
    // `data/sectors.toml`) puts the player's mine at (0,0) inside a Deep Space sector.
    state.board.sectors[0].id = 11;
    set_artifact_pool(&mut state, &[1]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(1),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 2);
}

#[test]
fn artifact_2_grants_2_power_to_bowl3() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[2]);
    let bowl3_before = state.players[0].resources.power.bowl3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(2),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].resources.power.bowl3, bowl3_before + 2);
}

#[test]
fn artifact_3_grants_1_ore_and_1_knowledge() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[3]);
    let ore_before = state.players[0].resources.ore;
    let knowledge_before = state.players[0].resources.knowledge;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(3),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].resources.ore, ore_before + 1);
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 1);
}

#[test]
fn artifact_4_grants_3_vp_per_gaia_project_level() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].research_tracks.gaia = 4;
    set_artifact_pool(&mut state, &[4]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(4),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 12);
}

#[test]
fn artifact_5_grants_3_vp_per_science_level() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].research_tracks.science = 5;
    set_artifact_pool(&mut state, &[5]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(5),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 15);
}

#[test]
fn artifact_6_grants_3_credits_and_3_ore() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[6]);
    let credits_before = state.players[0].resources.credits;
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(6),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].resources.credits, credits_before + 3);
    assert_eq!(state.players[0].resources.ore, ore_before + 3);
}

#[test]
fn artifact_7_grants_3_knowledge_and_1_qic() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[7]);
    let knowledge_before = state.players[0].resources.knowledge;
    let qic_before = state.players[0].resources.qic;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(7),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 3);
    assert_eq!(state.players[0].resources.qic, qic_before + 1);
}

#[test]
fn artifact_9_grants_5_credits_and_2_ore() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[9]);
    let credits_before = state.players[0].resources.credits;
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(9),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].resources.credits, credits_before + 5);
    assert_eq!(state.players[0].resources.ore, ore_before + 2);
}

#[test]
fn artifact_11_grants_3_vp_plus_1_vp_per_colonized_planet_type() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    // `board_with_extras`'s anchor hex (where player 0's mine sits) has `planet: None`, so
    // `MostPlanetTypes`'s scoring counts 0 distinct colonized planet types here — this test
    // exercises the flat +3 half of the effect in isolation.
    set_artifact_pool(&mut state, &[11]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(11),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 3);
}

#[test]
fn artifact_12_grants_7_vp_and_counts_as_a_virtual_asteroid_mine() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[12]);
    let vp_before = state.players[0].vp;
    let structures_before = state.players[0].structures.len();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(12),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 9);
    assert_eq!(state.players[0].structures.len(), structures_before);
    assert_eq!(state.players[0].artifact_mines, [PlanetType::Asteroid]);
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostAsteroids),
        1
    );
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostBuildings,),
        structures_before as u32 + 1
    );
}

#[test]
fn artifact_virtual_mine_triggers_mine_and_new_type_scoring_but_not_sector_scoring() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0]
        .advanced_tech_tiles
        .push(AdvancedTechTile(4)); // +3 VP whenever a Mine is built
    state.round_tiles[0] = RoundTile::from_id(10); // +3 VP for a new planet type
    set_artifact_pool(&mut state, &[8]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(8),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("virtual Protoplanet mine should succeed: {e}"));

    // 7 VP artifact + 3 VP new planet type round tile + 3 VP advanced Mine tech tile.
    assert_eq!(state.players[0].vp, vp_before + 13);

    let mut no_sector_state = base_state();
    no_sector_state.players[0].explored_ships.push(0);
    no_sector_state.round_tiles[0] = RoundTile::from_id(11); // new sector only
    set_artifact_pool(&mut no_sector_state, &[12]);
    let no_sector_vp_before = no_sector_state.players[0].vp;
    RuleEngine::apply_action(
        &mut no_sector_state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(12),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("virtual Asteroid mine should succeed: {e}"));
    assert_eq!(
        no_sector_state.players[0].vp,
        no_sector_vp_before + 7,
        "a coordinate-less artifact mine belongs to no sector"
    );
}

#[test]
fn artifact_13_grants_3_vp_per_research_track_at_level_3_plus() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].research_tracks.gaia = 3;
    state.players[0].research_tracks.science = 5;
    state.players[0].research_tracks.economy = 2; // below threshold, shouldn't count
    set_artifact_pool(&mut state, &[13]);
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(13),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("examine artifact should succeed: {e}"));

    // 2 tracks (gaia, science) at level >= 3 -> 2 * 3 = 6 VP.
    assert_eq!(state.players[0].vp, vp_before + 6);
}

#[test]
fn all_thirteen_artifacts_including_id_10_are_seeded() {
    let seeded = gaia_engine::map::MapEngine::initial_spaceship_boards("test-seed");
    let Some(twilight) = seeded.iter().find(|b| b.id == SpaceshipId::Twilight) else {
        panic!("Twilight board should exist");
    };
    assert!(twilight.artifact_pool.contains(&ArtifactId(10)));
    assert_eq!(twilight.artifact_pool.len(), 13);
}

#[test]
fn examine_artifact_lets_the_player_choose_which_one_to_take() {
    // Rulebook: "gain 1 artifact from the spaceship" — the physical components are laid out
    // face-up and chosen, not drawn blind. A pool of several artifacts should still let the
    // player take a specific one (here, the last of three) rather than always the first.
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    set_artifact_pool(&mut state, &[3, 6, 9]);
    let credits_before = state.players[0].resources.credits;
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(9),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("choosing artifact 9 should succeed: {e}"));

    // Artifact 9 ("5 credits + 2 ore"), not artifact 3 ("1 ore + 1 knowledge" — index 0).
    assert_eq!(state.players[0].resources.credits, credits_before + 5);
    assert_eq!(state.players[0].resources.ore, ore_before + 2);
    let Some(board) = state
        .spaceship_boards
        .iter()
        .find(|b| b.id == SpaceshipId::Twilight)
    else {
        panic!("Twilight board should exist");
    };
    assert_eq!(board.artifact_pool, vec![ArtifactId(3), ArtifactId(6)]);
}

#[test]
fn examine_artifact_rejects_an_id_not_in_the_pool() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[3]);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(9),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn artifact_10_copies_a_flat_reward_federation_token_effect_without_consuming_it() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[10]);
    state.players[0].federation_tokens.push(FederationToken(5)); // 7 VP + 6 credits
    let vp_before = state.players[0].vp;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(10),
            copy_federation_token_kind: Some(5),
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("Artifact 10 copy should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 7);
    assert_eq!(state.players[0].resources.credits, credits_before + 6);
    // Copying doesn't consume the original token.
    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(5)]);
}

#[test]
fn artifact_10_copies_a_federation_tokens_free_build_effect() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[10]);
    state.players[0].federation_tokens.push(FederationToken(14)); // free Build, 3 free steps
    let target = HexCoord::new(0, -1); // pre-seeded Volcanic planet, in range
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(10),
            copy_federation_token_kind: Some(14),
            bonus_build_coord: Some(target),
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("Artifact 10 copy should succeed: {e}"));

    assert!(state.players[0]
        .structures
        .iter()
        .any(|structure| structure.hex == target && structure.kind == StructureType::Mine));
    // 3 free terraforming steps fully cover Terra -> Volcanic (2 ring steps): only the flat
    // 1-ore Mine cost applies.
    assert_eq!(state.players[0].resources.ore, ore_before - 1);
}

#[test]
fn artifact_10_requires_choosing_an_owned_federation_token() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[10]);
    state.players[0].federation_tokens.push(FederationToken(5));

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(10),
            copy_federation_token_kind: None,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

#[test]
fn artifact_10_rejects_a_federation_token_kind_the_player_does_not_own() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    set_artifact_pool(&mut state, &[10]);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExamineArtifact {
            artifact: ArtifactId(10),
            copy_federation_token_kind: Some(5),
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(result.is_err());
}

// ── Rebellion: free Mine -> TradingStation, and knowledge -> credits+QIC ──────

#[test]
fn rebellion_free_trading_station_requires_rebellion_specifically() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 3;
    // Explored Twilight (ship_id 0), not Rebellion (ship_id 1).
    state.players[0].explored_ships.push(0);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionFreeTradingStation {
            coord: HexCoord::new(0, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn rebellion_free_trading_station_costs_3_power_and_1_ore() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1); // Rebellion
    state.players[0].resources.power.bowl3 = 3;
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;

    // Player 0's anchor mine (0,0), from `board_with_extras`, is the upgrade target.
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionFreeTradingStation {
            coord: HexCoord::new(0, 0),
        },
    )
    .unwrap_or_else(|e| panic!("free trading station upgrade should succeed: {e}"));

    assert_eq!(state.players[0].resources.power.bowl3, 0);
    assert_eq!(state.players[0].resources.ore, ore_before - 1);
    assert_eq!(state.players[0].resources.credits, credits_before);
    let upgraded = state.players[0]
        .structures
        .iter()
        .find(|s| s.hex == HexCoord::new(0, 0));
    assert_eq!(
        upgraded.map(|s| s.kind),
        Some(StructureType::TradingStation)
    );
}

#[test]
fn rebellion_free_trading_station_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1);
    state.players[1].explored_ships.push(1);
    state.players[0].resources.power.bowl3 = 3;
    state.players[1].resources.power.bowl3 = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionFreeTradingStation {
            coord: HexCoord::new(0, 0),
        },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::RebellionFreeTradingStation {
            coord: HexCoord::new(0, 2),
        },
    );
    assert!(result.is_err());
}

#[test]
fn rebellion_credits_and_qic_requires_rebellion_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not Rebellion

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::RebellionCreditsAndQic);
    assert!(result.is_err());
}

#[test]
fn rebellion_credits_and_qic_costs_2_knowledge_for_2_credits_and_1_qic() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1); // Rebellion
    state.players[0].resources.knowledge = 3;
    let credits_before = state.players[0].resources.credits;
    let qic_before = state.players[0].resources.qic;

    RuleEngine::apply_action(&mut state, 0, GameAction::RebellionCreditsAndQic)
        .unwrap_or_else(|e| panic!("credits+QIC action should succeed: {e}"));

    assert_eq!(state.players[0].resources.knowledge, 1);
    assert_eq!(state.players[0].resources.credits, credits_before + 2);
    assert_eq!(state.players[0].resources.qic, qic_before + 1);
}

#[test]
fn rebellion_credits_and_qic_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1);
    state.players[1].explored_ships.push(1);
    state.players[0].resources.knowledge = 3;
    state.players[1].resources.knowledge = 3;

    RuleEngine::apply_action(&mut state, 0, GameAction::RebellionCreditsAndQic)
        .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(&mut state, 1, GameAction::RebellionCreditsAndQic);
    assert!(result.is_err());
}

// ── T F Mars: QIC -> VP-per-tech-tile, and flat-power immediate Gaia Formation ────

#[test]
fn tfmars_tech_bonus_requires_tf_mars_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not T F Mars
    state.players[0].resources.qic = 5;

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::TFMarsTechBonus);
    assert!(result.is_err());
}

#[test]
fn tfmars_tech_bonus_costs_2_qic_for_2_vp_plus_1_vp_per_tech_tile() {
    let mut state = base_state();
    state.players[0].explored_ships.push(2); // T F Mars
    state.players[0].resources.qic = 5;
    state.players[0].tech_tiles.extend([
        gaia_engine::game_state::TechTile(1),
        gaia_engine::game_state::TechTile(2),
    ]);
    let qic_before = state.players[0].resources.qic;
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(&mut state, 0, GameAction::TFMarsTechBonus)
        .unwrap_or_else(|e| panic!("T F Mars tech bonus should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, qic_before - 2);
    // 2 flat + 2 tech tiles = 4 VP.
    assert_eq!(state.players[0].vp, vp_before + 4);
}

#[test]
fn tfmars_tech_bonus_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(2);
    state.players[1].explored_ships.push(2);
    state.players[0].resources.qic = 5;
    state.players[1].resources.qic = 5;

    RuleEngine::apply_action(&mut state, 0, GameAction::TFMarsTechBonus)
        .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(&mut state, 1, GameAction::TFMarsTechBonus);
    assert!(result.is_err());
}

fn insert_transdim_hex(state: &mut gaia_engine::game_state::GameState, coord: HexCoord) {
    state.board.hexes.insert(
        coord,
        gaia_engine::game_state::Hex {
            coord,
            planet: Some(gaia_engine::game_state::Planet {
                planet_type: PlanetType::Transdim,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
}

#[test]
fn tfmars_gaia_formation_requires_tf_mars_specifically() {
    let mut state = base_state();
    let transdim = HexCoord::new(1, -1);
    insert_transdim_hex(&mut state, transdim);
    state.players[0].explored_ships.push(0); // Twilight, not T F Mars
    state.players[0].gaiaformers_total = 1;
    state.players[0].resources.power.bowl3 = 3;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TFMarsGaiaFormation { coord: transdim },
    );
    assert!(result.is_err());
}

#[test]
fn tfmars_gaia_formation_costs_a_flat_2_power_regardless_of_gaia_track_level() {
    let mut state = base_state();
    let transdim = HexCoord::new(1, -1);
    insert_transdim_hex(&mut state, transdim);
    state.players[0].explored_ships.push(2); // T F Mars
    state.players[0].gaiaformers_total = 1;
    // Gaia Project track level 0 — the normal `GaiaFormation` action would reject this
    // outright; the flat-power alternative doesn't check the track level at all.
    state.players[0].research_tracks.gaia = 0;
    state.players[0].resources.power.bowl3 = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TFMarsGaiaFormation { coord: transdim },
    )
    .unwrap_or_else(|e| panic!("T F Mars gaia formation should succeed: {e}"));

    assert_eq!(state.players[0].resources.power.bowl3, 1);
    assert_eq!(state.players[0].gaiaformers_deployed, 0);
    assert_eq!(state.players[0].gaiaformers_available(), 1);
    let Some(hex) = state.board.hexes.get(&transdim) else {
        panic!("transdim hex should still exist");
    };
    let Some(planet) = hex.planet.as_ref() else {
        panic!("transdim hex should still have a planet");
    };
    assert_eq!(planet.owner, Some(0));
    assert!(planet.is_gaia_formed);
}

#[test]
fn tfmars_gaia_formation_can_only_be_used_once_per_round() {
    let mut state = base_state();
    let transdim = HexCoord::new(1, -1);
    insert_transdim_hex(&mut state, transdim);
    let transdim2 = HexCoord::new(-1, 1);
    insert_transdim_hex(&mut state, transdim2);
    state.players[0].explored_ships.push(2);
    state.players[1].explored_ships.push(2);
    state.players[0].gaiaformers_total = 1;
    state.players[1].gaiaformers_total = 1;
    state.players[0].resources.power.bowl3 = 3;
    state.players[1].resources.power.bowl3 = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TFMarsGaiaFormation { coord: transdim },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::TFMarsGaiaFormation { coord: transdim2 },
    );
    assert!(result.is_err());
}

// ── Eclipse: QIC -> VP-per-planet-type, power+knowledge -> research boost, and ───
// ── credit-paid Asteroid mine ─────────────────────────────────────────────────

#[test]
fn eclipse_planet_type_bonus_requires_eclipse_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not Eclipse
    state.players[0].resources.qic = 5;

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::EclipsePlanetTypeBonus);
    assert!(result.is_err());
}

#[test]
fn eclipse_planet_type_bonus_costs_2_qic_for_2_vp_plus_1_vp_per_planet_type() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3); // Eclipse
    state.players[0].resources.qic = 5;
    let qic_before = state.players[0].resources.qic;
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(&mut state, 0, GameAction::EclipsePlanetTypeBonus)
        .unwrap_or_else(|e| panic!("Eclipse planet type bonus should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, qic_before - 2);
    // `board_with_extras`'s anchor hex (player 0's mine) has `planet: None`, so 0 distinct
    // colonized planet types here -> flat +2 VP only.
    assert_eq!(state.players[0].vp, vp_before + 2);
}

#[test]
fn eclipse_planet_type_bonus_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3);
    state.players[1].explored_ships.push(3);
    state.players[0].resources.qic = 5;
    state.players[1].resources.qic = 5;

    RuleEngine::apply_action(&mut state, 0, GameAction::EclipsePlanetTypeBonus)
        .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(&mut state, 1, GameAction::EclipsePlanetTypeBonus);
    assert!(result.is_err());
}

#[test]
fn eclipse_research_boost_requires_eclipse_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not Eclipse
    state.players[0].resources.power.bowl3 = 3;
    state.players[0].resources.knowledge = 3;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseResearchBoost {
            track: gaia_engine::game_state::ResearchTrack::Science,
        },
    );
    assert!(result.is_err());
}

#[test]
fn eclipse_research_boost_costs_3_power_and_2_knowledge_instead_of_4_knowledge() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3); // Eclipse
    state.players[0].resources.power.bowl3 = 3;
    state.players[0].resources.knowledge = 2;
    let knowledge_before = state.players[0].resources.knowledge;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseResearchBoost {
            track: gaia_engine::game_state::ResearchTrack::Science,
        },
    )
    .unwrap_or_else(|e| panic!("Eclipse research boost should succeed: {e}"));

    assert_eq!(state.players[0].resources.power.bowl3, 0);
    assert_eq!(state.players[0].resources.knowledge, knowledge_before - 2);
    assert_eq!(state.players[0].research_tracks.science, 1);
}

#[test]
fn eclipse_research_boost_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3);
    state.players[1].explored_ships.push(3);
    state.players[0].resources.power.bowl3 = 3;
    state.players[0].resources.knowledge = 3;
    state.players[1].resources.power.bowl3 = 3;
    state.players[1].resources.knowledge = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseResearchBoost {
            track: gaia_engine::game_state::ResearchTrack::Science,
        },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::EclipseResearchBoost {
            track: gaia_engine::game_state::ResearchTrack::Science,
        },
    );
    assert!(result.is_err());
}

#[test]
fn eclipse_asteroid_mine_requires_eclipse_specifically() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight, not Eclipse
    state.players[0].gaiaformers_total = 1;
    state.players[0].resources.credits = 15;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseAsteroidMine {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn eclipse_asteroid_mine_rejects_non_asteroid_target() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3); // Eclipse
    state.players[0].gaiaformers_total = 1;
    state.players[0].resources.credits = 15;

    // (0, -1) is Volcanic in `board_with_extras`, not an Asteroid.
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseAsteroidMine {
            coord: HexCoord::new(0, -1),
        },
    );
    assert!(result.is_err());
}

#[test]
fn eclipse_asteroid_mine_costs_6_credits_and_consumes_a_gaiaformer() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3); // Eclipse
    state.players[0].gaiaformers_total = 1;
    state.players[0].resources.credits = 15;
    let credits_before = state.players[0].resources.credits;
    let ore_before = state.players[0].resources.ore;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseAsteroidMine {
            coord: HexCoord::new(1, 0), // Asteroid, per `board_with_extras`
        },
    )
    .unwrap_or_else(|e| panic!("Eclipse asteroid mine should succeed: {e}"));

    assert_eq!(state.players[0].resources.credits, credits_before - 6);
    // The reused Asteroid `Build` branch itself costs no additional ore/credits.
    assert_eq!(state.players[0].resources.ore, ore_before);
    assert_eq!(state.players[0].resources.spent_gaia_formers, 1);
}

#[test]
fn eclipse_asteroid_mine_can_only_be_used_once_per_round() {
    let mut state = base_state();
    state.players[0].explored_ships.push(3);
    state.players[0].gaiaformers_total = 1;
    state.players[0].resources.credits = 15;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseAsteroidMine {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("first use should succeed: {e}"));

    // Same player, same board, tries a second Asteroid — none left in `board_with_extras`
    // (only one Asteroid hex exists) — the shared exclusivity check happens first regardless.
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::EclipseAsteroidMine {
            coord: HexCoord::new(1, 0),
        },
    );
    assert!(result.is_err());
}

// ── Remaining Appendix II spaceship action spaces ───────────────────────────

#[test]
fn twilight_replays_an_owned_federation_token_without_consuming_it() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.qic = 3;
    state.players[0].federation_tokens.push(FederationToken(5));
    let vp_before = state.players[0].vp;
    let credits_before = state.players[0].resources.credits;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightReplayFederationToken {
            token_kind: 5, // 7 VP + 6 credits
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|e| panic!("Twilight federation replay should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, 0);
    assert_eq!(state.players[0].vp, vp_before + 7);
    assert_eq!(state.players[0].resources.credits, credits_before + 6);
    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(5)]);
    assert!(state.used_spaceship_actions.contains(&10));
}

#[test]
fn twilight_cannot_replay_a_federation_token_it_does_not_own() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].resources.qic = 3;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightReplayFederationToken {
            token_kind: 5,
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );

    assert!(result.is_err());
}

#[test]
fn twilight_replay_resolves_the_tech_tile_tokens_follow_up_choice() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].resources.qic = 3;
    state.players[0].federation_tokens.push(FederationToken(12));
    let tile = TechTile(2);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightReplayFederationToken {
            token_kind: 12,
            bonus_build_coord: None,
            bonus_tech_tile: Some(tile.clone()),
            bonus_research_track: Some(ResearchTrack::Economy),
        },
    )
    .unwrap_or_else(|e| panic!("Twilight Tech-tile replay should succeed: {e}"));

    assert!(state.players[0].tech_tiles.contains(&tile));
    assert!(!state.research_board.tech_tiles.contains(&tile));
    assert_eq!(state.players[0].research_tracks.economy, 1);
    assert_eq!(
        state.players[0].federation_tokens,
        vec![FederationToken(12)]
    );
}

#[test]
fn twilight_range_action_adds_three_range_and_uses_one_shared_slot() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.knowledge = 1;
    state.players[0].resources.qic = 0;

    // Navigation level 0 has range 1. A target at distance 4 cannot be reached without QIC,
    // but the Twilight space raises the range to 4 for this one action.
    // (1, 0) is already the test board's Asteroid and can still be crossed as a map hex.
    insert_empty_hex(&mut state, HexCoord::new(2, 0));
    insert_empty_hex(&mut state, HexCoord::new(3, 0));
    let target = HexCoord::new(4, 0);
    insert_planet_hex(&mut state, target, PlanetType::Terra);

    let normal_result =
        RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target });
    assert!(normal_result.is_err());

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeBuild { coord: target },
    )
    .unwrap_or_else(|e| panic!("Twilight +3 range build should succeed: {e}"));

    assert_eq!(state.players[0].resources.knowledge, 0);
    assert!(state.used_spaceship_actions.contains(&11));
    assert!(state.players[0]
        .structures
        .iter()
        .any(|structure| structure.hex == target && structure.kind == StructureType::Mine));

    // Build/Gaia/Explore are three target modes of one physical action space.
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let second_result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeExploreSpaceship {
            ship: SpaceshipId::Rebellion,
        },
    );
    assert!(second_result.is_err());
}

#[test]
fn rebellion_gain_tech_tile_costs_three_qic_and_advances_the_chosen_track() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1); // Rebellion
    state.players[0].resources.qic = 3;
    let tile = TechTile(1);
    assert!(state.research_board.tech_tiles.contains(&tile));

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionGainTechTile {
            tile: tile.clone(),
            track: ResearchTrack::Science,
        },
    )
    .unwrap_or_else(|e| panic!("Rebellion tech-tile action should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, 0);
    assert!(state.players[0].tech_tiles.contains(&tile));
    assert!(!state.research_board.tech_tiles.contains(&tile));
    assert_eq!(state.players[0].research_tracks.science, 1);
    assert!(state.used_spaceship_actions.contains(&12));
}

#[test]
fn rebellion_gain_tech_tile_rejects_an_unavailable_tile() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1);
    state.players[0].resources.qic = 3;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionGainTechTile {
            tile: TechTile(99),
            track: ResearchTrack::Science,
        },
    );

    assert!(result.is_err());
}

// ── Gleens / Space Giants Exploration Board special actions ────────────────────
//
// `GP_Exp_Rule_EN_V1_Web.pdf` p.10, "7) Special Actions": once per round, each of these two
// factions has a special action, exclusive with other actions this round (enforced the same way
// as every other main action — it consumes the turn). Distinct from the Space Giants'
// Planetary Institute one-time tech-tile ability (`GameAction::SpecialAction`, tested
// separately in `tests/unit/faction_abilities.rs`).

#[test]
fn gleens_special_action_adds_two_range_and_shares_one_once_per_round_flag() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Gleens);
    state.players[0].resources.qic = 0;

    // Navigation level 0 has range 1. A target at distance 3 cannot be reached without QIC,
    // but the Gleens special action raises the range to 3 (+2) for this one action.
    insert_empty_hex(&mut state, HexCoord::new(2, 0));
    let target = HexCoord::new(3, 0);
    insert_planet_hex(&mut state, target, PlanetType::Terra);

    let normal_result =
        RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target });
    assert!(
        normal_result.is_err(),
        "out of range without the special action"
    );

    RuleEngine::apply_action(&mut state, 0, GameAction::GleensBuildMine { coord: target })
        .unwrap_or_else(|e| panic!("Gleens +2 range build should succeed: {e}"));

    assert!(state.players[0]
        .structures
        .iter()
        .any(|structure| structure.hex == target && structure.kind == StructureType::Mine));
    assert!(state.players[0].gleens_special_action_used_this_round);

    // Build/Gaia/Explore are three target modes of one special action, sharing one flag.
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let second_result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::GleensExploreSpaceship {
            ship: SpaceshipId::Rebellion,
        },
    );
    assert!(
        second_result.is_err(),
        "already used the Gleens special action this round"
    );
}

#[test]
fn gleens_special_action_rejects_non_gleens_factions() {
    let mut state = base_state(); // player 0 is Terrans
    insert_empty_hex(&mut state, HexCoord::new(2, 0));
    let target = HexCoord::new(3, 0);
    insert_planet_hex(&mut state, target, PlanetType::Terra);

    let result =
        RuleEngine::apply_action(&mut state, 0, GameAction::GleensBuildMine { coord: target });
    assert!(result.is_err());
}

#[test]
fn gleens_special_action_resets_at_the_next_round() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Gleens);
    state.players[0].gleens_special_action_used_this_round = true;
    state.phase = GamePhase::RoundScoring { round: state.round };

    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|e| panic!("round should advance: {e}"));

    assert!(!state.players[0].gleens_special_action_used_this_round);
}

#[test]
fn space_giants_special_action_rejects_non_space_giants_factions() {
    let mut state = base_state(); // player 0 is Terrans
    let target = HexCoord::new(0, -1); // pre-seeded Volcanic planet, in range

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceGiantsBuildMine { coord: target },
    );
    assert!(result.is_err());
}

#[test]
fn space_giants_special_action_grants_two_free_terraform_steps_and_once_per_round() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::SpaceGiants);
    // Space Giants' own ability (`SpaceGiantsAbility::terraforming_distance_override`) fixes
    // every standard planet's terraforming distance at 2, so this special action's 2 free steps
    // always fully cover it — the rulebook's "pay extra ore for a 3rd step" clause is
    // structurally unreachable for this specific faction, hence the exact-cost assertion below.
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;
    let target = HexCoord::new(0, -1); // pre-seeded Volcanic planet, in range

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceGiantsBuildMine { coord: target },
    )
    .unwrap_or_else(|e| panic!("Space Giants free-terraform build should succeed: {e}"));

    assert!(state.players[0]
        .structures
        .iter()
        .any(|structure| structure.hex == target && structure.kind == StructureType::Mine));
    assert_eq!(state.players[0].resources.ore, ore_before - 1); // just the flat Mine ore cost
    assert_eq!(state.players[0].resources.credits, credits_before - 2);
    assert!(state.players[0].space_giants_special_action_used_this_round);

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let second_target = HexCoord::new(3, 0);
    insert_planet_hex(&mut state, second_target, PlanetType::Terra);
    let second_result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::SpaceGiantsBuildMine {
            coord: second_target,
        },
    );
    assert!(
        second_result.is_err(),
        "already used the Space Giants special action this round"
    );
}

#[test]
fn space_giants_special_action_resets_at_the_next_round() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::SpaceGiants);
    state.players[0].space_giants_special_action_used_this_round = true;
    state.phase = GamePhase::RoundScoring { round: state.round };

    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|e| panic!("round should advance: {e}"));

    assert!(!state.players[0].space_giants_special_action_used_this_round);
}

#[test]
fn twilight_range_build_rejects_without_twilight_explored() {
    let mut state = base_state();
    state.players[0].resources.knowledge = 1;
    let target = HexCoord::new(0, -1); // reachable Volcanic, so missing Twilight access is isolated

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeBuild { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn twilight_range_gaia_formation_adds_three_range_and_uses_shared_slot() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0); // Twilight
    state.players[0].resources.knowledge = 1;
    state.players[0].resources.qic = 0;
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;

    insert_empty_hex(&mut state, HexCoord::new(2, 0));
    insert_empty_hex(&mut state, HexCoord::new(3, 0));
    let target = HexCoord::new(4, 0);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let normal_result =
        RuleEngine::apply_action(&mut state, 0, GameAction::GaiaFormation { coord: target });
    assert!(
        normal_result.is_err(),
        "distance 4 is out of base range without QIC"
    );

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeGaiaFormation { coord: target },
    )
    .unwrap_or_else(|e| panic!("Twilight +3 range Gaia formation should succeed: {e}"));

    assert_eq!(state.players[0].resources.knowledge, 0);
    assert_eq!(state.players[0].gaiaformers_deployed, 1);
    assert_eq!(
        state.board.hexes[&target]
            .planet
            .as_ref()
            .map(|planet| planet.owner),
        Some(Some(0))
    );
    assert!(state.used_spaceship_actions.contains(&11));

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let second_result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeBuild {
            coord: HexCoord::new(0, -1),
        },
    );
    assert!(
        second_result.is_err(),
        "Twilight range modes share one action space"
    );
}

#[test]
fn twilight_range_gaia_formation_rejects_without_twilight_explored() {
    let mut state = base_state();
    state.players[0].resources.knowledge = 1;
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;
    let target = HexCoord::new(1, 1);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeGaiaFormation { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn twilight_range_gaia_formation_rejects_after_shared_slot_used() {
    let mut state = base_state();
    state.players[0].explored_ships.push(0);
    state.players[0].resources.knowledge = 1;
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;
    state.used_spaceship_actions.push(11);
    let target = HexCoord::new(1, 1);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TwilightRangeGaiaFormation { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn rebellion_gain_tech_tile_rejects_a_maxed_research_track() {
    let mut state = base_state();
    state.players[0].explored_ships.push(1); // Rebellion
    state.players[0].resources.qic = 3;
    state.players[0].research_tracks.science = 5;
    let tile = TechTile(1);
    assert!(state.research_board.tech_tiles.contains(&tile));

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RebellionGainTechTile {
            tile,
            track: ResearchTrack::Science,
        },
    );

    assert!(result.is_err());
}

#[test]
fn tech_tile_special_action_rejects_owned_non_special_standard_tile() {
    let mut state = base_state();
    state.players[0].tech_tiles.push(TechTile(1)); // immediate VP tile, no action space

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TechTileSpecialAction {
            tile: TechTileRef::Standard { tile: TechTile(1) },
        },
    );

    assert!(result.is_err());
}

#[test]
fn gleens_gaia_formation_adds_two_range_and_uses_once_per_round_flag() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Gleens);
    state.players[0].resources.qic = 0;
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;

    insert_empty_hex(&mut state, HexCoord::new(2, 0));
    let target = HexCoord::new(3, 0);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let normal_result =
        RuleEngine::apply_action(&mut state, 0, GameAction::GaiaFormation { coord: target });
    assert!(
        normal_result.is_err(),
        "distance 3 is out of base range without QIC"
    );

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::GleensGaiaFormation { coord: target },
    )
    .unwrap_or_else(|e| panic!("Gleens +2 range Gaia formation should succeed: {e}"));

    assert_eq!(state.players[0].gaiaformers_deployed, 1);
    assert_eq!(
        state.board.hexes[&target]
            .planet
            .as_ref()
            .map(|planet| planet.owner),
        Some(Some(0))
    );
    assert!(state.players[0].gleens_special_action_used_this_round);
}

#[test]
fn gleens_gaia_formation_rejects_non_gleens_factions() {
    let mut state = base_state();
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;
    let target = HexCoord::new(1, 1);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::GleensGaiaFormation { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn gleens_gaia_formation_rejects_after_special_action_used() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Gleens);
    state.players[0].research_tracks.gaia = 1;
    state.players[0].gaiaformers_total = 1;
    state.players[0].gleens_special_action_used_this_round = true;
    let target = HexCoord::new(1, 1);
    insert_planet_hex(&mut state, target, PlanetType::Transdim);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::GleensGaiaFormation { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn gleens_explore_spaceship_rejects_after_special_action_used() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Gleens);
    state.players[0].gleens_special_action_used_this_round = true;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::GleensExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    );

    assert!(result.is_err());
}
