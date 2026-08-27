use gaia_engine::scoring::ScoringEngine;
use gaia_engine::test_utils::builders::GameStateBuilder;

#[test]
fn final_scoring_all_zeros_no_panic() {
    let state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    let scores = ScoringEngine::calculate_final_scoring(&state);
    assert_eq!(scores.len(), 4);
}

#[test]
fn research_track_vp_at_level_5() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.research_tracks.science = 5;
        })
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    let scores = ScoringEngine::calculate_final_scoring(&state);
    // Player 0 should have 12 extra VP from science track at level 5
    let (_, p0_vp) = scores[0];
    let (_, p1_vp) = scores[1];
    assert!(
        p0_vp > p1_vp,
        "player 0 research bonus should exceed player 1"
    );
}

#[test]
fn round_scoring_empty_log_returns_empty() {
    let state = GameStateBuilder::new().with_player(0).with_round(1).build();
    let result = ScoringEngine::calculate_round_scoring(&state, 1);
    assert!(result.is_empty(), "no events → no round VP");
}

#[test]
fn final_scoring_breakdown_reports_each_component() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |player| {
            player.vp = 11;
            player.resources.ore = 2;
            player.resources.credits = 4;
            player.resources.knowledge = 3;
            player.resources.qic = 99;
            player.resources.power.bowl3 = 99;
            player.research_tracks.science = 5;
        })
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    for player in state.players.iter_mut().skip(1) {
        player.resources.ore = 0;
        player.resources.credits = 0;
        player.resources.knowledge = 0;
    }

    let breakdowns = ScoringEngine::calculate_final_scoring_breakdown(&state);
    let player_zero = breakdowns[0];

    assert_eq!(player_zero.gameplay_vp, 11);
    // All four players tie at zero on both default final tiles. Each player
    // receives (18 + 12 + 6 + 0) / 4 = 9 VP per tile.
    assert_eq!(player_zero.final_tile_vp, 18);
    assert_eq!(player_zero.research_vp, 12);
    assert_eq!(player_zero.resource_vp, 3);
    assert_eq!(player_zero.faction_vp, 0);
    assert_eq!(player_zero.total_vp, 44);

    let totals = ScoringEngine::calculate_final_scoring(&state);
    assert_eq!(totals[0], (player_zero.player_id, player_zero.total_vp));
}
