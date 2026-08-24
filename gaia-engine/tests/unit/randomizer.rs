use gaia_engine::{GameSetup, Randomizer};

fn setup(seed: &str) -> GameSetup {
    match Randomizer::generate_setup(seed) {
        Ok(setup) => setup,
        Err(e) => panic!("fixture seed should produce a setup: {e}"),
    }
}

#[test]
fn same_seed_produces_same_setup() {
    let s1 = setup("hello");
    let s2 = setup("hello");
    assert_eq!(s1.factions, s2.factions);
}

#[test]
fn different_seeds_differ() {
    // `factions` is always the fixed `FactionId::all()` list (every board
    // side is offered for sequential choice, see `build_setup`) — not
    // seed-derived, so it can't be used to tell seeds apart. `sector_layout`
    // (shuffled rotations/outer sector ids) is.
    let s1 = setup("seed-a");
    let s2 = setup("seed-b");
    let any_diff = s1
        .sector_layout
        .iter()
        .zip(s2.sector_layout.iter())
        .any(|(a, b)| a.sector_id != b.sector_id || a.rotation != b.rotation);
    assert!(any_diff, "different seeds should produce different setups");
}

#[test]
fn setup_offers_all_eighteen_factions() {
    // Every faction-board side is offered for sequential choice (PD-001) —
    // there's no per-seed subset selection.
    assert_eq!(setup("test").factions.len(), 18);
}

#[test]
fn setup_has_six_round_tiles() {
    assert_eq!(setup("test").round_tile_ids.len(), 6);
}

#[test]
fn setup_has_seven_boosters() {
    assert_eq!(setup("test").boosters.len(), 7);
}

#[test]
fn setup_has_two_final_scoring_tiles() {
    assert_eq!(setup("test").final_scoring.len(), 2);
}

#[test]
fn sector_layout_has_ten_sectors() {
    assert_eq!(setup("test").sector_layout.len(), 10);
}

#[test]
fn center_sectors_are_ids_one_to_four() {
    let center: Vec<u8> = setup("test")
        .sector_layout
        .iter()
        .take(4)
        .map(|s| s.sector_id)
        .collect();
    assert_eq!(center, vec![1, 2, 3, 4]);
}

#[test]
fn rotation_values_in_range() {
    for placement in &setup("test").sector_layout {
        assert!(placement.rotation < 6, "rotation must be in [0,5]");
    }
}
