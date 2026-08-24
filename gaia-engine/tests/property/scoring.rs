use gaia_engine::scoring::ScoringEngine;
use gaia_engine::test_utils::builders::GameStateBuilder;
use proptest::prelude::*;

proptest! {
    #[test]
    fn final_score_returns_four_entries(vp0 in 0i32..=100, vp1 in 0i32..=100) {
        let state = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.vp = vp0; })
            .with_player_fn(1, |p| { p.vp = vp1; })
            .with_player(2)
            .with_player(3)
            .build();
        let scores = ScoringEngine::calculate_final_scoring(&state);
        prop_assert_eq!(scores.len(), 4);
    }

    #[test]
    fn higher_research_never_lowers_score(track_level in 0u8..=5u8) {
        let state_low = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.research_tracks.science = 0; })
            .with_player(1).with_player(2).with_player(3)
            .build();
        let state_high = GameStateBuilder::new()
            .with_player_fn(0, |p| { p.research_tracks.science = track_level; })
            .with_player(1).with_player(2).with_player(3)
            .build();
        let low_vp = ScoringEngine::calculate_final_scoring(&state_low)[0].1;
        let high_vp = ScoringEngine::calculate_final_scoring(&state_high)[0].1;
        prop_assert!(high_vp >= low_vp, "more research should not decrease final score");
    }
}
