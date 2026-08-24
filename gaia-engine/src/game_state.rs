use crate::error::DeserializeError;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Primitive newtypes ────────────────────────────────────────────────────────

pub type PlayerId = u8; // 0..3
pub type ShipId = u8;
pub type BoosterId = u8;

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RoomCode(pub String);

// ── HexCoord (Axial) ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct HexCoord {
    pub q: i32,
    pub r: i32,
}

impl serde::Serialize for HexCoord {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(&format!("{},{}", self.q, self.r))
    }
}

impl<'de> serde::Deserialize<'de> for HexCoord {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        let s = String::deserialize(deserializer)?;
        let mut parts = s.splitn(2, ',');
        let q = parts
            .next()
            .ok_or_else(|| serde::de::Error::custom("HexCoord missing q"))?
            .parse::<i32>()
            .map_err(serde::de::Error::custom)?;
        let r = parts
            .next()
            .ok_or_else(|| serde::de::Error::custom("HexCoord missing r"))?
            .parse::<i32>()
            .map_err(serde::de::Error::custom)?;
        Ok(HexCoord { q, r })
    }
}

impl HexCoord {
    pub const fn new(q: i32, r: i32) -> Self {
        Self { q, r }
    }

    pub fn s(&self) -> i32 {
        -self.q - self.r
    }

    pub fn distance(&self, other: &HexCoord) -> u32 {
        let dq = (self.q - other.q).unsigned_abs();
        let dr = (self.r - other.r).unsigned_abs();
        let ds = (self.s() - other.s()).unsigned_abs();
        dq.max(dr).max(ds)
    }

    pub fn neighbors(&self) -> [HexCoord; 6] {
        let (q, r) = (self.q, self.r);
        [
            HexCoord::new(q + 1, r),
            HexCoord::new(q - 1, r),
            HexCoord::new(q, r + 1),
            HexCoord::new(q, r - 1),
            HexCoord::new(q + 1, r - 1),
            HexCoord::new(q - 1, r + 1),
        ]
    }

    /// Rotate 60° counter-clockwise around origin
    pub fn rotate_60(&self) -> HexCoord {
        HexCoord::new(-self.r, self.q + self.r)
    }

    pub fn rotate_n(&self, n: u8) -> HexCoord {
        let mut h = *self;
        for _ in 0..(n % 6) {
            h = h.rotate_60();
        }
        h
    }

    pub fn add(&self, other: &HexCoord) -> HexCoord {
        HexCoord::new(self.q + other.q, self.r + other.r)
    }
}

// ── Enums ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PlanetType {
    Terra,
    Swamp,
    Desert,
    Oxide,
    Titanium,
    Volcanic,
    Ice,
    Transdim,
    Gaia,
    LostPlanet,
    Asteroid,
    ProtoPlanet,
}

impl PlanetType {
    pub fn from_name(s: &str) -> Option<Self> {
        match s {
            "Terra" => Some(Self::Terra),
            "Swamp" => Some(Self::Swamp),
            "Desert" => Some(Self::Desert),
            "Oxide" => Some(Self::Oxide),
            "Titanium" => Some(Self::Titanium),
            "Volcanic" => Some(Self::Volcanic),
            "Ice" => Some(Self::Ice),
            "Transdim" => Some(Self::Transdim),
            "Gaia" => Some(Self::Gaia),
            "LostPlanet" => Some(Self::LostPlanet),
            "Asteroid" => Some(Self::Asteroid),
            "ProtoPlanet" => Some(Self::ProtoPlanet),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum StructureType {
    Mine,
    TradingStation,
    ResearchLab,
    PlanetaryInstitute,
    Academy(AcademyType),
    Satellite,
    SpaceStation,
}

impl StructureType {
    pub fn power_value(&self) -> u32 {
        match self {
            Self::Mine => 1,
            Self::TradingStation | Self::ResearchLab => 2,
            Self::PlanetaryInstitute | Self::Academy(_) => 3,
            Self::Satellite | Self::SpaceStation => 0,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum AcademyType {
    Science,
    Qic,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SpaceTileKind {
    Single,
    Outer,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ResearchTrack {
    Terraforming,
    Navigation,
    ArtificialIntelligence,
    GaiaProject,
    Economy,
    Science,
}

impl ResearchTrack {
    pub fn all() -> [ResearchTrack; 6] {
        [
            Self::Terraforming,
            Self::Navigation,
            Self::ArtificialIntelligence,
            Self::GaiaProject,
            Self::Economy,
            Self::Science,
        ]
    }

    /// The `id` string used in `data/research_tracks.toml` (and
    /// `data/factions.toml`'s `starting_track_bonuses`) for this track.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Terraforming => "Terraforming",
            Self::Navigation => "Navigation",
            Self::ArtificialIntelligence => "ArtificialIntelligence",
            Self::GaiaProject => "GaiaProject",
            Self::Economy => "Economy",
            Self::Science => "Science",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ResourceKind {
    Ore,
    Credits,
    Knowledge,
    Qic,
    Power,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FinalScoringCondition {
    // Base game (6 tiles)
    MostStructuresInFederation, // most structures that are part of federations
    MostBuildings,              // most structures total
    MostPlanetTypes,            // most different planet types colonized
    MostGaiaplanets,            // most Gaia planets colonized
    MostSectors,                // most sectors with at least 1 structure
    MostSatellites,             // most satellites (Ivits: space stations count)
    // Lost Fleet expansion (3 tiles, pool of 9 total)
    MostExploredShips,
    MostSpecialPlanets,
    HighestSingleTrack,
}

// ── FactionId ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum FactionId {
    Terrans,
    Lantids,
    Xenos,
    Gleens,
    Taklons,
    Ambas,
    HadschHallas,
    Ivits,
    Geodens,
    BalTaks,
    Firaks,
    Bescods,
    Nevlas,
    Itars,
    // Lost Fleet expansion factions
    Tinkeroids,
    Moweyds,
    SpaceGiants,
    Darkanians,
}

impl FactionId {
    pub fn all() -> Vec<FactionId> {
        vec![
            Self::Terrans,
            Self::Lantids,
            Self::Xenos,
            Self::Gleens,
            Self::Taklons,
            Self::Ambas,
            Self::HadschHallas,
            Self::Ivits,
            Self::Geodens,
            Self::BalTaks,
            Self::Firaks,
            Self::Bescods,
            Self::Nevlas,
            Self::Itars,
            Self::Tinkeroids,
            Self::Moweyds,
            Self::SpaceGiants,
            Self::Darkanians,
        ]
    }

    /// Returns the faction printed on the opposite side of the same faction board.
    ///
    /// The Lost Fleet expansion ships 2 double-sided faction boards for its 4
    /// new factions (rulebook p.2 component list), and every base-game pair in
    /// this crate's data shares one `home_planet` between its two sides
    /// (`gaia-engine/data/factions.toml`). Applying that same rule to the
    /// Lost Fleet appendix (p.13: Tinkeroids/Darkanians both start on an
    /// Asteroid, Moweyds/Space Giants both start on a Protoplanet) gives
    /// Tinkeroids/Darkanians and Moweyds/Space Giants as the two board pairs.
    pub fn other_board_side(self) -> FactionId {
        match self {
            Self::Terrans => Self::Lantids,
            Self::Lantids => Self::Terrans,
            Self::Xenos => Self::Gleens,
            Self::Gleens => Self::Xenos,
            Self::Taklons => Self::Ambas,
            Self::Ambas => Self::Taklons,
            Self::HadschHallas => Self::Ivits,
            Self::Ivits => Self::HadschHallas,
            Self::Geodens => Self::BalTaks,
            Self::BalTaks => Self::Geodens,
            Self::Firaks => Self::Bescods,
            Self::Bescods => Self::Firaks,
            Self::Nevlas => Self::Itars,
            Self::Itars => Self::Nevlas,
            Self::Tinkeroids => Self::Darkanians,
            Self::Darkanians => Self::Tinkeroids,
            Self::Moweyds => Self::SpaceGiants,
            Self::SpaceGiants => Self::Moweyds,
        }
    }
}

// ── Resources ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Resources {
    pub ore: u8,
    pub credits: u8,
    pub knowledge: u8,
    pub qic: u8,
    pub power: PowerCycle,
    pub spent_gaia_formers: u8,
}

impl Resources {
    pub fn zero() -> Self {
        Self {
            ore: 0,
            credits: 0,
            knowledge: 0,
            qic: 0,
            power: PowerCycle::zero(),
            spent_gaia_formers: 0,
        }
    }
}

/// Destination power bowl for the Gaia phase's cycle re-entry (rulebook p.11:
/// power moves to Area I, except the Terrans move it directly to Area II).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PowerBowl {
    Area1,
    Area2,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PowerCycle {
    pub bowl1: u8,
    pub bowl2: u8,
    pub bowl3: u8,
    pub gaia_bowl: u8,
    pub gaia_forming: u8,
}

impl PowerCycle {
    pub fn zero() -> Self {
        Self {
            bowl1: 0,
            bowl2: 0,
            bowl3: 0,
            gaia_bowl: 0,
            gaia_forming: 0,
        }
    }

    pub fn total(&self) -> u8 {
        self.bowl1
            .saturating_add(self.bowl2)
            .saturating_add(self.bowl3)
            .saturating_add(self.gaia_bowl)
            .saturating_add(self.gaia_forming)
    }
}

// ── ResourceDelta ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResourceDelta {
    pub ore: i8,
    pub credits: i8,
    pub knowledge: i8,
    pub qic: i8,
}

impl ResourceDelta {
    pub fn zero() -> Self {
        Self {
            ore: 0,
            credits: 0,
            knowledge: 0,
            qic: 0,
        }
    }
}

// ── PlayerState ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlayerState {
    pub player_id: PlayerId,
    pub nickname: String,
    pub faction: Option<FactionId>,
    pub resources: Resources,
    pub structures: Vec<Structure>,
    pub research_tracks: ResearchTracks,
    pub vp: i32,
    pub passed: bool,
    pub federation_tokens: Vec<FederationToken>,
    pub alliance_tiles: Vec<AllianceTile>,
    pub explored_ships: Vec<ShipId>,
    pub gaiaformers_total: u8,
    pub gaiaformers_deployed: u8,
    pub tech_tiles: Vec<TechTile>,
    /// Whether this player has used their faction's one-time Planetary
    /// Institute special action (e.g. Space Giants' free tech tile).
    /// Meaningless for factions without such an ability.
    pub pi_ability_used: bool,
    /// Whether this player has already received their faction's one-time
    /// "first colonization" bonus (e.g. Darkanians' credits+knowledge grant).
    /// An explicit flag rather than inferring "first" from `structures.len()`,
    /// since structure count also depends on the (separately unimplemented)
    /// starting-structure placement step and would silently break once that
    /// lands. Meaningless for factions without such an ability.
    pub first_colonization_bonus_used: bool,
    /// Whether this player has already taken their Academy(Qic) action this
    /// round (rulebook p.15: special action spaces — including Academy(Qic)
    /// — may only be used once per round, tracked by placing an action
    /// token; reset at Clean-up). Meaningless without a built Academy(Qic).
    pub academy_qic_action_used_this_round: bool,
}

impl PlayerState {
    pub fn gaiaformers_available(&self) -> u8 {
        let used = self
            .resources
            .spent_gaia_formers
            .saturating_add(self.gaiaformers_deployed);
        self.gaiaformers_total.saturating_sub(used)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Structure {
    pub hex: HexCoord,
    pub kind: StructureType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchTracks {
    pub terraforming: u8,
    pub navigation: u8,
    pub ai: u8,
    pub gaia: u8,
    pub economy: u8,
    pub science: u8,
}

impl ResearchTracks {
    pub fn new() -> Self {
        Self {
            terraforming: 0,
            navigation: 0,
            ai: 0,
            gaia: 0,
            economy: 0,
            science: 0,
        }
    }

    pub fn get(&self, track: ResearchTrack) -> u8 {
        match track {
            ResearchTrack::Terraforming => self.terraforming,
            ResearchTrack::Navigation => self.navigation,
            ResearchTrack::ArtificialIntelligence => self.ai,
            ResearchTrack::GaiaProject => self.gaia,
            ResearchTrack::Economy => self.economy,
            ResearchTrack::Science => self.science,
        }
    }

    pub fn increment(&mut self, track: ResearchTrack) {
        let val = match track {
            ResearchTrack::Terraforming => &mut self.terraforming,
            ResearchTrack::Navigation => &mut self.navigation,
            ResearchTrack::ArtificialIntelligence => &mut self.ai,
            ResearchTrack::GaiaProject => &mut self.gaia,
            ResearchTrack::Economy => &mut self.economy,
            ResearchTrack::Science => &mut self.science,
        };
        *val = (*val + 1).min(5);
    }

    /// Sets `track` directly to `level` (capped at 5) — used to seed a
    /// faction's non-zero starting track level, as opposed to `increment`
    /// which advances one step via the in-game Research action.
    pub fn set(&mut self, track: ResearchTrack, level: u8) {
        let val = match track {
            ResearchTrack::Terraforming => &mut self.terraforming,
            ResearchTrack::Navigation => &mut self.navigation,
            ResearchTrack::ArtificialIntelligence => &mut self.ai,
            ResearchTrack::GaiaProject => &mut self.gaia,
            ResearchTrack::Economy => &mut self.economy,
            ResearchTrack::Science => &mut self.science,
        };
        *val = level.min(5);
    }

    pub fn max_level(&self) -> u8 {
        [
            self.terraforming,
            self.navigation,
            self.ai,
            self.gaia,
            self.economy,
            self.science,
        ]
        .iter()
        .copied()
        .max()
        .unwrap_or(0)
    }

    pub fn total(&self) -> u32 {
        [
            self.terraforming,
            self.navigation,
            self.ai,
            self.gaia,
            self.economy,
            self.science,
        ]
        .iter()
        .map(|&v| v as u32)
        .sum()
    }
}

impl Default for ResearchTracks {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FederationToken(pub u8);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AllianceTile {
    pub track: ResearchTrack,
}

// ── BoardState ────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoardState {
    pub sectors: Vec<Sector>,
    pub hexes: HashMap<HexCoord, Hex>,
    pub lost_planet: Option<HexCoord>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Sector {
    pub id: u8,
    pub rotation: u8,
    pub origin: HexCoord,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Hex {
    pub coord: HexCoord,
    pub planet: Option<Planet>,
    pub space_tile_kind: Option<SpaceTileKind>,
    pub structures: Vec<PlacedStructure>,
    pub satellites: Vec<PlayerId>,
}

impl Hex {
    pub fn is_space_tile(&self) -> bool {
        self.space_tile_kind.is_some()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Planet {
    pub planet_type: PlanetType,
    pub is_gaia_formed: bool,
    pub owner: Option<PlayerId>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlacedStructure {
    pub owner: PlayerId,
    pub kind: StructureType,
}

// ── Research Board ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResearchBoard {
    pub tracks: HashMap<ResearchTrack, TrackState>,
    pub tech_tiles: Vec<TechTile>,
    pub advanced_tech_tiles: [Option<AdvancedTechTile>; 6],
    pub federation_tokens: Vec<FederationToken>,
}

impl ResearchBoard {
    pub fn new() -> Self {
        let tracks = ResearchTrack::all()
            .into_iter()
            .map(|t| (t, TrackState::new()))
            .collect();
        Self {
            tracks,
            tech_tiles: Vec::new(),
            advanced_tech_tiles: [None, None, None, None, None, None],
            federation_tokens: Vec::new(),
        }
    }
}

impl Default for ResearchBoard {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrackState {
    pub player_levels: HashMap<PlayerId, u8>,
    pub alliance_taken: [Option<PlayerId>; 3],
}

impl TrackState {
    pub fn new() -> Self {
        Self {
            player_levels: HashMap::new(),
            alliance_taken: [None, None, None],
        }
    }
}

impl Default for TrackState {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TechTile(pub u8);

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AdvancedTechTile(pub u8);

// ── Final Scoring ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FinalScoringTile {
    pub condition: FinalScoringCondition,
    pub vp_1st: u8,
    pub vp_2nd: u8,
    pub vp_3rd: u8,
}

// ── Booster ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Booster(pub u8);

// ── Phase enums ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum GamePhase {
    Setup(SetupPhase),
    GaiaPhase,
    IncomePhase,
    GaiaformingPhase,
    ActionPhase {
        active_player: usize,
    },
    /// Rulebook p.16-17, "Passive Action: Charge Power" — `ActionPhase` is
    /// paused right after a Build/Upgrade while eligible opponents decide,
    /// in clockwise order, whether to charge power. `queue.front()` is the
    /// player who must submit `GameAction::ChargePower` next. `resume`
    /// is `Some(active_player)` to reopen `ActionPhase`, or `None` if every
    /// other player had already passed (so the round ends once the queue
    /// drains).
    ChargePowerPending {
        queue: Vec<PendingCharge>,
        resume_active_player: Option<usize>,
    },
    /// Income phase pause: a player whose faction gets both a
    /// PlanetaryInstitute power charge and a per-round bonus power token
    /// must choose which happens first, since the fresh token can itself
    /// get swept up in the charge (bowl1→bowl2) if it enters before the
    /// charge is applied. Entries may be resolved in any order (each is an
    /// independent per-player decision, not reactive to another player's
    /// action). The round finishes (round increments, `ActionPhase` reopens)
    /// once the queue drains.
    IncomeOrderPending {
        queue: Vec<PendingIncomeOrder>,
        round: u8,
    },
    RoundScoring {
        round: u8,
    },
    FinalScoring,
    Ended,
}

/// One opponent's opportunity to charge power during `ChargePowerPending`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PendingCharge {
    pub player: PlayerId,
    pub hex: HexCoord,
    pub max_power: u8,
}

/// One player's PlanetaryInstitute charge-vs-bonus-token ordering decision
/// during `IncomeOrderPending`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PendingIncomeOrder {
    pub player: PlayerId,
    pub charge_amount: u8,
    pub bonus_tokens: u8,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum SetupPhase {
    FactionSelection { active_player: PlayerId },
    Complete,
}

// ── Faction selection ─────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FactionSelectionState {
    pub available_factions: Vec<FactionId>,
    pub player_order: Vec<PlayerId>,
    pub current_index: usize,
    pub assignments: Vec<FactionAssignment>,
}

impl FactionSelectionState {
    pub fn current_player(&self) -> Option<PlayerId> {
        self.player_order.get(self.current_index).copied()
    }

    pub fn is_complete(&self) -> bool {
        !self.player_order.is_empty() && self.current_index >= self.player_order.len()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FactionAssignment {
    pub player: PlayerId,
    pub faction: FactionId,
}

// ── GameEvent ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum GameEvent {
    FactionSelected {
        player: PlayerId,
        faction: FactionId,
    },
    ResourceChanged {
        player: PlayerId,
        delta: ResourceDelta,
    },
    VpAwarded {
        player: PlayerId,
        amount: i32,
        reason: VpReason,
    },
    StructureBuilt {
        player: PlayerId,
        hex: HexCoord,
        kind: StructureType,
    },
    StructureUpgraded {
        player: PlayerId,
        hex: HexCoord,
        from: StructureType,
        to: StructureType,
    },
    FederationFormed {
        player: PlayerId,
        hexes: Vec<HexCoord>,
        token: FederationToken,
    },
    ResearchAdvanced {
        player: PlayerId,
        track: ResearchTrack,
        level: u8,
    },
    GaiaFormingStarted {
        player: PlayerId,
        hex: HexCoord,
    },
    GaiaFormingComplete {
        player: PlayerId,
        hex: HexCoord,
    },
    PlayerPassed {
        player: PlayerId,
        booster: Booster,
    },
    ShipExplored {
        player: PlayerId,
        ship_id: ShipId,
    },
    AsteroidColonized {
        player: PlayerId,
        hex: HexCoord,
    },
    ProtoPlanetColonized {
        player: PlayerId,
        hex: HexCoord,
    },
    TechTileGained {
        player: PlayerId,
        tile: TechTile,
    },

    RoundStarted {
        round: u8,
    },
    RoundEnded {
        round: u8,
    },
    GameEnded {
        final_scores: [i32; 4],
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum VpReason {
    RoundTile { tile_id: u8 },
    FinalTile { tile_id: u8 },
    ResearchTrack { track: ResearchTrack },
    ResourceConversion,
    FactionSpecial,
    GaiaProject,
    ShipExploration,
    AsteroidColony,
    ProtoPlanetColony,
}

// ── RoundTile ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoundTile {
    pub id: u8,
    pub condition: RoundCondition,
    pub vp_per_unit: u8,
}

impl RoundTile {
    /// Map a round tile id (1–12) to its condition and VP value.
    pub fn from_id(id: u8) -> Self {
        let (condition, vp_per_unit) = match id {
            1 => (RoundCondition::BuildMine, 2),
            2 => (RoundCondition::BuildMine, 2),
            3 => (RoundCondition::Upgrade, 3),
            4 => (RoundCondition::Upgrade, 3),
            5 => (RoundCondition::ResearchAdvance, 2),
            6 => (RoundCondition::ResearchAdvance, 2),
            7 => (RoundCondition::GaiaProject, 3),
            8 => (RoundCondition::GaiaProject, 3),
            9 => (RoundCondition::BuildStation, 3),
            10 => (RoundCondition::BuildStation, 3),
            11 => (RoundCondition::FormFederation, 6),
            _ => (RoundCondition::BuildAcademy, 5), // id 12 and unknown
        };
        Self {
            id,
            condition,
            vp_per_unit,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum RoundCondition {
    BuildMine,
    Upgrade,
    ResearchAdvance,
    GaiaProject,
    BuildStation,
    FormFederation,
    BuildAcademy,
}

// ── GameState ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameState {
    pub room_code: RoomCode,
    pub created_at: u64,
    pub version: u64,

    pub round: u8,
    pub phase: GamePhase,
    pub players: Vec<PlayerState>,

    pub board: BoardState,
    pub round_tiles: [RoundTile; 6],
    pub boosters: Vec<Booster>,
    pub final_scoring_tiles: [FinalScoringTile; 2],
    pub research_board: ResearchBoard,
    pub faction_selection: Option<FactionSelectionState>,

    pub turn_order: Vec<PlayerId>,
    pub current_player: usize,

    /// Power-action board slot ids (rulebook Appendix III) already taken
    /// this round — shared across all players (whoever takes a slot first
    /// closes it to everyone until Clean-up), unlike
    /// `PlayerState::academy_qic_action_used_this_round`'s per-player
    /// exclusivity. Reset in `finish_round_transition`.
    pub used_power_actions: Vec<u8>,
    /// QIC-action board slot ids already taken this round (see
    /// `qic_action_slot_id` for the kind→id mapping) — same shared,
    /// once-per-round-across-all-players exclusivity as `used_power_actions`.
    pub used_qic_action_slots: Vec<u8>,

    pub event_log: Vec<GameEvent>,
}

impl GameState {
    pub fn serialize(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn deserialize(json: serde_json::Value) -> Result<Self, DeserializeError> {
        serde_json::from_value(json).map_err(DeserializeError::InvalidJson)
    }

    pub fn current_player_id(&self) -> Option<PlayerId> {
        self.turn_order.get(self.current_player).copied()
    }

    pub fn player(&self, id: PlayerId) -> Option<&PlayerState> {
        self.players.iter().find(|p| p.player_id == id)
    }

    pub fn player_mut(&mut self, id: PlayerId) -> Option<&mut PlayerState> {
        self.players.iter_mut().find(|p| p.player_id == id)
    }
}
