//! Read-only access to native rules, not a second evaluator or a weight table.
use super::*;
use serde_json::{json, Value};

fn payout(before: &PlayerState, after: &PlayerState) -> Value {
    json!({"vp":after.vp-before.vp,
        "ore":i32::from(after.resources.ore)-i32::from(before.resources.ore),
        "credits":i32::from(after.resources.credits)-i32::from(before.resources.credits),
        "knowledge":i32::from(after.resources.knowledge)-i32::from(before.resources.knowledge),
        "qic":i32::from(after.resources.qic)-i32::from(before.resources.qic)})
}

/// Gross next-income production. No future build/research is assumed.
fn income(state: &GameState, player_id: PlayerId) -> Value {
    let mut copy = state.clone();
    if let Some(p) = copy.player_mut(player_id) {
        p.resources.ore = 0;
        p.resources.credits = 0;
        p.resources.knowledge = 0;
        p.resources.qic = 0;
    }
    let (_, events) = apply_income_phase(&mut copy, state.round.saturating_add(1));
    events
        .into_iter()
        .find_map(|event| match event {
            GameEvent::IncomeReceived {
                player,
                ore,
                credits,
                knowledge,
                qic,
                power_charge,
                power_tokens,
                vp,
                ..
            } if player == player_id => {
                Some(json!({"ore":ore,"credits":credits,"knowledge":knowledge,
                "qic":qic,"power_charge":power_charge,"power_tokens":power_tokens,"vp":vp}))
            }
            _ => None,
        })
        .unwrap_or_else(|| json!({}))
}

/// Project an already-passed player's own round transition for evaluation only.
/// Opponents do not pass or receive hypothetical income in the returned state.
pub fn passed_next_round(state: &GameState, player_id: PlayerId) -> Result<GameState, RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    if !player.passed {
        return Err(RuleError::ActionNotAllowed(
            "evaluation projection requires a passed player".into(),
        ));
    }
    let mut projected = state.clone();
    if state.round == 6 {
        projected.phase = GamePhase::RoundScoring { round: 6 };
        RuleEngine::finalize_game(&mut projected)?;
        return Ok(projected);
    }

    let opponents: Vec<_> = state
        .players
        .iter()
        .filter(|p| p.player_id != player_id)
        .cloned()
        .collect();
    let board = state.board.clone();
    let turn_order = state.turn_order.clone();
    let pass_order = state.pass_order.clone();
    let _ = apply_income_phase(&mut projected, state.round + 1);
    let _ = apply_gaia_phase(&mut projected);
    // Keep only this player's Gaia formations; other players' projects have not resolved.
    for (coord, original) in &board.hexes {
        if original.planet.as_ref().and_then(|p| p.owner) != Some(player_id) {
            if let Some(hex) = projected.board.hexes.get_mut(coord) {
                *hex = original.clone();
            }
        }
    }
    if let Some(target) = projected.player(player_id) {
        if target.resources.power.gaia_forming > 0 {
            move_remaining_gaia_power(&mut projected, player_id);
        }
    }
    finish_round_transition(&mut projected, state.round);
    for opponent in opponents {
        if let Some(slot) = projected
            .players
            .iter_mut()
            .find(|p| p.player_id == opponent.player_id)
        {
            *slot = opponent;
        }
    }
    projected.turn_order = turn_order;
    projected.pass_order = pass_order;
    Ok(projected)
}

fn ship_options(state: &GameState, player_id: PlayerId) -> Vec<Value> {
    let Some(player) = state.player(player_id) else {
        return vec![];
    };
    if player.passed || matches!(state.phase, GamePhase::Setup(_) | GamePhase::Ended { .. }) {
        return vec![];
    }
    let mut rows = Vec::new();
    for ship in SpaceshipId::all() {
        let owned = player
            .explored_ships
            .contains(&spaceship_id_to_ship_id(ship));
        let mut copy = state.clone();
        copy.phase = GamePhase::ActionPhase {
            active_player: usize::from(player_id),
        };
        // A hypothetical own action window, not a promise about intervening opponents.
        for p in &mut copy.players {
            p.passed = false;
        }
        if !owned {
            if validate_explore_spaceship(&copy, player_id, ship).is_err() {
                continue;
            }
            apply_explore_spaceship(&mut copy, player_id, ship);
            copy.phase = GamePhase::ActionPhase {
                active_player: usize::from(player_id),
            };
        }
        let Some(before) = copy.player(player_id) else {
            continue;
        };
        let mut options = Vec::new();
        for action in RuleEngine::get_valid_actions(&copy, player_id) {
            let encoded = serde_json::to_value(&action).unwrap_or(Value::Null);
            let name = encoded["type"].as_str().unwrap_or("");
            let belongs = match ship {
                SpaceshipId::TFMars => {
                    name.starts_with("TFMars") || name == "SpaceshipCreditTerraform"
                }
                SpaceshipId::Twilight => name.starts_with("Twilight") || name == "ExamineArtifact",
                SpaceshipId::Rebellion => name.starts_with("Rebellion"),
                SpaceshipId::Eclipse => name.starts_with("Eclipse"),
            };
            // A second ship entry is another option, not a recursive ship search.
            if !belongs || name.ends_with("ExploreSpaceship") {
                continue;
            }
            let mut after = copy.clone();
            if RuleEngine::apply_action(&mut after, player_id, action).is_err() {
                continue;
            }
            let Some(target) = after.player(player_id) else {
                continue;
            };
            let new_colonies = target
                .structures
                .len()
                .saturating_sub(before.structures.len());
            options.push(json!({"action":encoded,"payout":payout(before,target),
                "new_colonies":new_colonies,"income_after":income(&after,player_id),
                "research_after":target.research_tracks,
                "brainstone_after":target.resources.power.brainstone,
                "power_before":before.resources.power,"power_after":target.resources.power,
                "new_gaia_projects":target.gaiaformers_deployed.saturating_sub(before.gaiaformers_deployed)}));
        }
        rows.push(
            json!({"ship":ship,"owned":owned,"entry_payout":payout(player,before),
            "income_before":income(&copy,player_id),"research_before":before.research_tracks,
            "power_before_entry":player.resources.power,"power_after_entry":before.resources.power,
            "options":options}),
        );
    }
    rows
}

pub fn facts(state: &GameState, player_id: PlayerId) -> Result<Value, RuleError> {
    let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
    let mut probe = state.clone();
    let mut final_track_vp = Vec::new();
    for level in 0..NAV_RANGE.len() {
        let target = probe.player_mut(player_id).ok_or(RuleError::NotYourTurn)?;
        target.research_tracks = crate::game_state::ResearchTracks::new();
        target.research_tracks.science = level as u8;
        let scores = crate::ScoringEngine::calculate_final_scoring_breakdown(&probe);
        let score = scores
            .iter()
            .find(|s| s.player_id == player_id)
            .ok_or(RuleError::NotYourTurn)?;
        final_track_vp.push(score.research_vp);
    }
    let mut rewards = serde_json::Map::new();
    for track in ResearchTrack::all() {
        let mut levels = Vec::new();
        for level in 0..NAV_RANGE.len() {
            let mut copy = state.clone();
            apply_research_level_reward(&mut copy, player_id, track, level as u8);
            levels.push(payout(
                player,
                copy.player(player_id).ok_or(RuleError::NotYourTurn)?,
            ));
        }
        rewards.insert(track.as_str().to_owned(), json!(levels));
    }
    let conditions = [
        RoundCondition::BuildMine,
        RoundCondition::TerraformingStep,
        RoundCondition::BuildMineOnGaia,
        RoundCondition::UpgradeTradingStation,
        RoundCondition::UpgradeLargeBuilding,
        RoundCondition::ResearchAdvance,
        RoundCondition::FormFederation,
    ];
    let action = |effect: Option<TechTileSpecialActionEffect>| {
        effect.map(|e| {
            json!({"ore":e.ore, "credits":e.credits, "knowledge":e.knowledge,
                             "qic":e.qic, "power_charge":e.charge_power})
        })
    };
    let mut tiles = Vec::new();
    for (advanced, ids) in [(false, 1..=13), (true, 1..=22)] {
        for id in ids {
            if advanced && id == 18 {
                continue;
            }
            let events: Vec<_> = conditions
                .iter()
                .filter_map(|condition| {
                    let value = if advanced {
                        advanced_tech_tile_event_vp_per_unit(id, condition)
                    } else {
                        tech_tile_event_vp_per_unit(id, condition)
                    };
                    value.map(|vp| json!({"condition":condition, "vp":vp}))
                })
                .collect();
            let pass = if advanced {
                advanced_tech_tile_pass_bonus(id).map(|(counter, vp)| {
                    tech_tile_counter_value(state, player_id, counter) as i32 * vp
                })
            } else {
                None
            };
            let mut copy = state.clone();
            let target = copy.player_mut(player_id).ok_or(RuleError::NotYourTurn)?;
            target.advanced_tech_tiles = if advanced {
                vec![crate::game_state::AdvancedTechTile(id)]
            } else {
                vec![]
            };
            let qic_vp_before = target.vp;
            apply_advanced_tech_qic_action_bonus(&mut copy, player_id);
            let qic_vp = copy.player(player_id).ok_or(RuleError::NotYourTurn)?.vp - qic_vp_before;
            let mut income_player = player.clone();
            income_player.resources.ore = 0;
            income_player.resources.credits = 0;
            income_player.resources.knowledge = 0;
            income_player.resources.qic = 0;
            income_player.tech_tiles = if advanced { vec![] } else { vec![TechTile(id)] };
            income_player.covered_tech_tiles.clear();
            let income_before = income_player.clone();
            let charge = apply_tech_tile_income(&mut income_player);
            let mut tile_income = payout(&income_before, &income_player);
            tile_income["power_charge"] = json!(charge);
            tiles.push(
                json!({"advanced":advanced,"id":id,"events":events,"pass_vp":pass,
                "qic_vp":qic_vp,"income":tile_income,
                "action":action(if advanced { advanced_tech_tile_special_action_effect(id) }
                               else { tech_tile_special_action_effect(id) })}),
            );
        }
    }
    let final_tiles: Vec<_> = state
        .final_scoring_tiles
        .iter()
        .map(|tile| {
            let values: Vec<_> = state
                .players
                .iter()
                .map(|p| {
                    json!([
                        p.player_id,
                        crate::ScoringEngine::final_scoring_metric(
                            state,
                            p.player_id,
                            &tile.condition
                        )
                    ])
                })
                .collect();
            json!({"condition":tile.condition,"values":values,
               "awards":[tile.vp_1st,tile.vp_2nd,tile.vp_3rd,0]})
        })
        .collect();
    let growth = player.faction == Some(FactionId::Ivits) && !player.federated_hexes.is_empty();
    let buildings: Vec<_> = player.structures.iter().filter(|s| growth || !player.federated_hexes.contains(&s.hex))
        .map(|s| json!({"coord":s.hex,"power":faction_structure_power_value(state, player_id, s.hex, s.kind)}))
        .collect();
    let mine_power: serde_json::Map<_, _> = state
        .board
        .hexes
        .keys()
        .map(|coord| {
            (
                format!("{},{}", coord.q, coord.r),
                json!(faction_structure_power_value(
                    state,
                    player_id,
                    *coord,
                    StructureType::Mine,
                )),
            )
        })
        .collect();
    let mut token_rewards = serde_json::Map::new();
    for token in &state.research_board.federation_tokens {
        let mut copy = state.clone();
        apply_federation_token_direct_reward(&mut copy, player_id, token.0);
        token_rewards.insert(
            token.0.to_string(),
            payout(
                player,
                copy.player(player_id).ok_or(RuleError::NotYourTurn)?,
            ),
        );
    }
    let sectors: serde_json::Map<_, _> = state
        .board
        .hexes
        .keys()
        .map(|coord| {
            (
                format!("{},{}", coord.q, coord.r),
                json!(MapEngine::sector_id_at(&state.board, *coord)),
            )
        })
        .collect();
    let mut upgrades = Vec::new();
    for structure in &player.structures {
        if is_lantids_cohabitation_target(state, player_id, structure.hex) {
            continue;
        }
        for target in upgrade_targets(player, structure.kind) {
            let (ore, credits) = upgrade_cost(
                &structure.kind,
                &target,
                has_opponent_structure_nearby(state, player_id, structure.hex),
            );
            upgrades
                .push(json!({"coord":structure.hex,"target":target,"ore":ore,"credits":credits}));
        }
    }
    Ok(json!({
        "navigation_range":NAV_RANGE,
        "terraform_ore_per_step":(0..NAV_RANGE.len()).map(|n| cost_for_distance(1,n as u8)).collect::<Vec<_>>(),
        "gaia_power_cost":GAIA_POWER_COST,
        "research_knowledge_cost":RESEARCH_KNOWLEDGE_COST,
        "final_track_vp":final_track_vp,
        "research_rewards":rewards,"sectors":sectors,"upgrades":upgrades,
        "income":income(state,player_id), "ships":ship_options(state,player_id),
        "active_power_tokens":active_power_tokens(&player.resources.power),
        "brainstone_return":({let mut copy = state.clone();
            if let Some(p) = copy.player_mut(player_id) {
                if p.resources.power.brainstone.is_some() { p.resources.power.brainstone = Some(BrainstoneLocation::Gaia); }
            }
            move_remaining_gaia_power(&mut copy,player_id);
            copy.player(player_id).and_then(|p| p.resources.power.brainstone)}),
        "colonized_types":colonized_planet_types(state,player_id),
        "tiles":tiles,"final_tiles":final_tiles,
        "federation":{"minimum_power":federation_minimum_power(player,growth),
                      "buildings":buildings,"mine_power":mine_power,
                      "growth":growth,"token_rewards":token_rewards},
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_utils::builders::GameStateBuilder;

    #[test]
    fn facts_are_native_and_do_not_mutate_state() {
        let state = GameStateBuilder::new().with_player_fn(0, |_| {}).build();
        let before = serde_json::to_string(&state).unwrap_or_default();
        let data = facts(&state, 0).unwrap_or_else(|e| panic!("facts: {e}"));
        assert_eq!(data["navigation_range"], json!(NAV_RANGE));
        assert_eq!(data["gaia_power_cost"], json!(GAIA_POWER_COST));
        for level in 0..NAV_RANGE.len() {
            assert_eq!(
                data["terraform_ore_per_step"][level],
                json!(cost_for_distance(1, level as u8))
            );
        }
        assert_eq!(data["final_track_vp"], json!([0, 0, 0, 4, 8, 12]));
        assert_eq!(before, serde_json::to_string(&state).unwrap_or_default());
    }
}
