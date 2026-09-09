// Base rulebook (`docs/EN_Gaia_rulebook_lo.pdf`), p.14: "In order to advance to level 5 of a
// research area, in addition to any other costs, you must flip one of your federation tokens
// from its green side to its gray side (this is the same cost as for taking an advanced tech
// tile). Only one player can advance to level 5 of each research area. Each time your research
// token advances from level 2 to level 3 in any research area, you charge three power (this also
// applies if you advanced by taking a tech tile)."

use gaia_engine::game_state::{FederationToken, GameEvent, GamePhase, ResearchTrack, RoundTile};
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

fn advance(state: &mut gaia_engine::game_state::GameState, track: ResearchTrack) -> Vec<GameEvent> {
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    RuleEngine::apply_action(state, 0, GameAction::ResearchAdvance { track })
        .unwrap_or_else(|e| panic!("research advance should succeed: {e}"))
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

#[test]
fn immediate_resource_rewards_are_granted_on_reaching_the_printed_level() {
    let mut terraforming = research_state();
    let ore_before = terraforming.players[0].resources.ore;
    advance(&mut terraforming, ResearchTrack::Terraforming);
    assert_eq!(terraforming.players[0].resources.ore, ore_before + 2);

    let mut ai = research_state();
    ai.players[0].research_tracks.ai = 2;
    ai.players[0].resources.power.bowl1 = 4;
    ai.players[0].resources.power.bowl2 = 0;
    let qic_before = ai.players[0].resources.qic;
    advance(&mut ai, ResearchTrack::ArtificialIntelligence);
    assert_eq!(ai.players[0].resources.qic, qic_before + 2);
    assert_eq!(ai.players[0].resources.power.bowl1, 1);
    assert_eq!(ai.players[0].resources.power.bowl2, 3);
}

#[test]
fn gaia_project_unlocks_gaiaformers_and_places_level_two_power_in_area_one() {
    let mut level_one = research_state();
    advance(&mut level_one, ResearchTrack::GaiaProject);
    assert_eq!(level_one.players[0].gaiaformers_total, 1);

    let mut level_two = research_state();
    level_two.players[0].research_tracks.gaia = 1;
    level_two.players[0].resources.power.bowl1 = 2;
    advance(&mut level_two, ResearchTrack::GaiaProject);
    assert_eq!(level_two.players[0].gaiaformers_total, 0);
    assert_eq!(level_two.players[0].resources.power.bowl1, 5);
}

#[test]
fn economy_and_science_level_five_rewards_are_immediate() {
    let mut economy = research_state();
    economy.players[0].research_tracks.economy = 4;
    economy.players[0]
        .federation_tokens
        .push(FederationToken(1));
    economy.players[0].resources.power.bowl1 = 6;
    economy.players[0].resources.power.bowl2 = 0;
    let ore_before = economy.players[0].resources.ore;
    let credits_before = economy.players[0].resources.credits;
    advance(&mut economy, ResearchTrack::Economy);
    assert_eq!(economy.players[0].resources.ore, ore_before + 3);
    assert_eq!(economy.players[0].resources.credits, credits_before + 6);
    assert_eq!(economy.players[0].resources.power.bowl1, 0);
    assert_eq!(economy.players[0].resources.power.bowl2, 6);

    let mut science = research_state();
    science.players[0].research_tracks.science = 4;
    science.players[0]
        .federation_tokens
        .push(FederationToken(1));
    let knowledge_before = science.players[0].resources.knowledge;
    advance(&mut science, ResearchTrack::Science);
    assert_eq!(
        science.players[0].resources.knowledge,
        knowledge_before - 4 + 9
    );
}

#[test]
fn terraforming_level_five_awards_the_reserved_token_as_a_federation() {
    let mut state = research_state();
    state.round_tiles[0] = RoundTile::from_id(5);
    state.players[0].research_tracks.terraforming = 4;
    state.players[0].federation_tokens.push(FederationToken(1));
    state.research_board.terraforming_level_5_token = Some(FederationToken(4));
    let vp_before = state.players[0].vp;
    let ore_before = state.players[0].resources.ore;

    let events = advance(&mut state, ResearchTrack::Terraforming);

    assert_eq!(state.research_board.terraforming_level_5_token, None);
    assert_eq!(state.players[0].federation_tokens, vec![FederationToken(4)]);
    assert_eq!(
        state.players[0].gray_federation_tokens,
        vec![FederationToken(1)]
    );
    assert_eq!(state.players[0].resources.ore, ore_before + 2);
    // Token 4 grants 7 VP; the current round's federation condition grants 5 VP.
    assert_eq!(state.players[0].vp, vp_before + 12);
    assert!(events.iter().any(|event| matches!(
        event,
        GameEvent::FederationFormed {
            player: 0,
            token: FederationToken(4),
            hexes,
        } if hexes.is_empty()
    )));
}
