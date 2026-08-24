use gaia_engine::game_state::{BoardState, Hex, HexCoord, Sector};
use gaia_engine::map::MapEngine;
use std::collections::HashMap;

fn make_board(coords: &[(i32, i32)]) -> BoardState {
    let mut hexes = HashMap::new();
    for &(q, r) in coords {
        let coord = HexCoord::new(q, r);
        hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![],
                satellites: vec![],
            },
        );
    }
    BoardState {
        sectors: vec![Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        }],
        hexes,
        lost_planet: None,
    }
}

#[test]
fn reachable_includes_start_hex() {
    let board = make_board(&[(0, 0), (1, 0)]);
    let starts = vec![HexCoord::new(0, 0)];
    let reachable = MapEngine::reachable_hexes(&board, &starts, 1);
    assert!(reachable.contains(&HexCoord::new(0, 0)));
}

#[test]
fn reachable_within_range_1() {
    let board = make_board(&[
        (0, 0),
        (1, 0),
        (0, 1),
        (-1, 0),
        (0, -1),
        (1, -1),
        (-1, 1),
        (2, 0),
    ]);
    let starts = vec![HexCoord::new(0, 0)];
    let reachable = MapEngine::reachable_hexes(&board, &starts, 1);
    // (2,0) is 2 steps away, should not be reachable with range 1
    assert!(!reachable.contains(&HexCoord::new(2, 0)));
}

#[test]
fn is_connected_single_hex() {
    assert!(MapEngine::is_connected(&[HexCoord::new(0, 0)]));
}

#[test]
fn is_connected_empty() {
    assert!(MapEngine::is_connected(&[]));
}

#[test]
fn is_connected_adjacent_pair() {
    let hexes = vec![HexCoord::new(0, 0), HexCoord::new(1, 0)];
    assert!(MapEngine::is_connected(&hexes));
}

#[test]
fn is_not_connected_distant_pair() {
    let hexes = vec![HexCoord::new(0, 0), HexCoord::new(5, 0)];
    assert!(!MapEngine::is_connected(&hexes));
}

#[test]
fn hex_distance_zero_for_same() {
    let h = HexCoord::new(3, -2);
    assert_eq!(h.distance(&h), 0);
}

#[test]
fn hex_distance_adjacent_is_one() {
    let a = HexCoord::new(0, 0);
    let b = HexCoord::new(1, 0);
    assert_eq!(a.distance(&b), 1);
}

#[test]
fn hex_distance_is_symmetric() {
    let a = HexCoord::new(2, -3);
    let b = HexCoord::new(-1, 4);
    assert_eq!(a.distance(&b), b.distance(&a));
}

#[test]
fn neighbors_count_is_six() {
    let center = HexCoord::new(0, 0);
    assert_eq!(center.neighbors().len(), 6);
}

#[test]
fn rotate_60_six_times_is_identity() {
    let h = HexCoord::new(2, -1);
    let mut rotated = h;
    for _ in 0..6 {
        rotated = rotated.rotate_60();
    }
    assert_eq!(rotated, h);
}
