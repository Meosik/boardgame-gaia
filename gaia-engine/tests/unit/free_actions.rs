use gaia_engine::game_state::{FactionId, GamePhase};
use gaia_engine::rules::actions::{FreeActionKind, GameAction};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn base_state() -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 5;
            p.resources.credits = 0;
            p.resources.knowledge = 5;
            p.resources.qic = 5;
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 0;
            p.resources.power.bowl3 = 10;
        })
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Terrans);
        })
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn ore_to_credit_converts_resources_without_ending_the_turn() {
    let mut state = base_state();

    let events = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToCredit,
            count: 1,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    assert!(matches!(
        events.first(),
        Some(gaia_engine::game_state::GameEvent::FreeActionTaken {
            player: 0,
            kind,
            count: 1,
        }) if kind == "OreToCredit"
    ));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 4);
    assert_eq!(player.resources.credits, 1);
    // Free actions don't consume the turn — still player 0's turn.
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn free_actions_can_be_chained_any_number_of_times() {
    let mut state = base_state();

    for _ in 0..3 {
        RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::FreeAction {
                kind: FreeActionKind::OreToCredit,
                count: 1,
            },
        )
        .unwrap_or_else(|e| panic!("{e}"));
    }

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 2);
    assert_eq!(player.resources.credits, 3);
}

#[test]
fn power_to_qic_spends_from_bowl3_only() {
    let mut state = base_state();
    state.players[0].resources.power.bowl1 = 10;
    state.players[0].resources.power.bowl2 = 10;
    state.players[0].resources.power.bowl3 = 4;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::PowerToQic,
            count: 1,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 10);
    assert_eq!(player.resources.power.bowl2, 10);
    assert_eq!(player.resources.power.bowl3, 0);
    assert_eq!(player.resources.qic, 6);
}

#[test]
fn ore_to_power_adds_a_fresh_token_to_bowl1() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToPower,
            count: 1,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 4);
    assert_eq!(player.resources.power.bowl1, 1);
    // Not routed through the spendable bowl3 pool.
    assert_eq!(player.resources.power.bowl3, 10);
}

#[test]
fn free_action_rejects_insufficient_resources() {
    let mut state = base_state();
    state.players[0].resources.power.bowl3 = 3; // PowerToQic needs 4

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::PowerToQic,
            count: 1,
        },
    );
    assert!(result.is_err());
}

#[test]
fn free_action_rejects_out_of_turn() {
    let mut state = base_state();

    let result = RuleEngine::apply_action(
        &mut state,
        1,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToCredit,
            count: 1,
        },
    );
    assert!(result.is_err());
}

#[test]
fn free_action_rejects_after_passing() {
    let mut state = base_state();
    state.players[0].passed = true;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToCredit,
            count: 1,
        },
    );
    assert!(result.is_err());
}

#[test]
fn batched_free_action_applies_the_full_count_without_ending_the_turn() {
    let mut state = base_state();

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToCredit,
            count: 4,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 1);
    assert_eq!(player.resources.credits, 4);
    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn batched_free_action_rejects_zero_and_unaffordable_counts() {
    let mut state = base_state();

    for count in [0, 6] {
        let result = RuleEngine::apply_action(
            &mut state,
            0,
            GameAction::FreeAction {
                kind: FreeActionKind::OreToCredit,
                count,
            },
        );
        assert!(result.is_err());
    }
}

#[test]
fn burn_power_discards_one_bowl2_token_and_moves_the_other_to_bowl3() {
    let mut state = base_state();
    state.players[0].resources.power.bowl2 = 4;
    state.players[0].resources.power.bowl3 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::BurnPower,
            count: 2,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let power = &state.players[0].resources.power;
    assert_eq!(power.bowl2, 0);
    assert_eq!(power.bowl3, 2);
    assert_eq!(power.total(), 2);
}

#[test]
fn burn_power_requires_two_bowl2_tokens_per_use() {
    let mut state = base_state();
    state.players[0].resources.power.bowl2 = 1;

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::BurnPower,
            count: 1,
        },
    );

    assert!(result.is_err());
}

#[test]
fn hadsch_hallas_pi_unlocks_credit_conversions() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::HadschHallas);
    state.players[0]
        .structures
        .push(gaia_engine::game_state::Structure {
            hex: gaia_engine::game_state::HexCoord::new(0, 0),
            kind: gaia_engine::game_state::StructureType::PlanetaryInstitute,
        });
    state.players[0].resources.credits = 12;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::CreditsToOre,
            count: 3,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.players[0].resources.credits, 3);
    assert_eq!(state.players[0].resources.ore, 8);
}

#[test]
fn faction_free_action_is_rejected_for_the_wrong_faction() {
    let mut state = base_state();
    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::CreditsToOre,
            count: 1,
        },
    );
    assert!(result.is_err());
}

#[test]
fn bal_taks_converts_available_gaiaformers_until_the_next_gaia_phase() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::BalTaks);
    state.players[0].gaiaformers_total = 3;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::GaiaformerToQic,
            count: 2,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.players[0].gaiaformers_available(), 1);
    assert_eq!(state.players[0].gaiaformers_in_gaia_area, 2);
    assert_eq!(state.players[0].resources.qic, 7);

    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));
    assert_eq!(state.players[0].gaiaformers_in_gaia_area, 0);
    assert_eq!(state.players[0].gaiaformers_available(), 3);
}

#[test]
fn nevlas_moves_power_to_gaia_area_and_gains_knowledge() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Nevlas);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::PowerToGaiaKnowledge,
            count: 2,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.players[0].resources.power.bowl3, 8);
    assert_eq!(state.players[0].resources.power.gaia_forming, 2);
    assert_eq!(state.players[0].resources.knowledge, 7);
}

#[test]
fn lost_fleet_xenos_converts_ore_directly_to_bowl3_power() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Xenos);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToPowerBowl3,
            count: 2,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.players[0].resources.ore, 3);
    assert_eq!(state.players[0].resources.power.bowl3, 12);
}

#[test]
fn itars_burned_power_enters_the_gaia_area_instead_of_the_supply() {
    let mut state = base_state();
    state.players[0].faction = Some(FactionId::Itars);
    state.players[0].resources.power.bowl2 = 2;
    state.players[0].resources.power.bowl3 = 0;

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::FreeAction {
            kind: FreeActionKind::BurnPower,
            count: 1,
        },
    )
    .unwrap_or_else(|e| panic!("{e}"));

    let power = &state.players[0].resources.power;
    assert_eq!(power.bowl2, 0);
    assert_eq!(power.bowl3, 1);
    assert_eq!(power.gaia_forming, 1);
    assert_eq!(power.total(), 2);
}

#[test]
fn legacy_single_free_action_payload_defaults_count_to_one() {
    let action: GameAction = serde_json::from_value(serde_json::json!({
        "type": "FreeAction",
        "kind": "OreToCredit"
    }))
    .unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(
        action,
        GameAction::FreeAction {
            kind: FreeActionKind::OreToCredit,
            count: 1,
        }
    );
}
