//! Decision interface for offline agents. UI helpers intentionally need not enumerate every
//! compound choice; this interface does. A bounded federation search can omit federation
//! candidates with a warning, but never replaces other legal decisions with a forced pass.
use super::*;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "phase", content = "action")]
pub enum AiDecision {
    Setup(SetupAction),
    Game(GameAction),
}

/// One candidate-generation call, not a count of real game decisions or search branches.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct AiCandidateDiagnostics {
    pub federation_limit_hits: u64,
    pub federation_limit_reasons: Vec<String>,
}

#[derive(Debug, thiserror::Error)]
pub enum AiActionError {
    #[error("unsupported autonomous phase: {0:?}")]
    UnsupportedPhase(GamePhase),
    #[error("no legal decisions for player {0}")]
    Empty(PlayerId),
    #[error("federation search exceeded its explicit resource limit ({0})")]
    SearchLimit(&'static str),
    #[error(transparent)]
    Rule(#[from] RuleError),
    #[error(transparent)]
    Serialization(#[from] serde_json::Error),
}

impl RuleEngine {
    /// Pending responses belong to the queued player, not to the interrupted turn's owner.
    pub fn decision_player(state: &GameState) -> Result<Option<PlayerId>, AiActionError> {
        let player = match &state.phase {
            GamePhase::Setup(SetupPhase::StartingStructures { active_player, .. }
                | SetupPhase::StartingBoosters { active_player, .. }
                | SetupPhase::FactionSelection { active_player }
                | SetupPhase::Bidding { active_player }) => *active_player,
            GamePhase::Setup(SetupPhase::BiddingChoice { winner }) => *winner,
            GamePhase::ActionPhase { active_player } => *state.turn_order.get(*active_player)
                .ok_or_else(|| AiActionError::UnsupportedPhase(state.phase.clone()))?,
            GamePhase::LostPlanetPlacementPending { player, .. }
                | GamePhase::TinkeroidsTileSelectionPending { player, .. } => *player,
            GamePhase::ChargePowerPending { queue, .. }
                | GamePhase::LostPlanetChargePowerPending { queue, .. } => queue.first()
                    .ok_or_else(|| AiActionError::UnsupportedPhase(state.phase.clone()))?.player,
            GamePhase::IncomeOrderPending { queue, .. } => queue.first()
                .ok_or_else(|| AiActionError::UnsupportedPhase(state.phase.clone()))?.player,
            GamePhase::GaiaDecisionPending { queue, .. } => queue.first()
                .ok_or_else(|| AiActionError::UnsupportedPhase(state.phase.clone()))?.player,
            GamePhase::Ended { .. } => return Ok(None),
            _ => return Err(AiActionError::UnsupportedPhase(state.phase.clone())),
        };
        Ok(Some(player))
    }

    /// Run only transitions which do not involve a player decision. Unknown phases fail closed.
    pub fn advance_automatic(state: &mut GameState) -> Result<(), AiActionError> {
        loop {
            match &state.phase {
                GamePhase::Setup(SetupPhase::Complete) => { Self::start_first_round(state)?; }
                GamePhase::RoundScoring { round: 6 } => { Self::finalize_game(state)?; }
                GamePhase::RoundScoring { .. } => { Self::advance_to_next_round(state)?; }
                _ => { Self::decision_player(state)?; return Ok(()); }
            }
        }
    }

    /// Concrete stable candidates. Setup bidding is intentionally outside the initial RL scope.
    pub fn ai_decisions(state: &GameState) -> Result<Vec<AiDecision>, AiActionError> {
        Self::ai_decisions_with_diagnostics(state).map(|(decisions, _)| decisions)
    }

    pub fn ai_decisions_with_diagnostics(
        state: &GameState,
    ) -> Result<(Vec<AiDecision>, AiCandidateDiagnostics), AiActionError> {
        let mut diagnostics = AiCandidateDiagnostics::default();
        let Some(player_id) = Self::decision_player(state)? else {
            return Ok((Vec::new(), diagnostics));
        };
        let mut decisions = Vec::new();
        if let GamePhase::Setup(phase) = &state.phase {
            let candidates: Vec<SetupAction> = match phase {
                SetupPhase::StartingStructures { .. } => state.board.hexes.keys()
                    .map(|&coord| SetupAction::PlaceStartingStructure { coord }).collect(),
                SetupPhase::StartingBoosters { .. } => state.boosters.iter()
                    .map(|b| SetupAction::SelectStartingBooster { booster_id: b.0 }).collect(),
                SetupPhase::FactionSelection { .. } => state.faction_selection.as_ref()
                    .map(|s| s.available_factions.iter().map(|&faction| SetupAction::SelectFaction { faction }).collect())
                    .unwrap_or_default(),
                _ => return Err(AiActionError::UnsupportedPhase(state.phase.clone())),
            };
            // Setup currently has a combined validate/apply API. Validate against a clone so a
            // rejected candidate cannot alter the real state, auction or setup selection order.
            for action in candidates {
                if Self::apply_setup_action(&mut state.clone(), player_id, action.clone()).is_ok() {
                    decisions.push(AiDecision::Setup(action));
                }
            }
        } else {
            let mut actions = Self::get_valid_actions(state, player_id);
            if matches!(state.phase, GamePhase::ActionPhase { .. }) {
                let player = state.player(player_id).ok_or(RuleError::NotYourTurn)?;
                // UI representatives use count 1. AI also needs concrete batches, notably
                // Nevlas PI conversions whose odd power costs can share a token in a batch.
                for kind in FreeActionKind::ALL {
                    for count in 2..=MAX_FREE_ACTION_COUNT {
                        actions.push(GameAction::FreeAction { kind, count });
                    }
                }
                for booster in &state.boosters {
                    actions.push(GameAction::Pass { booster_id: Some(booster.0) });
                }
                for id in 1..=7 {
                    actions.push(GameAction::PowerAction { id, coord: None });
                    if free_terraform_steps_for_power_action(id) > 0 {
                        for &coord in state.board.hexes.keys() {
                            actions.push(GameAction::PowerAction { id, coord: Some(coord) });
                        }
                    }
                }
                for tile in &player.tech_tiles {
                    actions.push(GameAction::TechTileSpecialAction { tile: TechTileRef::Standard { tile: tile.clone() } });
                }
                for tile in &player.advanced_tech_tiles {
                    actions.push(GameAction::TechTileSpecialAction { tile: TechTileRef::Advanced { tile: tile.clone() } });
                }
                let choices = valid_tech_tile_choices(state, player_id);
                for structure in &player.structures {
                    for to in upgrade_targets(player, structure.kind) {
                        for choice in &choices {
                            actions.push(GameAction::Upgrade { coord: structure.hex, to, tech_tile_choice: Some(choice.clone()) });
                        }
                    }
                    if structure.kind == StructureType::TradingStation {
                        for choice in &choices {
                            actions.push(GameAction::TwilightFreeResearchLab { coord: structure.hex, tech_tile_choice: Some(choice.clone()) });
                        }
                    }
                }
                if let Some(reason) = append_federation_candidates(
                    &mut actions, federation_candidates(state, player_id), player_id,
                )? {
                    diagnostics.federation_limit_hits += 1;
                    diagnostics.federation_limit_reasons.push(reason);
                }
            }
            decisions.extend(actions.into_iter()
                .filter(|a| Self::validate_action(state, player_id, a).is_ok())
                .map(AiDecision::Game));
        }
        let mut stable = BTreeMap::new();
        for decision in decisions {
            stable.insert(serde_json::to_string(&decision)?, decision);
        }
        if stable.is_empty() { return Err(AiActionError::Empty(player_id)); }
        Ok((stable.into_values().collect(), diagnostics))
    }
}

fn append_federation_candidates(
    actions: &mut Vec<GameAction>,
    result: Result<Vec<GameAction>, AiActionError>,
    player_id: PlayerId,
) -> Result<Option<String>, AiActionError> {
    match result {
        Ok(candidates) => actions.extend(candidates),
        Err(AiActionError::SearchLimit(limit)) => {
            log::warn!("Player {player_id}: federation search exceeded {limit}; retaining other legal actions");
            return Ok(Some(limit.to_owned()));
        }
        Err(error) => return Err(error),
    }
    Ok(None)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn federation_limit_preserves_other_actions_but_other_errors_propagate() {
        let original = vec![GameAction::Pass { booster_id: None }, GameAction::PowerAction { id: 1, coord: None }];
        let mut actions = original.clone();
        append_federation_candidates(&mut actions, Err(AiActionError::SearchLimit("search work")), 0)
            .unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(actions, original);
        assert!(matches!(append_federation_candidates(&mut actions, Err(RuleError::NotYourTurn.into()), 0),
            Err(AiActionError::Rule(RuleError::NotYourTurn))));
        assert_eq!(actions, original);
        let candidate = GameAction::Pass { booster_id: Some(1) };
        append_federation_candidates(&mut actions, Ok(vec![candidate.clone()]), 0)
            .unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(actions, [original, vec![candidate]].concat());
    }
}

#[path = "ai_federation.rs"]
mod federation;
use federation::federation_candidates;
