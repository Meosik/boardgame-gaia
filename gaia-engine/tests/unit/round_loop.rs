use gaia_engine::error::RuleError;
use gaia_engine::game_state::{
    BoardState, FactionId, GamePhase, Hex, HexCoord, Planet, PlanetType, ResearchTrack, Sector,
};
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

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.round, 3);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
    assert!(!state.players[0].passed);
    assert!(!state.players[1].passed);
}

#[test]
fn gaia_phase_completes_owned_transdim_planets() {
    let coord = HexCoord::new(0, 0);
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_board(empty_board_with_transdim(coord, Some(0)))
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    let planet = state
        .board
        .hexes
        .get(&coord)
        .and_then(|h| h.planet.as_ref())
        .unwrap_or_else(|| panic!("planet exists"));
    assert!(planet.is_gaia_formed);
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
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
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
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
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
