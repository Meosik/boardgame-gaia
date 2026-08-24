use crate::game_state::FactionId;
use crate::stub_faction_ability;

// ── DefaultFactionAbility ─────────────────────────────────────────────────────

/// Catch-all stub implementation used for all 18 factions until their real
/// abilities are coded.  Each method logs a warning and returns the
/// zero-effect default so the engine keeps running during development.
pub struct DefaultFactionAbility {
    pub faction_id: FactionId,
}

stub_faction_ability!(DefaultFactionAbility);
