use gaia_engine::error::RuleError;
use gaia_engine::game_state::{
    BoardState, FactionId, GaiaDecisionKind, GamePhase, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, ResearchTrack, Sector, Structure, StructureType, TechTile,
};
use gaia_engine::rules::actions::{FreeActionKind, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn empty_board_with_transdim(coord: HexCoord, owner: Option<u8>) -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        coord,
        Hex {
            coord,
            planet: Some(Planet {
                planet_type: PlanetType::Transdim,
                is_gaia_formed: false,
                owner,
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
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn resolve_income_order_if_pending(state: &mut gaia_engine::game_state::GameState) {
    let player = match &state.phase {
        GamePhase::IncomeOrderPending { queue, .. } => queue.first().map(|entry| entry.player),
        _ => None,
    };
    if let Some(player) = player {
        RuleEngine::apply_action(
            state,
            player,
            GameAction::ChooseIncomeOrder { charge_first: true },
        )
        .unwrap_or_else(|error| panic!("income order should resolve: {error}"));
    }
}

#[test]
fn advance_to_next_round_rejects_wrong_phase() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let result = RuleEngine::advance_to_next_round(&mut state);
    assert!(matches!(result, Err(RuleError::WrongPhase)));
}

#[test]
fn advance_to_next_round_reopens_action_phase_and_increments_round() {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .with_round(2)
        .with_phase(GamePhase::RoundScoring { round: 2 })
        .build();
    state.players[0].passed = true;
    state.players[1].passed = true;
    state.used_power_actions = vec![1, 4];
    state.used_spaceship_actions = vec![2, 7];

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.round, 3);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
    assert!(!state.players[0].passed);
    assert!(!state.players[1].passed);
    assert!(state.used_power_actions.is_empty());
    assert!(state.used_spaceship_actions.is_empty());
}

#[test]
fn gaia_phase_completes_owned_transdim_planets() {
    let coord = HexCoord::new(0, 0);
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_board(empty_board_with_transdim(coord, Some(0)))
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();
    state.players[0].gaiaformers_total = 1;
    state.players[0].gaiaformers_deployed = 1;

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let planet = state
        .board
        .hexes
        .get(&coord)
        .and_then(|h| h.planet.as_ref())
        .unwrap_or_else(|| panic!("planet exists"));
    assert!(planet.is_gaia_formed);
    assert_eq!(state.players[0].gaiaformers_deployed, 0);
    assert_eq!(state.players[0].gaiaformers_available(), 1);
}

#[test]
fn completed_gaia_project_owner_can_build_the_first_mine_on_the_reserved_planet() {
    let coord = HexCoord::new(1, 0);
    let anchor = HexCoord::new(0, 0);
    let mut board = empty_board_with_transdim(coord, Some(0));
    board.hexes.insert(
        anchor,
        Hex {
            coord: anchor,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: Some(0),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.structures = vec![Structure {
                hex: anchor,
                kind: StructureType::Mine,
            }];
            player.resources.ore = 5;
            player.resources.credits = 5;
            player.resources.qic = 2;
            player.gaiaformers_total = 1;
            player.gaiaformers_deployed = 1;
        })
        .with_board(board)
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| {
        panic!("completed Gaia planet should accept its owner's Mine: {error}")
    });

    assert!(state.players[0]
        .structures
        .iter()
        .any(|structure| structure.hex == coord && structure.kind == StructureType::Mine));
}

#[test]
fn gaia_phase_leaves_unowned_transdim_planets_alone() {
    let coord = HexCoord::new(0, 0);
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_board(empty_board_with_transdim(coord, None))
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let planet = state
        .board
        .hexes
        .get(&coord)
        .and_then(|h| h.planet.as_ref())
        .unwrap_or_else(|| panic!("planet exists"));
    assert!(!planet.is_gaia_formed);
}

#[test]
fn gaia_phase_moves_power_to_area_one_by_default() {
    // Xenos: any non-Terrans faction works here, but Xenos specifically has no
    // passive income that would muddy the exact power values below (unlike Lantids).
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Xenos);
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 0;
            p.resources.power.gaia_forming = 4;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 4);
    assert_eq!(player.resources.power.bowl2, 0);
    assert_eq!(player.resources.power.gaia_forming, 0);
}

#[test]
fn gaia_phase_moves_terrans_power_to_area_two() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 0;
            p.resources.power.gaia_forming = 4;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 0);
    assert_eq!(player.resources.power.bowl2, 4);
}

#[test]
fn income_resolves_before_terrans_planetary_institute_gaia_decision() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
            player.resources.power.gaia_forming = 4;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));

    assert!(matches!(state.phase, GamePhase::IncomeOrderPending { .. }));
    assert_eq!(state.players[0].resources.power.gaia_forming, 4);

    resolve_income_order_if_pending(&mut state);
    assert!(matches!(
        &state.phase,
        GamePhase::GaiaDecisionPending { queue, round: 1 }
            if queue.first().is_some_and(|entry|
                entry.player == 0
                    && entry.kind == GaiaDecisionKind::TerransPowerConversion
                    && entry.remaining_power == 4)
    ));
}

#[test]
fn terrans_planetary_institute_converts_gaia_power_then_moves_the_remainder_to_area_two() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
            player.resources.ore = 0;
            player.resources.power.bowl2 = 0;
            player.resources.power.gaia_forming = 4;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));
    resolve_income_order_if_pending(&mut state);
    let ore_after_income = state.players[0].resources.ore;
    let bowl2_before_finish = state.players[0].resources.power.bowl2;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TerransGaiaConversion {
            kind: FreeActionKind::PowerToOre,
            count: 1,
        },
    )
    .unwrap_or_else(|error| panic!("Terrans conversion should succeed: {error}"));

    assert_eq!(state.players[0].resources.ore, ore_after_income + 1);
    assert_eq!(state.players[0].resources.power.gaia_forming, 4);
    assert!(matches!(
        &state.phase,
        GamePhase::GaiaDecisionPending { queue, .. }
            if queue.first().is_some_and(|entry| entry.remaining_power == 1)
    ));
    let reused_value = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TerransGaiaConversion {
            kind: FreeActionKind::PowerToOre,
            count: 1,
        },
    );
    assert!(matches!(
        reused_value,
        Err(RuleError::InsufficientResources(
            gaia_engine::game_state::ResourceKind::Power
        ))
    ));

    RuleEngine::apply_action(&mut state, 0, GameAction::FinishGaiaDecision)
        .unwrap_or_else(|error| panic!("Terrans Gaia decision should finish: {error}"));

    assert_eq!(state.players[0].resources.power.gaia_forming, 0);
    assert_eq!(
        state.players[0].resources.power.bowl2,
        bowl2_before_finish + 4
    );
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
    assert_eq!(state.round, 2);
}

#[test]
fn itars_planetary_institute_can_gain_standard_tech_tiles_repeatedly() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Itars);
            player.structures.push(Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::PlanetaryInstitute,
            });
            player.resources.power.gaia_forming = 8;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));
    resolve_income_order_if_pending(&mut state);

    for (tile, track) in [
        (TechTile(1), ResearchTrack::Science),
        (TechTile(2), ResearchTrack::Economy),
    ] {
        RuleEngine::apply_action(&mut state, 0, GameAction::ItarsGaiaTechTile { tile, track })
            .unwrap_or_else(|error| panic!("Itars Tech tile should succeed: {error}"));
    }

    assert_eq!(state.players[0].resources.power.gaia_forming, 0);
    assert_eq!(state.players[0].tech_tiles, vec![TechTile(1), TechTile(2)]);
    assert_eq!(state.players[0].research_tracks.science, 1);
    assert_eq!(state.players[0].research_tracks.economy, 1);
    assert!(matches!(state.phase, GamePhase::GaiaDecisionPending { .. }));

    RuleEngine::apply_action(&mut state, 0, GameAction::FinishGaiaDecision)
        .unwrap_or_else(|error| panic!("Itars Gaia decision should finish: {error}"));
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn itars_without_planetary_institute_returns_gaia_power_to_area_one() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Itars);
            player.resources.power.bowl1 = 0;
            player.resources.power.gaia_forming = 4;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));

    assert_eq!(state.players[0].resources.power.bowl1, 4);
    assert_eq!(state.players[0].resources.power.gaia_forming, 0);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn income_phase_grants_current_research_track_level_income() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
            p.resources.knowledge = 0;
            p.research_tracks.set(ResearchTrack::Science, 3);
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    // research_tracks.toml: Science level 3 = 3 knowledge, plus the
    // universal ResearchLab base income (1 knowledge/round even with 0 built).
    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.research_tracks.science, 3);
    assert_eq!(player.resources.knowledge, 4);
}

#[test]
fn income_phase_charges_power_from_economy_track() {
    // Xenos: has no passive income that would muddy the exact power values below
    // (unlike Lantids).
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Xenos);
            p.resources.credits = 0;
            p.resources.power.bowl1 = 2;
            p.resources.power.bowl2 = 0;
            p.research_tracks.set(ResearchTrack::Economy, 1);
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    // research_tracks.toml: Economy level 1 = 2 credits, charge 1 power.
    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.credits, 2);
    assert_eq!(player.resources.power.bowl1, 1);
    assert_eq!(player.resources.power.bowl2, 1);
}

#[test]
fn lantids_gain_one_power_in_area_one_per_round_lost_fleet_exploration_board() {
    // GP_Exp_Rule_EN_V1_Web.pdf p.6, "Exploration Board": "For the Lantids, there is an
    // adjustment that relates to their income during the game: They gain 1 power in Area I."
    // A fresh bowl1 grant every round, on top of standard income, always enabled in this project.
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 0;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 1);
    assert_eq!(player.resources.power.bowl2, 0);
}

#[test]
fn round_tile_bonus_applies_vp_immediately_when_matched() {
    use gaia_engine::game_state::{PlacedStructure, Planet, RoundCondition, RoundTile};
    use gaia_engine::rules::actions::GameAction;

    let coord = HexCoord::new(1, 0);
    let anchor = HexCoord::new(0, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        coord,
        Hex {
            coord,
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
    hexes.insert(
        anchor,
        Hex {
            coord: anchor,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: gaia_engine::game_state::StructureType::Mine,
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

    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 10;
            p.resources.credits = 15;
            p.structures = vec![gaia_engine::game_state::Structure {
                hex: anchor,
                kind: gaia_engine::game_state::StructureType::Mine,
            }];
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.round_tiles[0] = RoundTile {
        id: 1,
        condition: RoundCondition::BuildMine,
        vp_per_unit: 3,
    };
    state.round = 1;
    let vp_before = state
        .player(0)
        .unwrap_or_else(|| panic!("player 0 exists"))
        .vp;

    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord })
        .unwrap_or_else(|e| panic!("build should be valid: {e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.vp, vp_before + 3);
}
