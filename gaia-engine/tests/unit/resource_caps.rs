use gaia_engine::game_state::{GamePhase, Resources};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

// Rulebook p.9: "Track your ore, knowledge, and credits using the corresponding tokens on the
// resource track of your faction board... The track ends at 15, so you cannot have more than
// 15 ore, 15 knowledge, and 30 credits (15 per token)." `Resources::gain_*` is the single choke
// point every resource-granting code path in `rules/engine.rs` now funnels through, replacing
// what used to be direct, uncapped `saturating_add` calls scattered across ~30 call sites.

#[test]
fn gain_ore_clamps_at_the_fifteen_ore_cap() {
    let mut resources = Resources::zero();
    resources.ore = 13;
    resources.gain_ore(10);
    assert_eq!(resources.ore, 15);
}

#[test]
fn gain_knowledge_clamps_at_the_fifteen_knowledge_cap() {
    let mut resources = Resources::zero();
    resources.knowledge = 13;
    resources.gain_knowledge(10);
    assert_eq!(resources.knowledge, 15);
}

#[test]
fn gain_credits_clamps_at_the_thirty_credits_cap() {
    let mut resources = Resources::zero();
    resources.credits = 28;
    resources.gain_credits(10);
    assert_eq!(resources.credits, 30);
}

#[test]
fn gain_under_the_cap_is_unaffected() {
    let mut resources = Resources::zero();
    resources.ore = 3;
    resources.gain_ore(5);
    assert_eq!(resources.ore, 8);
}

/// End-to-end: the shared power-action board's id-4 slot ("pay 4 power, gain 7 credits" —
/// `apply_power_effect`) is one of the real call sites migrated onto `gain_credits`. A player
/// already near the 30-credit cap should be clamped by the actual action, not just by the
/// `Resources` method in isolation.
#[test]
fn power_action_credit_grant_is_clamped_by_the_real_action_path() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.resources.credits = 26;
            p.resources.power.bowl3 = 4;
        })
        .with_player(1)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::PowerAction { id: 4, coord: None },
    )
    .unwrap_or_else(|e| panic!("power action should succeed: {e}"));

    assert_eq!(state.players[0].resources.credits, 30);
}
