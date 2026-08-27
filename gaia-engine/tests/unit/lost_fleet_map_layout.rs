//! Property tests for the real Lost Fleet 4-player variable map setup
//! (`Randomizer::build_sector_layout` + `MapEngine::place_interspace_tiles` +
//! `MapEngine::place_deep_space_sectors`), per rulebook p.4-5 "Setup for 4 players" /
//! "Interspace Tiles". These exercise only `gaia_engine`'s public API — no `MapEngine`
//! internals — reconstructing sector footprints from `sectors.toml` the same way
//! `MapEngine::insert_sector` does, so the assertions are cross-checks, not restatements
//! of the implementation.

use gaia_engine::data::load_sectors;
use gaia_engine::game_state::{HexCoord, PlayerId, Sector, SpaceshipId};
use gaia_engine::{GameSetup, MapEngine, Randomizer};
use std::collections::{HashMap, HashSet};

const SEEDS: usize = 25;

fn four_players() -> Vec<(PlayerId, String)> {
    (0..4).map(|i| (i as PlayerId, format!("p{i}"))).collect()
}

fn setup(seed: &str) -> GameSetup {
    Randomizer::generate_setup(seed).unwrap_or_else(|e| panic!("seed {seed} should be valid: {e}"))
}

/// World-space footprint of a Deep Space sector, reconstructed from its `sectors.toml`
/// template (side-independent: ids 11-18's "A"/"B" templates share the same 3-hex shape,
/// differing only in which cell holds the Asteroid/ProtoPlanet planet marker).
fn deep_space_footprint(sector: &Sector) -> HashSet<HexCoord> {
    let file = load_sectors();
    let template = file
        .sectors
        .iter()
        .find(|s| s.id == sector.id)
        .unwrap_or_else(|| panic!("sectors.toml missing template for id {}", sector.id));
    template
        .hexes
        .iter()
        .map(|h| {
            HexCoord::new(h.rel_q, h.rel_r)
                .rotate_n(sector.rotation)
                .add(&sector.origin)
        })
        .collect()
}

#[test]
fn standard_sectors_cover_exactly_190_unique_hexes() {
    for seed in 0..SEEDS {
        let setup = setup(&format!("lf-map-{seed}"));
        let board = MapEngine::build_board(&setup.sector_layout);
        assert_eq!(
            board.hexes.len(),
            190,
            "seed {seed}: 10 sectors x 19 hexes must be fully non-overlapping"
        );
    }
}

#[test]
fn interspace_holes_are_exactly_ten_and_each_borders_three_distinct_sectors() {
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let setup = setup(&seed_str);
        let standard = MapEngine::build_board(&setup.sector_layout);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);

        let standard_hexes: HashSet<HexCoord> = standard.hexes.keys().copied().collect();
        let deep_space_hexes: HashSet<HexCoord> = state
            .board
            .sectors
            .iter()
            .filter(|s| s.id >= 11)
            .flat_map(deep_space_footprint)
            .collect();

        let holes: Vec<HexCoord> = state
            .board
            .hexes
            .keys()
            .copied()
            .filter(|h| !standard_hexes.contains(h) && !deep_space_hexes.contains(h))
            .collect();

        assert_eq!(
            holes.len(),
            10,
            "seed {seed}: expected 10 single-hex Interspace tile holes"
        );

        // Sector-id membership by exact standard-sector origin distance (rotation-invariant).
        let standard_sectors: Vec<&Sector> =
            state.board.sectors.iter().filter(|s| s.id <= 10).collect();
        for hole in &holes {
            let bordering: HashSet<u8> = standard_sectors
                .iter()
                .filter(|s| hole.distance(&s.origin) == 3)
                .map(|s| s.id)
                .collect();
            assert_eq!(
                bordering.len(),
                3,
                "seed {seed}: hole {hole:?} should border exactly 3 distinct sectors, got {bordering:?}"
            );
        }
    }
}

#[test]
fn all_four_spaceship_tiles_present_and_pairwise_spaced_at_least_three() {
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let setup = setup(&seed_str);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);

        let tiles = &state.board.spaceship_tiles;
        assert_eq!(
            tiles.len(),
            4,
            "seed {seed}: all 4 spaceship tiles must be placed"
        );
        for ship in SpaceshipId::all() {
            assert!(
                tiles.contains_key(&ship),
                "seed {seed}: {ship:?} missing from spaceship_tiles"
            );
        }

        let coords: Vec<HexCoord> = tiles.values().copied().collect();
        for i in 0..coords.len() {
            for j in (i + 1)..coords.len() {
                assert!(
                    coords[i].distance(&coords[j]) >= 3,
                    "seed {seed}: spaceship tiles too close: {:?} and {:?}",
                    coords[i],
                    coords[j]
                );
            }
        }
    }
}

#[test]
fn eight_deep_space_sectors_have_real_non_overlapping_origins() {
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let setup = setup(&seed_str);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);

        let deep_space: Vec<&Sector> = state.board.sectors.iter().filter(|s| s.id >= 11).collect();
        assert_eq!(
            deep_space.len(),
            8,
            "seed {seed}: all 8 Deep Space sectors must be placed"
        );

        let mut ids: Vec<u8> = deep_space.iter().map(|s| s.id).collect();
        ids.sort_unstable();
        ids.dedup();
        assert_eq!(ids, (11..=18).collect::<Vec<u8>>());

        let zero = HexCoord::new(0, 0);
        let mut all_hexes: HashSet<HexCoord> = HashSet::new();
        for sector in &deep_space {
            assert_ne!(
                sector.origin, zero,
                "seed {seed}: Deep Space sector {} still at the (0,0) fallback placeholder",
                sector.id
            );
            for hex in deep_space_footprint(sector) {
                assert!(
                    all_hexes.insert(hex),
                    "seed {seed}: Deep Space sector {} overlaps another placement at {hex:?}",
                    sector.id
                );
            }
        }
        assert_eq!(all_hexes.len(), 24, "seed {seed}: 8 sectors x 3 hexes");
    }
}

#[test]
fn full_board_stays_a_single_connected_component() {
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let setup = setup(&seed_str);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);

        let coords: Vec<HexCoord> = state.board.hexes.keys().copied().collect();
        assert!(
            MapEngine::is_connected(&coords),
            "seed {seed}: assembled board must be a single connected blob"
        );
    }
}

#[test]
fn full_board_has_no_placeholder_hex_map_regressions() {
    // Cross-check against a HashMap-based rebuild to catch any accidental aliasing that a
    // plain length count could hide (e.g. two different logical hexes both landing on the
    // same key while a third key goes missing, netting the same count).
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let setup = setup(&seed_str);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);

        let mut seen: HashMap<HexCoord, u32> = HashMap::new();
        for coord in state.board.hexes.keys() {
            *seen.entry(*coord).or_insert(0) += 1;
        }
        assert!(seen.values().all(|&count| count == 1));
        assert_eq!(seen.len(), 224, "seed {seed}");
    }
}

/// Each Deep Space sector should sit in the gap "between" exactly 2 distinct Standard sectors —
/// the project owner's explicit ask ("각 번호 우주 보드 사이에 위치하면 되는걸": it should just
/// sit between each numbered sector) after two earlier attempts (unconstrained first-valid, then
/// snugness-maximizing) both left tiles clustering unevenly instead. Across all 8 Deep Space
/// sectors this also means: the 8 "ring" Standard sectors (the ones that actually reach the
/// outer boundary) are each bordered by exactly 2 Deep Space sectors, and the 2 fully-interior
/// "center" Standard sectors are bordered by none — since they never touch the outside edge at
/// all, matching `deep_space_gap_candidates`'s doc comment.
#[test]
fn eight_deep_space_sectors_each_sit_between_exactly_two_standard_sectors() {
    for seed in 0..SEEDS {
        let seed_str = format!("lf-map-{seed}");
        let s = setup(&seed_str);
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &s);
        let standard: Vec<&Sector> = state.board.sectors.iter().filter(|s| s.id <= 10).collect();

        let mut border_counts: HashMap<u8, u32> = HashMap::new();
        for sector in state.board.sectors.iter().filter(|s| s.id >= 11) {
            let footprint = deep_space_footprint(sector);
            let bordering: HashSet<u8> = standard
                .iter()
                .filter(|s| footprint.iter().any(|h| h.distance(&s.origin) <= 3))
                .map(|s| s.id)
                .collect();
            assert_eq!(
                bordering.len(),
                2,
                "seed {seed}: Deep Space sector {} should border exactly 2 Standard sectors, \
                 got {bordering:?}",
                sector.id
            );
            for id in bordering {
                *border_counts.entry(id).or_insert(0) += 1;
            }
        }

        let touched: Vec<u8> = {
            let mut v: Vec<u8> = border_counts.keys().copied().collect();
            v.sort_unstable();
            v
        };
        assert_eq!(
            touched.len(),
            8,
            "seed {seed}: expected exactly 8 of the 10 Standard sectors (the ring, not the 2 \
             interior centers) to border any Deep Space sector, got {touched:?}"
        );
        assert!(
            border_counts.values().all(|&c| c == 2),
            "seed {seed}: every ring sector should border exactly 2 Deep Space sectors, got \
             {border_counts:?}"
        );
    }
}
