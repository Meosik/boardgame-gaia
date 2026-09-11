use gaia_engine::error::RuleError;
use gaia_engine::faction::registry::global as faction_registry;
use gaia_engine::game_state::{
    BoardState, BrainstoneLocation, FactionId, FederationToken, FinalScoringCondition, GameEvent,
    GamePhase, Hex, HexCoord, PendingCharge, PlacedStructure, Planet, PlanetType, ResearchTrack,
    Sector, SetupPhase, SpaceshipId, Structure, StructureType, TechTile,
};
use gaia_engine::map::MapEngine;
use gaia_engine::rules::actions::{
    FederationTokenChoice, FreeActionKind, GameAction, SetupAction, TechTileChoice,
};
use gaia_engine::scoring::ScoringEngine;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{RuleEngine, SetupPolicy};
use std::collections::HashMap;

// ── Helpers ───────────────────────────────────────────────────────────────────

/// A board with one Standard sector (id 1) containing a single unowned Terra
/// planet at `planet_coord`, plus (optionally) `extra_coord` as a bare hex —
/// used to seed a player's pre-existing structure for reachability.
fn board_with_planet(planet_coord: HexCoord, extra_coord: Option<HexCoord>) -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        planet_coord,
        Hex {
            coord: planet_coord,
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
    if let Some(extra) = extra_coord {
        hexes.insert(
            extra,
            Hex {
                coord: extra,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure {
                    owner: 0,
                    kind: StructureType::Mine,
                }],
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

fn board_with_faction_structures(
    owned: &[(HexCoord, PlanetType, StructureType)],
    unowned: &[(HexCoord, PlanetType)],
) -> BoardState {
    let mut hexes = HashMap::new();
    for &(coord, planet_type, kind) in owned {
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: Some(Planet {
                    planet_type,
                    is_gaia_formed: false,
                    owner: Some(0),
                }),
                space_tile_kind: None,
                structures: vec![PlacedStructure { owner: 0, kind }],
                satellites: vec![],
            },
        );
    }
    for &(coord, planet_type) in unowned {
        hexes.insert(
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

// ── Setup completion seeds starting resources ──────────────────────────────────

#[test]
fn setup_completion_seeds_starting_resources() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![
            FactionId::Darkanians,
            FactionId::Tinkeroids,
            FactionId::Terrans,
            FactionId::Lantids,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    RuleEngine::apply_setup_action(
        &mut state,
        0,
        SetupAction::SelectFaction {
            faction: FactionId::Darkanians,
        },
    )
    .unwrap_or_else(|e| panic!("player 0 selects Darkanians: {e}"));
    RuleEngine::apply_setup_action(
        &mut state,
        1,
        SetupAction::SelectFaction {
            faction: FactionId::Terrans,
        },
    )
    .unwrap_or_else(|e| panic!("player 1 selects Terrans: {e}"));

    assert!(matches!(
        state.phase,
        GamePhase::Setup(SetupPhase::StartingStructures { .. })
    ));

    let darkanians = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(darkanians.resources.ore, 7);
    assert_eq!(darkanians.resources.credits, 15);
    assert_eq!(darkanians.resources.knowledge, 3);
    assert_eq!(darkanians.resources.power.bowl1, 4);
    assert_eq!(darkanians.resources.power.bowl2, 2);
    // Faction board icons (not in the rulebook prose): Darkanians start with
    // Navigation and Economy both at level 1.
    assert_eq!(darkanians.research_tracks.navigation, 1);
    assert_eq!(darkanians.research_tracks.economy, 1);
    assert_eq!(darkanians.research_tracks.gaia, 0);

    // The three physical Gaiaformers begin locked on the Gaia Project track.
    assert_eq!(darkanians.gaiaformers_total, 0);

    let terrans = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(terrans.resources.ore, 4);
    assert_eq!(terrans.resources.credits, 15);
    assert_eq!(terrans.resources.knowledge, 3);
    assert_eq!(terrans.research_tracks.navigation, 0);
    assert_eq!(terrans.research_tracks.economy, 0);
    // Not in the rulebook prose, but printed on the physical faction board —
    // Terrans also start with GaiaProject at level 1. Per the rulebook's
    // setup section, a non-zero starting track level also grants that
    // level's one-time bonus immediately: GaiaProject level 1 = 1 Gaiaformer.
    assert_eq!(terrans.research_tracks.gaia, 1);
    assert_eq!(terrans.gaiaformers_total, 1);
}

#[test]
fn setup_completion_seeds_moweyds_and_tinkeroids_starting_tracks() {
    // Moweyds pairs with SpaceGiants and Tinkeroids pairs with Darkanians
    // (`FactionId::other_board_side`) — picking one removes its pair-mate
    // from `available_factions`, so this combination (unpaired) is valid
    // while Moweyds+SpaceGiants together would not be.
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.spaceship_boards = MapEngine::initial_spaceship_boards("moweyds-setup-test");
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![
            FactionId::Moweyds,
            FactionId::SpaceGiants,
            FactionId::Tinkeroids,
            FactionId::Darkanians,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::Moweyds), (1, FactionId::Tinkeroids)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|e| panic!("player {player} selects {faction:?}: {e}"));
    }

    assert!(matches!(
        state.phase,
        GamePhase::Setup(SetupPhase::StartingStructures { .. })
    ));

    let moweyds = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(moweyds.research_tracks.gaia, 1);
    assert_eq!(moweyds.exploration_shuttles_available, 2);
    assert!(moweyds.explored_ships.contains(&2));
    assert_eq!(moweyds.expensive_terraforming_planet_types.len(), 3);
    let tf_mars = state
        .spaceship_boards
        .iter()
        .find(|board| board.id == SpaceshipId::TFMars)
        .unwrap_or_else(|| panic!("T F Mars board exists"));
    assert_eq!(tf_mars.explorers[0], Some(0));

    let tinkeroids = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(tinkeroids.research_tracks.science, 1);
    assert_eq!(tinkeroids.resources.knowledge, 3);
    assert_eq!(tinkeroids.expensive_terraforming_planet_types.len(), 3);
}

#[test]
fn setup_resolves_shared_opponent_colors_then_fills_from_terraforming_board_order() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    state.terraforming_color_order = vec![
        PlanetType::Ice,
        PlanetType::Swamp,
        PlanetType::Desert,
        PlanetType::Oxide,
        PlanetType::Titanium,
        PlanetType::Volcanic,
        PlanetType::Terra,
    ];
    state.spaceship_boards = MapEngine::initial_spaceship_boards("terraforming-cost-test");
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1, 2, 3],
        vec![
            FactionId::Moweyds,
            FactionId::Bescods,
            FactionId::Tinkeroids,
            FactionId::Terrans,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [
        (0, FactionId::Moweyds),
        (1, FactionId::Bescods),
        (2, FactionId::Tinkeroids),
        (3, FactionId::Terrans),
    ] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|error| panic!("player {player} selects {faction:?}: {error}"));
    }

    assert_eq!(
        state.players[0].expensive_terraforming_planet_types,
        vec![PlanetType::Titanium, PlanetType::Terra, PlanetType::Ice]
    );
    assert_eq!(
        state.players[2].expensive_terraforming_planet_types,
        vec![PlanetType::Titanium, PlanetType::Terra, PlanetType::Swamp]
    );
}

#[test]
fn one_lost_fleet_faction_uses_all_three_base_faction_colors() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    state.terraforming_color_order = vec![
        PlanetType::Ice,
        PlanetType::Swamp,
        PlanetType::Oxide,
        PlanetType::Volcanic,
        PlanetType::Terra,
        PlanetType::Desert,
        PlanetType::Titanium,
    ];
    state.spaceship_boards = MapEngine::initial_spaceship_boards("one-special-color-test");
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1, 2, 3],
        vec![
            FactionId::Tinkeroids,
            FactionId::Terrans,
            FactionId::Xenos,
            FactionId::Bescods,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [
        (0, FactionId::Tinkeroids),
        (1, FactionId::Terrans),
        (2, FactionId::Xenos),
        (3, FactionId::Bescods),
    ] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|error| panic!("player {player} selects {faction:?}: {error}"));
    }

    assert_eq!(
        state.players[0].expensive_terraforming_planet_types,
        vec![PlanetType::Terra, PlanetType::Desert, PlanetType::Titanium]
    );
}

#[test]
fn two_lost_fleet_factions_without_base_opponents_split_the_random_order() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.terraforming_color_order = vec![
        PlanetType::Ice,
        PlanetType::Swamp,
        PlanetType::Desert,
        PlanetType::Oxide,
        PlanetType::Titanium,
        PlanetType::Volcanic,
        PlanetType::Terra,
    ];
    state.spaceship_boards = MapEngine::initial_spaceship_boards("two-special-color-test");
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![FactionId::Tinkeroids, FactionId::Moweyds],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::Tinkeroids), (1, FactionId::Moweyds)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|error| panic!("player {player} selects {faction:?}: {error}"));
    }

    assert_eq!(
        state.players[0].expensive_terraforming_planet_types,
        vec![PlanetType::Ice, PlanetType::Swamp, PlanetType::Desert]
    );
    assert_eq!(
        state.players[1].expensive_terraforming_planet_types,
        vec![
            PlanetType::Oxide,
            PlanetType::Titanium,
            PlanetType::Volcanic
        ]
    );
}

#[test]
fn base_factions_do_not_receive_lost_fleet_terraforming_colors() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.spaceship_boards = MapEngine::initial_spaceship_boards("base-only-color-test");
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![FactionId::Terrans, FactionId::Xenos],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::Terrans), (1, FactionId::Xenos)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|error| panic!("player {player} selects {faction:?}: {error}"));
    }

    assert!(state
        .players
        .iter()
        .all(|player| player.expensive_terraforming_planet_types.is_empty()));
}

fn lantids_cohabitation_state(
    target_type: PlanetType,
    gaia: bool,
) -> gaia_engine::game_state::GameState {
    let pi = HexCoord::new(-1, 0);
    let origin = HexCoord::new(0, 0);
    let target = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    for (coord, kind) in [
        (pi, StructureType::PlanetaryInstitute),
        (origin, StructureType::Mine),
    ] {
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: Some(Planet {
                    planet_type: PlanetType::Terra,
                    is_gaia_formed: false,
                    owner: Some(0),
                }),
                space_tile_kind: None,
                structures: vec![PlacedStructure { owner: 0, kind }],
                satellites: vec![],
            },
        );
    }
    hexes.insert(
        target,
        Hex {
            coord: target,
            planet: Some(Planet {
                planet_type: target_type,
                is_gaia_formed: gaia,
                owner: Some(1),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 1,
                kind: StructureType::TradingStation,
            }],
            satellites: vec![],
        },
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

    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Lantids);
            player.resources.ore = 10;
            player.resources.credits = 15;
            player.resources.knowledge = 3;
            player.resources.qic = 0;
            player.resources.power.bowl1 = 1;
            player.resources.power.bowl2 = 0;
            player.structures = vec![
                Structure {
                    hex: pi,
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: origin,
                    kind: StructureType::Mine,
                },
            ];
        })
        .with_player_fn(1, |player| {
            player.structures = vec![Structure {
                hex: target,
                kind: StructureType::TradingStation,
            }];
        })
        .with_player(2)
        .with_player(3)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn lantids_build_on_an_opponents_planet_without_terraforming_and_keep_ownership() {
    let target = HexCoord::new(1, 0);
    let mut state = lantids_cohabitation_state(PlanetType::Ice, false);

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target })
        .unwrap_or_else(|error| panic!("Lantids cohabitation build should succeed: {error}"));

    let player = state
        .player(0)
        .unwrap_or_else(|| panic!("Lantids player exists"));
    assert_eq!(player.resources.ore, 9);
    assert_eq!(player.resources.credits, 13);
    assert_eq!(player.resources.knowledge, 5);
    assert!(player
        .structures
        .iter()
        .any(|structure| structure.hex == target && structure.kind == StructureType::Mine));
    let target_hex = state
        .board
        .hexes
        .get(&target)
        .unwrap_or_else(|| panic!("target exists"));
    assert_eq!(
        target_hex.planet.as_ref().and_then(|planet| planet.owner),
        Some(1)
    );
    assert_eq!(target_hex.structures.len(), 2);

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    assert!(matches!(
        RuleEngine::validate_action(&state, 0, &GameAction::Build { coord: target }),
        Err(RuleError::TargetOccupied(coord)) if coord == target
    ));
    assert!(matches!(
        RuleEngine::validate_action(
            &state,
            0,
            &GameAction::Upgrade {
                coord: target,
                to: StructureType::TradingStation,
                tech_tile_choice: None,
            },
        ),
        Err(RuleError::ActionNotAllowed(_))
    ));
}

#[test]
fn lantids_shared_gaia_mine_counts_as_a_building_but_not_as_a_planet_type() {
    let target = HexCoord::new(1, 0);
    let mut state = lantids_cohabitation_state(PlanetType::Transdim, true);

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target })
        .unwrap_or_else(|error| panic!("shared Gaia build should succeed: {error}"));

    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostBuildings),
        3
    );
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostPlanetTypes),
        1
    );
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, 0, &FinalScoringCondition::MostGaiaPlanets),
        0
    );
}

#[test]
fn setup_completion_seeds_ivits_and_bescods_lost_fleet_exploration_board_adjustments() {
    // Lost Fleet exploration board top adjustments (GP_Exp_Rule_EN_V1_Web.pdf p.6, always
    // enabled in this project): Ivits get 2 power in Area I / 2 power in Area II (not the base
    // game's 2/4 split), Bescods start with 3 knowledge (not the base game's 1).
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![
            FactionId::Ivits,
            FactionId::HadschHallas,
            FactionId::Bescods,
            FactionId::Firaks,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::Ivits), (1, FactionId::Bescods)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|e| panic!("player {player} selects {faction:?}: {e}"));
    }

    assert!(matches!(
        state.phase,
        GamePhase::Setup(SetupPhase::StartingStructures { .. })
    ));

    let ivits = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(ivits.resources.power.bowl1, 2);
    assert_eq!(ivits.resources.power.bowl2, 2);

    let bescods = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(bescods.resources.knowledge, 3);
}

#[test]
fn setup_completion_seeds_space_giants_starting_track() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![
            FactionId::SpaceGiants,
            FactionId::Moweyds,
            FactionId::Firaks,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::SpaceGiants), (1, FactionId::Firaks)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|e| panic!("player {player} selects {faction:?}: {e}"));
    }

    assert!(matches!(
        state.phase,
        GamePhase::Setup(SetupPhase::StartingStructures { .. })
    ));

    let space_giants = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(space_giants.research_tracks.navigation, 1);
}

#[test]
fn setup_places_the_taklons_brainstone_in_area_one() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![
            FactionId::Taklons,
            FactionId::Ambas,
            FactionId::HadschHallas,
            FactionId::Ivits,
        ],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    RuleEngine::apply_setup_action(
        &mut state,
        0,
        SetupAction::SelectFaction {
            faction: FactionId::Taklons,
        },
    )
    .unwrap_or_else(|error| panic!("Taklons selection should succeed: {error}"));
    RuleEngine::apply_setup_action(
        &mut state,
        1,
        SetupAction::SelectFaction {
            faction: FactionId::HadschHallas,
        },
    )
    .unwrap_or_else(|error| panic!("Hadsch Hallas selection should succeed: {error}"));

    let taklons = &state.players[0];
    assert_eq!(taklons.resources.power.bowl1, 2);
    assert_eq!(
        taklons.resources.power.brainstone,
        Some(BrainstoneLocation::Area1)
    );
    assert_eq!(taklons.resources.power.total(), 7);
}

#[test]
fn setup_completion_grants_xenos_ai_level_one_qic_bonus() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.faction_selection = Some(SetupPolicy::initialize(
        vec![0, 1],
        vec![FactionId::Xenos, FactionId::Gleens, FactionId::Firaks],
    ));
    state.phase = GamePhase::Setup(SetupPhase::FactionSelection { active_player: 0 });

    for (player, faction) in [(0, FactionId::Xenos), (1, FactionId::Firaks)] {
        RuleEngine::apply_setup_action(&mut state, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|e| panic!("player {player} selects {faction:?}: {e}"));
    }

    let xenos = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(xenos.research_tracks.ai, 1);
    // Base starting_qic (1) + ArtificialIntelligence level 1's one-time bonus (1 QIC).
    assert_eq!(xenos.resources.qic, 2);
}

// ── Darkanians ability ───────────────────────────────────────────────────────

#[test]
fn darkanians_terraforming_distance_is_always_one() {
    let ability = faction_registry().get(FactionId::Darkanians);
    assert_eq!(
        ability.terraforming_distance_override(PlanetType::Terra, PlanetType::Ice),
        Some(1)
    );
    assert_eq!(
        ability.terraforming_distance_override(PlanetType::Volcanic, PlanetType::Swamp),
        Some(1)
    );
}

#[test]
fn darkanians_gaia_colonization_costs_two_qic() {
    let ability = faction_registry().get(FactionId::Darkanians);
    assert_eq!(ability.gaia_colonization_qic_cost(), 2);
}

#[test]
fn darkanians_bonus_requires_pi_and_a_new_sector_not_a_global_first_use() {
    let target = HexCoord::new(1, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            p.structures.clear();
            p.first_colonization_bonus_used = true;
        })
        .with_board(board_with_planet(target, None))
        .build();
    let ability = faction_registry().get(FactionId::Darkanians);
    assert!(
        ability.on_build(&state, 0, target).is_empty(),
        "PI required"
    );
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(-10, 0),
        kind: StructureType::PlanetaryInstitute,
    });
    let events = ability.on_build(&state, 0, target);
    assert!(
        matches!(events.as_slice(), [GameEvent::ResourceChanged { delta, .. }]
        if delta.credits == 2 && delta.knowledge == 1)
    );
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(0, 0),
        kind: StructureType::Mine,
    });
    assert!(
        ability.on_build(&state, 0, target).is_empty(),
        "already occupied sector"
    );
    state.players[0].structures.pop();
    assert!(
        ability.on_build(&state, 0, HexCoord::new(20, 0)).is_empty(),
        "interspace excluded"
    );
}

#[test]
fn darkanians_builds_reward_each_new_standard_and_deep_sector_after_reload() {
    let mut board = board_with_planet(HexCoord::new(1, 0), None);
    let template = board.sectors[0].clone();
    board.sectors.extend([
        Sector {
            id: 2,
            origin: HexCoord::new(5, 0),
            ..template.clone()
        },
        Sector {
            id: 11,
            origin: HexCoord::new(10, 0),
            ..template
        },
    ]);
    for coord in [
        HexCoord::new(0, 1),
        HexCoord::new(5, 0),
        HexCoord::new(10, 0),
        HexCoord::new(11, 0),
        HexCoord::new(16, 0),
    ] {
        let mut hex = board.hexes[&HexCoord::new(1, 0)].clone();
        hex.coord = coord;
        board.hexes.insert(coord, hex);
    }
    for q in -3..=16 {
        let coord = HexCoord::new(q, 0);
        board.hexes.entry(coord).or_insert(Hex {
            coord,
            planet: None,
            structures: vec![],
            satellites: vec![],
            space_tile_kind: None,
        });
    }
    let mut pi_hex = board.hexes[&HexCoord::new(1, 0)].clone();
    pi_hex.coord = HexCoord::new(-3, 0);
    pi_hex.planet.as_mut().unwrap_or_else(|| panic!("planet")).owner = Some(0);
    pi_hex.structures = vec![PlacedStructure {
        owner: 0,
        kind: StructureType::PlanetaryInstitute,
    }];
    board.hexes.insert(pi_hex.coord, pi_hex);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            p.first_colonization_bonus_used = true;
            p.resources.ore = 100;
            p.resources.credits = 100;
            p.resources.qic = 100;
            p.research_tracks.navigation = 4;
            p.structures = vec![Structure {
                hex: HexCoord::new(-3, 0),
                kind: StructureType::PlanetaryInstitute,
            }];
        })
        .with_board(board)
        .build();
    for (coord, reward) in [
        (HexCoord::new(1, 0), true),
        (HexCoord::new(0, 1), false),
        (HexCoord::new(5, 0), true),
        (HexCoord::new(10, 0), true),
        (HexCoord::new(11, 0), false),
        (HexCoord::new(16, 0), false),
    ] {
        state.phase = GamePhase::ActionPhase { active_player: 0 };
        let events = RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord })
            .unwrap_or_else(|e| panic!("build at {coord:?}: {e}"));
        let bonus_count = events.iter().filter(|event| matches!(event,
            GameEvent::ResourceChanged { delta, .. } if delta.credits == 2 && delta.knowledge == 1
        )).count();
        assert_eq!(bonus_count, usize::from(reward), "{coord:?}");
        state = serde_json::from_str(&serde_json::to_string(&state).unwrap_or_else(|error| panic!("serialize: {error}")))
            .unwrap_or_else(|error| panic!("reload: {error}"));
    }
}

#[test]
fn darkanians_lost_planet_marks_a_sector_as_colonized() {
    let target = HexCoord::new(1, 0);
    let lost = HexCoord::new(0, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            p.structures = vec![Structure {
                hex: HexCoord::new(-10, 0),
                kind: StructureType::PlanetaryInstitute,
            }];
        })
        .with_board(board_with_planet(target, None))
        .build();
    let mut hex = state.board.hexes[&target].clone();
    hex.coord = lost;
    hex.planet = Some(Planet {
        planet_type: PlanetType::LostPlanet,
        owner: Some(0),
        is_gaia_formed: false,
    });
    state.board.hexes.insert(lost, hex);
    state.board.lost_planet = Some(lost);
    let ability = faction_registry().get(FactionId::Darkanians);
    assert_eq!(
        ability.on_build(&state, 0, lost).len(),
        1,
        "new Lost Planet is the first colony"
    );
    assert!(
        ability.on_build(&state, 0, target).is_empty(),
        "later mine cannot reward that sector again"
    );
}

#[test]
fn darkanians_flat_terraforming_cost_does_not_grant_bonus_without_pi() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.resources.knowledge = 3;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
        })
        .with_board(board_with_planet(
            HexCoord::new(1, 0),
            Some(HexCoord::new(0, 0)),
        ))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build should be valid: {e}"));
    assert_eq!(state.players[0].resources.ore, 6);
    assert_eq!(state.players[0].resources.credits, 13);
    assert_eq!(state.players[0].resources.knowledge, 3);
}

// ── Space Giants ability ─────────────────────────────────────────────────────

#[test]
fn space_giants_terraforming_distance_is_always_two() {
    let ability = faction_registry().get(FactionId::SpaceGiants);
    assert_eq!(
        ability.terraforming_distance_override(PlanetType::Terra, PlanetType::Ice),
        Some(2)
    );
}

#[test]
fn space_giants_gaia_colonization_costs_two_qic() {
    let ability = faction_registry().get(FactionId::SpaceGiants);
    assert_eq!(ability.gaia_colonization_qic_cost(), 2);
}

#[test]
fn space_giants_special_action_grants_tech_tile_once() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::SpaceGiants);
            p.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
            p.resources.ore = 0;
            p.resources.qic = 0;
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tiles = vec![TechTile(4)];
    state.research_board.tech_tile_slots = vec![None; 9];
    let tiles_before = state.research_board.tech_tiles.len();

    let action = GameAction::SpaceGiantsGainTechTile {
        choice: TechTileChoice::Standard {
            tile: TechTile(4),
            advance_track: Some(ResearchTrack::Science),
            bonus_build_coord: None,
        },
    };
    assert!(RuleEngine::get_valid_actions(&state, 0).contains(&action));
    let events = RuleEngine::apply_action(&mut state, 0, action.clone())
        .unwrap_or_else(|e| panic!("first use should succeed: {e}"));
    assert!(
        events
            .iter()
            .any(|e| matches!(e, GameEvent::TechTileGained { player: 0, .. })),
        "expected a TechTileGained event"
    );

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert!(player.pi_ability_used);
    assert_eq!(player.tech_tiles.len(), 1);
    assert_eq!(player.resources.ore, 1);
    assert_eq!(player.resources.qic, 1);
    assert_eq!(player.research_tracks.science, 1);
    assert_eq!(state.research_board.tech_tiles.len(), tiles_before - 1);

    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
    let result = RuleEngine::apply_action(&mut state, 0, action);
    assert!(
        matches!(result, Err(RuleError::ActionNotAllowed(_))),
        "second use should be rejected, got {result:?}"
    );
}

#[test]
fn space_giants_pi_tech_tile_requires_the_planetary_institute() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| player.faction = Some(FactionId::SpaceGiants))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tiles = vec![TechTile(4)];

    let result = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::SpaceGiantsGainTechTile {
            choice: TechTileChoice::Standard {
                tile: TechTile(4),
                advance_track: None,
                bonus_build_coord: None,
            },
        },
    );

    assert!(matches!(result, Err(RuleError::ActionNotAllowed(_))));
}

#[test]
fn faction_without_implemented_special_action_cannot_consume_a_turn() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |player| player.faction = Some(FactionId::Terrans))
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();

    let result = RuleEngine::validate_action(&state, 0, &GameAction::SpecialAction { id: 1 });

    assert!(matches!(result, Err(RuleError::ActionNotAllowed(_))));
    assert_eq!(state.current_player, 0);
}

// ── Remaining base-game faction abilities ────────────────────────────────────

#[test]
fn xenos_can_form_a_federation_with_six_power() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(0, 1);
    let structures = [
        (a, PlanetType::Desert, StructureType::PlanetaryInstitute),
        (b, PlanetType::Desert, StructureType::TradingStation),
        (c, PlanetType::Desert, StructureType::Mine),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Xenos);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_board(board_with_faction_structures(&structures, &[]))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1)];

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: vec![a, b, c],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .unwrap_or_else(|error| panic!("Xenos' six-power federation should be legal: {error}"));

    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(1)]);
}

#[test]
fn non_xenos_still_need_seven_federation_power() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(0, 1);
    let structures = [
        (a, PlanetType::Desert, StructureType::PlanetaryInstitute),
        (b, PlanetType::Desert, StructureType::TradingStation),
        (c, PlanetType::Desert, StructureType::Mine),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1)];

    let result = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: vec![a, b, c],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );
    assert!(matches!(
        result,
        Err(RuleError::FederationInsufficientPower)
    ));
}

#[test]
fn bal_taks_navigation_is_locked_until_the_planetary_institute_is_built() {
    let pi_coord = HexCoord::new(0, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::BalTaks);
            player.resources.knowledge = 10;
        })
        .build();

    let locked = RuleEngine::validate_action(
        &state,
        0,
        &GameAction::ResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    );
    assert!(matches!(locked, Err(RuleError::ActionNotAllowed(_))));

    state.players[0].structures.push(Structure {
        hex: pi_coord,
        kind: StructureType::PlanetaryInstitute,
    });
    assert!(RuleEngine::validate_action(
        &state,
        0,
        &GameAction::ResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    )
    .is_ok());
}

#[test]
fn ambas_swap_moves_the_pi_and_mine_without_scoring_an_upgrade() {
    let pi = HexCoord::new(0, 0);
    let mine = HexCoord::new(1, 0);
    let structures = [
        (pi, PlanetType::Swamp, StructureType::PlanetaryInstitute),
        (mine, PlanetType::Swamp, StructureType::Mine),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Ambas);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();
    let vp_before = state.players[0].vp;

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::AmbasSwapPlanetaryInstitute { mine_coord: mine },
    )
    .unwrap_or_else(|error| panic!("Ambas swap should succeed: {error}"));

    let player = &state.players[0];
    assert!(player
        .structures
        .iter()
        .any(|structure| structure.hex == pi && structure.kind == StructureType::Mine));
    assert!(player.structures.iter().any(|structure| {
        structure.hex == mine && structure.kind == StructureType::PlanetaryInstitute
    }));
    assert!(player.faction_special_action_used_this_round);
    assert_eq!(player.vp, vp_before);
    assert!(matches!(
        events.as_slice(),
        [GameEvent::StructuresSwapped { .. }]
    ));
    assert!(matches!(
        RuleEngine::validate_action(
            &state,
            0,
            &GameAction::AmbasSwapPlanetaryInstitute { mine_coord: pi }
        ),
        Err(RuleError::NotYourTurn)
    ));
}

#[test]
fn firaks_downgrades_a_lab_and_advances_research_once_per_round() {
    let pi = HexCoord::new(0, 0);
    let lab = HexCoord::new(1, 0);
    let structures = [
        (pi, PlanetType::Volcanic, StructureType::PlanetaryInstitute),
        (lab, PlanetType::Volcanic, StructureType::ResearchLab),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Firaks);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();

    state.players[0].resources.knowledge = 0;
    let ore_before = state.players[0].resources.ore;
    let credits_before = state.players[0].resources.credits;
    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FiraksDowngradeResearchLab {
            coord: lab,
            track: ResearchTrack::Science,
        },
    )
    .unwrap_or_else(|error| panic!("Firaks action should succeed: {error}"));

    let player = &state.players[0];
    assert!(player.structures.iter().any(|structure| {
        structure.hex == lab && structure.kind == StructureType::TradingStation
    }));
    assert_eq!(
        state.board.hexes[&lab].structures[0].kind,
        StructureType::TradingStation
    );
    assert_eq!(
        player.resources.knowledge, 0,
        "free research spends no knowledge"
    );
    assert_eq!(player.resources.ore, ore_before);
    assert_eq!(player.resources.credits, credits_before);
    assert_eq!(player.research_tracks.science, 1);
    assert!(player.faction_special_action_used_this_round);
    assert!(events.iter().any(|event| matches!(
        event,
        GameEvent::ResearchAdvanced {
            track: ResearchTrack::Science,
            level: 1,
            ..
        }
    )));
}

#[test]
fn bescods_may_only_advance_a_lowest_research_track() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Bescods);
            player.research_tracks.terraforming = 2;
            player.research_tracks.navigation = 1;
            player.research_tracks.ai = 1;
            player.research_tracks.gaia = 1;
            player.research_tracks.economy = 1;
            player.research_tracks.science = 1;
        })
        .with_player(1)
        .build();

    assert!(matches!(
        RuleEngine::validate_action(
            &state,
            0,
            &GameAction::BescodsLowestResearchAdvance {
                track: ResearchTrack::Terraforming
            }
        ),
        Err(RuleError::ActionNotAllowed(_))
    ));

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::BescodsLowestResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    )
    .unwrap_or_else(|error| panic!("a tied lowest track should be legal: {error}"));
    assert_eq!(state.players[0].research_tracks.navigation, 2);
    assert!(state.players[0].faction_special_action_used_this_round);
}

#[test]
fn base_faction_special_action_token_resets_during_cleanup() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Bescods);
            player.faction_special_action_used_this_round = true;
        })
        .with_player(1)
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|error| panic!("round transition should succeed: {error}"));

    assert!(!state.players[0].faction_special_action_used_this_round);
}

#[test]
fn bescods_pi_increases_home_planet_structure_power() {
    let pi = HexCoord::new(0, 0);
    let trading_station = HexCoord::new(1, 0);
    let structures = [
        (pi, PlanetType::Titanium, StructureType::PlanetaryInstitute),
        (
            trading_station,
            PlanetType::Titanium,
            StructureType::TradingStation,
        ),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Bescods);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1)];

    // Printed power is only 5 (PI 3 + TS 2), but the PI adds +1 to each
    // structure on the Bescods' gray/Titanium home planets, reaching 7.
    assert!(RuleEngine::validate_action(
        &state,
        0,
        &GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: vec![pi, trading_station],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    )
    .is_ok());
}

#[test]
fn bescods_use_the_swapped_academy_and_pi_upgrade_paths() {
    let trading_station = HexCoord::new(0, 0);
    let research_lab = HexCoord::new(1, 0);
    let structures = [
        (
            trading_station,
            PlanetType::Titanium,
            StructureType::TradingStation,
        ),
        (
            research_lab,
            PlanetType::Titanium,
            StructureType::ResearchLab,
        ),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Bescods);
            player.resources.ore = 20;
            player.resources.credits = 20;
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();

    assert!(matches!(
        RuleEngine::validate_action(
            &state,
            0,
            &GameAction::Upgrade {
                tech_tile_choice: None,
                coord: trading_station,
                to: StructureType::PlanetaryInstitute,
            },
        ),
        Err(RuleError::InvalidUpgrade { .. })
    ));
    assert!(RuleEngine::validate_action(
        &state,
        0,
        &GameAction::Upgrade {
            tech_tile_choice: None,
            coord: trading_station,
            to: StructureType::Academy(gaia_engine::game_state::AcademyType::Science),
        },
    )
    .is_ok());

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            tech_tile_choice: None,
            coord: research_lab,
            to: StructureType::PlanetaryInstitute,
        },
    )
    .unwrap_or_else(|error| panic!("Bescods Research Lab → PI should succeed: {error}"));
    assert!(state.players[0].structures.iter().any(|structure| {
        structure.hex == research_lab && structure.kind == StructureType::PlanetaryInstitute
    }));
    assert_eq!(state.players[0].resources.ore, 16);
    assert_eq!(state.players[0].resources.credits, 14);
}

#[test]
fn gleens_replace_qic_gains_with_ore_until_the_qic_academy_is_built() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Gleens);
            player.resources.ore = 0;
            player.resources.qic = 0;
            player.resources.power.bowl3 = 4;
        })
        .with_player(1)
        .build();

    let qic_action = GameAction::FreeAction {
        kind: FreeActionKind::PowerToQic,
        count: 1,
    };
    RuleEngine::apply_action(&mut state, 0, qic_action.clone())
        .unwrap_or_else(|error| panic!("Gleens should convert the QIC gain to ore: {error}"));
    assert_eq!(state.players[0].resources.ore, 1);
    assert_eq!(state.players[0].resources.qic, 0);

    state.players[0].resources.power.bowl3 = 4;
    state.players[0].structures.push(Structure {
        hex: HexCoord::new(0, 0),
        kind: StructureType::Academy(gaia_engine::game_state::AcademyType::Qic),
    });
    RuleEngine::apply_action(&mut state, 0, qic_action)
        .unwrap_or_else(|error| panic!("the QIC Academy should unlock normal QIC gains: {error}"));
    assert_eq!(state.players[0].resources.ore, 1);
    assert_eq!(state.players[0].resources.qic, 1);
}

#[test]
fn gleens_pay_one_ore_for_a_gaia_planet_and_score_two_vp() {
    let mine = HexCoord::new(0, 0);
    let gaia_planet = HexCoord::new(1, 0);
    let structures = [(mine, PlanetType::Desert, StructureType::Mine)];
    let mut board =
        board_with_faction_structures(&structures, &[(gaia_planet, PlanetType::Transdim)]);
    board
        .hexes
        .get_mut(&gaia_planet)
        .and_then(|hex| hex.planet.as_mut())
        .unwrap_or_else(|| panic!("Gaia target exists"))
        .is_gaia_formed = true;
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Gleens);
            player.resources.ore = 5;
            player.resources.credits = 5;
            player.resources.qic = 0;
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board)
        .build();
    let vp_before = state.players[0].vp;

    let events = RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: gaia_planet })
        .unwrap_or_else(|error| panic!("Gleens Gaia-planet mine should succeed: {error}"));

    assert_eq!(state.players[0].resources.ore, 3);
    assert_eq!(state.players[0].resources.credits, 3);
    assert_eq!(state.players[0].resources.qic, 0);
    assert!(state.players[0].vp >= vp_before + 2);
    assert!(events.iter().any(|event| matches!(
        event,
        GameEvent::VpAwarded {
            amount: 2,
            reason: gaia_engine::game_state::VpReason::FactionSpecial,
            ..
        }
    )));
}

#[test]
fn gleens_pi_grants_its_unique_federation_token_and_reward() {
    let trading_station = HexCoord::new(0, 0);
    let structures = [(
        trading_station,
        PlanetType::Desert,
        StructureType::TradingStation,
    )];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Gleens);
            // Kept below the 15-ore cap (`Resources::gain_ore`) — 20 was already an illegal
            // starting amount no legal game state could reach; the upgrade cost (-4) then the
            // federation reward (+1) below is what this test actually cares about.
            player.resources.ore = 10;
            player.resources.credits = 20;
            player.resources.knowledge = 3;
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            tech_tile_choice: None,
            coord: trading_station,
            to: StructureType::PlanetaryInstitute,
        },
    )
    .unwrap_or_else(|error| panic!("Gleens PI upgrade should succeed: {error}"));

    assert!(state.players[0]
        .federation_tokens
        .contains(&FederationToken(16)));
    assert_eq!(state.players[0].resources.ore, 7);
    assert_eq!(state.players[0].resources.credits, 16);
    assert_eq!(state.players[0].resources.knowledge, 4);
    assert!(events.iter().any(|event| matches!(
        event,
        GameEvent::FederationFormed {
            token: FederationToken(16),
            ..
        }
    )));
}

fn taklons_passive_charge_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Taklons);
            player.resources.power.bowl1 = 0;
            player.resources.power.bowl2 = 0;
            player.resources.power.bowl3 = 0;
            player.resources.power.brainstone = Some(BrainstoneLocation::Area2);
            player.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
        })
        .with_player(1)
        .with_phase(GamePhase::ChargePowerPending {
            queue: vec![PendingCharge {
                player: 0,
                hex: HexCoord::new(1, 0),
                max_power: 1,
            }],
            resume_active_player: Some(1),
        })
        .build()
}

#[test]
fn taklons_pi_chooses_whether_to_gain_power_before_or_after_a_passive_charge() {
    let mut gain_before = taklons_passive_charge_state();
    assert!(matches!(
        RuleEngine::validate_action(&gain_before, 0, &GameAction::ChargePower { accept: true }),
        Err(RuleError::ActionNotAllowed(_))
    ));
    RuleEngine::apply_action(
        &mut gain_before,
        0,
        GameAction::TaklonsChargePower { gain_before: true },
    )
    .unwrap_or_else(|error| panic!("gain-before charge should succeed: {error}"));
    assert_eq!(gain_before.players[0].resources.power.bowl2, 1);
    assert_eq!(
        gain_before.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Area2)
    );

    let mut gain_after = taklons_passive_charge_state();
    RuleEngine::apply_action(
        &mut gain_after,
        0,
        GameAction::TaklonsChargePower { gain_before: false },
    )
    .unwrap_or_else(|error| panic!("gain-after charge should succeed: {error}"));
    assert_eq!(gain_after.players[0].resources.power.bowl1, 1);
    assert_eq!(
        gain_after.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Area3)
    );
}

#[test]
fn taklons_brainstone_spends_as_three_power() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Taklons);
            player.resources.power.bowl1 = 0;
            player.resources.power.bowl2 = 0;
            player.resources.power.bowl3 = 4;
            player.resources.power.brainstone = Some(BrainstoneLocation::Area3);
        })
        .with_player(1)
        .build();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|error| panic!("Brainstone plus four power should pay seven: {error}"));

    assert_eq!(state.players[0].resources.power.bowl3, 0);
    assert_eq!(
        state.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Area1)
    );
    assert_eq!(state.players[0].resources.knowledge, 6);
}

#[test]
fn taklons_brainstone_counts_as_one_gaia_project_token_and_returns_next_round() {
    let mine = HexCoord::new(0, 0);
    let target = HexCoord::new(1, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Taklons);
            player.structures.push(Structure {
                hex: mine,
                kind: StructureType::Mine,
            });
            player.research_tracks.gaia = 1;
            player.gaiaformers_total = 1;
            player.resources.power.bowl1 = 2;
            player.resources.power.bowl2 = 3;
            player.resources.power.bowl3 = 0;
            player.resources.power.brainstone = Some(BrainstoneLocation::Area3);
        })
        .with_player(1)
        .with_board(board_with_planet(target, Some(mine)))
        .build();
    state
        .board
        .hexes
        .get_mut(&target)
        .and_then(|hex| hex.planet.as_mut())
        .unwrap_or_else(|| panic!("target exists"))
        .planet_type = PlanetType::Transdim;

    RuleEngine::apply_action(&mut state, 0, GameAction::GaiaFormation { coord: target })
        .unwrap_or_else(|error| panic!("sixth Gaia token may be the Brainstone: {error}"));
    assert_eq!(state.players[0].resources.power.gaia_forming, 5);
    assert_eq!(
        state.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Gaia)
    );

    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|error| panic!("round transition should return Gaia power: {error}"));
    assert_eq!(
        state.players[0].resources.power.brainstone,
        Some(BrainstoneLocation::Area1)
    );
}

#[test]
fn gaia_formation_moves_the_track_cost_into_the_gaia_area() {
    let mine = HexCoord::new(0, 0);
    let target = HexCoord::new(1, 0);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.structures.push(Structure {
                hex: mine,
                kind: StructureType::Mine,
            });
            player.research_tracks.gaia = 3;
            player.gaiaformers_total = 1;
            player.resources.power.bowl1 = 2;
            player.resources.power.bowl2 = 2;
            player.resources.power.bowl3 = 0;
        })
        .with_player(1)
        .with_board(board_with_planet(target, Some(mine)))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state
        .board
        .hexes
        .get_mut(&target)
        .and_then(|hex| hex.planet.as_mut())
        .unwrap_or_else(|| panic!("target exists"))
        .planet_type = PlanetType::Transdim;
    let total_before = state.players[0].resources.power.total();

    RuleEngine::apply_action(&mut state, 0, GameAction::GaiaFormation { coord: target })
        .unwrap_or_else(|error| panic!("Gaia formation should succeed: {error}"));

    let power = &state.players[0].resources.power;
    assert_eq!(power.bowl1, 0);
    assert_eq!(power.bowl2, 0);
    assert_eq!(power.bowl3, 0);
    assert_eq!(power.gaia_forming, 4);
    assert_eq!(power.total(), total_before);
}

#[test]
fn geodens_reward_only_applies_to_new_post_pi_planet_types_once() {
    let pi = HexCoord::new(0, 0);
    let existing_mine = HexCoord::new(1, 0);
    let first_swamp = HexCoord::new(0, 1);
    let second_swamp = HexCoord::new(-1, 1);
    let structures = [
        (pi, PlanetType::Volcanic, StructureType::TradingStation),
        (existing_mine, PlanetType::Ice, StructureType::Mine),
    ];
    let targets = [
        (first_swamp, PlanetType::Swamp),
        (second_swamp, PlanetType::Swamp),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Geodens);
            player.resources.ore = 30;
            player.resources.credits = 30;
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &targets))
        .build();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            tech_tile_choice: None,
            coord: pi,
            to: StructureType::PlanetaryInstitute,
        },
    )
    .unwrap_or_else(|error| panic!("PI upgrade should succeed: {error}"));
    assert!(state.players[0]
        .geodens_rewarded_planet_types
        .contains(&PlanetType::Volcanic));
    assert!(state.players[0]
        .geodens_rewarded_planet_types
        .contains(&PlanetType::Ice));

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let knowledge_before = state.players[0].resources.knowledge;
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: first_swamp })
        .unwrap_or_else(|error| panic!("first post-PI Swamp should build: {error}"));
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 3);

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: second_swamp,
        },
    )
    .unwrap_or_else(|error| panic!("second Swamp should build: {error}"));
    assert_eq!(state.players[0].resources.knowledge, knowledge_before + 3);
}

#[test]
fn nevlas_pi_spends_each_area_three_token_as_two_power() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Nevlas);
            player.resources.power.bowl3 = 4;
            player.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
        })
        .with_player(1)
        .build();

    // Printed cost 7 consumes ceil(7/2) = 4 tokens; the unused half of the
    // last token is lost, as required by the faction appendix.
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 1, coord: None },
    )
    .unwrap_or_else(|error| {
        panic!("Nevlas should afford printed power 7 with four tokens: {error}")
    });
    assert_eq!(state.players[0].resources.power.bowl3, 0);
    assert_eq!(state.players[0].resources.knowledge, 6);
}

#[test]
fn xenos_without_pi_cannot_form_a_six_power_federation() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let c = HexCoord::new(0, 1);
    let structures = [
        (
            a,
            PlanetType::Desert,
            StructureType::Academy(gaia_engine::game_state::AcademyType::Qic),
        ),
        (b, PlanetType::Desert, StructureType::TradingStation),
        (c, PlanetType::Desert, StructureType::Mine),
    ];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Xenos);
            player.structures = structures
                .iter()
                .map(|(hex, _, kind)| Structure {
                    hex: *hex,
                    kind: *kind,
                })
                .collect();
        })
        .with_board(board_with_faction_structures(&structures, &[]))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1)];

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FormFederation {
            satellite_hexes: vec![],
            hexes: vec![a, b, c],
            token: FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
            bonus_research_track: None,
        },
    );

    assert!(matches!(
        result,
        Err(RuleError::FederationInsufficientPower)
    ));
}

#[test]
fn space_giants_institute_bundles_technology_and_spends_only_one_turn() {
    let coord = HexCoord::new(0, 0);
    let structures = [(
        coord,
        PlanetType::ProtoPlanet,
        StructureType::TradingStation,
    )];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::SpaceGiants);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.structures = vec![Structure {
                hex: coord,
                kind: StructureType::TradingStation,
            }];
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tile_slots = vec![None; 9];
    let choice = TechTileChoice::Standard {
        tile: TechTile(2),
        advance_track: Some(ResearchTrack::Science),
        bonus_build_coord: None,
    };
    let no_choice = GameAction::Upgrade {
        coord,
        to: StructureType::PlanetaryInstitute,
        tech_tile_choice: None,
    };
    assert!(RuleEngine::validate_action(&state, 0, &no_choice).is_err());
    let action = GameAction::Upgrade {
        coord,
        to: StructureType::PlanetaryInstitute,
        tech_tile_choice: Some(choice.clone()),
    };
    assert!(RuleEngine::get_valid_actions(&state, 0).contains(&action));
    RuleEngine::apply_action(&mut state, 0, action).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(
        state.players[0].structures[0].kind,
        StructureType::PlanetaryInstitute
    );
    assert!(state.players[0].pi_ability_used);
    assert!(state.players[0].tech_tiles.contains(&TechTile(2)));
    assert_eq!(state.players[0].research_tracks.science, 1);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    assert!(RuleEngine::validate_action(
        &state,
        0,
        &GameAction::SpaceGiantsGainTechTile { choice }
    )
    .is_err());
}

#[test]
fn lantids_pi_reward_repeats_after_reload_and_is_absent_without_pi() {
    for has_pi in [false, true] {
        let mut state = lantids_cohabitation_state(PlanetType::Ice, false);
        let second = HexCoord::new(0, 1);
        let mut hex = state.board.hexes[&HexCoord::new(1, 0)].clone();
        hex.coord = second;
        state.board.hexes.insert(second, hex);
        state.players[1].structures.push(Structure {
            hex: second,
            kind: StructureType::TradingStation,
        });
        if !has_pi {
            state.players[0]
                .structures
                .retain(|s| s.kind != StructureType::PlanetaryInstitute);
            state.board.hexes.remove(&HexCoord::new(-1, 0));
        }
        for (index, coord) in [HexCoord::new(1, 0), second].into_iter().enumerate() {
            state.phase = GamePhase::ActionPhase { active_player: 0 };
            RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
            state = serde_json::from_value(state.serialize()).unwrap_or_else(|error| panic!("saved value should deserialize: {error}"));
            assert_eq!(
                state.players[0].resources.knowledge,
                3 + if has_pi { 2 * (index as u8 + 1) } else { 0 }
            );
        }
        assert_eq!(state.players[0].resources.ore, 8);
        assert_eq!(state.players[0].resources.credits, 11);
    }
}

#[test]
fn space_giants_pi_can_bundle_advanced_technology_with_another_research_track() {
    use gaia_engine::game_state::AdvancedTechTile;
    let coord = HexCoord::new(0, 0);
    let structures = [(
        coord,
        PlanetType::ProtoPlanet,
        StructureType::TradingStation,
    )];
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::SpaceGiants);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.structures = vec![Structure {
                hex: coord,
                kind: StructureType::TradingStation,
            }];
            p.research_tracks.terraforming = 4;
            p.tech_tiles = vec![TechTile(3)];
            p.federation_tokens = vec![FederationToken(1)];
        })
        .with_player(1)
        .with_board(board_with_faction_structures(&structures, &[]))
        .build();
    state.research_board.advanced_tech_tiles[0] = Some(AdvancedTechTile(20));
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            coord,
            to: StructureType::PlanetaryInstitute,
            tech_tile_choice: Some(TechTileChoice::Advanced {
                track: ResearchTrack::Terraforming,
                covered_tile: TechTile(3),
                advance_track: Some(ResearchTrack::Science),
            }),
        },
    )
    .unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    state = serde_json::from_value(state.serialize()).unwrap_or_else(|error| panic!("saved value should deserialize: {error}"));
    assert_eq!(
        state.players[0].advanced_tech_tiles,
        vec![AdvancedTechTile(20)]
    );
    assert_eq!(state.players[0].covered_tech_tiles, vec![TechTile(3)]);
    assert_eq!(
        state.players[0].gray_federation_tokens,
        vec![FederationToken(1)]
    );
    assert_eq!(state.players[0].research_tracks.terraforming, 4);
    assert_eq!(state.players[0].research_tracks.science, 1);
    assert!(state.players[0].pi_ability_used);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn firaks_invalid_downgrades_do_not_mutate_state() {
    for case in [
        "no_pi",
        "wrong_target",
        "no_trading_station_supply",
        "research_maxed",
        "already_used",
    ] {
        let pi = HexCoord::new(0, 0);
        let lab = HexCoord::new(1, 0);
        let structures = [
            (pi, PlanetType::Titanium, StructureType::PlanetaryInstitute),
            (lab, PlanetType::Titanium, StructureType::ResearchLab),
        ];
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(FactionId::Firaks);
                p.structures = structures
                    .iter()
                    .map(|(hex, _, kind)| Structure {
                        hex: *hex,
                        kind: *kind,
                    })
                    .collect();
            })
            .with_player(1)
            .with_board(board_with_faction_structures(&structures, &[]))
            .build();
        let mut target = lab;
        match case {
            "no_pi" => state.players[0]
                .structures
                .retain(|s| s.kind != StructureType::PlanetaryInstitute),
            "wrong_target" => target = pi,
            "no_trading_station_supply" => {
                for q in 10..14 {
                    state.players[0].structures.push(Structure {
                        hex: HexCoord::new(q, 0),
                        kind: StructureType::TradingStation,
                    });
                }
            }
            "research_maxed" => state.players[0].research_tracks.science = 5,
            "already_used" => state.players[0].faction_special_action_used_this_round = true,
            _ => unreachable!(),
        }
        let before = serde_json::to_value(&state).unwrap_or_else(|error| panic!("test value should serialize: {error}"));
        let result = RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::FiraksDowngradeResearchLab {
                coord: target,
                track: ResearchTrack::Science,
            },
        );
        assert!(result.is_err(), "{case}");
        assert_eq!(serde_json::to_value(&state).unwrap_or_else(|error| panic!("test value should serialize: {error}")), before, "{case}");
    }
}
