use gaia_engine::game_state::{
    BoardState, FederationToken, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType,
    ResearchTrack, Sector, Structure, StructureType, TechTile,
};
use gaia_engine::rules::actions::{GameAction, TechTileChoice};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn charge_order_state() -> gaia_engine::game_state::GameState {
    let lab = HexCoord::new(0, 0);
    let bonus_mine = HexCoord::new(1, 0);
    let neighbor = HexCoord::new(0, 1);
    let mut hexes = HashMap::new();
    for (coord, planet_type, structure) in [
        (
            lab,
            PlanetType::Terra,
            Some((0, StructureType::TradingStation)),
        ),
        (bonus_mine, PlanetType::Volcanic, None),
        (neighbor, PlanetType::Desert, Some((1, StructureType::Mine))),
    ] {
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: Some(Planet {
                    planet_type,
                    is_gaia_formed: false,
                    owner: structure.map(|(owner, _)| owner),
                }),
                space_tile_kind: None,
                structures: structure
                    .map(|(owner, kind)| vec![PlacedStructure { owner, kind }])
                    .unwrap_or_default(),
                satellites: vec![],
            },
        );
    }
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: lab,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(gaia_engine::game_state::FactionId::Terrans);
            player.resources.ore = 10;
            player.resources.credits = 10;
            player.structures = vec![Structure {
                hex: lab,
                kind: StructureType::TradingStation,
            }];
        })
        .with_player_fn(1, |player| {
            player.vp = 10;
            player.structures = vec![Structure {
                hex: neighbor,
                kind: StructureType::Mine,
            }];
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tiles = vec![TechTile(11)];
    state
}

// LF2-14: upgrading the lab should offer its charge first, then the free mine's charge.
#[test]
fn lab_charge_precedes_lost_fleet_free_mine_charge() {
    let mut state = charge_order_state();
    let upgrade = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            coord: HexCoord::new(0, 0),
            to: StructureType::ResearchLab,
            tech_tile_choice: Some(TechTileChoice::Standard {
                tile: TechTile(11),
                advance_track: Some(ResearchTrack::Navigation),
                bonus_build_coord: Some(HexCoord::new(1, 0)),
            }),
        },
    );
    assert!(
        upgrade.is_ok(),
        "lab upgrade and free mine must be legal: {upgrade:?}"
    );
    assert_eq!(state.players[0].research_tracks.navigation, 1);
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(
                queue[0].hex,
                HexCoord::new(0, 0),
                "lab charge must be first"
            );
            // The charging opponent owns a Mine: both offers are one power.
            assert_eq!(queue[0].max_power, 1);
        }
        other => panic!("expected lab charge, got {other:?}"),
    }
    let saved = serde_json::to_string(&state).unwrap_or_else(|error| panic!("{error}"));
    state = serde_json::from_str(&saved).unwrap_or_else(|error| panic!("{error}"));
    let decline =
        RuleEngine::apply_action(&mut state, 1, GameAction::ChargePower { accept: false });
    assert!(
        decline.is_ok(),
        "opponent should be able to decline the lab charge: {decline:?}"
    );
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(queue[0].hex, HexCoord::new(1, 0), "mine charge must follow");
            assert_eq!(queue[0].max_power, 1);
        }
        other => panic!("expected subsequent mine charge, got {other:?}"),
    }
}

fn level_five_state(token: u8) -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.resources.knowledge = 10;
            player.research_tracks.terraforming = 4;
            player.federation_tokens = vec![FederationToken(token)];
        })
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn lost_fleet_twelve_vp_token_can_be_flipped_for_level_five() {
    let mut state = level_five_state(9);
    let advance = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(
        advance.is_ok(),
        "Lost Fleet 12-VP token has a green side: {advance:?}"
    );
    assert_eq!(state.players[0].research_tracks.terraforming, 5);
    assert!(state.players[0].federation_tokens.is_empty());
    assert_eq!(
        state.players[0].gray_federation_tokens,
        vec![FederationToken(9)]
    );
}

// LF3-10: the base-game 12-VP token has no green side, unlike the Lost Fleet token.
#[test]
fn base_twelve_vp_token_cannot_be_flipped_for_level_five() {
    let mut state = level_five_state(1);
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(
        result.is_err(),
        "base 12-VP token must not satisfy the green-token cost"
    );
}

#[test]
fn flipping_a_green_token_preserves_a_base_twelve_vp_token_on_top() {
    let mut state = level_five_state(9);
    state.players[0].federation_tokens.push(FederationToken(1));
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    )
    .unwrap_or_else(|error| panic!("green Lost Fleet token must be usable: {error}"));
    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(1)]);
    assert_eq!(state.players[0].gray_federation_tokens, vec![FederationToken(9)]);
}

#[test]
fn saved_base_twelve_vp_token_does_not_become_green_after_reload() {
    let state = level_five_state(1);
    let saved = serde_json::to_string(&state).unwrap_or_else(|error| panic!("{error}"));
    let mut loaded = serde_json::from_str(&saved).unwrap_or_else(|error| panic!("{error}"));
    let result = RuleEngine::apply_action(
        &mut loaded,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(result.is_err());
    assert_eq!(loaded.players[0].federation_tokens, vec![FederationToken(1)]);
    assert_eq!(loaded.players[0].research_tracks.terraforming, 4);
}
