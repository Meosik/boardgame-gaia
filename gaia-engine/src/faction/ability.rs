use crate::error::RuleError;
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlanetType, PlayerId, PowerBowl, Resources,
};

// ── FederationPowerRule ───────────────────────────────────────────────────────

/// Controls how federation power is counted for a given faction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FederationPowerRule {
    /// Standard rule: sum structure power values within a connected group.
    Standard,
    /// Ivits: space stations count toward power; range limited by navigation track.
    IvitsRule,
    /// Faction-specific override with a custom minimum power threshold.
    Custom(u32),
}

// ── FactionAbility trait ──────────────────────────────────────────────────────

/// Per-faction game-rule overrides and hooks.
///
/// All methods have cheap default stubs so only rules that deviate from
/// standard behaviour need to be overridden in real faction implementations.
pub trait FactionAbility: Send + Sync {
    fn faction_id(&self) -> FactionId;

    /// Whether this faction currently exposes a turn-consuming special
    /// action through [`Self::special_action`]. Unsupported/stub factions
    /// must remain `false` so the engine cannot consume a turn for no effect.
    fn has_special_action(&self) -> bool {
        false
    }

    /// Triggered after a Mine is successfully placed on `coord`.
    /// Returns additional events to append (e.g. Lantids building on occupied hexes).
    fn on_build(&self, state: &GameState, player_id: PlayerId, coord: HexCoord) -> Vec<GameEvent>;

    /// Triggered after a research track advances to `new_level`.
    /// Returns bonus events (e.g. Itars converting power to tech tiles).
    fn on_research(
        &self,
        state: &GameState,
        player_id: PlayerId,
        track: &str,
        new_level: u8,
    ) -> Vec<GameEvent>;

    /// Extra resources granted during the income phase beyond standard income.
    fn passive_income(&self, state: &GameState, player_id: PlayerId) -> Resources;

    /// Execute the faction's unique special action; returns resulting events.
    fn special_action(
        &self,
        state: &GameState,
        player_id: PlayerId,
    ) -> Result<Vec<GameEvent>, RuleError>;

    /// Additional VP earned during final scoring (beyond standard tile scoring).
    fn final_scoring(&self, state: &GameState, player_id: PlayerId) -> i32;

    /// Override the federation-power accounting rule for this faction.
    fn federation_power_rule(&self) -> FederationPowerRule;

    /// Override the terraforming distance (in ring-steps) between two planet
    /// types for this faction, replacing the standard `ring_distance` lookup.
    /// `None` (the default) means "use the standard rule."
    fn terraforming_distance_override(&self, _from: PlanetType, _to: PlanetType) -> Option<u8> {
        None
    }

    /// QIC cost to colonize an already Gaia-formed planet. The standard rule
    /// (rulebook p.11) is 1 QIC; some Lost Fleet factions pay 2 instead.
    fn gaia_colonization_qic_cost(&self) -> u8 {
        1
    }

    /// Which power bowl the Gaia phase moves this faction's Gaia-area power
    /// into. Standard rule (rulebook p.11) is Area I; the Terrans move it
    /// directly to Area II instead.
    fn gaia_phase_power_destination(&self) -> PowerBowl {
        PowerBowl::Area1
    }
}

// ── stub_faction_ability! ─────────────────────────────────────────────────────

/// Generates a complete `FactionAbility` impl for a struct that has a
/// `faction_id: FactionId` field.  Every method logs a warning and returns
/// the appropriate "no effect" default so the game continues without
/// panicking while individual factions are being fleshed out.
///
/// ```ignore
/// struct TerransAbility { faction_id: FactionId }
/// stub_faction_ability!(TerransAbility);
/// ```
#[macro_export]
macro_rules! stub_faction_ability {
    ($struct_name:ident) => {
        impl $crate::faction::ability::FactionAbility for $struct_name {
            fn faction_id(&self) -> $crate::game_state::FactionId {
                self.faction_id
            }

            fn on_build(
                &self,
                _state: &$crate::game_state::GameState,
                _player_id: $crate::game_state::PlayerId,
                _coord: $crate::game_state::HexCoord,
            ) -> Vec<$crate::game_state::GameEvent> {
                log::warn!(
                    "on_build stub — {:?} faction ability not yet implemented",
                    self.faction_id
                );
                vec![]
            }

            fn on_research(
                &self,
                _state: &$crate::game_state::GameState,
                _player_id: $crate::game_state::PlayerId,
                _track: &str,
                _new_level: u8,
            ) -> Vec<$crate::game_state::GameEvent> {
                log::warn!(
                    "on_research stub — {:?} faction ability not yet implemented",
                    self.faction_id
                );
                vec![]
            }

            fn passive_income(
                &self,
                _state: &$crate::game_state::GameState,
                _player_id: $crate::game_state::PlayerId,
            ) -> $crate::game_state::Resources {
                log::warn!(
                    "passive_income stub — {:?} faction ability not yet implemented",
                    self.faction_id
                );
                $crate::game_state::Resources::zero()
            }

            fn special_action(
                &self,
                _state: &$crate::game_state::GameState,
                _player_id: $crate::game_state::PlayerId,
            ) -> Result<Vec<$crate::game_state::GameEvent>, $crate::error::RuleError> {
                log::warn!(
                    "special_action stub — {:?} faction ability not yet implemented",
                    self.faction_id
                );
                Ok(vec![])
            }

            fn final_scoring(
                &self,
                _state: &$crate::game_state::GameState,
                _player_id: $crate::game_state::PlayerId,
            ) -> i32 {
                log::warn!(
                    "final_scoring stub — {:?} faction ability not yet implemented",
                    self.faction_id
                );
                0
            }

            fn federation_power_rule(&self) -> $crate::faction::ability::FederationPowerRule {
                $crate::faction::ability::FederationPowerRule::Standard
            }
        }
    };
}
