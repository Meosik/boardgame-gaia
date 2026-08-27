use super::builders::{minimal_player, GameStateBuilder};
use crate::game_state::{GameState, HexCoord, PlayerState, PowerCycle, Resources};
use proptest::prelude::*;

// ── Primitive strategies ──────────────────────────────────────────────────────

/// Valid axial hex coordinate with coordinates in [-10, 10].
pub fn valid_hex_coord() -> impl Strategy<Value = HexCoord> {
    (-10i32..=10, -10i32..=10).prop_map(|(q, r)| HexCoord::new(q, r))
}

/// Resources with non-pathological values (no overflow risk).
pub fn valid_resources() -> impl Strategy<Value = Resources> {
    (
        0u8..=20,
        0u8..=30,
        0u8..=10,
        0u8..=10,
        0u8..=8,
        0u8..=8,
        0u8..=8,
    )
        .prop_map(|(ore, credits, knowledge, qic, b1, b2, b3)| Resources {
            ore,
            credits,
            knowledge,
            qic,
            power: PowerCycle {
                bowl1: b1,
                bowl2: b2,
                bowl3: b3,
                gaia_bowl: 0,
                gaia_forming: 0,
                brainstone: None,
            },
            spent_gaia_formers: 0,
        })
}

/// `PlayerState` with valid resources and research tracks.
pub fn valid_player_state(player_id: u8) -> impl Strategy<Value = PlayerState> {
    valid_resources().prop_map(move |resources| {
        let mut p = minimal_player(player_id);
        p.resources = resources;
        p
    })
}

/// A minimal 1-player `GameState` suitable for rule engine property tests.
pub fn minimal_game_state() -> impl Strategy<Value = GameState> {
    valid_player_state(0).prop_map(|player| {
        GameStateBuilder::new()
            .with_player_fn(player.player_id, |p| {
                p.resources = player.resources.clone();
            })
            .build()
    })
}
