use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlanetType, PlayerId, Resources,
};

// ── SpaceGiantsAbility ───────────────────────────────────────────────────────

/// Lost Fleet expansion faction.
///
/// Rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`, p.13, Appendix I): "You start
/// the game with 1 instead of 2 mines ... When terraforming a standard
/// planet, you require 2 terraforming steps ... Making a Gaia planet
/// habitable costs 2 Q.I.C.s." Planetary Institute: "Immediately take
/// 1 Tech tile of your choice. The same rules apply as for the action
/// 'Upgrade Existing Structures'. You may only perform this ability once."
pub struct SpaceGiantsAbility;

impl FactionAbility for SpaceGiantsAbility {
    fn faction_id(&self) -> FactionId {
        FactionId::SpaceGiants
    }

    fn on_build(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
        _coord: HexCoord,
    ) -> Vec<GameEvent> {
        vec![]
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
        Err(RuleError::ActionNotAllowed(
            "Space Giants must choose a Tech tile for their Planetary Institute ability"
                .to_string(),
        ))
    }

    fn final_scoring(&self, _state: &GameState, _player_id: PlayerId) -> i32 {
        0
    }

    fn federation_power_rule(&self) -> FederationPowerRule {
        FederationPowerRule::Standard
    }

    fn terraforming_distance_override(&self, _from: PlanetType, _to: PlanetType) -> Option<u8> {
        Some(2)
    }

    fn gaia_colonization_qic_cost(&self) -> u8 {
        2
    }
}
