//! Additional checklist boundaries; fixtures are isolated, never live user rooms.
use gaia_engine::game_state::{
    FactionId, GamePhase, GameState, Hex, HexCoord, PlacedStructure, Planet, PlanetType,
    ResearchTrack, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn reload(state: &GameState) -> GameState {
    serde_json::from_value(state.serialize()).unwrap_or_else(|error| panic!("saved state must deserialize: {error}"))
}

fn assert_rejected_unchanged(state: &mut GameState, action: GameAction) {
    let before = state.serialize();
    assert!(RuleEngine::apply_action(state, 0, action).is_err());
    assert_eq!(
        state.serialize(),
        before,
        "rejected action must not mutate state"
    );
}

fn special_scenario(faction: FactionId) -> (GameState, GameAction, GameAction) {
    let origin = HexCoord::new(0, 0);
    let a = HexCoord::new(1, 0);
    let b = HexCoord::new(0, 1);
    let target_kind = if faction == FactionId::Firaks {
        StructureType::ResearchLab
    } else {
        StructureType::Mine
    };
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(faction);
            p.resources.ore = 5;
            p.resources.credits = 10;
            p.resources.qic = 4;
            p.structures = vec![Structure {
                hex: origin,
                kind: StructureType::PlanetaryInstitute,
            }];
            if faction != FactionId::Ivits {
                p.structures.extend([a, b].map(|hex| Structure {
                    hex,
                    kind: target_kind,
                }));
            }
        })
        .with_player(1)
        .build();
    state.board.hexes.clear();
    for coord in [origin, a, b] {
        let kind = state.players[0]
            .structures
            .iter()
            .find(|s| s.hex == coord)
            .map(|s| s.kind);
        state.board.hexes.insert(
            coord,
            Hex {
                coord,
                planet: kind.map(|_| Planet {
                    planet_type: PlanetType::Swamp,
                    owner: Some(0),
                    is_gaia_formed: false,
                }),
                space_tile_kind: None,
                structures: kind
                    .map(|kind| vec![PlacedStructure { owner: 0, kind }])
                    .unwrap_or_default(),
                satellites: vec![],
            },
        );
    }
    let (first, second) = match faction {
        FactionId::Ambas => (
            GameAction::AmbasSwapPlanetaryInstitute { mine_coord: a },
            GameAction::AmbasSwapPlanetaryInstitute { mine_coord: origin },
        ),
        FactionId::Firaks => (
            GameAction::FiraksDowngradeResearchLab {
                coord: a,
                track: ResearchTrack::Science,
            },
            GameAction::FiraksDowngradeResearchLab {
                coord: b,
                track: ResearchTrack::Science,
            },
        ),
        FactionId::Bescods => (
            GameAction::BescodsLowestResearchAdvance {
                track: ResearchTrack::Terraforming,
            },
            GameAction::BescodsLowestResearchAdvance {
                track: ResearchTrack::Science,
            },
        ),
        FactionId::Ivits => (
            GameAction::IvitsPlaceSpaceStation { coord: a },
            GameAction::IvitsPlaceSpaceStation { coord: b },
        ),
        FactionId::Moweyds => (
            GameAction::MoweydsPlacePowerRing { coord: a },
            GameAction::MoweydsPlacePowerRing { coord: b },
        ),
        _ => unreachable!("bounded special-action matrix"),
    };
    (state, first, second)
}

#[test]
fn special_actions_reject_without_pi_except_bescods_without_mutation() {
    for faction in [
        FactionId::Ambas,
        FactionId::Firaks,
        FactionId::Bescods,
        FactionId::Ivits,
        FactionId::Moweyds,
    ] {
        let (mut state, first, _) = special_scenario(faction);
        state.players[0]
            .structures
            .retain(|s| s.kind != StructureType::PlanetaryInstitute);
        state.board.hexes.remove(&HexCoord::new(0, 0));
        if faction == FactionId::Bescods {
            RuleEngine::apply_action(&mut state, 0, first).unwrap_or_else(|error| panic!("Bescods does not require PI: {error}"));
        } else {
            assert_rejected_unchanged(&mut state, first);
        }
    }
}

#[test]
fn special_actions_keep_usage_after_reload_and_unlock_only_next_round() {
    for faction in [
        FactionId::Ambas,
        FactionId::Firaks,
        FactionId::Bescods,
        FactionId::Ivits,
        FactionId::Moweyds,
    ] {
        let (mut state, first, second) = special_scenario(faction);
        RuleEngine::apply_action(&mut state, 0, first)
            .unwrap_or_else(|e| panic!("{faction:?}: {e}"));
        assert!(state.players[0].faction_special_action_used_this_round);
        let saved = state.serialize();
        state = reload(&state);
        assert_eq!(state.serialize(), saved);
        // Return control to the owner so a NotYourTurn error cannot hide a missing usage guard.
        state.phase = GamePhase::ActionPhase { active_player: 0 };
        let mut unused = state.clone();
        unused.players[0].faction_special_action_used_this_round = false;
        RuleEngine::validate_action(&unused, 0, &second).unwrap_or_else(|error| panic!("second target is otherwise legal: {error}"));
        assert_rejected_unchanged(&mut state, second.clone());
        state.phase = GamePhase::RoundScoring { round: 1 };
        RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        while matches!(state.phase, GamePhase::IncomeOrderPending { .. }) {
            let GamePhase::IncomeOrderPending { ref queue, .. } = state.phase else {
                unreachable!()
            };
            let player = queue[0].player;
            RuleEngine::apply_action(
                &mut state,
                player,
                GameAction::ChooseIncomeOrder { charge_first: true },
            )
            .unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        }
        assert!(!state.players[0].faction_special_action_used_this_round);
        assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
        RuleEngine::apply_action(&mut state, 0, second)
            .unwrap_or_else(|e| panic!("next round {faction:?}: {e}"));
    }
}
