use gaia_engine::error::RuleError;
use gaia_engine::faction::registry::global as faction_registry;
use gaia_engine::game_state::{
    BoardState, BrainstoneLocation, FactionId, FederationToken, GameEvent, GamePhase, Hex,
    HexCoord, PendingCharge, PlacedStructure, Planet, PlanetType, ResearchTrack, Sector,
    SetupPhase, Structure, StructureType,
};
use gaia_engine::rules::actions::{FederationTokenChoice, FreeActionKind, GameAction, SetupAction};
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

    // Base rule: every faction starts with 3 Gaiaformers.
    assert_eq!(darkanians.gaiaformers_total, 3);

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
    assert_eq!(terrans.gaiaformers_total, 4);
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

    let tinkeroids = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(tinkeroids.research_tracks.science, 1);
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
fn darkanians_on_build_grants_bonus_before_first_use() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            // first_colonization_bonus_used defaults to false — the bonus is
            // gated on this explicit flag, not on how many structures the
            // player happens to have (structure count depends on the
            // separately unimplemented starting-structure placement step).
        })
        .with_board(board_with_planet(HexCoord::new(1, 0), None))
        .build();

    let ability = faction_registry().get(FactionId::Darkanians);
    let events = ability.on_build(&state, 0, HexCoord::new(1, 0));

    assert_eq!(events.len(), 1);
    match &events[0] {
        GameEvent::ResourceChanged { player, delta } => {
            assert_eq!(*player, 0);
            assert_eq!(delta.credits, 2);
            assert_eq!(delta.knowledge, 1);
        }
        other => panic!("expected ResourceChanged, got {other:?}"),
    }
}

#[test]
fn darkanians_on_build_no_bonus_once_flag_is_set() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Darkanians);
            p.first_colonization_bonus_used = true;
        })
        .with_board(board_with_planet(HexCoord::new(1, 0), None))
        .build();

    let ability = faction_registry().get(FactionId::Darkanians);
    let events = ability.on_build(&state, 0, HexCoord::new(1, 0));
    assert!(events.is_empty(), "bonus should only trigger once");
}

#[test]
fn darkanians_flat_terraforming_cost_and_bonus_apply_through_build_action() {
    // Home planet type (Asteroid) is off the standard ring, so without the
    // override this would fall back to a free (0-ore) terraform. With the
    // override it's always 1 step, i.e. COST_PER_STEP[level 0] = 3 ore.
    // The player also has a pre-existing structure (needed for reachability,
    // since starting-structure placement isn't implemented) but hasn't used
    // the first-colonization bonus yet, so this Build should also trigger it.
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

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Ore: 10 - (1 Mine cost + 3 for 1 terraforming step at level 0) = 6
    assert_eq!(player.resources.ore, 6);
    // Credits: 15 - 2 (Mine cost) + 2 (first-colonization bonus) = 15
    assert_eq!(player.resources.credits, 15);
    // Knowledge: 3 + 1 (first-colonization bonus) = 4
    assert_eq!(player.resources.knowledge, 4);
    assert!(player.first_colonization_bonus_used);
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
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let tiles_before = state.research_board.tech_tiles.len();

    let events = RuleEngine::apply_action(&mut state, 0, GameAction::SpecialAction { id: 1 })
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
    assert_eq!(state.research_board.tech_tiles.len(), tiles_before - 1);

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::SpecialAction { id: 1 });
    assert!(
        matches!(result, Err(RuleError::ActionNotAllowed(_))),
        "second use should be rejected, got {result:?}"
    );
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
            player.resources.ore = 20;
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
    assert_eq!(state.players[0].resources.ore, 17);
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
