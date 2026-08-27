use gaia_engine::error::RuleError;
use gaia_engine::game_state::{
    BoardState, Booster, FactionId, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, Sector, SetupPhase, Structure, StructureType,
};
use gaia_engine::rules::actions::{GameAction, SetupAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{GameState, MapEngine, Randomizer, RuleEngine};
use std::collections::HashMap;

const PLAYERS: [(u8, &str); 4] = [(7, "P1"), (3, "P2"), (9, "P3"), (1, "P4")];

fn new_game(seed: &str) -> GameState {
    let setup = Randomizer::generate_setup(seed)
        .unwrap_or_else(|error| panic!("fixture setup should be valid: {error}"));
    let players = PLAYERS
        .iter()
        .map(|(id, name)| (*id, (*name).to_string()))
        .collect::<Vec<_>>();
    MapEngine::init_game_state("SETUP", "SETUP", &players, &setup)
}

fn select_factions(game: &mut GameState, factions: [FactionId; 4]) {
    for ((player, _), faction) in PLAYERS.into_iter().zip(factions) {
        RuleEngine::apply_setup_action(game, player, SetupAction::SelectFaction { faction })
            .unwrap_or_else(|error| panic!("faction selection should succeed: {error}"));
    }
}

fn home_planet(faction: FactionId) -> PlanetType {
    match faction {
        FactionId::Terrans | FactionId::Lantids => PlanetType::Terra,
        FactionId::Xenos | FactionId::Gleens => PlanetType::Desert,
        FactionId::Taklons | FactionId::Ambas => PlanetType::Swamp,
        FactionId::HadschHallas | FactionId::Ivits => PlanetType::Oxide,
        FactionId::Geodens | FactionId::BalTaks => PlanetType::Volcanic,
        FactionId::Firaks | FactionId::Bescods => PlanetType::Titanium,
        FactionId::Nevlas | FactionId::Itars => PlanetType::Ice,
        FactionId::Tinkeroids | FactionId::Darkanians => PlanetType::Asteroid,
        FactionId::Moweyds | FactionId::SpaceGiants => PlanetType::ProtoPlanet,
    }
}

fn open_home_planet(game: &GameState, player: u8) -> HexCoord {
    let faction = game
        .player(player)
        .and_then(|state| state.faction)
        .unwrap_or_else(|| panic!("player {player} should have a faction"));
    let expected = home_planet(faction);
    let mut matches = game
        .board
        .hexes
        .values()
        .filter(|hex| {
            hex.planet.as_ref().is_some_and(|planet| {
                planet.planet_type == expected
                    && !planet.is_gaia_formed
                    && planet.owner.is_none()
                    && hex.structures.is_empty()
            })
        })
        .map(|hex| hex.coord)
        .collect::<Vec<_>>();
    matches.sort_by_key(|coord| (coord.q, coord.r));
    matches
        .into_iter()
        .next()
        .unwrap_or_else(|| panic!("an open {expected:?} planet should exist for player {player}"))
}

fn placement_phase(game: &GameState) -> (u8, usize, StructureType) {
    match game.phase {
        GamePhase::Setup(SetupPhase::StartingStructures {
            active_player,
            placement_index,
            kind,
        }) => (active_player, placement_index, kind),
        ref phase => panic!("expected starting-structure phase, got {phase:?}"),
    }
}

fn booster_phase(game: &GameState) -> (u8, usize) {
    match game.phase {
        GamePhase::Setup(SetupPhase::StartingBoosters {
            active_player,
            selection_index,
        }) => (active_player, selection_index),
        ref phase => panic!("expected starting-booster phase, got {phase:?}"),
    }
}

fn select_starting_booster(game: &mut GameState, player: u8, booster_id: u8) {
    let events = RuleEngine::apply_setup_action(
        game,
        player,
        SetupAction::SelectStartingBooster { booster_id },
    )
    .unwrap_or_else(|error| panic!("starting booster should be selected: {error}"));
    assert!(matches!(
        events.as_slice(),
        [GameEvent::BoosterSelected {
            player: event_player,
            booster,
        }] if *event_player == player && booster.0 == booster_id
    ));
}

fn place_current(game: &mut GameState) -> (u8, HexCoord, StructureType) {
    let (player, _, kind) = placement_phase(game);
    let coord = open_home_planet(game, player);
    let events =
        RuleEngine::apply_setup_action(game, player, SetupAction::PlaceStartingStructure { coord })
            .unwrap_or_else(|error| panic!("starting structure should be placed: {error}"));
    assert!(matches!(
        events.as_slice(),
        [GameEvent::StructureBuilt {
            player: event_player,
            hex,
            kind: event_kind,
        }] if *event_player == player && *hex == coord && *event_kind == kind
    ));
    (player, coord, kind)
}

#[test]
fn base_factions_place_clockwise_then_counterclockwise_with_exceptions_last() {
    let mut game = new_game("starting-structure-base-order");
    game.boosters = [1, 2, 3, 4, 5, 9, 13].into_iter().map(Booster).collect();
    select_factions(
        &mut game,
        [
            FactionId::Terrans,
            FactionId::Xenos,
            FactionId::Taklons,
            FactionId::Ivits,
        ],
    );

    let expected = [
        (7, StructureType::Mine),
        (3, StructureType::Mine),
        (9, StructureType::Mine),
        (9, StructureType::Mine),
        (3, StructureType::Mine),
        (7, StructureType::Mine),
        (3, StructureType::Mine),
        (1, StructureType::PlanetaryInstitute),
    ];
    let initial_booster_count = game.boosters.len();
    assert_eq!(placement_phase(&game), (7, 0, StructureType::Mine));
    assert!(game.players.iter().all(|player| player.booster.is_none()));

    let first_terra = open_home_planet(&game, 7);
    let wrong_actor = RuleEngine::apply_setup_action(
        &mut game,
        3,
        SetupAction::PlaceStartingStructure { coord: first_terra },
    );
    assert!(matches!(wrong_actor, Err(RuleError::NotYourTurn)));

    let wrong_planet = game
        .board
        .hexes
        .values()
        .find(|hex| {
            hex.planet.as_ref().is_some_and(|planet| {
                planet.planet_type != PlanetType::Terra && planet.owner.is_none()
            })
        })
        .map(|hex| hex.coord)
        .unwrap_or_else(|| panic!("a non-Terra planet should exist"));
    let wrong_target = RuleEngine::apply_setup_action(
        &mut game,
        7,
        SetupAction::PlaceStartingStructure {
            coord: wrong_planet,
        },
    );
    assert!(matches!(wrong_target, Err(RuleError::InvalidTarget(coord)) if coord == wrong_planet));

    let mut placements: Vec<(u8, HexCoord, StructureType)> = Vec::new();
    for (index, expected_placement) in expected.iter().copied().enumerate() {
        assert_eq!(
            placement_phase(&game),
            (expected_placement.0, index, expected_placement.1)
        );

        if index == 5 {
            let occupied_terra = placements[0].1;
            let occupied = RuleEngine::apply_setup_action(
                &mut game,
                7,
                SetupAction::PlaceStartingStructure {
                    coord: occupied_terra,
                },
            );
            assert!(
                matches!(occupied, Err(RuleError::TargetOccupied(coord)) if coord == occupied_terra)
            );
        }

        placements.push(place_current(&mut game));
    }

    assert_eq!(booster_phase(&game), (1, 0));
    assert_eq!(game.round, 0);
    assert_eq!(game.boosters.len(), initial_booster_count);
    assert!(game.players.iter().all(|player| player.booster.is_none()));

    let wrong_booster_actor = RuleEngine::apply_setup_action(
        &mut game,
        7,
        SetupAction::SelectStartingBooster { booster_id: 1 },
    );
    assert!(matches!(wrong_booster_actor, Err(RuleError::NotYourTurn)));
    let unavailable_booster = RuleEngine::apply_setup_action(
        &mut game,
        1,
        SetupAction::SelectStartingBooster { booster_id: 99 },
    );
    assert!(matches!(
        unavailable_booster,
        Err(RuleError::ActionNotAllowed(message)) if message.contains("not available")
    ));

    for (index, (player, booster_id)) in [(1, 1), (9, 2), (3, 13), (7, 9)].into_iter().enumerate() {
        assert_eq!(booster_phase(&game), (player, index));
        select_starting_booster(&mut game, player, booster_id);
    }

    assert_eq!(game.phase, GamePhase::Setup(SetupPhase::Complete));
    assert_eq!(game.round, 1);
    assert_eq!(game.boosters.len(), initial_booster_count - PLAYERS.len());
    assert!(game.players.iter().all(|player| player.booster.is_some()));

    for (player, expected_count, expected_kind) in [
        (7, 2, StructureType::Mine),
        (3, 3, StructureType::Mine),
        (9, 2, StructureType::Mine),
        (1, 1, StructureType::PlanetaryInstitute),
    ] {
        let player_state = game
            .player(player)
            .unwrap_or_else(|| panic!("player {player} should exist"));
        assert_eq!(player_state.structures.len(), expected_count);
        assert!(player_state
            .structures
            .iter()
            .all(|structure| structure.kind == expected_kind));
        for structure in &player_state.structures {
            let hex = game
                .board
                .hexes
                .get(&structure.hex)
                .unwrap_or_else(|| panic!("placed hex should remain on the board"));
            assert_eq!(
                hex.planet.as_ref().and_then(|planet| planet.owner),
                Some(player)
            );
            assert!(hex
                .structures
                .iter()
                .any(|placed| placed.owner == player && placed.kind == structure.kind));
        }
    }

    let terrans_qic_before_income = game
        .player(7)
        .map(|player| player.resources.qic)
        .unwrap_or_else(|| panic!("Terrans player should exist"));
    let events = RuleEngine::start_first_round(&mut game)
        .unwrap_or_else(|error| panic!("first-round income should start: {error}"));
    assert!(matches!(
        events.as_slice(),
        [GameEvent::RoundStarted { round: 1 }]
    ));
    assert_eq!(
        game.player(7).map(|player| player.resources.qic),
        Some(terrans_qic_before_income + 1),
        "booster 9 income should be granted before round-one actions"
    );
    assert!(matches!(game.phase, GamePhase::IncomeOrderPending { .. }));
    RuleEngine::apply_action(
        &mut game,
        1,
        GameAction::ChooseIncomeOrder { charge_first: true },
    )
    .unwrap_or_else(|error| panic!("Ivits income order should resolve: {error}"));
    assert_eq!(game.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn lost_fleet_single_structure_factions_enter_during_second_stage() {
    let mut game = new_game("starting-structure-lost-fleet-order");
    select_factions(
        &mut game,
        [
            FactionId::Terrans,
            FactionId::Xenos,
            FactionId::Moweyds,
            FactionId::Darkanians,
        ],
    );

    let expected = [
        (7, StructureType::Mine),
        (3, StructureType::Mine),
        (1, StructureType::Mine),
        (9, StructureType::Mine),
        (3, StructureType::Mine),
        (7, StructureType::Mine),
        (3, StructureType::Mine),
    ];
    for (index, (player, kind)) in expected.into_iter().enumerate() {
        assert_eq!(placement_phase(&game), (player, index, kind));
        place_current(&mut game);
    }

    assert_eq!(booster_phase(&game), (1, 0));
    assert_eq!(
        game.player(9).map(|player| player.structures.len()),
        Some(1)
    );
    assert_eq!(
        game.player(1).map(|player| player.structures.len()),
        Some(1)
    );
}

#[test]
fn normal_build_never_overwrites_an_opponents_planet() {
    let anchor = HexCoord::new(0, 0);
    let target = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        anchor,
        Hex {
            coord: anchor,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: Some(7),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 7,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        target,
        Hex {
            coord: target,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: Some(3),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 3,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: anchor,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let mut game = GameStateBuilder::new()
        .with_player_fn(7, |player| {
            player.faction = Some(FactionId::Terrans);
            player.structures.push(Structure {
                hex: anchor,
                kind: StructureType::Mine,
            });
        })
        .with_player_fn(3, |player| {
            player.faction = Some(FactionId::Xenos);
            player.structures.push(Structure {
                hex: target,
                kind: StructureType::Mine,
            });
        })
        .with_board(board)
        .build();

    let result = RuleEngine::apply_action(&mut game, 7, GameAction::Build { coord: target });

    assert!(matches!(result, Err(RuleError::TargetOccupied(coord)) if coord == target));
    let target_hex = game
        .board
        .hexes
        .get(&target)
        .unwrap_or_else(|| panic!("target should remain on the board"));
    assert_eq!(
        target_hex.planet.as_ref().and_then(|planet| planet.owner),
        Some(3)
    );
    assert_eq!(target_hex.structures[0].owner, 3);
}
