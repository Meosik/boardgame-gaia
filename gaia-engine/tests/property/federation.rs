use gaia_engine::game_state::{BoardState, Hex, HexCoord, PlacedStructure, Sector, StructureType};
use gaia_engine::map::MapEngine;
use proptest::prelude::*;
use std::collections::HashMap;

fn make_board_with_structures(
    player: u8,
    coords: Vec<HexCoord>,
    kind: StructureType,
) -> BoardState {
    let mut hexes = HashMap::new();
    for coord in &coords {
        hexes.insert(
            *coord,
            Hex {
                coord: *coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure {
                    owner: player,
                    kind,
                }],
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
fn trading_station_power_value_is_two() {
    let ts = StructureType::TradingStation;
    assert_eq!(ts.power_value(), 2);
}

#[test]
fn mine_power_value_is_one() {
    assert_eq!(StructureType::Mine.power_value(), 1);
}

#[test]
fn planetary_institute_power_value_is_three() {
    // Base rulebook p.14: "Planetary institutes and academies have a power
    // value of 3" (confirmed again in the worked example on the same page).
    assert_eq!(StructureType::PlanetaryInstitute.power_value(), 3);
}

#[test]
fn satellite_power_value_is_zero() {
    assert_eq!(StructureType::Satellite.power_value(), 0);
}

#[test]
fn federation_power_sums_structures() {
    let coords = vec![HexCoord::new(0, 0), HexCoord::new(1, 0)];
    let board = make_board_with_structures(0, coords.clone(), StructureType::TradingStation);
    let power = MapEngine::federation_power(&board, 0, &coords);
    // 2 trading stations × 2 = 4
    assert_eq!(power, 4);
}

#[test]
fn satellites_excluded_from_federation_power() {
    let coords = vec![HexCoord::new(0, 0)];
    let board = make_board_with_structures(0, coords.clone(), StructureType::Satellite);
    let power = MapEngine::federation_power(&board, 0, &coords);
    assert_eq!(power, 0, "satellites contribute 0 to federation power");
}

proptest! {
    #[test]
    fn federation_power_non_negative(
        q1 in -5i32..=5i32,
        r1 in -5i32..=5i32,
    ) {
        let coords = vec![HexCoord::new(q1, r1)];
        let board = make_board_with_structures(0, coords.clone(), StructureType::Mine);
        let power = MapEngine::federation_power(&board, 0, &coords);
        prop_assert!(power >= 1, "at least one mine contributes power >= 1");
    }
}
