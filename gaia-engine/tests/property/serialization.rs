use gaia_engine::test_utils::strategies::minimal_game_state;
use gaia_engine::GameState;
use proptest::prelude::*;

proptest! {
    #[test]
    fn serialize_deserialize_roundtrip(state in minimal_game_state()) {
        let json = state.serialize();
        let restored = match GameState::deserialize(json) {
            Ok(restored) => restored,
            Err(e) => panic!("deserialize should succeed: {e}"),
        };
        // Key invariant: player count preserved
        prop_assert_eq!(state.players.len(), restored.players.len());
        // Round preserved
        prop_assert_eq!(state.round, restored.round);
    }
}
