use gaia_engine::game_state::{
    Booster, FactionId, GamePhase, Hex, HexCoord, PlacedStructure, SpaceshipBoard, SpaceshipId,
    Structure, StructureType, TechTile,
};
use gaia_engine::rules::actions::{GameAction, TechTileRef};
use gaia_engine::rules::engine::AiDecision;
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;

#[test]
fn concrete_menu_includes_booster_pass_power_and_owned_tech_action(
) -> Result<(), Box<dyn std::error::Error>> {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(FactionId::Terrans);
            p.booster = Some(Booster(8));
            p.resources.power.bowl3 = 10;
            p.tech_tiles = vec![TechTile(10)];
        })
        .with_player(1)
        .build();
    let candidates = RuleEngine::ai_decisions(&state)?;
    assert!(!candidates.contains(&AiDecision::Game(GameAction::Pass { booster_id: None })));
    assert!(candidates.contains(&AiDecision::Game(GameAction::Pass {
        booster_id: Some(1)
    })));
    assert!(
        candidates.contains(&AiDecision::Game(GameAction::PowerAction {
            id: 1,
            coord: None
        }))
    );
    assert!(
        candidates.contains(&AiDecision::Game(GameAction::TechTileSpecialAction {
            tile: TechTileRef::Standard { tile: TechTile(10) }
        }))
    );
    for candidate in candidates {
        if let AiDecision::Game(action) = candidate {
            RuleEngine::validate_action(&state, 0, &action)?;
        }
    }
    Ok(())
}

#[test]
fn ice_factions_discard_a_token_and_baltaks_pay_seven_vp() -> Result<(), Box<dyn std::error::Error>>
{
    for faction in [
        FactionId::Nevlas,
        FactionId::Itars,
        FactionId::BalTaks,
        FactionId::Terrans,
    ] {
        let coord = HexCoord::new(0, 0);
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(faction);
                p.vp = 10;
                p.resources.power.bowl1 = 1;
                p.resources.power.bowl2 = 2;
                p.resources.power.bowl3 = 3;
                p.exploration_shuttles_available = 3;
                p.structures = vec![Structure {
                    hex: coord,
                    kind: StructureType::Mine,
                }];
            })
            .with_player(1)
            .build();
        state.board.hexes.insert(
            coord,
            Hex {
                coord,
                planet: None,
                space_tile_kind: None,
                structures: vec![PlacedStructure {
                    owner: 0,
                    kind: StructureType::Mine,
                }],
                satellites: vec![],
            },
        );
        let target = HexCoord::new(1, 0);
        state.board.hexes.insert(
            target,
            Hex {
                coord: target,
                planet: None,
                space_tile_kind: None,
                structures: vec![],
                satellites: vec![],
            },
        );
        state
            .board
            .spaceship_tiles
            .insert(SpaceshipId::TFMars, HexCoord::new(1, 0));
        state.spaceship_boards.push(SpaceshipBoard {
            id: SpaceshipId::TFMars,
            explorers: vec![None; 4],
            artifact_pool: vec![],
            tech_tiles: vec![],
            federation_token: None,
        });
        let action = GameAction::ExploreSpaceship {
            ship: SpaceshipId::TFMars,
        };
        if matches!(faction, FactionId::Nevlas | FactionId::Itars) {
            let mut empty = state.clone();
            empty.players[0].resources.power.bowl1 = 0;
            empty.players[0].resources.power.bowl2 = 0;
            empty.players[0].resources.power.bowl3 = 0;
            assert!(RuleEngine::validate_action(&empty, 0, &action).is_err());
        }
        RuleEngine::apply_action(&mut state, 0, action)?;
        assert_eq!(
            state.players[0].vp,
            if faction == FactionId::BalTaks { 3 } else { 5 }
        );
        assert_eq!(
            state.players[0].resources.power.bowl1,
            if matches!(faction, FactionId::Nevlas | FactionId::Itars) {
                0
            } else {
                1
            }
        );
        assert_eq!(state.players[0].resources.power.bowl2, 2);
        assert_eq!(state.players[0].resources.power.bowl3, 3);
        assert_eq!(state.players[0].resources.power.gaia_forming, 0);
    }
    Ok(())
}

#[test]
fn interrupted_turn_returns_the_responder() -> Result<(), Box<dyn std::error::Error>> {
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.phase = GamePhase::ChargePowerPending {
        queue: vec![gaia_engine::game_state::PendingCharge {
            player: 1,
            hex: HexCoord::new(0, 0),
            max_power: 1,
        }],
        resume_active_player: Some(0),
    };
    assert_eq!(RuleEngine::decision_player(&state)?, Some(1));
    assert!(!RuleEngine::ai_decisions(&state)?.is_empty());
    Ok(())
}

#[test]
fn active_player_is_an_index_into_the_changed_turn_order() -> Result<(), Box<dyn std::error::Error>>
{
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player(1)
        .build();
    state.turn_order = vec![1, 0];
    assert_eq!(RuleEngine::decision_player(&state)?, Some(1));
    assert!(!RuleEngine::ai_decisions(&state)?.is_empty());
    Ok(())
}

#[test]
fn rare_pending_phases_expose_valid_decisions_for_the_named_player(
) -> Result<(), Box<dyn std::error::Error>> {
    use gaia_engine::game_state::{GaiaDecisionKind, PendingGaiaDecision, PendingIncomeOrder};
    let base = GameStateBuilder::new()
        .with_player(0)
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Terrans);
            p.resources.power.gaia_forming = 4;
        })
        .build();
    let phases = [
        GamePhase::IncomeOrderPending {
            queue: vec![PendingIncomeOrder {
                player: 1,
                charge_amount: 2,
                bonus_tokens: 1,
            }],
            round: 1,
        },
        GamePhase::GaiaDecisionPending {
            queue: vec![PendingGaiaDecision {
                player: 1,
                kind: GaiaDecisionKind::TerransPowerConversion,
                remaining_power: 4,
            }],
            round: 1,
        },
        GamePhase::LostPlanetChargePowerPending {
            queue: vec![gaia_engine::game_state::PendingCharge {
                player: 1,
                hex: HexCoord::new(0, 0),
                max_power: 1,
            }],
            resume_phase: Box::new(GamePhase::ActionPhase { active_player: 0 }),
        },
    ];
    for phase in phases {
        let mut state = base.clone();
        state.phase = phase;
        assert_eq!(RuleEngine::decision_player(&state)?, Some(1));
        let candidates = RuleEngine::ai_decisions(&state)?;
        assert!(!candidates.is_empty());
        for candidate in candidates {
            if let AiDecision::Game(action) = candidate {
                RuleEngine::validate_action(&state, 1, &action)?;
            }
        }
    }
    let mut state = base;
    state.players[1].faction = Some(FactionId::Tinkeroids);
    state.phase = GamePhase::TinkeroidsTileSelectionPending {
        player: 1,
        round: 1,
    };
    let candidates = RuleEngine::ai_decisions(&state)?;
    assert!(!candidates.is_empty());
    for candidate in candidates {
        if let AiDecision::Game(action) = candidate {
            RuleEngine::validate_action(&state, 1, &action)?;
        }
    }
    Ok(())
}

#[test]
fn adjacent_federation_needs_no_satellites_for_terrans_or_ivits(
) -> Result<(), Box<dyn std::error::Error>> {
    use gaia_engine::game_state::{AcademyType, Planet, PlanetType};
    for faction in [FactionId::Terrans, FactionId::Ivits] {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(faction);
                p.resources.power.bowl1 = 0;
                p.resources.power.bowl2 = 0;
                p.resources.power.bowl3 = 0;
                p.resources.qic = 0;
            })
            .with_player(1)
            .build();
        state.research_board.federation_tokens = vec![gaia_engine::game_state::FederationToken(1)];
        for (coord, kind) in [
            (HexCoord::new(0, 0), StructureType::PlanetaryInstitute),
            (
                HexCoord::new(1, 0),
                StructureType::Academy(AcademyType::Science),
            ),
            (HexCoord::new(0, 1), StructureType::Mine),
        ] {
            state.players[0]
                .structures
                .push(Structure { hex: coord, kind });
            state.board.hexes.insert(
                coord,
                Hex {
                    coord,
                    planet: Some(Planet {
                        planet_type: PlanetType::Terra,
                        is_gaia_formed: false,
                        owner: Some(0),
                    }),
                    space_tile_kind: None,
                    structures: vec![PlacedStructure { owner: 0, kind }],
                    satellites: vec![],
                },
            );
        }
        let actions = RuleEngine::ai_decisions(&state)?;
        let federations: Vec<_> = actions
            .iter()
            .filter_map(|a| match a {
                AiDecision::Game(
                    action @ GameAction::FormFederation {
                        satellite_hexes, ..
                    },
                ) if satellite_hexes.is_empty() => Some(action),
                _ => None,
            })
            .collect();
        assert!(
            !federations.is_empty(),
            "missing zero-satellite federation for {faction:?}"
        );
        for action in federations {
            RuleEngine::validate_action(&state, 0, action)?;
        }
    }
    Ok(())
}

#[test]
fn pending_lost_planet_exposes_a_concrete_placement() -> Result<(), Box<dyn std::error::Error>> {
    use gaia_engine::game_state::{Planet, PlanetType};
    let home = HexCoord::new(0, 0);
    let target = HexCoord::new(1, 0);
    let mut state = GameStateBuilder::new()
        .with_player(0)
        .with_player_fn(1, |p| {
            p.faction = Some(FactionId::Terrans);
            p.research_tracks.navigation = 5;
            p.structures.push(Structure {
                hex: home,
                kind: StructureType::Mine,
            });
        })
        .build();
    state.board.hexes.insert(
        home,
        Hex {
            coord: home,
            planet: Some(Planet {
                planet_type: PlanetType::Terra,
                is_gaia_formed: false,
                owner: Some(1),
            }),
            space_tile_kind: None,
            structures: vec![PlacedStructure {
                owner: 1,
                kind: StructureType::Mine,
            }],
            satellites: vec![],
        },
    );
    state.board.hexes.insert(
        target,
        Hex {
            coord: target,
            planet: None,
            space_tile_kind: None,
            structures: vec![],
            satellites: vec![],
        },
    );
    state.phase = GamePhase::LostPlanetPlacementPending {
        player: 1,
        resume_phase: Box::new(GamePhase::ActionPhase { active_player: 0 }),
    };
    let action = GameAction::PlaceLostPlanet { coord: target };
    assert_eq!(RuleEngine::decision_player(&state)?, Some(1));
    assert!(RuleEngine::ai_decisions(&state)?.contains(&AiDecision::Game(action.clone())));
    RuleEngine::apply_action(&mut state, 1, action)?;
    assert_eq!(state.board.lost_planet, Some(target));
    Ok(())
}

#[test]
fn concrete_menu_includes_legal_same_kind_batches_without_replacing_single_conversions(
) -> Result<(), Box<dyn std::error::Error>> {
    use gaia_engine::rules::actions::FreeActionKind;
    for faction in [FactionId::Nevlas, FactionId::Terrans] {
        let state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(faction);
                p.resources.power.bowl3 = 3;
                p.resources.qic = 3;
                p.structures.push(Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                });
            })
            .with_player(1)
            .build();
        let before = state.serialize();
        let candidates = RuleEngine::ai_decisions(&state)?;
        for kind in FreeActionKind::ALL {
            for count in 0..=31 {
                let action = GameAction::FreeAction { kind, count };
                assert_eq!(
                    candidates.contains(&AiDecision::Game(action.clone())),
                    RuleEngine::validate_action(&state, 0, &action).is_ok(),
                    "{faction:?} {kind:?} x{count}"
                );
            }
        }
        assert_eq!(state.serialize(), before);
        assert_eq!(candidates, RuleEngine::ai_decisions(&state)?);
        if faction == FactionId::Nevlas {
            let mut next = state.clone();
            let ore = next.players[0].resources.ore;
            RuleEngine::apply_action(
                &mut next,
                0,
                GameAction::FreeAction {
                    kind: FreeActionKind::PowerToOre,
                    count: 2,
                },
            )?;
            assert_eq!(next.players[0].resources.ore, ore + 2);
            assert_eq!(next.players[0].resources.power.bowl3, 0);
            assert_eq!(next.phase, state.phase);
        }
    }
    Ok(())
}
