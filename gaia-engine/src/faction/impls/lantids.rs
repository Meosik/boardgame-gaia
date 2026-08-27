use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlayerId, PowerCycle, Resources,
};

// ── LantidsAbility ───────────────────────────────────────────────────────────

/// Lost Fleet expansion adjustment (always enabled in this project).
///
/// Rulebook (`docs/GP_Exp_Rule_EN_V1_Web.pdf`, p.6, "Exploration Board"):
/// "For the Lantids, there is an adjustment that relates to their income
/// during the game: They gain 1 power in Area I." Confirmed against the
/// exploration board's own top icon (`gaia-frontend/src/assets/exploration_boards/lantida.jpg`,
/// a "+1" purple power token). This is a per-round income grant (fresh
/// token into bowl1, not a charge), on top of the base game's standard
/// income — everything else about Lantids (their normal Planetary
/// Institute ability, "build on an adjacent occupied planet") is
/// unaffected and stays unimplemented, matching every other stubbed method
/// here.
pub struct LantidsAbility;

impl FactionAbility for LantidsAbility {
    fn faction_id(&self) -> FactionId {
        FactionId::Lantids
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
        Resources {
            power: PowerCycle {
                bowl1: 1,
                ..PowerCycle::zero()
            },
            ..Resources::zero()
        }
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
}
