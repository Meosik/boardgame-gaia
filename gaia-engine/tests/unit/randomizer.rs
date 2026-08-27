use gaia_engine::game_state::FinalScoringTile;
use gaia_engine::{GameSetup, MapEngine, Randomizer, SetupMode};

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
fn bidding_setup_offers_four_factions_from_distinct_boards() {
    let setup = Randomizer::generate_bidding_setup("bidding-factions")
        .unwrap_or_else(|error| panic!("fixture seed should produce a bidding setup: {error}"));

    assert_eq!(setup.setup_mode, SetupMode::Bidding);
    assert_eq!(setup.factions.len(), 4);
    for faction in &setup.factions {
        assert!(!setup.factions.contains(&faction.other_board_side()));
    }
}

#[test]
fn setup_has_six_round_tiles() {
    let round_tile_ids = setup("test").round_tile_ids;
    assert_eq!(round_tile_ids.len(), 6);
    assert!(round_tile_ids.iter().all(|id| (1..=12).contains(id)));
    let mut unique = round_tile_ids.clone();
    unique.sort_unstable();
    unique.dedup();
    assert_eq!(unique.len(), 6, "physical round tiles cannot repeat");
}

#[test]
fn setup_has_seven_boosters() {
    let boosters = setup("test").boosters;
    assert_eq!(boosters.len(), 7);
    assert!(boosters.iter().all(|booster| (1..=14).contains(&booster.0)));
    let mut unique = boosters.iter().map(|booster| booster.0).collect::<Vec<_>>();
    unique.sort_unstable();
    unique.dedup();
    assert_eq!(unique.len(), 7, "physical boosters cannot repeat");
}

#[test]
fn setup_has_two_final_scoring_tiles() {
    let tiles = setup("test").final_scoring;
    assert_eq!(tiles.len(), 2);
    assert_ne!(tiles[0].id, tiles[1].id);
    assert!(tiles
        .iter()
        .all(|tile| FinalScoringTile::IDS.contains(&tile.id)));
}

#[test]
fn setup_places_nine_distinct_base_tech_piles_on_the_research_board() {
    let setup = setup("tech-layout");
    let mut slots = setup.tech_tile_slot_ids.clone();
    assert_eq!(slots.len(), 9);
    slots.sort_unstable();
    assert_eq!(slots, (2..=10).collect::<Vec<_>>());

    for tile_id in 2..=10 {
        assert_eq!(
            setup
                .tech_tile_ids
                .iter()
                .filter(|id| **id == tile_id)
                .count(),
            4,
            "base Standard Tech pile {tile_id} must contain four copies"
        );
    }
    assert!(setup.tech_tile_ids.iter().all(|id| (2..=10).contains(id)));
}

#[test]
fn sector_layout_has_ten_sectors() {
    assert_eq!(setup("test").sector_layout.len(), 10);
}

#[test]
fn two_center_sectors_are_selected_from_ids_one_to_four() {
    let center: Vec<u8> = setup("test")
        .sector_layout
        .iter()
        .take(2)
        .map(|s| s.sector_id)
        .collect();
    assert_eq!(center.len(), 2);
    assert!(center.iter().all(|id| (1..=4).contains(id)));
    assert_ne!(center[0], center[1]);
}

#[test]
fn four_player_standard_sector_sides_are_fixed() {
    let setup = setup("test");
    for placement in setup
        .sector_layout
        .iter()
        .filter(|placement| (5..=7).contains(&placement.sector_id))
    {
        assert_eq!(placement.side.as_deref(), Some("A"));
    }
}

#[test]
fn generated_sector_layouts_never_overwrite_hexes() {
    for seed in 0..100 {
        let setup = setup(&format!("collision-regression-{seed}"));
        let standard_board = MapEngine::build_board(&setup.sector_layout);
        assert_eq!(
            standard_board.hexes.len(),
            190,
            "ten 19-hex standard sectors must remain distinct for seed {seed}"
        );

        // `setup.deep_space_layout`'s own `origin`/`rotation` are placeholders — Deep Space
        // sectors are placed board-dependently (in the gaps along the assembled board's outer
        // edge), which only `MapEngine::init_game_state` can do, since it needs the standard
        // board (plus Interspace tiles) to already exist. Exercise the real pipeline instead of
        // `build_board` on the raw setup, which would only see collision-prone placeholders.
        let players: Vec<(gaia_engine::game_state::PlayerId, String)> = (0..4)
            .map(|i| (i as gaia_engine::game_state::PlayerId, format!("p{i}")))
            .collect();
        let seed_str = format!("collision-regression-{seed}");
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &players, &setup);
        assert_eq!(
            state.board.hexes.len(),
            190 + 10 + 24,
            "10 standard sectors (190) + 10 Interspace tile holes (10) + 8 Deep Space sectors \
             (24) must all remain distinct, non-overlapping hexes for seed {seed}"
        );
    }
}

#[test]
fn rotation_values_in_range() {
    for placement in &setup("test").sector_layout {
        assert!(placement.rotation < 6, "rotation must be in [0,5]");
    }
}
