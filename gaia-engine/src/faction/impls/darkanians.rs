use crate::error::RuleError;
use crate::faction::ability::{FactionAbility, FederationPowerRule};
use crate::game_state::{
    FactionId, GameEvent, GameState, HexCoord, PlanetType, PlayerId, ResourceDelta, Resources,
    StructureType,
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
        if !player
            .structures
            .iter()
            .any(|s| s.kind == StructureType::PlanetaryInstitute)
        {
            return vec![];
        }
        let Some(sector_id) = MapEngine::sector_id_at(&state.board, coord) else {
            return vec![];
        };
        // The hook runs after placement: exclude the new colony itself. Existing
        // colonies (including pre-PI ones and the Lost Planet) already occupy a
        // sector, so no mutable reward flag or saved-game migration is needed.
        let already_colonized = player.structures.iter().any(|structure| {
            structure.hex != coord
                && MapEngine::sector_id_at(&state.board, structure.hex) == Some(sector_id)
        }) || state.board.hexes.values().any(|hex| {
            hex.coord != coord
                && hex.planet.as_ref().is_some_and(|planet| {
                    planet.planet_type == PlanetType::LostPlanet && planet.owner == Some(player_id)
                })
                && MapEngine::sector_id_at(&state.board, hex.coord) == Some(sector_id)
        });
        if already_colonized {
            return vec![];
        }
        vec![GameEvent::ResourceChanged {
            player: player_id,
            delta: ResourceDelta {
                credits: 2,
                knowledge: 1,
                ..ResourceDelta::zero()
            },
        }]
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
