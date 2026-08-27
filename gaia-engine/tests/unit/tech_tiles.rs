// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), p.15, "Research Progress": "Tech tiles grant
// you various benefits, such as immediate resources or income... Whenever you gain a tech tile,
// you may advance in a research area... You can take any standard tech tile, except one you
// already own... Every upgrade follows these rules... Instead of taking a standard tech tile,
// you can take an advanced tech tile [if] your player token [is] on level 4 or 5 of the research
// area [it sits under]." Standard tile ids 2-10 are the base game's 9; 11-13 are the Lost Fleet
// expansion's Appendix V additions. Advanced tile ids are 1-22 (minus 18). Effects confirmed
// against `gaia-frontend/src/assets/tech_tiles/{standard,advanced,lost_fleet}/`.

use gaia_engine::game_state::{
    AdvancedTechTile, BoardState, FactionId, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure,
    Planet, PlanetType, ResearchTrack, Sector, SpaceshipBoard, SpaceshipId, Structure,
    StructureType, TechTile,
};
use gaia_engine::rules::actions::{GameAction, TechTileChoice, TechTileRef};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn board_with_mine() -> BoardState {
    let mine = HexCoord::new(0, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        mine,
        Hex {
            coord: mine,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: mine,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn tech_tiles_state(supply: Vec<u8>) -> gaia_engine::game_state::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.ore = 10;
            p.resources.credits = 10;
            p.resources.knowledge = 10;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
        })
        .with_player(1)
        .with_board(board_with_mine())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tiles = supply.into_iter().map(TechTile).collect();
    state
}

fn upgrade_action(tech_tile_choice: Option<TechTileChoice>) -> GameAction {
    GameAction::Upgrade {
        coord: HexCoord::new(0, 0),
        to: StructureType::TradingStation,
        tech_tile_choice,
    }
}

#[test]
fn upgrade_can_take_a_standard_tile_and_advance_a_research_track() {
    let mut state = tech_tiles_state(vec![4]); // std_04: immediately gain 1 ore + 1 QIC
    let ore_before = state.players[0].resources.ore;
    let qic_before = state.players[0].resources.qic;

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Standard {
            tile: TechTile(4),
            advance_track: Some(ResearchTrack::Terraforming),
            bonus_build_coord: None,
        })),
    )
    .unwrap_or_else(|e| panic!("upgrade with a tech tile choice should succeed: {e}"));

    assert!(state.players[0].tech_tiles.contains(&TechTile(4)));
    // Upgrade cost is 2 ore, the tile grants 1 ore + 1 QIC back.
    assert_eq!(state.players[0].resources.ore, ore_before - 2 + 1);
    assert_eq!(state.players[0].resources.qic, qic_before + 1);
    assert_eq!(state.players[0].research_tracks.terraforming, 1);
    assert!(events.iter().any(
        |e| matches!(e, GameEvent::TechTileGained { player: 0, tile } if *tile == TechTile(4))
    ));
}

#[test]
fn spaceship_standard_tech_requires_exploring_that_ship_and_is_removed_from_its_pile() {
    let spaceship_board = SpaceshipBoard {
        id: SpaceshipId::TFMars,
        explorers: vec![None; 4],
        artifact_pool: vec![],
        tech_tiles: vec![TechTile(12); 4],
        federation_token: None,
    };
    let choice = TechTileChoice::Standard {
        tile: TechTile(12),
        advance_track: None,
        bonus_build_coord: None,
    };

    let mut inaccessible = tech_tiles_state(vec![]);
    inaccessible.spaceship_boards = vec![spaceship_board.clone()];
    assert!(
        RuleEngine::apply_action(&mut inaccessible, 0, upgrade_action(Some(choice.clone())))
            .is_err()
    );

    let mut accessible = tech_tiles_state(vec![]);
    accessible.players[0].explored_ships.push(2); // T F Mars
    accessible.spaceship_boards = vec![spaceship_board];
    RuleEngine::apply_action(&mut accessible, 0, upgrade_action(Some(choice))).unwrap_or_else(
        |error| {
            panic!("an explored spaceship should make its Standard Tech pile available: {error}")
        },
    );

    assert!(accessible.players[0].tech_tiles.contains(&TechTile(12)));
    assert_eq!(accessible.spaceship_boards[0].tech_tiles.len(), 3);
}

#[test]
fn upgrade_rejects_a_tile_the_player_already_owns() {
    let mut state = tech_tiles_state(vec![4]);
    state.players[0].tech_tiles.push(TechTile(4));

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Standard {
            tile: TechTile(4),
            advance_track: None,
            bonus_build_coord: None,
        })),
    );
    assert!(result.is_err());
}

#[test]
fn upgrade_rejects_a_tile_not_in_the_supply() {
    let mut state = tech_tiles_state(vec![7]);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Standard {
            tile: TechTile(4),
            advance_track: None,
            bonus_build_coord: None,
        })),
    );
    assert!(result.is_err());
}

#[test]
fn upgrade_can_take_an_advanced_tile_only_at_level_4_or_5() {
    let mut state = tech_tiles_state(vec![]);
    state.research_board.advanced_tech_tiles[0] = Some(AdvancedTechTile(20)); // Terraforming slot
                                                                              // Taking an Advanced tile also requires an owned, uncovered Standard tile to cover, and a
                                                                              // green Federation token to flip.
    state.players[0].tech_tiles.push(TechTile(7));
    state.players[0]
        .federation_tokens
        .push(gaia_engine::game_state::FederationToken(1));

    let too_low = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Advanced {
            track: ResearchTrack::Terraforming,
            covered_tile: TechTile(7),
            advance_track: None,
        })),
    );
    assert!(too_low.is_err(), "level 0 should not be eligible");

    state.players[0].research_tracks.terraforming = 4;
    let knowledge_before = state.players[0].resources.knowledge;
    RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Advanced {
            track: ResearchTrack::Terraforming,
            covered_tile: TechTile(7),
            advance_track: None,
        })),
    )
    .unwrap_or_else(|e| panic!("level 4 should be eligible: {e}"));

    assert!(state.players[0]
        .advanced_tech_tiles
        .contains(&AdvancedTechTile(20)));
    assert!(state.research_board.advanced_tech_tiles[0].is_none());
    // adv_20's own special action isn't triggered by taking it (it's a "special action" tile,
    // not an immediate grant) — only the flat gain-3-knowledge action, used separately, would.
    assert_eq!(state.players[0].resources.knowledge, knowledge_before);
    // Taking the advanced tile flipped the green token to gray and covered the standard tile.
    assert!(state.players[0].federation_tokens.is_empty());
    assert_eq!(
        state.players[0].gray_federation_tokens,
        vec![gaia_engine::game_state::FederationToken(1)]
    );
    assert!(state.players[0].covered_tech_tiles.contains(&TechTile(7)));
}

#[test]
fn upgrade_cannot_take_an_advanced_tile_without_a_green_federation_token() {
    let mut state = tech_tiles_state(vec![]);
    state.research_board.advanced_tech_tiles[0] = Some(AdvancedTechTile(20));
    state.players[0].tech_tiles.push(TechTile(7));
    state.players[0].research_tracks.terraforming = 4;
    // No federation tokens owned at all.

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Advanced {
            track: ResearchTrack::Terraforming,
            covered_tile: TechTile(7),
            advance_track: None,
        })),
    );
    assert!(result.is_err());
}

#[test]
fn covered_standard_tile_stops_granting_its_ongoing_power_value_bonus() {
    // Tile 6: "Your large buildings have a power value of 4" — an ongoing effect, not a one-time
    // grant, so covering it should immediately stop it applying. Checked via the amount an
    // opponent may charge when building near the Planetary Institute (base power value 3).
    let pi = HexCoord::new(0, 0);
    let mine = HexCoord::new(2, 0); // player 0's own Mine, used to take the covering Advanced tile
    let target = HexCoord::new(1, 0); // player 1's Build target, within charge-power range of `pi`
    let mut hexes = HashMap::new();
    hexes.insert(
        pi,
        Hex {
            coord: pi,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::PlanetaryInstitute,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        mine,
        Hex {
            coord: mine,
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
        target,
        Hex {
            coord: target,
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
    // Player 1's own anchor Mine, adjacent to `target` so it's reachable, and within
    // charge-power range 2 of `pi`.
    let player1_anchor = HexCoord::new(2, 0);
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
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: pi,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.tech_tiles = vec![TechTile(6), TechTile(7)];
            p.federation_tokens = vec![gaia_engine::game_state::FederationToken(1)];
            p.research_tracks.terraforming = 4;
            p.structures = vec![
                Structure {
                    hex: pi,
                    kind: StructureType::PlanetaryInstitute,
                },
                Structure {
                    hex: mine,
                    kind: StructureType::Mine,
                },
            ];
        })
        .with_player_fn(1, |p| {
            p.resources.ore = 10;
            p.resources.credits = 10;
            p.structures = vec![Structure {
                hex: player1_anchor,
                kind: StructureType::Mine,
            }];
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 1 })
        .build();
    state.research_board.advanced_tech_tiles[0] = Some(AdvancedTechTile(20));

    // Player 1 builds near player 0's PI — with tile 6 active, PI power value is 4.
    RuleEngine::apply_action(&mut state, 1, GameAction::Build { coord: target })
        .unwrap_or_else(|e| panic!("build should succeed: {e}"));
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(
                queue[0].max_power, 4,
                "PI power value should be 4 with tile 6 active"
            );
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }
    RuleEngine::apply_action(&mut state, 0, GameAction::ChargePower { accept: false })
        .unwrap_or_else(|e| panic!("decline should succeed: {e}"));

    // Player 0 covers tile 6 by taking an Advanced tile via upgrading their Mine.
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Upgrade {
            coord: mine,
            to: StructureType::TradingStation,
            tech_tile_choice: Some(TechTileChoice::Advanced {
                track: ResearchTrack::Terraforming,
                covered_tile: TechTile(6),
                advance_track: None,
            }),
        },
    )
    .unwrap_or_else(|e| panic!("covering tile 6 should succeed: {e}"));
    assert!(state.players[0].covered_tech_tiles.contains(&TechTile(6)));

    // Player 1 builds near the PI again — tile 6 is now covered, so PI power value is back to 3.
    state.phase = GamePhase::ActionPhase { active_player: 1 };
    // Adjacent to `player1_anchor` (reachable) and within charge-power range 2 of `pi`.
    let target2 = HexCoord::new(2, -1);
    state.board.hexes.insert(
        target2,
        Hex {
            coord: target2,
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
    RuleEngine::apply_action(&mut state, 1, GameAction::Build { coord: target2 })
        .unwrap_or_else(|e| panic!("second build should succeed: {e}"));
    match &state.phase {
        GamePhase::ChargePowerPending { queue, .. } => {
            assert_eq!(
                queue[0].max_power, 3,
                "PI power value should be back to 3 once tile 6 is covered"
            );
        }
        other => panic!("expected ChargePowerPending, got {other:?}"),
    }
}

#[test]
fn income_tile_grants_resources_every_income_phase() {
    let mut state = tech_tiles_state(vec![]);
    // `apply_income_phase` skips players with no faction assigned entirely.
    state.players[0].faction = Some(FactionId::Terrans);
    state.players[0].tech_tiles.push(TechTile(3)); // std_03: income 4 credits
    let credits_before = state.players[0].resources.credits;
    state.phase = GamePhase::RoundScoring { round: 1 };

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.players[0].resources.credits, credits_before + 4);
}

#[test]
fn event_triggered_tile_scores_vp_when_its_condition_fires() {
    let target = HexCoord::new(1, 0);
    let mut board = board_with_mine();
    board.hexes.insert(
        target,
        Hex {
            coord: target,
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
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.ore = 10;
            p.resources.credits = 10;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
            p.advanced_tech_tiles = vec![AdvancedTechTile(4)]; // whenever build a mine, +3 VP
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    // Round 1's default test-fixture round tile also scores on BuildMine — swap it for an
    // unrelated condition so only the tech tile's own +3 VP is being measured here.
    state.round_tiles[0].condition = gaia_engine::game_state::RoundCondition::FormFederation;
    let vp_before = state.players[0].vp;

    let events = RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord: target })
        .unwrap_or_else(|e| panic!("build should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 3);
    assert!(events.iter().any(|e| matches!(
        e,
        GameEvent::VpAwarded {
            player: 0,
            amount: 3,
            ..
        }
    )));
}

#[test]
fn pass_time_tile_tallies_a_live_count() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    for coord in [a, b] {
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: Some(Planet {
                    planet_type: PlanetType::Asteroid,
                    is_gaia_formed: false,
                    owner: None,
                }),
                space_tile_kind: None,
                structures: vec![PlacedStructure {
                    owner: 0,
                    kind: StructureType::Mine,
                }],
                satellites: vec![],
            },
        );
    }
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: a,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.structures = vec![
                Structure {
                    hex: a,
                    kind: StructureType::Mine,
                },
                Structure {
                    hex: b,
                    kind: StructureType::Mine,
                },
            ];
            p.tech_tiles = vec![TechTile(14)]; // LF4: when you pass, 2 VP per asteroid colonized
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    let vp_before = state.players[0].vp;

    RuleEngine::apply_action(&mut state, 0, GameAction::Pass { booster_id: None })
        .unwrap_or_else(|e| panic!("pass should succeed: {e}"));

    assert_eq!(state.players[0].vp, vp_before + 4); // 2 asteroids * 2 VP
}

#[test]
fn power_value_tile_increases_federation_power_from_large_buildings() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    let mut hexes = HashMap::new();
    hexes.insert(
        a,
        Hex {
            coord: a,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::PlanetaryInstitute,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        b,
        Hex {
            coord: b,
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Academy(gaia_engine::game_state::AcademyType::Science),
            }],
            satellites: vec![],
        },
    );
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: a,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    let federation_state = |owns_tile_6: bool| {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.structures = vec![
                    Structure {
                        hex: a,
                        kind: StructureType::PlanetaryInstitute,
                    },
                    Structure {
                        hex: b,
                        kind: StructureType::Academy(gaia_engine::game_state::AcademyType::Science),
                    },
                ];
                if owns_tile_6 {
                    p.tech_tiles = vec![TechTile(6)];
                }
            })
            .with_player(1)
            .with_board(board.clone())
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        state.research_board.federation_tokens = vec![gaia_engine::game_state::FederationToken(1)];
        state
    };
    let hexes_vec = vec![a, b];

    let mut without_tile = federation_state(false);
    let result = RuleEngine::apply_action(
        &mut without_tile,
        0,
        GameAction::FormFederation {
            hexes: hexes_vec.clone(),
            satellite_hexes: vec![],
            token: gaia_engine::rules::actions::FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_err(),
        "3 (PI) + 3 (Academy) = 6 power without the tile should fall short of 7"
    );

    let mut with_tile = federation_state(true);
    let result = RuleEngine::apply_action(
        &mut with_tile,
        0,
        GameAction::FormFederation {
            hexes: hexes_vec,
            satellite_hexes: vec![],
            token: gaia_engine::rules::actions::FederationTokenChoice::Supply { kind: 1 },
            bonus_build_coord: None,
            bonus_tech_tile: None,
        },
    );
    assert!(
        result.is_ok(),
        "(3+1) + (3+1) = 8 power with the tile should clear the threshold: {result:?}"
    );
}

#[test]
fn special_action_tile_is_usable_once_per_round() {
    let mut state = tech_tiles_state(vec![]);
    state.players[0].tech_tiles.push(TechTile(10)); // std_10: as a special action, charge 4 power
    state.players[0].resources.power.bowl1 = 4;
    state.players[0].resources.power.bowl2 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TechTileSpecialAction {
            tile: TechTileRef::Standard { tile: TechTile(10) },
        },
    )
    .unwrap_or_else(|e| panic!("special action should succeed: {e}"));
    assert_eq!(state.players[0].resources.power.bowl1, 0);
    assert_eq!(state.players[0].resources.power.bowl2, 4);
    state.phase = GamePhase::ActionPhase { active_player: 0 };

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::TechTileSpecialAction {
            tile: TechTileRef::Standard { tile: TechTile(10) },
        },
    );
    assert!(result.is_err(), "already used this round");
}

#[test]
fn lost_fleet_free_build_mine_tile_requires_a_coord() {
    let target = HexCoord::new(1, 0);
    let mut board = board_with_mine();
    board.hexes.insert(
        target,
        Hex {
            coord: target,
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
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 10;
            p.resources.credits = 10;
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.tech_tiles = vec![TechTile(11)];

    let missing_coord = RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Standard {
            tile: TechTile(11),
            advance_track: None,
            bonus_build_coord: None,
        })),
    );
    assert!(missing_coord.is_err());

    let ore_before = state.players[0].resources.ore;
    RuleEngine::apply_action(
        &mut state,
        0,
        upgrade_action(Some(TechTileChoice::Standard {
            tile: TechTile(11),
            advance_track: None,
            bonus_build_coord: Some(target),
        })),
    )
    .unwrap_or_else(|e| panic!("free build mine should succeed: {e}"));

    assert!(state.players[0]
        .structures
        .iter()
        .any(|s| s.hex == target && s.kind == StructureType::Mine));
    // Target is the player's own home planet type (Terra), so terraforming distance is 0 either
    // way — this only confirms the flat 1-ore Mine build cost applied, not the free-step waiver
    // itself (a distance-1+ target would be needed for that, and isn't essential here). The
    // enclosing Upgrade itself also costs 2 ore (Mine -> Trading Station), so total ore spent is
    // 2 (upgrade) + 1 (the tile's free mine build) = 3.
    assert_eq!(state.players[0].resources.ore, ore_before - 3);
}

#[test]
fn lost_fleet_range_tile_extends_basic_navigation_range() {
    // Nav level 0 = basic range 1; the target is 2 hexes away and the player has no QIC to pay
    // for range extension, so this is only reachable with tile 12's permanent +1.
    let anchor = HexCoord::new(0, 0);
    let target = HexCoord::new(2, 0);
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
        target,
        Hex {
            coord: target,
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
    // Reachability is a BFS through hexes that actually exist on the board, not raw geometric
    // distance — the stepping-stone hex between anchor and target must be present too.
    let stepping_stone = HexCoord::new(1, 0);
    hexes.insert(
        stepping_stone,
        Hex {
            coord: stepping_stone,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
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
    let state_with = |owns_tile_12: bool| {
        GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.resources.ore = 10;
                p.resources.credits = 10;
                p.resources.qic = 0;
                p.structures = vec![Structure {
                    hex: anchor,
                    kind: StructureType::Mine,
                }];
                if owns_tile_12 {
                    p.tech_tiles = vec![TechTile(12)];
                }
            })
            .with_player(1)
            .with_board(board.clone())
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build()
    };

    let mut without_tile = state_with(false);
    let result =
        RuleEngine::apply_action(&mut without_tile, 0, GameAction::Build { coord: target });
    assert!(
        result.is_err(),
        "distance 2 at basic range 1 with no QIC should be out of reach"
    );

    let mut with_tile = state_with(true);
    let result = RuleEngine::apply_action(&mut with_tile, 0, GameAction::Build { coord: target });
    assert!(
        result.is_ok(),
        "tile 12's +1 range should make distance 2 reachable: {result:?}"
    );
}
