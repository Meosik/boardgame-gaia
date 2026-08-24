use crate::faction::registry::global as faction_registry;
use crate::game_state::{FinalScoringCondition, GameEvent, GameState, PlayerId, RoundCondition};
use crate::map::MapEngine;

// ── ScoringEngine ─────────────────────────────────────────────────────────────

pub struct ScoringEngine;

impl ScoringEngine {
    // ── Round scoring ───────────────────────────────────────────────────────

    /// Returns VP earned by each player from the current round's scoring tile.
    /// Scans the event log for actions that triggered round-tile bonuses.
    pub fn calculate_round_scoring(state: &GameState, round: u8) -> Vec<(PlayerId, i32)> {
        let tile = match state.round_tiles.get((round as usize).saturating_sub(1)) {
            Some(t) => t,
            None => return vec![],
        };

        let vp_per = tile.vp_per_unit as i32;
        let _tile_id = tile.id;
        let condition = &tile.condition;

        // Count qualifying events in this round
        let mut counts: std::collections::HashMap<PlayerId, i32> = std::collections::HashMap::new();

        for event in &state.event_log {
            match (condition, event) {
                (
                    RoundCondition::BuildMine,
                    GameEvent::StructureBuilt {
                        player,
                        kind: crate::game_state::StructureType::Mine,
                        ..
                    },
                ) => {
                    *counts.entry(*player).or_default() += 1;
                }

                (RoundCondition::Upgrade, GameEvent::StructureUpgraded { player, .. }) => {
                    *counts.entry(*player).or_default() += 1;
                }

                (RoundCondition::ResearchAdvance, GameEvent::ResearchAdvanced { player, .. }) => {
                    *counts.entry(*player).or_default() += 1;
                }

                (RoundCondition::GaiaProject, GameEvent::GaiaFormingComplete { player, .. }) => {
                    *counts.entry(*player).or_default() += 1;
                }

                (RoundCondition::FormFederation, GameEvent::FederationFormed { player, .. }) => {
                    *counts.entry(*player).or_default() += 1;
                }

                (
                    RoundCondition::BuildAcademy,
                    GameEvent::StructureBuilt {
                        player,
                        kind: crate::game_state::StructureType::Academy(_),
                        ..
                    },
                ) => {
                    *counts.entry(*player).or_default() += 1;
                }

                _ => {}
            }
        }

        counts
            .into_iter()
            .map(|(player, count)| (player, count * vp_per))
            .collect()
    }

    // ── Final scoring ───────────────────────────────────────────────────────

    /// Computes the full final score breakdown for all 4 players.
    ///
    /// Components (in order):
    /// 1. Final scoring tiles (2 tiles, 9-tile pool including Lost Fleet)
    /// 2. Gaia Project VP (2 VP per Gaia-formed planet with a mine)
    /// 3. Research track VP (4/8/12 for tracks ≥ 3/4/5)
    /// 4. Resource conversion (1 VP per 3 resources remaining)
    /// 5. Faction special final scoring
    /// 6. Bid VP deduction
    pub fn calculate_final_scoring(state: &GameState) -> [(PlayerId, i32); 4] {
        let mut scores: std::collections::HashMap<PlayerId, i32> =
            state.players.iter().map(|p| (p.player_id, p.vp)).collect();

        // 1. Final scoring tiles
        for tile in &state.final_scoring_tiles {
            apply_final_tile_vp(
                state,
                &tile.condition,
                tile.vp_1st,
                tile.vp_2nd,
                tile.vp_3rd,
                &mut scores,
            );
        }

        // 2. Research track VP
        for player in &state.players {
            let track_vp = research_track_vp(&player.research_tracks);
            *scores.entry(player.player_id).or_default() += track_vp;
        }

        // 3. Resource conversion (rulebook p.18: 1 VP per 3 credits/knowledge/ore in any combination)
        for player in &state.players {
            let res = &player.resources;
            let total_res = (res.ore as u32) + (res.credits as u32) + (res.knowledge as u32);
            *scores.entry(player.player_id).or_default() += (total_res / 3) as i32;
        }

        // 5. Faction special final scoring
        for player in &state.players {
            if let Some(faction) = player.faction {
                let bonus = faction_registry()
                    .get(faction)
                    .final_scoring(state, player.player_id);
                *scores.entry(player.player_id).or_default() += bonus;
            }
        }

        // Build sorted result array (players 0-3)
        let mut result = [(0u8, 0i32); 4];
        for (i, player) in state.players.iter().enumerate().take(4) {
            let vp = scores.get(&player.player_id).copied().unwrap_or(0);
            result[i] = (player.player_id, vp);
        }
        result
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
    ranked.sort_by_key(|entry| std::cmp::Reverse(entry.1));

    // Tie-sharing: players with equal metric share the combined VP evenly
    let distribute = |group: &[(PlayerId, u32)],
                      pool: u32,
                      scores: &mut std::collections::HashMap<PlayerId, i32>| {
        let share = pool / group.len() as u32;
        for (pid, _) in group {
            *scores.entry(*pid).or_default() += share as i32;
        }
    };

    let mut i = 0;
    let places = [(vp_1st as u32, 1), (vp_2nd as u32, 2), (vp_3rd as u32, 3)];
    for (vp, _place) in &places {
        if i >= ranked.len() {
            break;
        }
        let val = ranked[i].1;
        let group_end = ranked[i..].partition_point(|(_, v)| *v == val) + i;
        let group = &ranked[i..group_end];
        distribute(group, *vp * group.len() as u32 / group.len() as u32, scores);
        i = group_end;
    }
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
    use crate::game_state::{PlanetType, StructureType};
    match condition {
        // Structures that are part of a federation (mine=1, TS/Lab=2, PI/Academy=3)
        FinalScoringCondition::MostStructuresInFederation => {
            // Simplified: count structures on planets that have a record token (part of federation)
            // Full implementation requires tracking federation membership per structure.
            // For now, use federation_tokens.len() as a proxy (each token = 1 federation's structures)
            player.federation_tokens.len() as u32
        }
        // All structures regardless of federation membership
        FinalScoringCondition::MostBuildings => player
            .structures
            .iter()
            .filter(|s| {
                !matches!(
                    s.kind,
                    StructureType::Satellite | StructureType::SpaceStation
                )
            })
            .count() as u32,
        // Number of distinct planet types colonized (Gaia + Lost Planet count as own types)
        FinalScoringCondition::MostPlanetTypes => {
            let mut types: std::collections::HashSet<String> = std::collections::HashSet::new();
            for s in &player.structures {
                if let Some(pt) = state
                    .board
                    .hexes
                    .get(&s.hex)
                    .and_then(|h| h.planet.as_ref())
                    .map(|p| format!("{:?}", p.planet_type))
                {
                    types.insert(pt);
                }
            }
            types.len() as u32
        }
        FinalScoringCondition::MostGaiaplanets => player
            .structures
            .iter()
            .filter(|s| {
                state
                    .board
                    .hexes
                    .get(&s.hex)
                    .and_then(|h| h.planet.as_ref())
                    .is_some_and(|p| p.is_gaia_formed)
            })
            .count() as u32,
        FinalScoringCondition::MostSectors => {
            MapEngine::sectors_occupied(&state.board, player_id) as u32
        }
        FinalScoringCondition::MostSatellites => player
            .structures
            .iter()
            .filter(|s| {
                matches!(
                    s.kind,
                    StructureType::Satellite | StructureType::SpaceStation
                )
            })
            .count() as u32,
        // ── Lost Fleet expansion ──────────────────────────────────────────
        FinalScoringCondition::MostExploredShips => player.explored_ships.len() as u32,
        FinalScoringCondition::MostSpecialPlanets => player
            .structures
            .iter()
            .filter(|s| {
                state
                    .board
                    .hexes
                    .get(&s.hex)
                    .and_then(|h| h.planet.as_ref())
                    .is_some_and(|p| {
                        matches!(
                            p.planet_type,
                            PlanetType::LostPlanet | PlanetType::Asteroid | PlanetType::ProtoPlanet
                        )
                    })
            })
            .count() as u32,
        FinalScoringCondition::HighestSingleTrack => player.research_tracks.max_level() as u32,
    }
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
