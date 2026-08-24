// IMPORTANT: This PRNG algorithm is locked to match JavaScript randomizer v2.3.2.
// DO NOT modify the hash function or bit operations.
// Cross-language reproducibility (Rust ↔ JS) is verified by test vectors in
// tests/property/prng_vectors.rs

use crate::error::SetupError;
use crate::game_state::{Booster, FactionId, FinalScoringCondition, FinalScoringTile};
use serde::{Deserialize, Serialize};

// ── Randomizer ────────────────────────────────────────────────────────────────

pub struct Randomizer {
    state: u32,
}

impl Randomizer {
    pub fn new(seed: &str) -> Self {
        // Hash seed as UTF-16 code points — matches JS String.charCodeAt()
        let mut h: u32 = 1779033703u32.wrapping_add(seed.encode_utf16().count() as u32);
        for ch in seed.encode_utf16() {
            h ^= ch as u32;
            h = h.wrapping_mul(3432918353);
            h = h.rotate_left(13);
        }
        Self { state: h }
    }

    /// Returns a pseudo-random f64 in [0.0, 1.0) — identical to JS randomizer.
    pub fn random(&mut self) -> f64 {
        let mut h = self.state;
        h ^= h >> 16;
        h = h.wrapping_mul(2246822507);
        h ^= h >> 13;
        h = h.wrapping_mul(3266489909);
        h ^= h >> 16;
        self.state = h;
        (h as f64) / 4294967296.0
    }

    /// Fisher-Yates shuffle — matches JS implementation.
    pub fn shuffle<T>(&mut self, arr: &mut [T]) {
        let n = arr.len();
        if n <= 1 {
            return;
        }
        for i in (1..n).rev() {
            let j = (self.random() * (i + 1) as f64) as usize;
            arr.swap(i, j);
        }
    }

    /// Generate a random integer in [0, n).
    pub fn random_int(&mut self, n: usize) -> usize {
        (self.random() * n as f64) as usize
    }

    /// Generate game setup from seed string.
    /// Returns `Err(InvalidSeed)` for empty or whitespace-only seeds.
    pub fn generate_setup(seed: &str) -> Result<GameSetup, SetupError> {
        if seed.trim().is_empty() {
            return Err(SetupError::InvalidSeed(
                "seed must not be empty".to_string(),
            ));
        }
        let mut rng = Self::new(seed);
        Ok(rng.build_setup())
    }

    fn build_setup(&mut self) -> GameSetup {
        // Step 1: every faction-board side is available for sequential choice.
        let factions = FactionId::all();

        // Step 2: Round tiles — shuffle pool, take 6
        let mut round_tile_ids: Vec<u8> = (1..=12).collect();
        self.shuffle(&mut round_tile_ids);
        let round_tile_ids: Vec<u8> = round_tile_ids.into_iter().take(6).collect();

        // Step 3: Boosters — shuffle pool, take 4+3=7
        let mut booster_ids: Vec<u8> = (1..=10).collect();
        self.shuffle(&mut booster_ids);
        let boosters: Vec<Booster> = booster_ids.into_iter().take(7).map(Booster).collect();

        // Step 4: Final scoring tiles — pool of 9 (6 base + 3 Lost Fleet), take 2
        let mut final_pool = all_final_scoring_tiles();
        self.shuffle(&mut final_pool);
        let final_scoring = [final_pool.remove(0), final_pool.remove(0)];

        // Step 5: Tech tiles — shuffle per-track pools (simplified: 1 tech tile per track slot)
        let mut tech_tile_ids: Vec<u8> = (1..=6).collect();
        self.shuffle(&mut tech_tile_ids);

        // Step 6: Sector layout
        // Center Balance sectors 01-04 fixed at center positions
        // Remaining sectors shuffled for outer positions
        let sector_layout = self.build_sector_layout();

        // Step 7: Deep Space Sectors (Lost Fleet) — always all 8 (ids 11-18)
        let deep_space_layout = self.build_deep_space_layout();

        GameSetup {
            factions,
            round_tile_ids,
            boosters,
            final_scoring,
            tech_tile_ids,
            sector_layout,
            deep_space_layout,
        }
    }

    fn build_sector_layout(&mut self) -> Vec<SectorPlacement> {
        use crate::game_state::HexCoord;

        // Center 4 sectors (Center Balance): fixed positions
        // 4-player only — no player_count branching.
        let center_positions = [
            HexCoord::new(0, 0),
            HexCoord::new(3, -2),
            HexCoord::new(-3, 2),
            HexCoord::new(0, -3),
        ];
        let center_rotations: Vec<u8> = (0..4).map(|_| self.random_int(6) as u8).collect();

        let mut placements: Vec<SectorPlacement> = center_positions
            .iter()
            .zip(center_rotations.iter())
            .enumerate()
            .map(|(i, (pos, &rot))| SectorPlacement {
                sector_id: (i + 1) as u8,
                side: None,
                origin: *pos,
                rotation: rot,
            })
            .collect();

        // Outer sectors: shuffle ids 5-10, assign to outer positions
        let outer_positions = [
            HexCoord::new(3, 1),
            HexCoord::new(-3, -1),
            HexCoord::new(0, 3),
            HexCoord::new(3, -3),
            HexCoord::new(-3, 3),
            HexCoord::new(0, -6),
        ];
        let mut outer_ids: Vec<u8> = (5..=10).collect();
        self.shuffle(&mut outer_ids);

        for (pos, id) in outer_positions.iter().zip(outer_ids.iter()) {
            let rot = self.random_int(6) as u8;
            let side = if *id <= 7 {
                Some(if self.random() < 0.5 { "A" } else { "B" }.to_string())
            } else {
                None
            };
            placements.push(SectorPlacement {
                sector_id: *id,
                side,
                origin: *pos,
                rotation: rot,
            });
        }

        placements
    }

    /// Always places all 8 Deep Space Sectors (ids 11-18, Lost Fleet expansion).
    /// Origins are set to (0,0) as a placeholder — actual positions require the
    /// lattice shift / hole-detection algorithm (TODO: map-data-model.md §4.6).
    fn build_deep_space_layout(&mut self) -> Vec<SectorPlacement> {
        use crate::game_state::HexCoord;

        let mut ds_ids: Vec<u8> = (11..=18).collect();
        self.shuffle(&mut ds_ids);

        ds_ids
            .into_iter()
            .map(|id| {
                let side = if self.random() < 0.5 { "A" } else { "B" };
                let rot = self.random_int(6) as u8;
                SectorPlacement {
                    sector_id: id,
                    side: Some(side.to_string()),
                    origin: HexCoord::new(0, 0), // placeholder — see §4.6
                    rotation: rot,
                }
            })
            .collect()
    }
}

// ── GameSetup ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameSetup {
    pub factions: Vec<FactionId>,
    pub round_tile_ids: Vec<u8>,
    pub boosters: Vec<Booster>,
    pub final_scoring: [FinalScoringTile; 2],
    pub tech_tile_ids: Vec<u8>,
    /// 10 standard sector placements (ids 1-10). Always 4-player; no player_count branching.
    pub sector_layout: Vec<SectorPlacement>,
    /// 8 Deep Space sector placements (ids 11-18, Lost Fleet expansion). Always included.
    /// Origins are placeholder (0,0) until the lattice layout algorithm is implemented.
    pub deep_space_layout: Vec<SectorPlacement>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SectorPlacement {
    pub sector_id: u8,
    /// "A" or "B" for double-sided sectors; None for single-sided.
    #[serde(default)]
    pub side: Option<String>,
    pub origin: crate::game_state::HexCoord,
    pub rotation: u8,
}

// ── Static data helpers ───────────────────────────────────────────────────────

fn all_final_scoring_tiles() -> Vec<FinalScoringTile> {
    // Base game 6 tiles (rulebook p.18) + 3 Lost Fleet expansion tiles = pool of 9.
    // 2 tiles are drawn per game.
    vec![
        FinalScoringTile {
            condition: FinalScoringCondition::MostStructuresInFederation,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostBuildings,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostPlanetTypes,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostGaiaplanets,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostSectors,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostSatellites,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        // Lost Fleet expansion tiles
        FinalScoringTile {
            condition: FinalScoringCondition::MostExploredShips,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::MostSpecialPlanets,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
        FinalScoringTile {
            condition: FinalScoringCondition::HighestSingleTrack,
            vp_1st: 18,
            vp_2nd: 12,
            vp_3rd: 6,
        },
    ]
}
