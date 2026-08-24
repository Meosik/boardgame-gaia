use crate::game_state::{FactionId, PlanetType, ResearchTrack, ResourceKind, StructureType};
use serde::Deserialize;

static FACTIONS_TOML: &str = include_str!("../../data/factions.toml");

#[derive(Debug, Deserialize)]
pub struct FactionDataFile {
    pub factions: Vec<FactionData>,
}

#[derive(Debug, Deserialize)]
pub struct FactionData {
    pub id: String,
    pub home_planet: String,
    pub starting_ore: u8,
    pub starting_credits: u8,
    pub starting_knowledge: u8,
    pub starting_qic: u8,
    pub starting_bowl1: u8,
    pub starting_bowl2: u8,
    pub starting_bowl3: u8,
    pub gaiaformers: u8,
    pub starting_structures: Vec<RelativeStructure>,
    /// Research tracks this faction starts at a non-zero level, e.g. the
    /// Lost Fleet factions (rulebook faction board icons, not in the prose
    /// text: Tinkeroids/Science, Moweyds/GaiaProject, SpaceGiants/Navigation,
    /// Darkanians/Navigation+Economy — all at level 1).
    #[serde(default)]
    pub starting_track_bonuses: Vec<StartingTrackBonus>,
    /// Overrides the universal TradingStation round-income (base=0 credits,
    /// table=[3,4,4,5]) when this faction's board differs. Only Bescods
    /// deviates (its ability swaps TradingStation/ResearchLab income).
    #[serde(default)]
    pub trading_station_income: Option<StructureIncomeOverride>,
    /// Overrides the universal ResearchLab round-income (base=1 knowledge,
    /// table=[1,1,1]) when this faction's board differs (Firaks: base only;
    /// Bescods/Nevlas: base, table, and resource all differ).
    #[serde(default)]
    pub research_lab_income: Option<StructureIncomeOverride>,
    /// Overrides the universal Academy(Science) income (2 knowledge/round)
    /// when built. Only Itars deviates (3 knowledge/round).
    #[serde(default)]
    pub academy_science_income: Option<u8>,
    /// Overrides the universal PlanetaryInstitute power charge (4/round)
    /// when built. Only Space Giants deviates (6/round).
    #[serde(default)]
    pub planetary_institute_charge: Option<u8>,
    /// Overrides the universal PlanetaryInstitute bonus power token (1/round,
    /// entering bowl1) granted alongside the charge when built. Lantids get
    /// none; Xenos/Gleens get a different resource instead (see
    /// `planetary_institute_bonus_resource`); Ambas/Bescods get 2/round.
    #[serde(default)]
    pub planetary_institute_bonus_power_tokens: Option<u8>,
    /// An additional per-round PlanetaryInstitute income (on top of the
    /// power charge and/or bonus power token) paid in a different resource.
    /// Only Xenos (1 QIC), Gleens (1 ore), and Ivits (1 QIC, alongside its
    /// normal power token) have this.
    #[serde(default)]
    pub planetary_institute_bonus_resource: Option<BonusResource>,
    /// Overrides the universal Academy(Qic) action (gain 1 QIC) when taken.
    /// Only BalTaks deviates (gain 4 credits instead).
    #[serde(default)]
    pub academy_qic_action: Option<BonusResource>,
}

/// A flat `amount` of `resource` (rulebook resource name — see
/// `parse_resource_kind`), used for faction-board deviations that are just
/// "gain N of resource X" with no table/base structure.
#[derive(Debug, Deserialize)]
pub struct BonusResource {
    pub resource: String,
    pub amount: u8,
}

impl BonusResource {
    pub fn resource_kind(&self) -> Option<ResourceKind> {
        parse_resource_kind(&self.resource)
    }
}

/// A faction-board deviation from the universal structure round-income
/// table (rulebook: each round, gain `base` plus the revealed portion of
/// `table`, left-to-right, as the Nth structure of that type is built —
/// i.e. total = base + table[0..count_built].sum()).
#[derive(Debug, Deserialize)]
pub struct StructureIncomeOverride {
    pub base: u8,
    pub table: Vec<u8>,
    /// The resource this income is paid in. `None` means the structure's
    /// usual resource (Credits for TradingStation, Knowledge for ResearchLab).
    #[serde(default)]
    pub resource: Option<String>,
}

impl StructureIncomeOverride {
    pub fn resource_kind(&self) -> Option<ResourceKind> {
        self.resource.as_deref().and_then(parse_resource_kind)
    }
}

#[derive(Debug, Deserialize)]
pub struct StartingTrackBonus {
    pub track: String,
    pub level: u8,
}

#[derive(Debug, Deserialize)]
pub struct RelativeStructure {
    pub rel_q: i32,
    pub rel_r: i32,
    pub kind: String,
}

impl FactionData {
    pub fn faction_id(&self) -> Option<FactionId> {
        match self.id.as_str() {
            "Terrans" => Some(FactionId::Terrans),
            "Lantids" => Some(FactionId::Lantids),
            "Xenos" => Some(FactionId::Xenos),
            "Gleens" => Some(FactionId::Gleens),
            "Taklons" => Some(FactionId::Taklons),
            "Ambas" => Some(FactionId::Ambas),
            "HadschHallas" => Some(FactionId::HadschHallas),
            "Ivits" => Some(FactionId::Ivits),
            "Geodens" => Some(FactionId::Geodens),
            "BalTaks" => Some(FactionId::BalTaks),
            "Firaks" => Some(FactionId::Firaks),
            "Bescods" => Some(FactionId::Bescods),
            "Nevlas" => Some(FactionId::Nevlas),
            "Itars" => Some(FactionId::Itars),
            "Tinkeroids" => Some(FactionId::Tinkeroids),
            "Moweyds" => Some(FactionId::Moweyds),
            "SpaceGiants" => Some(FactionId::SpaceGiants),
            "Darkanians" => Some(FactionId::Darkanians),
            _ => None,
        }
    }

    pub fn home_planet_type(&self) -> Option<PlanetType> {
        parse_planet_type(&self.home_planet)
    }

    /// Parsed `(track, level)` pairs from `starting_track_bonuses`, skipping
    /// any entry whose `track` name doesn't parse (defensive; `data/mod.rs`'s
    /// `factions_toml_parses` test should catch a typo in the data file).
    pub fn starting_tracks(&self) -> Vec<(ResearchTrack, u8)> {
        self.starting_track_bonuses
            .iter()
            .filter_map(|b| Some((parse_research_track(&b.track)?, b.level)))
            .collect()
    }
}

pub fn parse_research_track(s: &str) -> Option<ResearchTrack> {
    match s {
        "Terraforming" => Some(ResearchTrack::Terraforming),
        "Navigation" => Some(ResearchTrack::Navigation),
        "ArtificialIntelligence" => Some(ResearchTrack::ArtificialIntelligence),
        "GaiaProject" => Some(ResearchTrack::GaiaProject),
        "Economy" => Some(ResearchTrack::Economy),
        "Science" => Some(ResearchTrack::Science),
        _ => None,
    }
}

pub fn parse_planet_type(s: &str) -> Option<PlanetType> {
    match s {
        "Terra" => Some(PlanetType::Terra),
        "Swamp" => Some(PlanetType::Swamp),
        "Desert" => Some(PlanetType::Desert),
        "Oxide" => Some(PlanetType::Oxide),
        "Titanium" => Some(PlanetType::Titanium),
        "Volcanic" => Some(PlanetType::Volcanic),
        "Ice" => Some(PlanetType::Ice),
        "Transdim" => Some(PlanetType::Transdim),
        "Gaia" => Some(PlanetType::Gaia),
        "LostPlanet" => Some(PlanetType::LostPlanet),
        "Asteroid" => Some(PlanetType::Asteroid),
        "ProtoPlanet" => Some(PlanetType::ProtoPlanet),
        _ => None,
    }
}

pub fn parse_resource_kind(s: &str) -> Option<ResourceKind> {
    match s {
        "Ore" => Some(ResourceKind::Ore),
        "Credits" => Some(ResourceKind::Credits),
        "Knowledge" => Some(ResourceKind::Knowledge),
        "Qic" => Some(ResourceKind::Qic),
        "Power" => Some(ResourceKind::Power),
        _ => None,
    }
}

pub fn parse_structure_kind(s: &str) -> Option<StructureType> {
    match s {
        "Mine" => Some(StructureType::Mine),
        "TradingStation" => Some(StructureType::TradingStation),
        "ResearchLab" => Some(StructureType::ResearchLab),
        "PlanetaryInstitute" => Some(StructureType::PlanetaryInstitute),
        "Satellite" => Some(StructureType::Satellite),
        _ => None,
    }
}

pub fn load_factions() -> FactionDataFile {
    #[allow(clippy::expect_used)]
    toml::from_str(FACTIONS_TOML)
        .expect("factions.toml embedded at compile time — parse failure is a build error")
}
