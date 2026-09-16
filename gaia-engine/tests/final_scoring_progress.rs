use gaia_engine::game_state::FinalScoringCondition;
use gaia_engine::{GameState, ScoringEngine};

#[test]
fn frontend_progress_fixture_matches_authoritative_metrics(
) -> Result<(), Box<dyn std::error::Error>> {
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "../../gaia-frontend/src/tests/fixtures/finalScoringProgress.json"
    ))?;
    let state: GameState = serde_json::from_value(fixture["state"].clone())?;
    let conditions: Vec<FinalScoringCondition> =
        serde_json::from_value(fixture["conditions"].clone())?;
    let expected: Vec<Vec<u32>> = serde_json::from_value(fixture["expected"].clone())?;
    assert_eq!(conditions.len(), 9);
    assert_eq!(expected.len(), state.players.len());
    for (player, values) in state.players.iter().zip(expected) {
        assert_eq!(values.len(), conditions.len());
        for (condition, value) in conditions.iter().zip(values) {
            assert_eq!(
                ScoringEngine::final_scoring_metric(&state, player.player_id, condition),
                value,
                "player {}: {condition:?}",
                player.player_id
            );
        }
    }
    Ok(())
}
