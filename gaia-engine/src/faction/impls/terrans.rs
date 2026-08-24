use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlayerId, PowerBowl, Resources,
};

// ── TerransAbility ───────────────────────────────────────────────────────────

/// Base game faction.
///
/// Rulebook (`docs/EN_Gaia_rulebook_lo.pdf`, p.20, Appendix I): "During the
/// Gaia phase, move the power tokens in your Gaia area to area II of your
/// power cycle instead of to area I." Everything else (the Planetary
/// Institute's free-action resource conversion) remains unimplemented —
/// stubbed like every other ability method here.
pub struct TerransAbility;

impl FactionAbility for TerransAbility {
    fn faction_id(&self) -> FactionId {
        FactionId::Terrans
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
        Ok(vec![])
    }

    fn final_scoring(&self, _state: &GameState, _player_id: PlayerId) -> i32 {
        0
    }

    fn federation_power_rule(&self) -> FederationPowerRule {
        FederationPowerRule::Standard
    }

    fn gaia_phase_power_destination(&self) -> PowerBowl {
        PowerBowl::Area2
    }
}
