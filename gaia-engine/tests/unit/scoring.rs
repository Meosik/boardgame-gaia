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
