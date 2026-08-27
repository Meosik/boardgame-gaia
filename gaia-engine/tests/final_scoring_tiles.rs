use gaia_engine::game_state::{
    AcademyType, FederationToken, FinalScoringCondition, FinalScoringTile, GameEvent, Hex,
    HexCoord, PlacedStructure, Planet, PlanetType, Sector, Structure, StructureType,
};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::ScoringEngine;
use std::collections::HashMap;

const PLAYER: u8 = 0;

fn add_planet_building(
    state: &mut gaia_engine::GameState,
    coord: HexCoord,
    planet_type: PlanetType,
    is_gaia_formed: bool,
    kind: StructureType,
) {
    state.board.hexes.insert(
        coord,
        Hex {
            coord,
            planet: Some(Planet {
                planet_type,
                is_gaia_formed,
                owner: Some(PLAYER),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: PLAYER,
                kind,
            }],
            satellites: vec![],
        },
    );
    let Some(player) = state.player_mut(PLAYER) else {
        panic!("fixture player missing");
    };
    player.structures.push(Structure { hex: coord, kind });
}

fn scoring_fixture() -> gaia_engine::GameState {
    let mut state = GameStateBuilder::new()
        .with_player(PLAYER)
        .with_player(1)
        .with_player(2)
        .with_player(3)
        .build();
    state.board.sectors = vec![
        Sector {
            id: 1,
            rotation: 0,
            origin: HexCoord::new(0, 0),
        },
        Sector {
            id: 11,
            rotation: 0,
            origin: HexCoord::new(10, 0),
        },
    ];
    state.board.hexes = HashMap::new();

    add_planet_building(
        &mut state,
        HexCoord::new(0, 0),
        PlanetType::Gaia,
        false,
        StructureType::PlanetaryInstitute,
    );
    add_planet_building(
        &mut state,
        HexCoord::new(1, 0),
        PlanetType::Terra,
        false,
        StructureType::Academy(AcademyType::Science),
    );
    add_planet_building(
        &mut state,
        HexCoord::new(10, 0),
        PlanetType::Asteroid,
        false,
        StructureType::Mine,
    );
    add_planet_building(
        &mut state,
        HexCoord::new(11, 0),
        PlanetType::Transdim,
        true,
        StructureType::Mine,
    );

    let lost_planet = HexCoord::new(20, 0);
    state.board.lost_planet = Some(lost_planet);
    state.board.hexes.insert(
        lost_planet,
        Hex {
            coord: lost_planet,
            planet: Some(Planet {
                planet_type: PlanetType::LostPlanet,
                is_gaia_formed: false,
                owner: Some(PLAYER),
            }),
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );

    let Some(standard_hex) = state.board.hexes.get_mut(&HexCoord::new(0, 0)) else {
        panic!("standard fixture hex missing");
    };
    standard_hex.satellites.push(PLAYER);
    let Some(deep_space_hex) = state.board.hexes.get_mut(&HexCoord::new(10, 0)) else {
        panic!("deep-space fixture hex missing");
    };
    deep_space_hex.satellites.push(PLAYER);
    let Some(player) = state.player_mut(PLAYER) else {
        panic!("fixture player missing");
    };
    player.structures.push(Structure {
        hex: HexCoord::new(30, 0),
        kind: StructureType::SpaceStation,
    });

    state.event_log.push(GameEvent::FederationFormed {
        player: PLAYER,
        hexes: vec![HexCoord::new(0, 0), HexCoord::new(1, 0)],
        token: FederationToken(1),
    });
    state
}

#[test]
fn all_nine_asset_ids_map_to_the_expected_conditions() {
    let expected = [
        (1, FinalScoringCondition::MostGaiaPlanets),
        (2, FinalScoringCondition::MostDeepSpaceSectors),
        (3, FinalScoringCondition::MostStructuresInFederation),
        (4, FinalScoringCondition::MostPlanetTypes),
        (5, FinalScoringCondition::MostBuildings),
        (6, FinalScoringCondition::MostAsteroids),
        (8, FinalScoringCondition::MostSectors),
        (9, FinalScoringCondition::GreatestDistancePiAcademy),
        (10, FinalScoringCondition::MostSatellites),
    ];

    assert_eq!(FinalScoringTile::IDS.len(), expected.len());
    for (id, condition) in expected {
        let tile = FinalScoringTile::from_id(id);
        assert_eq!(tile.id, id);
        assert_eq!(tile.condition, condition);
        assert_eq!((tile.vp_1st, tile.vp_2nd, tile.vp_3rd), (18, 12, 6));
    }
}

#[test]
fn every_final_tile_metric_uses_its_real_board_data() {
    let state = scoring_fixture();
    let cases = [
        (FinalScoringCondition::MostGaiaPlanets, 2),
        (FinalScoringCondition::MostDeepSpaceSectors, 1),
        (FinalScoringCondition::MostStructuresInFederation, 2),
        (FinalScoringCondition::MostPlanetTypes, 4),
        (FinalScoringCondition::MostBuildings, 5),
        (FinalScoringCondition::MostAsteroids, 1),
        (FinalScoringCondition::MostSectors, 1),
        (FinalScoringCondition::GreatestDistancePiAcademy, 1),
        (FinalScoringCondition::MostSatellites, 3),
    ];

    for (condition, expected) in cases {
        assert_eq!(
            ScoringEngine::final_scoring_metric(&state, PLAYER, &condition),
            expected,
            "wrong metric for {condition:?}"
        );
    }
}

#[test]
fn ordinary_sector_tile_excludes_deep_space_and_interspace() {
    let state = scoring_fixture();
    assert_eq!(
        ScoringEngine::final_scoring_metric(&state, PLAYER, &FinalScoringCondition::MostSectors,),
        1
    );
    assert_eq!(
        ScoringEngine::final_scoring_metric(
            &state,
            PLAYER,
            &FinalScoringCondition::MostDeepSpaceSectors,
        ),
        1
    );
}
