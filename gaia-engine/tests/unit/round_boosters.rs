use gaia_engine::game_state::{
    BoardState, Booster, FactionId, GameEvent, GamePhase, Hex, HexCoord, PlacedStructure, Planet,
    PlanetType, Sector, SpaceshipBoard, SpaceshipId, Structure, StructureType, VpReason,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

fn income_state(booster: Option<u8>) -> gaia_engine::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.booster = booster.map(Booster);
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build()
}

#[test]
fn booster_income_is_added_during_round_transition() {
    let mut control = income_state(None);
    let mut boosted = income_state(Some(13));

    RuleEngine::advance_to_next_round(&mut control).unwrap_or_else(|error| panic!("{error}"));
    RuleEngine::advance_to_next_round(&mut boosted).unwrap_or_else(|error| panic!("{error}"));

    let control = control
        .player(0)
        .unwrap_or_else(|| panic!("control player"));
    let boosted = boosted
        .player(0)
        .unwrap_or_else(|| panic!("boosted player"));
    assert_eq!(boosted.resources.ore, control.resources.ore + 1);
    assert_eq!(boosted.resources.knowledge, control.resources.knowledge + 1);
}

#[test]
fn booster_income_is_applied_when_the_first_round_starts() {
    let mut control = income_state(None);
    control.phase = GamePhase::Setup(gaia_engine::game_state::SetupPhase::Complete);
    let mut boosted = income_state(Some(13));
    boosted.phase = GamePhase::Setup(gaia_engine::game_state::SetupPhase::Complete);

    RuleEngine::start_first_round(&mut control).unwrap_or_else(|error| panic!("{error}"));
    RuleEngine::start_first_round(&mut boosted).unwrap_or_else(|error| panic!("{error}"));

    let control = control
        .player(0)
        .unwrap_or_else(|| panic!("control player"));
    let boosted = boosted
        .player(0)
        .unwrap_or_else(|| panic!("boosted player"));
    assert_eq!(boosted.resources.ore, control.resources.ore + 1);
    assert_eq!(boosted.resources.knowledge, control.resources.knowledge + 1);
}

#[test]
fn passing_scores_owned_booster_and_swaps_with_available_pool() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.booster = Some(Booster(3));
            player.structures = (0..3)
                .map(|q| Structure {
                    hex: HexCoord::new(q, 0),
                    kind: StructureType::Mine,
                })
                .collect();
            player.artifact_mines = vec![PlanetType::ProtoPlanet, PlanetType::Asteroid];
        })
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.boosters = vec![Booster(8), Booster(9), Booster(10)];

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Pass {
            booster_id: Some(8),
        },
    )
    .unwrap_or_else(|error| panic!("{error}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player"));
    assert_eq!(player.vp, 15);
    assert_eq!(player.booster, Some(Booster(8)));
    assert!(state.boosters.contains(&Booster(3)));
    assert!(!state.boosters.contains(&Booster(8)));
    assert!(events.iter().any(|event| matches!(
        event,
        GameEvent::VpAwarded {
            player: 0,
            amount: 5,
            reason: VpReason::RoundBooster { booster_id: 3 }
        }
    )));
}

#[test]
fn booster_five_charges_power_instead_of_adding_fresh_tokens() {
    let mut control = income_state(None);
    let mut boosted = income_state(Some(5));

    RuleEngine::advance_to_next_round(&mut control).unwrap_or_else(|error| panic!("{error}"));
    RuleEngine::advance_to_next_round(&mut boosted).unwrap_or_else(|error| panic!("{error}"));

    let control = &control
        .player(0)
        .unwrap_or_else(|| panic!("control player"))
        .resources
        .power;
    let boosted = &boosted
        .player(0)
        .unwrap_or_else(|| panic!("boosted player"))
        .resources
        .power;
    assert_eq!(
        boosted.total(),
        control.total(),
        "charging must not create power tokens"
    );
    assert_eq!(boosted.bowl1 + 2, control.bowl1);
    assert_eq!(boosted.bowl2, control.bowl2 + 2);
    assert_eq!(boosted.bowl3, control.bowl3);
}

#[test]
fn owned_booster_requires_a_replacement_before_final_round() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |player| player.booster = Some(Booster(1)))
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();

    let result = RuleEngine::validate_action(&state, 0, &GameAction::Pass { booster_id: None });
    assert!(result.is_err());
}

#[test]
fn final_round_returns_booster_without_choosing_a_new_one() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| player.booster = Some(Booster(7)))
        .with_round(6)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::Pass { booster_id: None })
        .unwrap_or_else(|error| panic!("{error}"));

    assert_eq!(
        state.player(0).and_then(|player| player.booster.clone()),
        None
    );
    assert!(state.boosters.contains(&Booster(7)));
}

fn booster_gaia_state(booster_id: u8, target: HexCoord) -> gaia_engine::GameState {
    let anchor = HexCoord::new(0, 0);
    let mut hexes = HashMap::new();
    for q in 0..=target.q {
        let coord = HexCoord::new(q, 0);
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: if coord == target {
                    Some(Planet {
                        planet_type: PlanetType::Transdim,
                        is_gaia_formed: false,
                        owner: None,
                    })
                } else if coord == anchor {
                    Some(Planet {
                        planet_type: PlanetType::Terra,
                        is_gaia_formed: false,
                        owner: Some(0),
                    })
                } else {
                    None
                },
                space_tile_kind: None,
                structures: if coord == anchor {
                    vec![PlacedStructure {
                        owner: 0,
                        kind: StructureType::Mine,
                    }]
                } else {
                    vec![]
                },
                satellites: vec![],
            },
        );
    }
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
    GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.booster = Some(Booster(booster_id));
            player.structures = vec![Structure {
                hex: anchor,
                kind: StructureType::Mine,
            }];
            player.research_tracks.gaia = 1;
            player.resources.power.bowl3 = 10;
            player.resources.qic = 0;
            player.gaiaformers_total = 1;
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn booster_five_immediately_completes_gaiaforming_and_keeps_the_gaiaformer() {
    let target = HexCoord::new(1, 0);
    let mut state = booster_gaia_state(5, target);
    state.players[0].research_tracks.gaia = 0;
    state.players[0].resources.power.bowl3 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterImmediateGaiaFormation { coord: target },
    )
    .unwrap_or_else(|error| panic!("round booster 5 should immediately gaiaform: {error}"));

    let planet = state.board.hexes[&target]
        .planet
        .as_ref()
        .unwrap_or_else(|| panic!("target planet"));
    assert!(planet.is_gaia_formed);
    assert_eq!(planet.owner, Some(0));
    assert_eq!(state.players[0].gaiaformers_deployed, 1);
    assert_eq!(state.players[0].gaiaformers_available(), 0);
    assert!(state.players[0].round_booster_special_action_used_this_round);
}

#[test]
fn booster_eight_adds_three_range_to_gaiaforming_and_shares_one_action_space() {
    let target = HexCoord::new(4, 0);
    let mut state = booster_gaia_state(8, target);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeGaiaFormation { coord: target },
    )
    .unwrap_or_else(|error| panic!("round booster 8 +3 range should reach target: {error}"));

    let planet = state.board.hexes[&target]
        .planet
        .as_ref()
        .unwrap_or_else(|| panic!("target planet"));
    assert!(!planet.is_gaia_formed);
    assert_eq!(planet.owner, Some(0));
    assert_eq!(state.players[0].gaiaformers_deployed, 1);
    assert!(state.players[0].round_booster_special_action_used_this_round);

    state.phase = GamePhase::ActionPhase { active_player: 0 };
    let second_mode = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeBuild { coord: target },
    );
    assert!(second_mode.is_err());
}

fn empty_spaceship_board(id: SpaceshipId) -> SpaceshipBoard {
    SpaceshipBoard {
        id,
        explorers: vec![None; 4],
        artifact_pool: vec![],
        tech_tiles: vec![],
        federation_token: None,
    }
}

fn booster_spaceship_state(booster: Option<u8>, ship: SpaceshipId) -> gaia_engine::GameState {
    let anchor = HexCoord::new(0, 0);
    let ship_coord = HexCoord::new(4, 0);
    let mut hexes = HashMap::new();
    for q in 0..=ship_coord.q {
        let coord = HexCoord::new(q, 0);
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: if coord == anchor {
                    vec![PlacedStructure {
                        owner: 0,
                        kind: StructureType::Mine,
                    }]
                } else {
                    vec![]
                },
                satellites: vec![],
            },
        );
    }
    let mut spaceship_tiles = HashMap::new();
    spaceship_tiles.insert(ship, ship_coord);
    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: anchor,
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles,
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.booster = booster.map(Booster);
            player.structures = vec![Structure {
                hex: anchor,
                kind: StructureType::Mine,
            }];
            player.resources.qic = 0;
            player.vp = 10;
        })
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.spaceship_boards = SpaceshipId::all()
        .into_iter()
        .map(empty_spaceship_board)
        .collect();
    state
}

#[test]
fn round_booster_special_action_resets_during_cleanup() {
    for booster in [5, 8, 12] {
        let mut state = income_state(Some(booster));
        state.players[0].round_booster_special_action_used_this_round = true;
        RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("{error}"));
        assert!(!state.players[0].round_booster_special_action_used_this_round);
    }
}

#[test]
fn round_booster_eight_explores_spaceship_with_plus_three_range() {
    let mut state = booster_spaceship_state(Some(8), SpaceshipId::Twilight);

    let normal_result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    );
    assert!(
        normal_result.is_err(),
        "distance 4 is out of base range without QIC"
    );

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    )
    .unwrap_or_else(|error| panic!("round booster 8 should explore at +3 range: {error}"));

    assert!(state.players[0].explored_ships.contains(&0));
    assert_eq!(state.players[0].exploration_shuttles_available, 2);
    assert_eq!(state.players[0].vp, 5);
    assert!(state.players[0].round_booster_special_action_used_this_round);
}

#[test]
fn round_booster_eight_explore_spaceship_rejects_when_not_owned() {
    let mut state = booster_spaceship_state(None, SpaceshipId::Twilight);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeExploreSpaceship {
            ship: SpaceshipId::Twilight,
        },
    );

    assert!(result.is_err());
}

#[test]
fn round_booster_eight_explore_spaceship_rejects_after_shared_special_used() {
    let target = HexCoord::new(4, 0);
    let mut state = booster_gaia_state(8, target);
    state.players[0].round_booster_special_action_used_this_round = true;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeGaiaFormation { coord: target },
    );

    assert!(
        result.is_err(),
        "booster 8 modes share one once-per-round flag"
    );
}

#[test]
fn round_booster_eight_range_build_rejects_when_booster_not_owned() {
    let target = HexCoord::new(1, 0);
    let mut state = booster_gaia_state(5, target);
    let Some(target_hex) = state.board.hexes.get_mut(&target) else {
        panic!("the booster test target exists");
    };
    target_hex.planet = Some(Planet {
        planet_type: PlanetType::Terra,
        is_gaia_formed: false,
        owner: None,
    });

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeBuild { coord: target },
    );

    assert!(result.is_err());
}

#[test]
fn round_booster_eight_range_gaia_formation_rejects_when_booster_not_owned() {
    let target = HexCoord::new(4, 0);
    let mut state = booster_gaia_state(5, target);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::RoundBoosterRangeGaiaFormation { coord: target },
    );

    assert!(result.is_err());
}

fn booster_twelve_state(target: HexCoord, planet_type: PlanetType) -> gaia_engine::GameState {
    let mut state = booster_gaia_state(12, target);
    let player = &mut state.players[0];
    player.faction = Some(FactionId::Terrans);
    player.resources.ore = 15;
    player.resources.credits = 10;
    player.resources.qic = 5;
    player.research_tracks.terraforming = 0;
    player.research_tracks.navigation = 0;
    state
        .board
        .hexes
        .get_mut(&target)
        .unwrap_or_else(|| panic!("target"))
        .planet
        .as_mut()
        .unwrap_or_else(|| panic!("planet"))
        .planet_type = planet_type;
    state
}

fn booster_twelve_action(coord: HexCoord) -> GameAction {
    serde_json::from_value(serde_json::json!({
        "type": "RoundBoosterTerraformBuild", "coord": coord,
    }))
    .unwrap_or_else(|error| panic!("booster 12 wire action must exist: {error}"))
}

#[test]
fn booster_twelve_discounts_one_step_but_always_pays_normal_mine_cost() {
    let target = HexCoord::new(1, 0);
    // Terrans: Oxide is one step, Volcanic two; ProtoPlanet always needs three.
    for (planet, ore_cost) in [
        (PlanetType::Terra, 1),
        (PlanetType::Oxide, 1),
        (PlanetType::Volcanic, 4),
        (PlanetType::ProtoPlanet, 7),
    ] {
        let mut state = booster_twelve_state(target, planet);
        let power = state.players[0].resources.power.clone();
        let events = RuleEngine::apply_action(&mut state, 0, booster_twelve_action(target))
            .unwrap_or_else(|error| panic!("{planet:?}: {error}"));
        assert_eq!(state.players[0].resources.ore, 15 - ore_cost);
        assert_eq!(state.players[0].resources.credits, 8);
        assert_eq!(state.players[0].resources.qic, 5);
        assert_eq!(
            state.players[0].resources.power, power,
            "no activation power cost"
        );
        assert!(state.players[0].round_booster_special_action_used_this_round);
        assert!(events.iter().any(|event| matches!(event,
            GameEvent::StructureBuilt { player: 0, hex, .. } if *hex == target)));
        assert_eq!(
            state.board.hexes[&target].structures[0].kind,
            StructureType::Mine
        );
    }
}

#[test]
fn booster_twelve_rejects_unpaid_mine_or_extra_terraforming_without_mutation() {
    let target = HexCoord::new(1, 0);
    for (planet, ore, credits) in [
        (PlanetType::Oxide, 0, 2),
        (PlanetType::Oxide, 1, 1),
        (PlanetType::Volcanic, 3, 2),
    ] {
        let mut state = booster_twelve_state(target, planet);
        state.players[0].resources.ore = ore;
        state.players[0].resources.credits = credits;
        let before = state.serialize();
        assert!(RuleEngine::apply_action(&mut state, 0, booster_twelve_action(target)).is_err());
        assert_eq!(state.serialize(), before);
    }
}

#[test]
fn booster_twelve_pays_range_and_natural_gaia_entry_qic() {
    // Base range 1; distance 3 needs one QIC. Natural Gaia also needs an entry QIC.
    let target = HexCoord::new(3, 0);
    for (planet, qic_cost) in [(PlanetType::Oxide, 1), (PlanetType::Gaia, 2)] {
        let mut state = booster_twelve_state(target, planet);
        state.players[0].resources.qic = qic_cost - 1;
        let before = state.serialize();
        assert!(RuleEngine::apply_action(&mut state, 0, booster_twelve_action(target)).is_err());
        assert_eq!(state.serialize(), before);
        state.players[0].resources.qic = qic_cost;
        RuleEngine::apply_action(&mut state, 0, booster_twelve_action(target))
            .unwrap_or_else(|error| panic!("{error}"));
        assert_eq!(state.players[0].resources.qic, 0);
        assert_eq!(state.players[0].resources.ore, 14);
        assert_eq!(state.players[0].resources.credits, 8);
    }
}

#[test]
fn booster_twelve_requires_ownership_unused_action_and_legal_target() {
    let target = HexCoord::new(1, 0);
    for (booster, used, planet) in [
        (None, false, PlanetType::Oxide),
        (Some(8), false, PlanetType::Oxide),
        (Some(12), true, PlanetType::Oxide),
        (Some(12), false, PlanetType::Transdim),
    ] {
        let mut state = booster_twelve_state(target, planet);
        state.players[0].booster = booster.map(Booster);
        state.players[0].round_booster_special_action_used_this_round = used;
        let before = state.serialize();
        let action = booster_twelve_action(target);
        assert!(!RuleEngine::get_valid_actions(&state, 0).contains(&action));
        assert!(RuleEngine::apply_action(&mut state, 0, action).is_err());
        assert_eq!(state.serialize(), before);
    }
}

#[test]
fn booster_twelve_is_an_ai_candidate_even_when_normal_terraforming_is_unaffordable() {
    use gaia_engine::rules::engine::AiDecision;
    let target = HexCoord::new(1, 0);
    let mut state = booster_twelve_state(target, PlanetType::Oxide);
    state.players[0].resources.ore = 1;
    state.players[0].resources.credits = 2;
    let before = state.serialize();
    let action = booster_twelve_action(target);
    assert!(RuleEngine::get_valid_actions(&state, 0).contains(&action));
    let candidates = RuleEngine::ai_decisions(&state).unwrap_or_else(|error| panic!("{error}"));
    assert!(candidates.contains(&AiDecision::Game(action.clone())));
    assert!(!candidates.contains(&AiDecision::Game(GameAction::Build { coord: target })));
    assert_eq!(state.serialize(), before);
    RuleEngine::apply_action(&mut state, 0, action).unwrap_or_else(|error| panic!("{error}"));
    assert_eq!(state.players[0].resources.ore, 0);
    assert_eq!(state.players[0].resources.credits, 0);
}

#[test]
fn booster_twelve_still_receives_two_credit_income() {
    let mut control = income_state(None);
    let mut boosted = income_state(Some(12));
    RuleEngine::advance_to_next_round(&mut control).unwrap_or_else(|error| panic!("{error}"));
    RuleEngine::advance_to_next_round(&mut boosted).unwrap_or_else(|error| panic!("{error}"));
    assert_eq!(
        boosted.players[0].resources.credits,
        control.players[0].resources.credits + 2
    );
}
