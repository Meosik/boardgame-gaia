use gaia_engine::game_state::{EconomyResearchTileSide, FactionId, GamePhase};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn income_state(side: EconomyResearchTileSide, economy_level: u8) -> gaia_engine::GameState {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.faction = Some(FactionId::Terrans);
            player.research_tracks.economy = economy_level;
            player.resources.credits = 0;
            player.resources.power.bowl1 = 4;
            player.resources.power.bowl2 = 0;
            player.resources.power.bowl3 = 0;
            player.vp = 10;
        })
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();
    state.research_board.economy_research_tile_side = side;
    state
}

#[test]
fn power_side_replaces_economy_level_three_income() {
    let mut state = income_state(EconomyResearchTileSide::Power, 3);
    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|error| panic!("income transition failed: {error}"));

    let player = state.player(0).unwrap_or_else(|| unreachable!());
    assert_eq!(player.resources.credits, 2);
    assert_eq!(player.resources.power.bowl1, 1);
    assert_eq!(player.resources.power.bowl2, 3);
    assert_eq!(player.vp, 10);
}

#[test]
fn victory_point_side_replaces_economy_level_four_income() {
    let mut state = income_state(EconomyResearchTileSide::VictoryPoints, 4);
    RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|error| panic!("income transition failed: {error}"));

    let player = state.player(0).unwrap_or_else(|| unreachable!());
    assert_eq!(player.resources.credits, 4);
    assert_eq!(player.resources.power.bowl1, 4);
    assert_eq!(player.resources.power.bowl2, 0);
    assert_eq!(player.vp, 11);
}
