use crate::faction::registry::global as faction_registry;
use crate::game_state::{
    FinalScoringCondition, GameEvent, GameState, HexCoord, PlanetType, PlayerId, StructureType,
    VpReason,
};
use crate::map::MapEngine;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Auditable components of one player's final score. `gameplay_vp` is the VP
/// already accumulated before final scoring; every other field is added at
/// game end according to rulebook p.18 or the faction's scoring hook.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct FinalScoreBreakdown {
    pub player_id: PlayerId,
    pub gameplay_vp: i32,
    /// Negative VP adjustment promised during setup bidding.
    pub bid_penalty_vp: i32,
    pub final_tile_vp: i32,
    pub research_vp: i32,
    pub resource_vp: i32,
    pub faction_vp: i32,
    pub total_vp: i32,
}

// ── ScoringEngine ─────────────────────────────────────────────────────────────

pub struct ScoringEngine;

impl ScoringEngine {
    // ── Round scoring ───────────────────────────────────────────────────────

    /// Returns VP earned by each player from the selected round's scoring tile.
    /// Qualifying actions award VP immediately, so this aggregates the
    /// auditable `VpAwarded(RoundTile)` events instead of re-deriving complex
    /// predicates such as new planet types or terraforming steps.
    pub fn calculate_round_scoring(state: &GameState, round: u8) -> Vec<(PlayerId, i32)> {
        let tile = match state.round_tiles.get((round as usize).saturating_sub(1)) {
            Some(t) => t,
            None => return vec![],
        };

        let mut totals: std::collections::HashMap<PlayerId, i32> = std::collections::HashMap::new();
        for event in &state.event_log {
            if let GameEvent::VpAwarded {
                player,
                amount,
                reason: VpReason::RoundTile { tile_id },
            } = event
            {
                if *tile_id == tile.id {
                    *totals.entry(*player).or_default() += *amount;
                }
            }
        }
        totals.into_iter().collect()
    }

    // ── Final scoring ───────────────────────────────────────────────────────

    /// Computes the final score totals for all 4 players.
    pub fn calculate_final_scoring(state: &GameState) -> [(PlayerId, i32); 4] {
        Self::calculate_final_scoring_breakdown(state)
            .map(|breakdown| (breakdown.player_id, breakdown.total_vp))
    }

    /// Computes an auditable final score breakdown for all 4 players.
    ///
    /// Components follow rulebook p.18: accumulated gameplay VP, two final
    /// scoring tiles, research levels, remaining resources, and any explicit
    /// faction final-scoring hook.
    pub fn calculate_final_scoring_breakdown(state: &GameState) -> [FinalScoreBreakdown; 4] {
        let mut final_tile_scores: std::collections::HashMap<PlayerId, i32> =
            std::collections::HashMap::new();
        for tile in &state.final_scoring_tiles {
            apply_final_tile_vp(
                state,
                &tile.condition,
                tile.vp_1st,
                tile.vp_2nd,
                tile.vp_3rd,
                &mut final_tile_scores,
            );
        }

        let mut result = [FinalScoreBreakdown::default(); 4];
        for (index, player) in state.players.iter().enumerate().take(4) {
            let res = &player.resources;
            let total_res = (res.ore as u32) + (res.credits as u32) + (res.knowledge as u32);
            let faction_vp = player.faction.map_or(0, |faction| {
                faction_registry()
                    .get(faction)
                    .final_scoring(state, player.player_id)
            });
            let mut breakdown = FinalScoreBreakdown {
                player_id: player.player_id,
                gameplay_vp: player.vp,
                bid_penalty_vp: -(player.setup_bid_vp as i32),
                final_tile_vp: final_tile_scores
                    .get(&player.player_id)
                    .copied()
                    .unwrap_or(0),
                research_vp: research_track_vp(&player.research_tracks),
                resource_vp: (total_res / 3) as i32,
                faction_vp,
                total_vp: 0,
            };
            breakdown.total_vp = breakdown.gameplay_vp
                + breakdown.bid_penalty_vp
                + breakdown.final_tile_vp
                + breakdown.research_vp
                + breakdown.resource_vp
                + breakdown.faction_vp;
            result[index] = breakdown;
        }
        result
    }

    /// Current progress value for one final-scoring condition. Exposed so
    /// clients/tests can show and verify the same metric used for ranking.
    pub fn final_scoring_metric(
        state: &GameState,
        player_id: PlayerId,
        condition: &FinalScoringCondition,
    ) -> u32 {
        metric_for_condition(state, player_id, condition)
    }
}

// ── Final tile helpers ────────────────────────────────────────────────────────

fn apply_final_tile_vp(
    state: &GameState,
    condition: &FinalScoringCondition,
    vp_1st: u8,
    vp_2nd: u8,
    vp_3rd: u8,
    scores: &mut std::collections::HashMap<PlayerId, i32>,
) {
    let mut ranked: Vec<(PlayerId, u32)> = state
        .players
        .iter()
        .map(|p| {
            (
                p.player_id,
                metric_for_condition(state, p.player_id, condition),
            )
        })
        .collect();
    for (player_id, vp) in ranked_vp_awards(
        &mut ranked,
        [vp_1st as u32, vp_2nd as u32, vp_3rd as u32, 0],
    ) {
        *scores.entry(player_id).or_default() += vp;
    }
}

/// Rulebook p.18 tie rule: a tied group pools the VP for every rank it
/// occupies and divides that pool evenly. For example, two tied first-place
/// players each receive `(18 + 12) / 2 = 15`, not `18 / 2 = 9`.
fn ranked_vp_awards(ranked: &mut [(PlayerId, u32)], rank_vp: [u32; 4]) -> Vec<(PlayerId, i32)> {
    ranked.sort_by_key(|entry| std::cmp::Reverse(entry.1));

    let mut awards = Vec::with_capacity(ranked.len());
    let mut rank_index = 0;
    while rank_index < ranked.len() {
        let metric = ranked[rank_index].1;
        let group_end =
            ranked[rank_index..].partition_point(|(_, value)| *value == metric) + rank_index;
        let group_size = group_end - rank_index;
        let pool: u32 = (rank_index..group_end)
            .map(|occupied_rank| rank_vp.get(occupied_rank).copied().unwrap_or(0))
            .sum();
        let share = (pool / group_size as u32) as i32;
        awards.extend(
            ranked[rank_index..group_end]
                .iter()
                .map(|(player_id, _)| (*player_id, share)),
        );
        rank_index = group_end;
    }
    awards
}

fn metric_for_condition(
    state: &GameState,
    player_id: PlayerId,
    condition: &FinalScoringCondition,
) -> u32 {
    let player = match state.player(player_id) {
        Some(p) => p,
        None => return 0,
    };
    match condition {
        FinalScoringCondition::MostStructuresInFederation => {
            let federated_hexes: HashSet<HexCoord> = state
                .event_log
                .iter()
                .filter_map(|event| match event {
                    GameEvent::FederationFormed { player, hexes, .. } if *player == player_id => {
                        Some(hexes.as_slice())
                    }
                    _ => None,
                })
                .flatten()
                .copied()
                .collect();
            player
                .structures
                .iter()
                .filter(|structure| {
                    federated_hexes.contains(&structure.hex) && is_scoring_building(structure.kind)
                })
                .count() as u32
        }
        FinalScoringCondition::MostBuildings => {
            let tracked = player
                .structures
                .iter()
                .filter(|structure| is_scoring_building(structure.kind))
                .count() as u32;
            tracked + untracked_lost_planet_mine(state, player_id)
        }
        FinalScoringCondition::MostPlanetTypes => {
            let types: HashSet<PlanetType> = colonized_planets(state, player_id)
                .into_iter()
                .map(|(_, planet)| {
                    normalized_planet_type(planet.planet_type, planet.is_gaia_formed)
                })
                .collect();
            types.len() as u32
        }
        FinalScoringCondition::MostGaiaPlanets => colonized_planets(state, player_id)
            .into_iter()
            .filter(|(_, planet)| {
                normalized_planet_type(planet.planet_type, planet.is_gaia_formed)
                    == PlanetType::Gaia
            })
            .count() as u32,
        FinalScoringCondition::MostSectors => {
            occupied_sector_count(state, player_id, crate::data::SectorCategory::Standard)
        }
        FinalScoringCondition::MostSatellites => {
            let satellites = state
                .board
                .hexes
                .values()
                .map(|hex| {
                    hex.satellites
                        .iter()
                        .filter(|owner| **owner == player_id)
                        .count() as u32
                })
                .sum::<u32>();
            let space_stations = player
                .structures
                .iter()
                .filter(|structure| structure.kind == StructureType::SpaceStation)
                .count() as u32;
            satellites + space_stations
        }
        FinalScoringCondition::MostDeepSpaceSectors => {
            occupied_sector_count(state, player_id, crate::data::SectorCategory::DeepSpace)
        }
        FinalScoringCondition::MostAsteroids => colonized_planets(state, player_id)
            .into_iter()
            .filter(|(_, planet)| planet.planet_type == PlanetType::Asteroid)
            .count() as u32,
        FinalScoringCondition::GreatestDistancePiAcademy => {
            let planetary_institutes: Vec<HexCoord> = player
                .structures
                .iter()
                .filter(|structure| structure.kind == StructureType::PlanetaryInstitute)
                .map(|structure| structure.hex)
                .collect();
            let academies: Vec<HexCoord> = player
                .structures
                .iter()
                .filter(|structure| matches!(structure.kind, StructureType::Academy(_)))
                .map(|structure| structure.hex)
                .collect();
            planetary_institutes
                .iter()
                .flat_map(|pi| academies.iter().map(move |academy| pi.distance(academy)))
                .max()
                .unwrap_or(0)
        }
    }
}

fn is_scoring_building(kind: StructureType) -> bool {
    !matches!(kind, StructureType::Satellite | StructureType::SpaceStation)
}

fn normalized_planet_type(planet_type: PlanetType, is_gaia_formed: bool) -> PlanetType {
    if is_gaia_formed {
        PlanetType::Gaia
    } else {
        planet_type
    }
}

fn colonized_planets(
    state: &GameState,
    player_id: PlayerId,
) -> Vec<(HexCoord, &crate::game_state::Planet)> {
    let structure_hexes: HashSet<HexCoord> = state
        .player(player_id)
        .into_iter()
        .flat_map(|player| player.structures.iter().map(|structure| structure.hex))
        .collect();
    state
        .board
        .hexes
        .iter()
        .filter_map(|(coord, hex)| {
            let planet = hex.planet.as_ref()?;
            (planet.owner == Some(player_id) || structure_hexes.contains(coord))
                .then_some((*coord, planet))
        })
        .collect()
}

fn occupied_sector_count(
    state: &GameState,
    player_id: PlayerId,
    category: crate::data::SectorCategory,
) -> u32 {
    colonized_planets(state, player_id)
        .into_iter()
        .filter_map(|(coord, _)| MapEngine::sector_id_at(&state.board, coord))
        .filter(|sector_id| crate::data::category_for_sector(*sector_id) == category)
        .collect::<HashSet<_>>()
        .len() as u32
}

fn untracked_lost_planet_mine(state: &GameState, player_id: PlayerId) -> u32 {
    let Some(coord) = state.board.lost_planet else {
        return 0;
    };
    let is_colonized = state
        .board
        .hexes
        .get(&coord)
        .and_then(|hex| hex.planet.as_ref())
        .is_some_and(|planet| planet.owner == Some(player_id));
    let is_tracked = state.player(player_id).is_some_and(|player| {
        player
            .structures
            .iter()
            .any(|structure| structure.hex == coord)
    });
    u32::from(is_colonized && !is_tracked)
}

/// Rulebook p.18: for each level 3, 4, 5 reached, gain 4 VP (cumulative per track).
/// e.g. level 5 in Navigation = 4+4+4 = 12 VP.
fn research_track_vp(tracks: &crate::game_state::ResearchTracks) -> i32 {
    let all = [
        tracks.terraforming,
        tracks.navigation,
        tracks.ai,
        tracks.gaia,
        tracks.economy,
        tracks.science,
    ];
    all.iter()
        .map(|&level| {
            // Count how many of levels 3, 4, 5 were reached
            let levels_reached = level.saturating_sub(2).min(3) as i32;
            levels_reached * 4
        })
        .sum()
}

#[cfg(test)]
mod tests {
    use super::ranked_vp_awards;

    #[test]
    fn tied_first_place_pools_first_and_second_rank_vp() {
        let mut ranked = [(0, 5), (1, 5), (2, 3), (3, 1)];

        let awards = ranked_vp_awards(&mut ranked, [18, 12, 6, 0]);

        assert!(awards.contains(&(0, 15)));
        assert!(awards.contains(&(1, 15)));
        assert!(awards.contains(&(2, 6)));
        assert!(awards.contains(&(3, 0)));
    }

    #[test]
    fn tied_second_place_pools_second_and_third_rank_vp() {
        let mut ranked = [(0, 6), (1, 4), (2, 4), (3, 1)];

        let awards = ranked_vp_awards(&mut ranked, [18, 12, 6, 0]);

        assert!(awards.contains(&(0, 18)));
        assert!(awards.contains(&(1, 9)));
        assert!(awards.contains(&(2, 9)));
        assert!(awards.contains(&(3, 0)));
    }

    #[test]
    fn four_way_tie_splits_all_rank_vp() {
        let mut ranked = [(0, 0), (1, 0), (2, 0), (3, 0)];

        let awards = ranked_vp_awards(&mut ranked, [18, 12, 6, 0]);

        assert!(awards.iter().all(|(_, vp)| *vp == 9));
    }
}
