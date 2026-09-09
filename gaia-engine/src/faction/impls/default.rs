use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{FactionId, GameEvent, GameState, HexCoord, PlayerId, Resources};

// ── DefaultFactionAbility ─────────────────────────────────────────────────────

/// Standard no-op hook implementation for factions whose stateful rules live in
/// `rules::engine` rather than in this stateless trait.
///
/// A no-op hook is not evidence that the faction itself is unimplemented, so these methods stay
/// silent instead of emitting the old misleading "ability not yet implemented" warnings.
pub struct DefaultFactionAbility {
    pub faction_id: FactionId,
}

impl FactionAbility for DefaultFactionAbility {
    fn faction_id(&self) -> FactionId {
        self.faction_id
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
        FederationPowerRule::Standard
    }
}
