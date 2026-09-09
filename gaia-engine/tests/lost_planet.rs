use gaia_engine::game_state::{
    BoardState, FederationToken, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, ResearchTrack, Sector, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{RuleEngine, RuleError};
use std::collections::HashMap;

fn lost_planet_state(qic: u8) -> gaia_engine::GameState {
    let mut hexes = HashMap::new();
    for q in 0..=7 {
        hexes.insert(
            HexCoord::new(q, 0),
            Hex {
                coord: HexCoord::new(q, 0),
                planet: None,
                space_tile_kind: None,
                structures: vec![],
                satellites: vec![],
            },
        );
    }
    let home = HexCoord::new(0, 0);
    let opponent_home = HexCoord::new(6, 0);
    for (coord, owner) in [(home, 0), (opponent_home, 1)] {
        let hex = hexes.get_mut(&coord).unwrap_or_else(|| unreachable!());
        hex.planet = Some(Planet {
            planet_type: if owner == 0 {
                PlanetType::Terra
            } else {
                PlanetType::Ice
            },
            is_gaia_formed: false,
            owner: Some(owner),
        });
        hex.structures.push(PlacedStructure {
            owner,
            kind: StructureType::Mine,
        });
    }

    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.research_tracks.navigation = 4;
            player.resources.knowledge = 4;
            player.resources.qic = qic;
            player.federation_tokens.push(FederationToken(1));
            player.structures.push(Structure {
                hex: home,
                kind: StructureType::Mine,
            });
        })
        .with_player_fn(1, |player| {
            player.structures.push(Structure {
                hex: opponent_home,
                kind: StructureType::Mine,
            });
        })
        .with_board(BoardState {
            sectors: vec![Sector {
                id: 1,
                rotation: 0,
                origin: HexCoord::new(3, 0),
            }],
            hexes,
            lost_planet: None,
            spaceship_tiles: HashMap::new(),
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn navigation_five_requires_and_resolves_lost_planet_before_play_continues() {
    let mut state = lost_planet_state(1);

    let research_events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    )
    .unwrap_or_else(|error| panic!("Navigation advance failed: {error}"));

    assert!(research_events.iter().any(|event| matches!(
        event,
        GameEvent::ResearchAdvanced {
            player: 0,
            track: ResearchTrack::Navigation,
            level: 5,
        }
    )));
    assert!(matches!(
        state.phase,
        GamePhase::LostPlanetPlacementPending { player: 0, .. }
    ));
    assert!(RuleEngine::get_valid_actions(&state, 1).is_empty());
    assert!(matches!(
        RuleEngine::apply_action(&mut state, 0, GameAction::Pass { booster_id: None }),
        Err(RuleError::ActionNotAllowed(_))
    ));

    let target = HexCoord::new(5, 0);
    let placement_events =
        RuleEngine::apply_action(&mut state, 0, GameAction::PlaceLostPlanet { coord: target })
            .unwrap_or_else(|error| panic!("Lost Planet placement failed: {error}"));

    assert!(placement_events.iter().any(|event| matches!(
        event,
        GameEvent::LostPlanetPlaced { player: 0, hex } if *hex == target
    )));
    assert_eq!(state.board.lost_planet, Some(target));
    let target_hex = state
        .board
        .hexes
        .get(&target)
        .unwrap_or_else(|| unreachable!());
    assert!(target_hex.planet.as_ref().is_some_and(|planet| {
        planet.planet_type == PlanetType::LostPlanet && planet.owner == Some(0)
    }));
    assert_eq!(target_hex.satellites, vec![0]);
    assert!(state
        .player(0)
        .is_some_and(|player| player.resources.qic == 0 && player.structures.len() == 1));
    assert!(matches!(
        state.phase,
        GamePhase::LostPlanetChargePowerPending { ref queue, .. }
            if queue.first().is_some_and(|entry| entry.player == 1 && entry.hex == target)
    ));

    RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: false })
        .unwrap_or_else(|error| panic!("charge decision failed: {error}"));
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 1 });
}

#[test]
fn lost_planet_rejects_occupied_out_of_range_and_wrong_phase_targets() {
    let mut state = lost_planet_state(0);
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Navigation,
        },
    )
    .unwrap_or_else(|error| panic!("Navigation advance failed: {error}"));

    assert!(matches!(
        RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::PlaceLostPlanet {
                coord: HexCoord::new(6, 0),
            },
        ),
        Err(RuleError::TargetOccupied(_))
    ));
    assert!(matches!(
        RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::PlaceLostPlanet {
                coord: HexCoord::new(5, 0),
            },
        ),
        Err(RuleError::OutOfRange { .. })
    ));

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PlaceLostPlanet {
            coord: HexCoord::new(4, 0),
        },
    )
    .unwrap_or_else(|error| panic!("in-range placement failed: {error}"));
    assert!(matches!(
        RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::PlaceLostPlanet {
                coord: HexCoord::new(3, 0),
            },
        ),
        Err(RuleError::WrongPhase)
    ));
}
