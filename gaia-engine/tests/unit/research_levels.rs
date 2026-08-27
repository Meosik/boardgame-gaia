// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), p.14: "In order to advance to level 5 of a
// research area, in addition to any other costs, you must flip one of your federation tokens
// from its green side to its gray side (this is the same cost as for taking an advanced tech
// tile). Only one player can advance to level 5 of each research area. Each time your research
// token advances from level 2 to level 3 in any research area, you charge three power (this also
// applies if you advanced by taking a tech tile)."

use gaia_engine::game_state::{FederationToken, GamePhase, ResearchTrack};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn research_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.knowledge = 20;
        })
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn advancing_from_level_2_to_3_charges_three_power() {
    let mut state = research_state();
    state.players[0].research_tracks.terraforming = 2;
    state.players[0].resources.power.bowl1 = 4;
    state.players[0].resources.power.bowl2 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    )
    .unwrap_or_else(|e| panic!("advance to level 3 should succeed: {e}"));

    assert_eq!(state.players[0].research_tracks.terraforming, 3);
    assert_eq!(state.players[0].resources.power.bowl1, 1);
    assert_eq!(state.players[0].resources.power.bowl2, 3);
}

#[test]
fn advancing_between_other_levels_does_not_charge_power() {
    let mut state = research_state();
    state.players[0].research_tracks.terraforming = 0;
    state.players[0].resources.power.bowl1 = 4;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    )
    .unwrap_or_else(|e| panic!("advance to level 1 should succeed: {e}"));

    assert_eq!(state.players[0].research_tracks.terraforming, 1);
    assert_eq!(state.players[0].resources.power.bowl1, 4);
}

#[test]
fn advancing_to_level_five_requires_a_green_federation_token() {
    let mut state = research_state();
    state.players[0].research_tracks.terraforming = 4;
    // No federation tokens owned.

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(result.is_err());

    state.players[0].federation_tokens.push(FederationToken(1));
    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    )
    .unwrap_or_else(|e| panic!("advance to level 5 with a green token should succeed: {e}"));

    assert_eq!(state.players[0].research_tracks.terraforming, 5);
    assert!(state.players[0].federation_tokens.is_empty());
    assert_eq!(
        state.players[0].gray_federation_tokens,
        vec![FederationToken(1)]
    );
}

#[test]
fn level_five_is_exclusive_to_one_player() {
    let mut state = research_state();
    state.players[0].research_tracks.terraforming = 5;
    state
        .research_board
        .tracks
        .get_mut(&ResearchTrack::Terraforming)
        .unwrap_or_else(|| panic!("Terraforming track state should exist"))
        .player_levels
        .insert(0, 5);

    state.players[1].research_tracks.terraforming = 4;
    state.players[1].resources.knowledge = 20;
    state.players[1].federation_tokens.push(FederationToken(1));
    state.phase = GamePhase::ActionPhase { active_player: 1 };

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::ResearchAdvance {
            track: ResearchTrack::Terraforming,
        },
    );
    assert!(
        result.is_err(),
        "a second player should not be able to reach level 5 of the same track"
    );
}
