//! Generate sidebar production tables from real native income transitions.
//! cargo run -p gaia-engine --example income_projection_data > gaia-frontend/src/data/income.json
use gaia_engine::game_state::{
    AcademyType, ArtifactId, Booster, EconomyResearchTileSide, FactionId, GameEvent, GamePhase,
    HexCoord, PlayerState, Resources, Structure, StructureType, TechTile,
};
use gaia_engine::test_utils::builders::GameStateBuilder;
use gaia_engine::RuleEngine;
use serde_json::{json, Map, Value};

type Income = [i32; 7]; // ore, credits, knowledge, QIC, charge, fresh tokens, VP

fn receive(player: &PlayerState, side: EconomyResearchTileSide) -> Income {
    let mut state = GameStateBuilder::new()
        .with_player_fn(0, |p| *p = player.clone())
        .with_phase(GamePhase::RoundScoring { round: 1 })
        .build();
    state.research_board.economy_research_tile_side = side;
    let events = RuleEngine::advance_to_next_round(&mut state)
        .unwrap_or_else(|error| panic!("income transition: {error}"));
    events
        .iter()
        .find_map(|event| match event {
            GameEvent::IncomeReceived {
                ore,
                credits,
                knowledge,
                qic,
                power_charge,
                power_tokens,
                vp,
                ..
            } => Some(
                [
                    *ore,
                    *credits,
                    *knowledge,
                    *qic,
                    *power_charge,
                    *power_tokens,
                    *vp,
                ]
                .map(i32::from),
            ),
            _ => None,
        })
        .unwrap_or_else(|| panic!("missing native income"))
}

fn player(faction: FactionId) -> PlayerState {
    let state = GameStateBuilder::new()
        .with_player_fn(0, |p| {
            p.faction = Some(faction);
            p.resources = Resources::zero();
            p.booster = None;
            p.structures.clear();
        })
        .build();
    state.players[0].clone()
}

fn structure(kind: StructureType) -> Structure {
    Structure {
        hex: HexCoord::new(0, 0),
        kind,
    }
}

fn delta(
    base: &PlayerState,
    change: impl FnOnce(&mut PlayerState),
    side: EconomyResearchTileSide,
) -> Income {
    let before = receive(base, side);
    let mut after = base.clone();
    change(&mut after);
    let result = receive(&after, side);
    std::array::from_fn(|i| result[i] - before[i])
}

fn generate() -> Value {
    let power = EconomyResearchTileSide::Power;
    let mut factions = Map::new();
    let mut cases = Vec::new();
    for data in gaia_engine::data::load_factions().factions {
        let id = data
            .faction_id()
            .unwrap_or_else(|| panic!("unknown faction"));
        let base = player(id);
        let mut curves = Map::new();
        for (name, kind, supply) in [
            ("Mine", StructureType::Mine, 8),
            ("TradingStation", StructureType::TradingStation, 4),
            ("ResearchLab", StructureType::ResearchLab, 3),
            ("PlanetaryInstitute", StructureType::PlanetaryInstitute, 1),
            ("Science", StructureType::Academy(AcademyType::Science), 1),
            ("Qic", StructureType::Academy(AcademyType::Qic), 1),
        ] {
            let values: Vec<_> = (0..=supply)
                .map(|count| {
                    delta(
                        &base,
                        |p| {
                            p.structures = vec![structure(kind); count];
                        },
                        power,
                    )
                })
                .collect();
            curves.insert(name.into(), json!(values));
        }
        factions.insert(
            data.id.clone(),
            json!({"base": receive(&base, power), "structures": curves}),
        );
        // Combined independent oracle: catches composition, covering, faction and QIC conversion errors.
        for with_qic_academy in [false, true] {
            let mut p = base.clone();
            p.structures = vec![structure(StructureType::Mine); 2];
            p.structures.extend([
                structure(StructureType::TradingStation),
                structure(StructureType::ResearchLab),
                structure(StructureType::PlanetaryInstitute),
                structure(StructureType::Academy(AcademyType::Science)),
            ]);
            if with_qic_academy {
                p.structures
                    .push(structure(StructureType::Academy(AcademyType::Qic)));
            }
            p.research_tracks.economy = 4;
            p.research_tracks.science = 3;
            p.booster = Some(Booster(9));
            p.tech_tiles = vec![TechTile(2), TechTile(3), TechTile(5)];
            p.covered_tech_tiles = vec![TechTile(3)];
            p.artifacts = vec![ArtifactId(2), ArtifactId(3)];
            for side in [power, EconomyResearchTileSide::VictoryPoints] {
                cases.push(json!({"player": p, "side": side, "income": receive(&p, side)}));
            }
        }
    }
    let base = player(FactionId::Terrans);
    let boosters: Map<_, _> = (1..=14)
        .map(|id| {
            (
                id.to_string(),
                json!(delta(&base, |p| p.booster = Some(Booster(id)), power)),
            )
        })
        .collect();
    let tech: Map<_, _> = [2, 3, 5]
        .into_iter()
        .map(|id| {
            (
                id.to_string(),
                json!(delta(&base, |p| p.tech_tiles = vec![TechTile(id)], power)),
            )
        })
        .collect();
    let artifacts: Map<_, _> = [2, 3]
        .into_iter()
        .map(|id| {
            (
                id.to_string(),
                json!(delta(&base, |p| p.artifacts = vec![ArtifactId(id)], power)),
            )
        })
        .collect();
    let mut economy = Map::new();
    for (name, side) in [
        ("Power", power),
        ("VictoryPoints", EconomyResearchTileSide::VictoryPoints),
    ] {
        economy.insert(
            name.into(),
            json!((0..=5)
                .map(|level| delta(&base, |p| p.research_tracks.economy = level, side))
                .collect::<Vec<_>>()),
        );
    }
    let science: Vec<_> = (0..=5)
        .map(|level| delta(&base, |p| p.research_tracks.science = level, power))
        .collect();
    json!({"fields": ["ore", "credits", "knowledge", "qic", "power_charge", "power_tokens", "vp"],
        "factions": factions, "boosters": boosters, "tech": tech, "artifacts": artifacts,
        "economy": economy, "science": science, "cases": cases})
}

fn main() {
    let mut generated = generate();
    let cases = generated
        .as_object_mut()
        .unwrap_or_else(|| panic!("object"))
        .remove("cases")
        .unwrap_or_else(|| panic!("cases"));
    let output = if std::env::args().any(|arg| arg == "--fixtures") {
        cases
    } else {
        generated
    };
    println!(
        "{}",
        serde_json::to_string(&output).unwrap_or_else(|e| panic!("{e}"))
    );
}

#[cfg(test)]
mod tests {
    #[test]
    fn committed_projection_tables_match_native_income() {
        let file = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../gaia-frontend/src/data/income.json");
        let mut recorded: serde_json::Value = serde_json::from_slice(
            &std::fs::read(file).unwrap_or_else(|e| panic!("Generate income data first: {e}")),
        )
        .unwrap_or_else(|e| panic!("{e}"));
        let cases = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../gaia-frontend/src/tests/fixtures/incomeProjection.json");
        recorded["cases"] = serde_json::from_slice(
            &std::fs::read(cases).unwrap_or_else(|e| panic!("Generate --fixtures first: {e}")),
        )
        .unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(
            recorded,
            super::generate(),
            "Regenerate sidebar income data after income rules change"
        );
    }
}
