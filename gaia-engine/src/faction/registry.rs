use std::collections::HashMap;
use std::sync::LazyLock;

use super::ability::FactionAbility;
use super::impls::{
    DarkaniansAbility, DefaultFactionAbility, LantidsAbility, SpaceGiantsAbility, TerransAbility,
    XenosAbility,
};
use crate::game_state::FactionId;

// ── FactionRegistry ───────────────────────────────────────────────────────────

/// Holds one `FactionAbility` implementation per faction.
///
/// Initialised with `DefaultFactionAbility` stubs for all 18 factions.
/// Future work: replace individual entries with real implementations.
pub struct FactionRegistry {
    map: HashMap<FactionId, Box<dyn FactionAbility>>,
}

impl FactionRegistry {
    pub fn new() -> Self {
        use FactionId::*;
        let all = [
            Terrans,
            Lantids,
            Xenos,
            Gleens,
            Taklons,
            Ambas,
            HadschHallas,
            Ivits,
            Geodens,
            BalTaks,
            Firaks,
            Bescods,
            Nevlas,
            Itars,
            Tinkeroids,
            Moweyds,
            SpaceGiants,
            Darkanians,
        ];

        let mut map: HashMap<FactionId, Box<dyn FactionAbility>> = HashMap::new();
        for fid in all {
            map.insert(fid, Box::new(DefaultFactionAbility { faction_id: fid }));
        }

        // Real implementations replace the stub as each faction's ability is coded.
        // Tinkeroids/Moweyds stay on the stub too, like Ambas/Firaks/Bescods/Ivits above them:
        // their abilities (Tinkering tiles, Power Rings, and the opponent-dependent 3-vs-1
        // terraforming split) are state-dependent in ways this trait's stateless per-faction
        // methods can't express, so `rules::engine` implements them directly via
        // `GameAction::TinkeroidsUseTile`/`MoweydsPlacePowerRing` and faction-id checks inside
        // `terraforming_distance`/`gaia_qic_cost`/`faction_structure_power_value` instead.
        map.insert(FactionId::Darkanians, Box::new(DarkaniansAbility));
        map.insert(FactionId::SpaceGiants, Box::new(SpaceGiantsAbility));
        map.insert(FactionId::Terrans, Box::new(TerransAbility));
        map.insert(FactionId::Lantids, Box::new(LantidsAbility));
        map.insert(FactionId::Xenos, Box::new(XenosAbility));

        Self { map }
    }

    /// Returns the ability implementation for the given faction.
    ///
    /// # Panics
    /// Never — all 18 factions are registered at construction time.
    pub fn get(&self, faction: FactionId) -> &dyn FactionAbility {
        self.map
            .get(&faction)
            .map(|b| b.as_ref())
            .unwrap_or_else(|| unreachable!("FactionRegistry always contains all 18 factions"))
    }
}

impl Default for FactionRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ── Global instance ────────────────────────────────────────────────────────────

static REGISTRY: LazyLock<FactionRegistry> = LazyLock::new(FactionRegistry::new);

/// The shared `FactionRegistry` instance.
///
/// `FactionAbility` implementations are stateless per-faction lookups, not
/// part of a game's mutable state, so the registry lives as a process-wide
/// static rather than a `GameState` field (keeps the engine's serialized
/// state and its deterministic-transition contract unaffected).
pub fn global() -> &'static FactionRegistry {
    &REGISTRY
}
