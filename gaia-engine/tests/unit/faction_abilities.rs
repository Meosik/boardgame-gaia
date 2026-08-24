use gaia_engine::error::RuleError;
use gaia_engine::faction::registry::global as faction_registry;
use gaia_engine::game_state::{
    BoardState, FactionId, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, Sector, SetupPhase, Structure, StructureType,
};
use gaia_engine::rules::actions::{GameAction, SetupAction};
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

    assert_eq!(state.phase, GamePhase::Setup(SetupPhase::Complete));

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

    assert_eq!(state.phase, GamePhase::Setup(SetupPhase::Complete));

    let moweyds = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(moweyds.research_tracks.gaia, 1);

    let tinkeroids = state.player(1).unwrap_or_else(|| panic!("player 1 exists"));
    assert_eq!(tinkeroids.research_tracks.science, 1);
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

    assert_eq!(state.phase, GamePhase::Setup(SetupPhase::Complete));

    let space_giants = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(space_giants.research_tracks.navigation, 1);
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
