use gaia_engine::game_state::{
    BoardState, FactionId, GamePhase, Hex, HexCoord, PlacedStructure, Planet, PlanetType, Sector,
    Structure, StructureType,
};
use gaia_engine::rules::actions::GameAction;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use std::collections::HashMap;

// Rulebook p.11 ("Build a Mine"): "you can spend any number of Q.I.C. to increase your range by
// two spaces for each Q.I.C. spent" — confirmed by the worked example (Navigation level 2, basic
// range 2, spend 1 QIC -> range 4). This project's engine auto-computes the minimum QIC needed
// to reach a target rather than exposing a separate "how much QIC" choice — see
// `range_and_qic_cost` in `rules/engine.rs`. A straight 4-hex line puts the target exactly 3
// steps from the anchor; basic range is 1 (Navigation level 0), so reaching it needs 1 QIC
// (ceil((3-1)/2) = 1).

fn line_board() -> BoardState {
    let mut hexes = HashMap::new();
    hexes.insert(
        HexCoord::new(0, 0),
        Hex {
            coord: HexCoord::new(0, 0),
            planet: None,
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 0,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    hexes.insert(
        HexCoord::new(1, 0),
        Hex {
            coord: HexCoord::new(1, 0),
            planet: Some(Planet {
                planet_type: PlanetType::Volcanic,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        HexCoord::new(2, 0),
        Hex {
            coord: HexCoord::new(2, 0),
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    hexes.insert(
        HexCoord::new(3, 0),
        Hex {
            coord: HexCoord::new(3, 0),
            planet: Some(Planet {
                planet_type: PlanetType::Volcanic,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );

    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
        spaceship_tiles: HashMap::new(),
    }
}

fn base_state(qic: u8) -> gaia_engine::game_state::GameState {
    GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.structures = vec![Structure {
                hex: HexCoord::new(0, 0),
                kind: StructureType::Mine,
            }];
            p.resources.ore = 15;
            p.resources.credits = 15;
            p.resources.qic = qic;
        })
        .with_player(1)
        .with_board(line_board())
        .with_phase(GamePhase::ActionPhase { active_player: 0 })
        .build()
}

#[test]
fn build_out_of_range_fails_even_spending_all_available_qic_if_still_short() {
    let mut state = base_state(0);

    let result = RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(3, 0),
        },
    );
    assert!(result.is_err());
}

#[test]
fn build_beyond_basic_range_spends_the_minimum_qic_needed() {
    let mut state = base_state(1);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(3, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build with QIC range extension should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, 0);
}

#[test]
fn build_does_not_overspend_qic_beyond_what_the_distance_requires() {
    let mut state = base_state(3);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(3, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build with QIC range extension should succeed: {e}"));

    // Only 1 QIC was needed (distance 3, basic range 1); the other 2 remain unspent.
    assert_eq!(state.players[0].resources.qic, 2);
}

#[test]
fn build_within_basic_range_spends_no_qic() {
    let mut state = base_state(5);

    RuleEngine::apply_action(
        &mut state,
        0,
        GameAction::Build {
            coord: HexCoord::new(1, 0),
        },
    )
    .unwrap_or_else(|e| panic!("build within basic range should succeed: {e}"));

    assert_eq!(state.players[0].resources.qic, 5);
}

// `get_valid_actions` used to enumerate Build/GaiaFormation-family candidates only over the base
// navigation-range `reachable_hexes` set, so a QIC-extended target like (3, 0) here — accepted by
// `validate_action`/`apply_action` above — never appeared in its own candidate list. Fixed by
// enumerating every board hex and letting each `validate_*` call (which already accounts for QIC
// extension) be the single source of truth for what's actually reachable.
#[test]
fn get_valid_actions_includes_a_qic_extended_build_target() {
    let state = base_state(1);

    let actions = RuleEngine::get_valid_actions(&state, 0);

    assert!(
        actions.contains(&GameAction::Build {
            coord: HexCoord::new(3, 0),
        }),
        "expected the QIC-reachable (3, 0) Build target to be enumerated, got: {actions:?}"
    );
}

#[test]
fn get_valid_actions_omits_a_build_target_still_out_of_range_with_all_available_qic() {
    let state = base_state(0);

    let actions = RuleEngine::get_valid_actions(&state, 0);

    assert!(
        !actions.contains(&GameAction::Build {
            coord: HexCoord::new(3, 0),
        }),
        "target (3, 0) needs 1 QIC the player doesn't have, so it should not be enumerated"
    );
}
