// IMPORTANT: This PRNG algorithm is locked to match JavaScript randomizer v2.3.2.
// DO NOT modify the hash function or bit operations.
// Cross-language reproducibility (Rust ↔ JS) is verified by test vectors in
// tests/property/prng_vectors.rs

use crate::error::SetupError;
use crate::game_state::{Booster, FactionId, FinalScoringTile};
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
        Ok(rng.build_setup(seed))
    }

    /// Generate the normal board setup plus exactly four individual factions
    /// for the optional bidding setup. At most one side of each double-sided
    /// faction board is offered.
    pub fn generate_bidding_setup(seed: &str) -> Result<GameSetup, SetupError> {
        if seed.trim().is_empty() {
            return Err(SetupError::InvalidSeed(
                "seed must not be empty".to_string(),
            ));
        }
        let mut rng = Self::new(seed);
        let mut setup = rng.build_setup(seed);
        let mut candidates = FactionId::all();
        rng.shuffle(&mut candidates);

        let mut offered = Vec::with_capacity(4);
        for faction in candidates {
            if offered.contains(&faction.other_board_side()) {
                continue;
            }
            offered.push(faction);
            if offered.len() == 4 {
                break;
            }
        }
        setup.factions = offered;
        setup.setup_mode = SetupMode::Bidding;
        Ok(setup)
    }

    fn build_setup(&mut self, seed: &str) -> GameSetup {
        // Step 1: every faction-board side is available for sequential choice.
        let factions = FactionId::all();

        // Step 2: Round tiles — shuffle pool, take 6
        // Twelve distinct round-scoring assets are available in this project.
        let mut round_tile_ids: Vec<u8> = (1..=12).collect();
        self.shuffle(&mut round_tile_ids);
        let round_tile_ids: Vec<u8> = round_tile_ids.into_iter().take(6).collect();

        // Step 3: Boosters — shuffle pool, take 4+3=7
        let mut booster_ids: Vec<u8> = (1..=14).collect();
        self.shuffle(&mut booster_ids);
        let boosters: Vec<Booster> = booster_ids.into_iter().take(7).map(Booster).collect();

        // Step 4: Final scoring tiles — pool of 9 (6 base + 3 Lost Fleet), take 2
        let mut final_pool = all_final_scoring_tiles();
        self.shuffle(&mut final_pool);
        let final_scoring = [final_pool.remove(0), final_pool.remove(0)];

        // Step 5: Tech tiles. Standard supply: 13 types (ids 2-10 base game, 11-14 Lost Fleet
        // Appendix V), 4 physical copies each — "this will give you nine piles of four identical
        // tech tiles" (rulebook p.4), extended by the same count for the 4 Lost Fleet additions
        // (expansion components list: "12 Standard Tech tiles"). Advanced supply: 1 tile per
        // research track (6 total), drawn from the 21 known kinds (`gaia-frontend/src/assets/
        // tech_tiles/advanced/` — id 18's scan is missing, so it never appears here).
        let mut tech_tile_ids: Vec<u8> =
            (2..=14).flat_map(|id| std::iter::repeat_n(id, 4)).collect();
        self.shuffle(&mut tech_tile_ids);
        let known_advanced_tech_tile_ids: [u8; 21] = [
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22,
        ];
        let mut advanced_tech_tile_ids: Vec<u8> = known_advanced_tech_tile_ids.to_vec();
        self.shuffle(&mut advanced_tech_tile_ids);
        let advanced_tech_tile_ids: Vec<u8> = advanced_tech_tile_ids.into_iter().take(6).collect();

        // Step 6: Sector layout
        // Center Balance sectors 01-04 fixed at center positions
        // Remaining sectors shuffled for outer positions
        let sector_layout = self.build_sector_layout();

        // Step 7: Deep Space Sectors (Lost Fleet) — always all 8 (ids 11-18)
        let deep_space_layout = self.build_deep_space_layout();

        GameSetup {
            seed: seed.to_string(),
            setup_mode: SetupMode::Sequential,
            factions,
            round_tile_ids,
            boosters,
            final_scoring,
            tech_tile_ids,
            advanced_tech_tile_ids,
            sector_layout,
            deep_space_layout,
        }
    }

    /// Lost Fleet four-player layout (rulebook p.5): 2 of sectors 01-04 occupy the center
    /// "domino"; the remaining 8 (the other 2 of 01-04, plus 05-10) surround them, using the
    /// geometrically-derived origins from `lost_fleet_sector_origins` — zero overlap, and
    /// (verified separately by `MapEngine::find_interspace_holes`) exactly 10 natural single-hex
    /// gaps at the resulting triple-junctions, matching the rulebook's stated Interspace tile
    /// hole count exactly. `origins[0]`/`origins[1]` are the 2 center sectors; `origins[2..10]`
    /// are the 8 ring sectors, in no particular further order (any of the remaining 8 ids can go
    /// in any ring slot).
    fn build_sector_layout(&mut self) -> Vec<SectorPlacement> {
        let origins = lost_fleet_sector_origins();

        let mut center_ids: Vec<u8> = (1..=4).collect();
        self.shuffle(&mut center_ids);
        let mut ring_ids = center_ids.split_off(2);
        ring_ids.extend(5..=10);
        self.shuffle(&mut ring_ids);

        let mut ids = center_ids;
        ids.extend(ring_ids);

        ids.into_iter()
            .zip(origins)
            .map(|(sector_id, origin)| {
                // Four-player Lost Fleet uses the white-number side of 05-07 (rulebook p.5) —
                // fixed, not random, unlike the Deep Space sectors below.
                let side = if (5..=7).contains(&sector_id) {
                    Some("A".to_string())
                } else {
                    None
                };
                SectorPlacement {
                    sector_id,
                    side,
                    origin,
                    rotation: self.random_int(6) as u8,
                }
            })
            .collect()
    }

    /// Shuffles the 8 Deep Space sector ids and picks a random side for each (rulebook p.5:
    /// "place them with a random side up"). `origin`/`rotation` here are placeholders —
    /// `MapEngine::place_deep_space_sectors` computes the real, board-dependent values once the
    /// standard-sector board actually exists (this function runs before any board is built), but
    /// still owns the id/side shuffle so it stays part of `Randomizer`'s single deterministic
    /// PRNG stream rather than a second independent shuffle that could drift from what
    /// `GameSetup.deep_space_layout` reports.
    fn build_deep_space_layout(&mut self) -> Vec<SectorPlacement> {
        use crate::game_state::HexCoord;

        let mut ds_ids: Vec<u8> = (11..=18).collect();
        self.shuffle(&mut ds_ids);

        ds_ids
            .into_iter()
            .map(|id| {
                let side = if self.random() < 0.5 { "A" } else { "B" };
                SectorPlacement {
                    sector_id: id,
                    side: Some(side.to_string()),
                    origin: HexCoord::new(0, 0),
                    rotation: 0,
                }
            })
            .collect()
    }
}

/// The 6 canonical direction vectors between two Standard sector origins for "tight" (matched)
/// adjacency — sharing exactly 3 border hexes, the rulebook's "as per the base game" spacing for
/// placing hex sector tiles edge-to-edge. A single `HexCoord::rotate_60` cycle starting from
/// `(-5, 1)`; verified (brute-force search over all offsets up to distance 10, and by this
/// module's property tests) to be the only family of offsets giving zero-overlap, touching-3
/// pairs between two 19-hex radius-2 sector disks.
pub(crate) fn tight_sector_directions() -> [crate::game_state::HexCoord; 6] {
    let mut dirs = [crate::game_state::HexCoord::new(-5, 1); 6];
    for i in 1..6 {
        dirs[i] = dirs[i - 1].rotate_60();
    }
    dirs
}

/// The 10 Standard sector origins for the Lost Fleet 4-player layout (rulebook p.5): 2 "center"
/// sectors placed next to each other (a "domino", `out[0]`/`out[1]`), with the other 8 arranged
/// around them (`out[2..10]`) — mechanically derived from `tight_sector_directions`, not
/// hand-tuned: center `B` sits at `A + dirs[0]`; the 8 ring sectors are `A`'s other 5
/// tight-adjacent neighbors plus `B`'s other 5 (2 coincide, netting 8 unique positions). This
/// produces exactly 10 sectors with zero overlap and exactly 10 single-hex gaps at the resulting
/// triple-junctions — the Interspace tile holes (`MapEngine::find_interspace_holes`).
pub(crate) fn lost_fleet_sector_origins() -> [crate::game_state::HexCoord; 10] {
    let dirs = tight_sector_directions();
    let a = crate::game_state::HexCoord::new(0, 0);
    let b = a.add(&dirs[0]);
    let dir_to_a = dirs[3]; // opposite direction: 180° = 3 * 60°

    let mut ring: Vec<crate::game_state::HexCoord> = Vec::with_capacity(8);
    for &d in dirs.iter().skip(1) {
        ring.push(a.add(&d));
    }
    for &d in dirs.iter() {
        if d.q == dir_to_a.q && d.r == dir_to_a.r {
            continue;
        }
        let p = b.add(&d);
        if !ring.contains(&p) {
            ring.push(p);
        }
    }

    let mut out = [a; 10];
    out[1] = b;
    for (i, p) in ring.into_iter().enumerate() {
        out[2 + i] = p;
    }
    out
}

// ── GameSetup ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SetupMode {
    #[default]
    Sequential,
    Bidding,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameSetup {
    /// The RNG seed this setup was generated from (`Room.seed`'s value at generation time) —
    /// carried on the setup itself so clients that only ever see `GameSetup` JSON (the waiting
    /// room) can display it and detect a reroll by watching this field change, without the
    /// server having to thread `room.seed` through every response separately.
    #[serde(default)]
    pub seed: String,
    #[serde(default)]
    pub setup_mode: SetupMode,
    pub factions: Vec<FactionId>,
    pub round_tile_ids: Vec<u8>,
    pub boosters: Vec<Booster>,
    pub final_scoring: [FinalScoringTile; 2],
    pub tech_tile_ids: Vec<u8>,
    /// One Advanced Tech tile id per research track (`ResearchTrack::all()` order), drawn from
    /// the known kinds — see `Randomizer::generate_setup`.
    #[serde(default)]
    pub advanced_tech_tile_ids: Vec<u8>,
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
    FinalScoringTile::all()
}
