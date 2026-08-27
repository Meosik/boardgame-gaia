use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{FactionId, GameEvent, GameState, HexCoord, PlayerId, Resources};

/// Base-game Xenos ability implementation. Their third starting Mine and
/// Planetary Institute income are handled by setup/data respectively; this
/// hook supplies the remaining six-power federation threshold.
pub struct XenosAbility;

impl FactionAbility for XenosAbility {
    fn faction_id(&self) -> FactionId {
        FactionId::Xenos
    }

    fn on_build(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
        _coord: HexCoord,
    ) -> Vec<GameEvent> {
        Vec::new()
    }

    fn on_research(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
        _track: &str,
        _new_level: u8,
    ) -> Vec<GameEvent> {
        Vec::new()
    }

    fn passive_income(&self, _state: &GameState, _player_id: PlayerId) -> Resources {
        Resources::zero()
    }

    fn special_action(
        &self,
        _state: &GameState,
        _player_id: PlayerId,
    ) -> Result<Vec<GameEvent>, RuleError> {
        Ok(Vec::new())
    }

    fn final_scoring(&self, _state: &GameState, _player_id: PlayerId) -> i32 {
        0
    }

    fn federation_power_rule(&self) -> FederationPowerRule {
        FederationPowerRule::Custom(6)
    }
}
