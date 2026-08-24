use gaia_engine::game_state::{
    AcademyType, FactionId, GamePhase, HexCoord, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

fn structure(kind: StructureType) -> Structure {
    Structure {
        hex: HexCoord::new(0, 0),
        kind,
    }
}

/// Advances from `RoundScoring`, resolving any `IncomeOrderPending` pause
/// (PlanetaryInstitute charge vs. bonus power token) by always choosing
/// `charge_first` — most tests here don't care about the resulting bowl
/// split, only that the amounts involved are correct.
fn advance_from_round_scoring(
    state: gaia_engine::game_state::GameState,
) -> gaia_engine::game_state::GameState {
    advance_from_round_scoring_with_order(state, true)
}

fn advance_from_round_scoring_with_order(
    mut state: gaia_engine::game_state::GameState,
    charge_first: bool,
) -> gaia_engine::game_state::GameState {
    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));
    loop {
        let next_player = match &state.phase {
            GamePhase::IncomeOrderPending { queue, .. } => queue.first().map(|e| e.player),
            _ => None,
        };
        let Some(player) = next_player else { break };
        RuleEngine::apply_action(
            &mut state,
            player,
            GameAction::ChooseIncomeOrder { charge_first },
        )
        .unwrap_or_else(|e| panic!("{e}"));
    }
    state
}

#[test]
fn universal_mine_trading_station_research_lab_income_applies() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 0;
            p.resources.credits = 0;
            p.resources.knowledge = 0;
            p.structures = vec![
                structure(StructureType::Mine),
                structure(StructureType::Mine),
                structure(StructureType::TradingStation),
                structure(StructureType::ResearchLab),
            ];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Mine: base 1 + table[0..2]=[1,1] → 3 ore.
    assert_eq!(player.resources.ore, 3);
    // TradingStation: base 0 + table[0]=3 → 3 credits.
    assert_eq!(player.resources.credits, 3);
    // ResearchLab: base 1 + table[0]=1 → 2 knowledge.
    assert_eq!(player.resources.knowledge, 2);
}

#[test]
fn academy_science_grants_universal_two_knowledge_per_round() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.knowledge = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Science))];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Academy(Science) 2 knowledge + the universal ResearchLab base income
    // (1 knowledge/round, granted even with 0 ResearchLabs built).
    assert_eq!(player.resources.knowledge, 3);
}

#[test]
fn academy_qic_grants_no_passive_income() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.qic = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Qic))];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 0);
}

#[test]
fn planetary_institute_charges_universal_four_power() {
    // Lantids get no PlanetaryInstitute bonus power token, so this stays a
    // plain (non-order-pausing) charge — see `no_bonus_token_skips_income_order_pause`.
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 0;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 0);
    assert_eq!(player.resources.power.bowl2, 4);
}

#[test]
fn space_giants_planetary_institute_charges_six_power() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::SpaceGiants);
            p.resources.power.bowl1 = 6;
            p.resources.power.bowl2 = 0;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    // charge_first: 6 charged (bowl1→bowl2), then the universal +1 bonus
    // token enters bowl1 fresh.
    let state = advance_from_round_scoring_with_order(state, true);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.power.bowl1, 1);
    assert_eq!(player.resources.power.bowl2, 6);
}

#[test]
fn no_bonus_token_skips_income_order_pause() {
    // Lantids get no PlanetaryInstitute bonus power token, so the income
    // phase should never pause into `IncomeOrderPending` for them.
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Lantids);
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();
    state.phase = GamePhase::RoundScoring { round: 1 };

    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
}

#[test]
fn charge_first_can_sweep_the_bonus_token_into_bowl2() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 5;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    let state = advance_from_round_scoring_with_order(state, true);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Charge 4 first (bowl1 empty → moves bowl2→bowl3 x4): bowl2=1, bowl3=4.
    // Then the bonus token enters bowl1 fresh, untouched by the charge.
    assert_eq!(player.resources.power.bowl1, 1);
    assert_eq!(player.resources.power.bowl2, 1);
    assert_eq!(player.resources.power.bowl3, 4);
}

#[test]
fn bonus_token_first_lets_it_get_charged_alongside_existing_tokens() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.bowl1 = 0;
            p.resources.power.bowl2 = 5;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    let state = advance_from_round_scoring_with_order(state, false);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Bonus token enters bowl1 first (bowl1=1, bowl2=5). Charging 4 then
    // prefers bowl1 (1 token) before bowl2 (3 more): bowl1=0, bowl2=5-3+1=3,
    // bowl3=3.
    assert_eq!(player.resources.power.bowl1, 0);
    assert_eq!(player.resources.power.bowl2, 3);
    assert_eq!(player.resources.power.bowl3, 3);
}

#[test]
fn firaks_research_lab_base_is_two_knowledge() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Firaks);
            p.resources.knowledge = 0;
            p.structures = vec![structure(StructureType::ResearchLab)];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Firaks override: base 2 + table[0]=1 → 3 knowledge (universal would be 2).
    assert_eq!(player.resources.knowledge, 3);
}

#[test]
fn bescods_trading_station_and_research_lab_income_are_swapped() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Bescods);
            p.resources.credits = 0;
            p.resources.knowledge = 0;
            p.structures = vec![
                structure(StructureType::TradingStation),
                structure(StructureType::ResearchLab),
            ];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // TradingStation pays knowledge (base 0 + table[0]=1), ResearchLab pays
    // credits (base 0 + table[0]=3) — no credits/knowledge come from the
    // structure each would normally pay in.
    assert_eq!(player.resources.knowledge, 1);
    assert_eq!(player.resources.credits, 3);
}

#[test]
fn nevlas_research_lab_income_is_power_not_knowledge() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Nevlas);
            p.resources.knowledge = 0;
            p.resources.power.bowl1 = 2;
            p.resources.power.bowl2 = 0;
            p.structures = vec![structure(StructureType::ResearchLab)];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.knowledge, 0);
    // ResearchLab pays 2 power (base 0 + table[0]=2), charged from bowl1→bowl2.
    assert_eq!(player.resources.power.bowl1, 0);
    assert_eq!(player.resources.power.bowl2, 2);
}

#[test]
fn itars_academy_science_grants_three_knowledge_per_round() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Itars);
            p.resources.knowledge = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Science))];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Itars' Academy(Science) override (3 knowledge) + the universal
    // ResearchLab base income (1 knowledge/round, granted even with 0
    // ResearchLabs built).
    assert_eq!(player.resources.knowledge, 4);
}

#[test]
fn no_structures_still_grants_universal_base_income() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.ore = 0;
            p.resources.credits = 0;
            p.resources.knowledge = 0;
            p.structures = vec![];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.ore, 1);
    assert_eq!(player.resources.credits, 0);
    assert_eq!(player.resources.knowledge, 1);
}

#[test]
fn xenos_planetary_institute_grants_one_qic_per_round() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Xenos);
            p.resources.qic = 0;
            p.resources.power.bowl1 = 4;
            p.resources.power.bowl2 = 0;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    // Xenos have no bonus power token (0), so no IncomeOrderPending pause.
    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 1);
    assert_eq!(player.resources.power.bowl1, 0);
    assert_eq!(player.resources.power.bowl2, 4);
}

#[test]
fn gleens_planetary_institute_grants_one_ore_per_round() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Gleens);
            p.resources.ore = 0;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    // Universal Mine base (0 mines built, still 1 ore) + PlanetaryInstitute
    // bonus (1 ore) = 2.
    assert_eq!(player.resources.ore, 2);
}

#[test]
fn ivits_planetary_institute_grants_qic_alongside_the_power_token() {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Ivits);
            p.resources.qic = 0;
            p.structures = vec![structure(StructureType::PlanetaryInstitute)];
        })
        .build();

    // Ivits keep the universal +1 bonus power token, so this does pause.
    let state = advance_from_round_scoring(state);

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 1);
}

#[test]
fn academy_qic_action_grants_one_qic_by_default() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.qic = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Qic))];
        })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction)
        .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 1);
}

#[test]
fn academy_qic_action_requires_an_academy_qic_structure() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.structures = vec![];
        })
        .build();

    let result = RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction);
    assert!(result.is_err());
}

#[test]
fn academy_qic_action_is_once_per_round() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.qic = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Qic))];
        })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction)
        .unwrap_or_else(|e| panic!("{e}"));
    let result = RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction);

    assert!(result.is_err());
    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 1); // only the first use counted
}

#[test]
fn academy_qic_action_resets_at_the_next_round() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.qic = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Qic))];
        })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction)
        .unwrap_or_else(|e| panic!("{e}"));

    state.phase = GamePhase::RoundScoring { round: 1 };
    RuleEngine::advance_to_next_round(&mut state).unwrap_or_else(|e| panic!("{e}"));

    RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction)
        .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 2); // used once per round, twice across 2 rounds
}

#[test]
fn baltaks_academy_qic_action_grants_four_credits_instead() {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::BalTaks);
            p.resources.qic = 0;
            p.resources.credits = 0;
            p.structures = vec![structure(StructureType::Academy(AcademyType::Qic))];
        })
        .build();

    RuleEngine::apply_action(&mut state, 0, GameAction::AcademyQicAction)
        .unwrap_or_else(|e| panic!("{e}"));

    let player = state.player(0).unwrap_or_else(|| panic!("player 0 exists"));
    assert_eq!(player.resources.qic, 0);
    assert_eq!(player.resources.credits, 4);
}
