//! `MapEngine::distance_map` is the one-BFS form of `MapEngine::shortest_distance` that
//! candidate generation memoizes per (start set, range bound) (`ReachMemoScope`, E58). The
//! memo can only be exact if the two agree on every hex of a real board, for every bound, so
//! that equivalence is checked here on generated Lost Fleet maps. The candidate list itself is
//! generated inside the scope, so `ai_decisions` on a real board is cross-checked against
//! `validate_action` outside any scope (the scope must not admit an unreachable target or drop
//! a reachable one).

use gaia_engine::game_state::{
    Booster, FactionId, HexCoord, PlacedStructure, PlanetType, PlayerId, Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::rules::engine::AiDecision;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::{MapEngine, Randomizer, RuleEngine};

fn four_players() -> Vec<(PlayerId, String)> {
    (0..4).map(|i| (i as PlayerId, format!("p{i}"))).collect()
}

#[test]
fn distance_map_agrees_with_shortest_distance_on_every_hex_and_bound() {
    for seed in 0..6usize {
        let seed_str = format!("reach-memo-{seed}");
        let setup = Randomizer::generate_setup(&seed_str)
            .unwrap_or_else(|e| panic!("seed {seed_str} should be valid: {e}"));
        let state = MapEngine::init_game_state(&seed_str, &seed_str, &four_players(), &setup);
        let board = &state.board;
        let mut hexes: Vec<HexCoord> = board.hexes.keys().copied().collect();
        hexes.sort_by_key(|c| (c.q, c.r));
        let starts = [hexes[seed * 7 % hexes.len()], hexes[seed * 13 % hexes.len()]];
        for max_range in 0..=9u8 {
            let map = MapEngine::distance_map(board, &starts, max_range);
            for &target in &hexes {
                let direct = MapEngine::shortest_distance(board, &starts, target, max_range);
                assert_eq!(
                    map.get(&target).copied(),
                    direct,
                    "seed {seed} range {max_range} target {target:?}"
                );
            }
            for (hex, distance) in &map {
                assert!(board.hexes.contains_key(hex), "map entry off the board: {hex:?}");
                assert!(*distance <= max_range);
            }
        }
        assert!(MapEngine::distance_map(board, &[], 5).is_empty());
        assert_eq!(MapEngine::shortest_distance(board, &[], hexes[0], 5), None);
    }
}

#[test]
fn candidate_builds_inside_the_scope_match_direct_validation() -> Result<(), Box<dyn std::error::Error>> {
    let mut any_builds = false;
    for seed in 0..3 {
        let seed_str = format!("reach-memo-build-{seed}");
        let setup = Randomizer::generate_setup(&seed_str)
            .unwrap_or_else(|e| panic!("seed {seed_str} should be valid: {e}"));
        let board = MapEngine::build_board(&setup.sector_layout);
        let home = board
            .hexes
            .values()
            .filter(|hex| hex.planet.as_ref().is_some_and(|p| p.planet_type == PlanetType::Terra))
            .map(|hex| hex.coord)
            .min_by_key(|c| (c.q, c.r))
            .expect("a Terra planet on the board");
        let mut state = GameStateBuilder::new()
            .with_board(board)
            .with_player_fn(0, |p| {
                p.faction = Some(FactionId::Terrans);
                p.booster = Some(Booster(1));
                p.resources.ore = 15;
                p.resources.credits = 15;
                p.resources.qic = 2;
                p.structures = vec![Structure { hex: home, kind: StructureType::Mine }];
            })
            .with_player(1)
            .build();
        let hex = state.board.hexes.get_mut(&home).expect("home hex");
        hex.planet.as_mut().expect("home planet").owner = Some(0);
        hex.structures.push(PlacedStructure { owner: 0, kind: StructureType::Mine });

        // Generated inside ReachMemoScope: every candidate must validate directly (no scope
        // active here), and every directly valid Build must be a candidate.
        let candidates = RuleEngine::ai_decisions(&state)?;
        let mut candidate_builds = Vec::new();
        for candidate in &candidates {
            if let AiDecision::Game(action) = candidate {
                RuleEngine::validate_action(&state, 0, action)?;
                if let GameAction::Build { coord } = action {
                    candidate_builds.push(*coord);
                }
            }
        }
        let mut direct_builds: Vec<HexCoord> = state
            .board
            .hexes
            .keys()
            .copied()
            .filter(|&hex| {
                RuleEngine::validate_action(&state, 0, &GameAction::Build { coord: hex }).is_ok()
            })
            .collect();
        candidate_builds.sort_by_key(|c| (c.q, c.r));
        direct_builds.sort_by_key(|c| (c.q, c.r));
        assert_eq!(candidate_builds, direct_builds, "seed {seed_str}");
        any_builds |= !direct_builds.is_empty();
    }
    assert!(any_builds, "at least one seed should offer a reachable mine site");
    Ok(())
}
