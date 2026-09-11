use gaia_engine::game_state::{
    Booster, FactionId, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType, Structure,
    StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{GameState, RuleEngine};

fn gaia_state(faction: FactionId, distance: i32, qic: u8) -> GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(faction);
            player.resources.ore = 7;
            player.resources.credits = 17;
            player.resources.qic = qic;
            player.booster = Some(Booster(8));
            player.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
        })
        .with_player(1)
        .with_round(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    for q in 0..=distance {
        let coord = HexCoord::new(q, 0);
        state.board.hexes.insert(
            coord,
            Hex {
                coord,
                planet: (q == distance).then_some(Planet {
                    planet_type: PlanetType::Gaia,
                    is_gaia_formed: false,
                    owner: None,
                }),
                space_tile_kind: None,
                structures: if q == 0 {
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
    state
}

fn assert_rejected_without_mutation(state: &mut GameState, action: GameAction) {
    let before = serde_json::to_value(&*state).unwrap_or_else(|error| panic!("test value should serialize: {error}"));
    assert!(RuleEngine::validate_action(state, 0, &action).is_err());
    assert!(RuleEngine::apply_action(state, 0, action).is_err());
    assert_eq!(serde_json::to_value(&*state).unwrap_or_else(|error| panic!("test value should serialize: {error}")), before);
}

#[test]
fn natural_gaia_requires_and_spends_entry_qic() {
    let coord = HexCoord::new(1, 0);
    let mut state = gaia_state(FactionId::HadschHallas, 1, 0);
    assert_rejected_without_mutation(&mut state, GameAction::Build { coord });
    state.players[0].resources.qic = 1;
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(state.players[0].resources.qic, 0);
    assert_eq!(state.players[0].resources.ore, 6);
    assert_eq!(state.players[0].resources.credits, 15);
}

#[test]
fn natural_gaia_entry_is_added_to_range_qic_with_and_without_booster() {
    // HH 137-point replay, action 16: distance 6, base range 1 + booster 3,
    // one range QIC and one Gaia-entry QIC. Owning only one must not suffice.
    for distance in [3, 6] {
        let coord = HexCoord::new(distance, 0);
        let action = if distance == 6 {
            GameAction::RoundBoosterRangeBuild { coord }
        } else {
            GameAction::Build { coord }
        };
        let mut state = gaia_state(FactionId::HadschHallas, distance, 1);
        assert!(!RuleEngine::get_valid_actions(&state, 0).contains(&action));
        assert_rejected_without_mutation(&mut state, action.clone());
        state.players[0].resources.qic = 2;
        assert!(RuleEngine::get_valid_actions(&state, 0).contains(&action));
        RuleEngine::apply_action(&mut state, 0, action).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        assert_eq!(state.players[0].resources.qic, 0);
        assert_eq!(state.players[0].resources.ore, 6);
        assert_eq!(state.players[0].resources.credits, 15);
        assert_eq!(
            state.players[0].round_booster_special_action_used_this_round,
            distance == 6
        );
    }
}

#[test]
fn natural_gaia_honors_two_qic_faction_costs() {
    for faction in [
        FactionId::Darkanians,
        FactionId::SpaceGiants,
        FactionId::Tinkeroids,
        FactionId::Moweyds,
    ] {
        let mut state = gaia_state(faction, 1, 1);
        let action = GameAction::Build {
            coord: HexCoord::new(1, 0),
        };
        assert_rejected_without_mutation(&mut state, action.clone());
        state.players[0].resources.qic = 2;
        RuleEngine::apply_action(&mut state, 0, action).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        assert_eq!(state.players[0].resources.qic, 0, "{faction:?}");
    }
}

#[test]
fn gleens_natural_gaia_pays_ore_instead_of_entry_qic_but_still_pays_for_range() {
    let coord = HexCoord::new(3, 0);
    let mut state = gaia_state(FactionId::Gleens, 3, 0);
    let action = GameAction::Build { coord };
    assert_rejected_without_mutation(&mut state, action.clone());
    state.players[0].resources.qic = 1;
    state.players[0].resources.ore = 1;
    assert_rejected_without_mutation(&mut state, action.clone());
    state.players[0].resources.ore = 2;
    RuleEngine::apply_action(&mut state, 0, action).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(state.players[0].resources.ore, 0);
    assert_eq!(state.players[0].resources.qic, 0);
}

#[test]
fn own_completed_gaia_project_keeps_entry_exemption_and_returns_former() {
    let coord = HexCoord::new(1, 0);
    let mut state = gaia_state(FactionId::HadschHallas, 1, 0);
    let planet = state
        .board
        .hexes
        .get_mut(&coord)
        .unwrap_or_else(|| panic!("fixture hex should exist"))
        .planet
        .as_mut()
        .unwrap_or_else(|| panic!("fixture planet should exist"));
    planet.planet_type = PlanetType::Transdim;
    planet.is_gaia_formed = true;
    planet.owner = Some(0);
    state.players[0].gaiaformers_total = 1;
    state.players[0].gaiaformers_deployed = 1;
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(state.players[0].resources.qic, 0);
    assert_eq!(state.players[0].gaiaformers_deployed, 0);
}

#[test]
fn unreserved_formed_gaia_still_requires_entry_qic() {
    let coord = HexCoord::new(1, 0);
    let mut state = gaia_state(FactionId::HadschHallas, 1, 0);
    let planet = state
        .board
        .hexes
        .get_mut(&coord)
        .unwrap_or_else(|| panic!("fixture hex should exist"))
        .planet
        .as_mut()
        .unwrap_or_else(|| panic!("fixture planet should exist"));
    planet.planet_type = PlanetType::Transdim;
    planet.is_gaia_formed = true;
    assert_rejected_without_mutation(&mut state, GameAction::Build { coord });
    state.players[0].resources.qic = 1;
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(state.players[0].resources.qic, 0);
}

#[test]
fn home_planet_does_not_gain_a_gaia_entry_cost() {
    let coord = HexCoord::new(1, 0);
    let mut state = gaia_state(FactionId::HadschHallas, 1, 0);
    state
        .board
        .hexes
        .get_mut(&coord)
        .unwrap_or_else(|| panic!("fixture hex should exist"))
        .planet
        .as_mut()
        .unwrap_or_else(|| panic!("fixture planet should exist"))
        .planet_type = PlanetType::Oxide;
    RuleEngine::apply_action(&mut state, 0, GameAction::Build { coord }).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
    assert_eq!(state.players[0].resources.qic, 0);
    assert_eq!(state.players[0].resources.ore, 6);
}
