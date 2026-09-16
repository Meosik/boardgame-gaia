use gaia_engine::game_state::{
    BoardState, FederationToken, GamePhase, Hex, HexCoord, PlacedStructure, PowerCycle, Sector,
    Structure, StructureType,
};
use gaia_engine::rules::actions::{FederationTokenChoice, GameAction};
use gaia_engine::rules::engine::AiDecision;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::BTreeSet;
use std::collections::HashMap;

/// A line of adjacent building clusters separated by one satellite-eligible hex.
fn spread_out_empire(count: usize, cluster_size: usize) -> (BoardState, Vec<Structure>) {
    let mut hexes = HashMap::new();
    let mut structures = Vec::new();

    for i in 0..count {
        let owned = HexCoord::new((i + i / cluster_size) as i32, 0);
        hexes.insert(
            owned,
            Hex {
                coord: owned,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure {
                    owner: 0,
                    kind: StructureType::TradingStation,
                }],
                satellites: vec![],
            },
        );
        structures.push(Structure {
            hex: owned,
            kind: StructureType::TradingStation,
        });

        if i + 1 < count && (i + 1) % cluster_size == 0 {
            let gap = HexCoord::new(owned.q + 1, 0);
            hexes.insert(
                gap,
                Hex {
                    coord: gap,
                    planet: None,
                    space_tile_kind: None,
                    structures: vec![],
                    satellites: vec![],
                },
            );
        }
    }

    let board = BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    };
    (board, structures)
}

fn state_with_empire(count: usize, cluster_size: usize) -> gaia_engine::game_state::GameState {
    let (board, structures) = spread_out_empire(count, cluster_size);
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.vp = 10;
            p.resources.power = PowerCycle {
                bowl1: 30,
                bowl2: 0,
                bowl3: 0,
                gaia_bowl: 0,
                gaia_forming: 0,
                brainstone: None,
            };
            p.structures = structures;
        })
        .with_player(1)
        .with_board(board)
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build();
    state.research_board.federation_tokens = vec![FederationToken(1), FederationToken(2)];
    state
}

// This synthetic stress case has 15 genuinely separate clusters (and more trading
// stations than the physical supply). Clustering cannot shrink it; a bounded search
// must leave other legal actions available rather than fail the entire turn.
#[test]
fn ai_decisions_preserves_other_actions_for_a_fifteen_cluster_empire() {
    let mut state = state_with_empire(15, 1);
    state.round = 6;
    state.players[0].resources.power.bowl3 = 6;
    let before = serde_json::to_value(&state).unwrap_or_else(|e| panic!("{e}"));
    let decisions = RuleEngine::ai_decisions(&state).unwrap_or_else(|e| panic!("{e}"));
    let (reported, diagnostics) = RuleEngine::ai_decisions_with_diagnostics(&state)
        .unwrap_or_else(|e| panic!("{e}"));
    assert_eq!(reported, decisions);
    assert_eq!(diagnostics.federation_limit_hits, 1);
    assert!(!diagnostics.federation_limit_reasons.is_empty());
    assert!(decisions
        .iter()
        .any(|d| matches!(d, AiDecision::Game(GameAction::Pass { .. }))));
    assert!(decisions
        .iter()
        .any(|d| matches!(d, AiDecision::Game(GameAction::PowerAction { .. }))));
    for decision in &decisions {
        if let AiDecision::Game(action) = decision {
            assert!(RuleEngine::validate_action(&state, 0, action).is_ok());
        }
    }
    assert_eq!(
        serde_json::to_value(&state).unwrap_or_else(|e| panic!("{e}")),
        before
    );
}

#[test]
fn clustered_candidates_match_all_valid_building_and_satellite_subsets() {
    // Three two-building clusters: selecting an entire cluster automatically could
    // introduce redundant buildings, whereas selecting just its representative could
    // disconnect the submitted federation. Compare the actual actions, not just cost.
    let state = state_with_empire(6, 2);
    assert_candidates_match_exhaustive(&state);
}

#[test]
fn ivits_growth_preserves_existing_cluster_and_qic_satellite_cost() {
    use gaia_engine::game_state::FactionId;
    let mut state = state_with_empire(7, 3);
    state.players[0].faction = Some(FactionId::Ivits);
    state.players[0].federated_hexes = state.players[0].structures[..3]
        .iter()
        .map(|s| s.hex)
        .collect();
    state.players[0].federation_tokens = vec![FederationToken(1)];
    state.players[0].resources.qic = 2;
    state.players[0].resources.power.bowl1 = 0;
    let institute = state.players[0].structures[0].hex;
    state.players[0].structures[0].kind = StructureType::PlanetaryInstitute;
    state
        .board
        .hexes
        .get_mut(&institute)
        .unwrap_or_else(|| panic!("missing institute"))
        .structures[0]
        .kind = StructureType::PlanetaryInstitute;
    assert_candidates_match_exhaustive(&state);
    state.players[0].resources.qic = 1;
    assert!(RuleEngine::ai_decisions(&state)
        .unwrap_or_else(|e| panic!("{e}"))
        .iter()
        .all(|d| !matches!(d, AiDecision::Game(GameAction::FormFederation { .. }))));
}

fn assert_candidates_match_exhaustive(state: &gaia_engine::game_state::GameState) {
    let owned: Vec<_> = state.players[0]
        .structures
        .iter()
        .map(|s| s.hex)
        .filter(|c| !state.players[0].federated_hexes.contains(c))
        .collect();
    let mut gaps: Vec<_> = state
        .board
        .hexes
        .values()
        .filter(|h| h.structures.is_empty())
        .map(|h| h.coord)
        .collect();
    gaps.sort_by_key(|c| (c.q, c.r));
    let mut expected = BTreeSet::new();
    for mask in 1..1usize << owned.len() {
        let hexes: Vec<_> = owned
            .iter()
            .enumerate()
            .filter(|(i, _)| mask & (1 << i) != 0)
            .map(|(_, c)| *c)
            .collect();
        for satellite_mask in 0..1usize << gaps.len() {
            let satellite_hexes: Vec<_> = gaps
                .iter()
                .enumerate()
                .filter(|(i, _)| satellite_mask & (1 << i) != 0)
                .map(|(_, c)| *c)
                .collect();
            for kind in [1, 2] {
                let action = GameAction::FormFederation {
                    hexes: hexes.clone(),
                    satellite_hexes: satellite_hexes.clone(),
                    token: FederationTokenChoice::Supply { kind },
                    bonus_build_coord: None,
                    bonus_tech_tile: None,
                    bonus_research_track: None,
                };
                if RuleEngine::validate_action(state, 0, &action).is_ok() {
                    expected
                        .insert(serde_json::to_string(&action).unwrap_or_else(|e| panic!("{e}")));
                }
            }
        }
    }
    assert!(!expected.is_empty());
    let actual: BTreeSet<_> = RuleEngine::ai_decisions(state)
        .unwrap_or_else(|e| panic!("{e}"))
        .into_iter()
        .filter_map(|decision| match decision {
            AiDecision::Game(action @ GameAction::FormFederation { .. }) => {
                Some(serde_json::to_string(&action).unwrap_or_else(|e| panic!("{e}")))
            }
            _ => None,
        })
        .collect();
    assert_eq!(actual, expected);
}
