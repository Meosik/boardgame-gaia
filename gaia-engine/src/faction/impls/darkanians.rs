use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlanetType, PlayerId, ResourceDelta, Resources,
};
use crate::map::MapEngine;

// ── DarkaniansAbility ────────────────────────────────────────────────────────

/// Lost Fleet expansion faction.
///
/// Rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`, p.13, Appendix I): "You start
/// the game with 1 mine instead of 2 ... Making a standard planet habitable
/// costs you 1 terraforming step, and making a Gaia planet habitable costs
/// 2 Q.I.C.s." Planetary Institute: "The first time the Darkanians colonize
/// a planet in a Space sector or Deep Space sector, they always gain
/// 2 credits and 1 knowledge. Interspace tiles do not count as sectors."
pub struct DarkaniansAbility;

impl FactionAbility for DarkaniansAbility {
    fn faction_id(&self) -> FactionId {
        FactionId::Darkanians
    }

    fn on_build(&self, state: &GameState, player_id: PlayerId, coord: HexCoord) -> Vec<GameEvent> {
        let Some(player) = state.player(player_id) else {
            return vec![];
        };
        if player.first_colonization_bonus_used {
            return vec![];
        }
        // Interspace tiles aren't modeled as sectors, so a hex that doesn't
        // resolve to any sector correctly does not trigger the bonus.
        match MapEngine::sector_category_at(&state.board, coord) {
            Some(_) => vec![GameEvent::ResourceChanged {
                player: player_id,
                delta: ResourceDelta {
                    credits: 2,
                    knowledge: 1,
                    ..ResourceDelta::zero()
                },
            }],
            None => vec![],
        }
    }

    fn on_research(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
        _track: &str,
        _new_level: u8,
    ) -> Vec<GameEvent> {
        vec![]
    }

    fn passive_income(&self, _state: &GameState, _player_id: PlayerId) -> Resources {
        Resources::zero()
    }

    fn special_action(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
    ) -> Result<Vec<GameEvent>, RuleError> {
        Ok(vec![])
    }

    fn final_scoring(&self, _state: &GameState, _player_id: PlayerId) -> i32 {
        0
    }

    fn federation_power_rule(&self) -> FederationPowerRule {
        FederationPowerRule::Standard
    }

    fn terraforming_distance_override(&self, _from: PlanetType, _to: PlanetType) -> Option<u8> {
        Some(1)
    }

    fn gaia_colonization_qic_cost(&self) -> u8 {
        2
    }
}
