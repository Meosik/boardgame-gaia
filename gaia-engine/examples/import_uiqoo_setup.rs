//! Offline, setup-only preview adapter for tools/import_uiqoo_setup.py output.
//! Does not create a room, choose factions, place mines, or change game rules.
use gaia_engine::game_state::{
    ArtifactId, Booster, EconomyResearchTileSide, FederationToken, FinalScoringTile, Hex, HexCoord,
    LostFleetAdvancedTechRequirement, Planet, PlanetType, SpaceTileKind, SpaceshipId, TechTile,
};
use gaia_engine::randomizer::SectorPlacement;
use gaia_engine::{MapEngine, Randomizer};
use serde::de::DeserializeOwned;
use serde_json::{json, Value};
use std::{error::Error, fs, io::Write};

fn field<T: DeserializeOwned>(value: &Value, key: &str) -> Result<T, serde_json::Error> {
    serde_json::from_value(value[key].clone())
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        return Err("usage: import_uiqoo_setup observed-setup.json replay.json".into());
    }
    let observed: Value = serde_json::from_slice(&fs::read(&args[1])?)?;
    if observed["kind"] != "observed-randomizer-setup"
        || observed["schema_version"] != 1
        || !observed["player_assignments"].is_null()
        || !observed["bids"].is_null()
        || observed["actions"] != json!([])
    {
        return Err("expected unassigned, setup-only observation".into());
    }
    let seed: String = field(&observed["source"], "seed")?;
    let sectors: Vec<SectorPlacement> = field(&observed, "sectors")?;
    let mut setup = Randomizer::generate_setup(&seed)?;
    setup.factions = field(&observed, "factions_in_source_order")?;
    setup.round_tile_ids = field(&observed, "round_tile_ids")?;
    setup.boosters = field::<Vec<u8>>(&observed, "booster_ids")?
        .into_iter()
        .map(Booster)
        .collect();
    setup.final_scoring =
        field::<[u8; 2]>(&observed, "final_scoring_ids")?.map(FinalScoringTile::from_id);
    setup.tech_tile_slot_ids = field(&observed, "tech_tile_slot_ids")?;
    setup.tech_tile_ids = setup
        .tech_tile_slot_ids
        .iter()
        .flat_map(|id| [*id; 4])
        .collect();
    setup.advanced_tech_tile_ids = field(&observed, "advanced_tech_tile_ids")?;
    setup.terraforming_color_order = field(&observed, "terraforming_color_order")?;
    setup.sector_layout = sectors
        .iter()
        .filter(|s| s.sector_id <= 10)
        .cloned()
        .collect();
    setup.deep_space_layout = sectors
        .iter()
        .filter(|s| s.sector_id > 10)
        .cloned()
        .collect();
    let players = (0..4)
        .map(|id| (id, format!("미배정 {}", id + 1)))
        .collect::<Vec<_>>();
    let mut state = MapEngine::init_game_state("UIQOO-PREVIEW", &seed, &players, &setup);
    // Native initialization randomizes interspaces and outer sectors. Replace the entire
    // board with observed placements, preserving the engine's planet templates and sides.
    state.board = MapEngine::build_board(&sectors);
    if state.board.hexes.len() != 214 {
        return Err("overlapping or incomplete sector geometry".into());
    }
    let interspaces: Vec<Value> = field(&observed, "interspaces")?;
    for tile in interspaces {
        let coord: HexCoord = field(&tile, "coord")?;
        let kind: String = field(&tile, "kind")?;
        let planet_type = match kind.as_str() {
            "asteroid" => Some(PlanetType::Asteroid),
            "proto" => Some(PlanetType::ProtoPlanet),
            "empty" => None,
            ship => {
                let id = match ship {
                    "twilight" => SpaceshipId::Twilight,
                    "eclipse" => SpaceshipId::Eclipse,
                    "tfmars" => SpaceshipId::TFMars,
                    "rebellion" => SpaceshipId::Rebellion,
                    _ => return Err("unknown interspace tile".into()),
                };
                if state.board.spaceship_tiles.insert(id, coord).is_some() {
                    return Err("duplicate spaceship".into());
                }
                None
            }
        };
        let hex = Hex {
            coord,
            planet: planet_type.map(|planet_type| Planet {
                planet_type,
                is_gaia_formed: false,
                owner: None,
            }),
            space_tile_kind: Some(SpaceTileKind::Single),
            structures: vec![],
            satellites: vec![],
        };
        if state.board.hexes.insert(coord, hex).is_some() {
            return Err("overlapping interspace".into());
        }
    }
    if state.board.hexes.len() != 224 || state.board.spaceship_tiles.len() != 4 {
        return Err("incomplete board".into());
    }
    let token: u8 = field(&observed, "terraforming_level_5_token")?;
    if !(1..=6).contains(&token) {
        return Err("invalid terraforming token".into());
    }
    state.research_board.terraforming_level_5_token = Some(FederationToken(token));
    state.research_board.federation_tokens = (1..=6)
        .flat_map(|id| std::iter::repeat(FederationToken(id)).take(if id == token { 2 } else { 3 }))
        .collect();
    state.research_board.economy_research_tile_side =
        match observed["economy_research_tile_side"].as_str() {
            Some("vp") => EconomyResearchTileSide::VictoryPoints,
            Some("pw") => EconomyResearchTileSide::Power,
            _ => return Err("unknown economy side".into()),
        };
    // The source's 25 VP face differs from this project's four-player default.
    // Preserve it only in this read-only example; never change normal room rules.
    state.research_board.lost_fleet_advanced_tech_requirement =
        match observed["lost_fleet_advanced_tech_requirement"].as_str() {
            Some("vp") => LostFleetAdvancedTechRequirement::VictoryPoints,
            Some("shuttle") => LostFleetAdvancedTechRequirement::ExplorationShuttles,
            _ => return Err("unknown advanced requirement face".into()),
        };
    let feds: [u8; 4] = field(&observed, "spaceship_federation_ids")?;
    let techs: [u8; 3] = field(&observed, "spaceship_tech_ids")?;
    let artifacts: [u8; 4] = field(&observed, "artifact_ids")?;
    for ship in &mut state.spaceship_boards {
        let (fed_index, tech_index) = match ship.id {
            SpaceshipId::Twilight => (0, None),
            SpaceshipId::Eclipse => (2, Some(1)),
            SpaceshipId::TFMars => (1, Some(0)),
            SpaceshipId::Rebellion => (3, Some(2)),
        };
        ship.federation_token = Some(FederationToken(feds[fed_index]));
        ship.tech_tiles = tech_index
            .map(|i| vec![TechTile(techs[i]); 4])
            .unwrap_or_default();
        ship.artifact_pool = if ship.id == SpaceshipId::Twilight {
            artifacts.into_iter().map(ArtifactId).collect()
        } else {
            vec![]
        };
    }
    let replay = json!({
        "schema_version": 1,
        "metadata": { "focus_player": 0, "seed": seed, "policy": "observed-setup-only",
            "faction": "unassigned", "steps": 0,
            "versions": { "source_observation": observed,
                "warning": "Setup preview only. Player resources and VP are engine placeholders, not observed gameplay." } },
        "events": [],
        "frames": [{ "decision_id": 0, "player": null, "action": null,
            "legal_action_count": 0, "legal_federation_count": 0, "event_end": 0, "state": state }]
    });
    let mut output = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[2])?;
    serde_json::to_writer_pretty(&mut output, &replay)?;
    output.write_all(b"\n")?;
    Ok(())
}
