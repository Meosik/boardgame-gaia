use crate::game_state::{
    AdvancedTechTile, ArtifactId, FactionId, HexCoord, ResearchTrack, SpaceshipId, StructureType,
    TechTile,
};
use serde::{Deserialize, Serialize};

// ── Type aliases ──────────────────────────────────────────────────────────────

/// Index into the shared power-action board (1-based, matches rulebook slots).
pub type PowerActionId = u8;

/// Faction-specific special-action identifier (1-based per faction).
pub type SpecialActionId = u8;

// ── SetupAction ───────────────────────────────────────────────────────────────

/// Actions that may only occur during pre-game setup phases.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "PascalCase")]
pub enum SetupAction {
    /// Choose one available side of a faction board on the player's setup turn.
    SelectFaction { faction: FactionId },
    /// Raise the current setup auction. The amount is only deducted at final
    /// scoring, but cannot exceed the player's current VP when placed.
    PlaceBid { amount: u32 },
    /// Permanently leave the current auction. Eligibility resets when the next
    /// auction begins.
    PassBid,
    /// The auction winner chooses one offered faction and one remaining final
    /// turn-order position (1 through 4).
    ChooseBidReward {
        faction: FactionId,
        turn_position: u8,
    },
    /// Place the next faction-defined starting structure on an unoccupied
    /// home-planet hex during the setup placement sequence.
    PlaceStartingStructure { coord: HexCoord },
    /// Choose one available round booster during initial setup. Selection
    /// proceeds in reverse final turn order after all structures are placed.
    SelectStartingBooster { booster_id: u8 },
}

// ── GameAction ────────────────────────────────────────────────────────────────

/// Actions that may occur during normal game rounds.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "PascalCase")]
pub enum GameAction {
    /// Build a Mine on an unoccupied planet.
    Build { coord: HexCoord },

    /// Upgrade an existing structure one step up the upgrade path. Base rulebook (p.15,
    /// "Research Progress"): "Whenever you gain a tech tile, you may advance in a research
    /// area... Every upgrade follows these rules: You can take any standard tech tile, except
    /// one you already own... Instead of taking a standard tech tile, you can take an advanced
    /// tech tile [if] your player token [is] on level 4 or 5 of the research area [it sits
    /// under]. When you take an advanced tech tile, you may advance in any research area." This
    /// engine simplifies the "which research area a standard tile lets you advance" physical
    /// board-layout detail (which of the 6 tracks each of the 13 standard tile types happens to
    /// sit under is a random per-game setup outcome this engine doesn't model precisely) to "any
    /// track of your choice," matching what an Advanced tile already grants unconditionally.
    Upgrade {
        coord: HexCoord,
        to: StructureType,
        #[serde(default)]
        tech_tile_choice: Option<TechTileChoice>,
    },

    /// Advance one level on a research track.
    ResearchAdvance { track: ResearchTrack },

    /// Form a new federation from a connected set of `hexes` (planets the player has already
    /// colonized) plus, when those colonized planets aren't all directly adjacent, freshly built
    /// `satellite_hexes` bridging them (rulebook p.14, "Connecting Planets": "To connect planets
    /// that are not adjacent, you must immediately build satellites... Take one of the satellites
    /// near your faction board and place it in a space adjacent to either one of your colonized
    /// planets or one of your satellites"). Each satellite costs 1 power, discarded from any
    /// combination of bowls 1/2/3 (mirrors `ExamineArtifact`'s "discard N power" draw order). A
    /// satellite hex must be empty (no planet, no structure, not a Lost Fleet spaceship tile —
    /// "you may not place a satellite on a spaceship tile"). `token` selects which Federation
    /// token to gain (rulebook p.14: "gain one federation token of your choice from the supply",
    /// extended by the Lost Fleet expansion's per-spaceship tokens). `bonus_build_coord` and
    /// `bonus_tech_tile` are required exactly when the chosen token grants a follow-up
    /// "Build a Mine" action or a Standard Tech tile of choice respectively (see
    /// `FederationTokenChoice`/`federation_token_kind` in `rules::engine`) — bundled into this
    /// same action rather than a separate pending phase, matching `SpaceshipCreditTerraform`/
    /// `TwilightFreeResearchLab`/`EclipseAsteroidMine`'s existing coord-bundling pattern.
    FormFederation {
        hexes: Vec<HexCoord>,
        #[serde(default)]
        satellite_hexes: Vec<HexCoord>,
        token: FederationTokenChoice,
        #[serde(default)]
        bonus_build_coord: Option<HexCoord>,
        #[serde(default)]
        bonus_tech_tile: Option<TechTile>,
    },

    /// Spend power tokens to take a power action from the shared board
    /// (rulebook Appendix III). `coord` is required for the two slots that
    /// perform a "build a mine with N free terraforming steps" instead of a
    /// plain resource gain (`free_terraform_steps_for_power_action`);
    /// ignored otherwise.
    PowerAction {
        id: PowerActionId,
        coord: Option<HexCoord>,
    },

    /// Activate the faction's unique special action.
    SpecialAction { id: SpecialActionId },

    /// Ambas Planetary Institute special action: exchange the positions of
    /// the Planetary Institute and one of the player's Mines.
    AmbasSwapPlanetaryInstitute { mine_coord: HexCoord },

    /// Firaks Planetary Institute special action: downgrade one Research Lab
    /// to a Trading Station and immediately advance the chosen research track.
    FiraksDowngradeResearchLab {
        coord: HexCoord,
        track: ResearchTrack,
    },

    /// Bescods faction-board special action: advance one of the player's
    /// currently lowest research tracks without paying knowledge.
    BescodsLowestResearchAdvance { track: ResearchTrack },

    /// Ivits Planetary Institute special action: place a Space Station on an accessible,
    /// planet-free space (same accessibility/QIC-for-range rule as `Build`). A Space Station
    /// isn't a colonized planet and can't be power-charged by opponents, but counts as a range
    /// starting point and as power value 1 toward Ivits' one-and-only, ever-growing federation
    /// (rulebook Appendix I).
    IvitsPlaceSpaceStation { coord: HexCoord },

    /// Tinkeroids Planetary Institute special action: use the effect printed on the player's
    /// currently-chosen Tinkering tile (rulebook Appendix I). `tile` is one of 6 ids (1-3 usable
    /// only in rounds 1-3, 4-6 usable only in rounds 4-6), each usable at most once per game;
    /// `coord` is required exactly for the two "Build a Mine" tiles (1 and 5) and must be omitted
    /// for the four flat-resource tiles (2, 3, 4, 6).
    TinkeroidsUseTile { tile: u8, coord: Option<HexCoord> },

    /// Moweyds Planetary Institute special action: place one of the player's (at most 6) Power
    /// Rings on a hex containing one of their own buildings that doesn't already have one. The
    /// power value of the structure on that hex permanently increases by 2, both for federation
    /// power and for the amount opponents may charge (rulebook Appendix I).
    MoweydsPlacePowerRing { coord: HexCoord },

    /// Use a Tech tile's printed "as a special action" ability (standard tile 10 or advanced
    /// tiles 20/21/22 — see `tech_tile_special_action_reward`/`advanced_tech_tile_special_action_reward`
    /// in `rules::engine`). Each owned special-action tile is independently usable once per round.
    TechTileSpecialAction { tile: TechTileRef },

    /// Begin gaiaforming on a Transdim planet.
    GaiaFormation { coord: HexCoord },

    /// Round booster 5 special action: start and immediately complete a Gaia Project without
    /// moving power into the Gaia area. The temporarily deployed Gaiaformer is immediately
    /// available again.
    RoundBoosterImmediateGaiaFormation { coord: HexCoord },

    /// Round booster 8 special action: immediately Build a Mine with +3 range.
    RoundBoosterRangeBuild { coord: HexCoord },

    /// Round booster 8 special action: immediately start a Gaia Project with +3 range.
    RoundBoosterRangeGaiaFormation { coord: HexCoord },

    /// Lost Fleet extension of round booster 8: immediately explore a spaceship with +3 range.
    RoundBoosterRangeExploreSpaceship { ship: SpaceshipId },

    /// Pass for the remainder of the round, optionally activating a booster.
    Pass { booster_id: Option<u8> },

    /// Respond to a "Passive Action: Charge Power" opportunity (rulebook
    /// p.16-17). Only valid while `GamePhase::ChargePowerPending` names this
    /// player as next in the queue. This is all-or-nothing — the player
    /// cannot choose a partial amount; the engine computes the actual
    /// chargeable amount (capped by the qualifying structure's power value,
    /// available power tokens, and available VP) and either applies it in
    /// full (`accept: true`) or not at all (`accept: false`).
    ChargePower { accept: bool },

    /// Taklons Planetary Institute version of accepting a passive charge.
    /// The bonus fresh power token may enter Area I either before or after
    /// the charge; declining still uses ordinary `ChargePower`.
    TaklonsChargePower { gain_before: bool },

    /// Choose whether this round's PlanetaryInstitute power charge is
    /// applied before or after gaining the faction's per-round bonus power
    /// token. Only valid while `GamePhase::IncomeOrderPending` names this
    /// player in its queue. `charge_first: true` applies the charge (which
    /// can carry the fresh token from bowl1 to bowl2) before the token
    /// enters bowl1; `false` lets the token enter bowl1 first, so it is not
    /// swept up in this round's charge.
    ChooseIncomeOrder { charge_first: bool },

    /// Terrans Planetary Institute, Gaia phase: spend power currently in the
    /// Gaia area as if taking one of the four power-to-resource free actions.
    /// This does not consume a turn and may be repeated before finishing the
    /// pending Gaia decision.
    TerransGaiaConversion {
        kind: FreeActionKind,
        #[serde(default = "default_free_action_count")]
        count: u8,
    },

    /// Itars Planetary Institute, Gaia phase: discard four power tokens from
    /// the Gaia area to gain one available Standard Tech tile and advance the
    /// chosen research track. This may be repeated while affordable.
    ItarsGaiaTechTile {
        tile: TechTile,
        track: ResearchTrack,
    },

    /// End the current Terrans/Itars optional Gaia-phase ability window and
    /// move any remaining Gaia-area power to the faction's normal bowl.
    FinishGaiaDecision,

    /// The repeatable action granted by an Academy(Qic) (rulebook p.13):
    /// "gain one Q.I.C." Requires the player to have built an
    /// Academy(Qic). BalTaks' board replaces this with a different
    /// resource/amount (`factions.toml`'s `academy_qic_action`). Limited to
    /// once per round (`PlayerState::academy_qic_action_used_this_round`).
    AcademyQicAction,

    /// A free-action resource conversion (rulebook p.15, "9) Free Actions")
    /// — unlike every other variant here, this does **not** end the turn:
    /// it may be taken any number of times, before or after the player's
    /// main action, as long as it's their turn and they haven't passed.
    FreeAction {
        kind: FreeActionKind,
        /// Number of identical conversions to resolve atomically. Older
        /// clients that omit this field retain the original single-use
        /// behaviour.
        #[serde(default = "default_free_action_count")]
        count: u8,
    },

    /// Lost Fleet expansion, "11) Action: Explore a Lost Fleet Spaceship" — deploy an
    /// Exploration Shuttle to one of the 4 spaceship boards. Requires the spaceship's map hex
    /// to be in range and an unused shuttle available; costs VP.
    ExploreSpaceship { ship: SpaceshipId },

    /// Lost Fleet expansion, "12) Action: Examine an Artifact" — only available once the player
    /// has explored the Twilight spaceship. Discards 6 power to take one chosen Artifact from
    /// the ship's pool (rulebook: "gain 1 artifact from the spaceship" — per the physical
    /// components the artifacts are laid out and chosen, not drawn blind).
    ExamineArtifact {
        artifact: ArtifactId,
        /// Required exactly when `artifact` is id 10 ("Copy the effect of a Federation Token
        /// you own") — which owned token's effect to replay. Mirrors
        /// `TwilightReplayFederationToken`'s bundling shape, including its same 3 follow-up
        /// fields below for the token kinds that need one.
        #[serde(default)]
        copy_federation_token_kind: Option<u8>,
        #[serde(default)]
        bonus_build_coord: Option<HexCoord>,
        #[serde(default)]
        bonus_tech_tile: Option<TechTile>,
        #[serde(default)]
        bonus_research_track: Option<ResearchTrack>,
    },

    /// Lost Fleet expansion Appendix II ("New Action Spaces") — a Credit action space unlocked
    /// once the player has explored any Lost Fleet spaceship: "the same as the power action
    /// 'Take 1 free terraforming step' from the base game, except it costs 3 credits." Shared,
    /// once-per-round exclusivity (`GameState.used_spaceship_actions`), like the base power
    /// action board. Performs a `Build`-equivalent action with 1 free
    /// terraforming step, same as `PowerAction { id: 6, .. }` but paid in credits instead of
    /// power.
    SpaceshipCreditTerraform { coord: HexCoord },

    /// Lost Fleet expansion, Twilight spaceship's Appendix II action space: once explored,
    /// costs 3 power + 2 ore to activate, then grants a free "Upgrade Existing Structures"
    /// action — Trading Station to Research Lab only, at no *additional* ore/credit cost beyond
    /// the activation fee (rulebook: "at no additional cost"). Shared, once-per-round
    /// exclusivity (`GameState.used_spaceship_actions`), like `SpaceshipCreditTerraform`.
    /// Requires the player to have explored Twilight specifically (not any spaceship).
    TwilightFreeResearchLab { coord: HexCoord },

    /// Twilight's 3-QIC action: repeat every immediate effect of one Federation token the
    /// player already owns without gaining or consuming another token. Follow-up choices are
    /// bundled for the three Lost Fleet token effects that need a target or selection.
    TwilightReplayFederationToken {
        token_kind: u8,
        #[serde(default)]
        bonus_build_coord: Option<HexCoord>,
        #[serde(default)]
        bonus_tech_tile: Option<TechTile>,
        #[serde(default)]
        bonus_research_track: Option<ResearchTrack>,
    },

    /// Twilight's 1-knowledge action: immediately perform Build a Mine with +3 range.
    TwilightRangeBuild { coord: HexCoord },

    /// Twilight's 1-knowledge action: immediately start a Gaia Project with +3 range.
    TwilightRangeGaiaFormation { coord: HexCoord },

    /// Twilight's 1-knowledge action: immediately explore a spaceship with +3 range.
    TwilightRangeExploreSpaceship { ship: SpaceshipId },

    /// Lost Fleet expansion, Rebellion spaceship's Appendix II action space: once explored,
    /// costs 3 power + 1 ore to activate, then grants a free "Upgrade Existing Structures"
    /// action — Mine to Trading Station only, at no additional cost. Mirrors
    /// `TwilightFreeResearchLab`'s shape with a different upgrade path and ore cost. Requires
    /// the player to have explored Rebellion specifically.
    RebellionFreeTradingStation { coord: HexCoord },

    /// Lost Fleet expansion, Rebellion spaceship's Appendix II action space: once explored,
    /// costs 2 knowledge to immediately and only once gain 2 credits and 1 QIC. Requires the
    /// player to have explored Rebellion specifically.
    RebellionCreditsAndQic,

    /// Rebellion's 3-QIC action: gain an available Standard Tech tile and advance one chosen
    /// research track under the normal Tech-tile acquisition rules.
    RebellionGainTechTile {
        tile: TechTile,
        track: ResearchTrack,
    },

    /// Lost Fleet expansion, T F Mars spaceship's Appendix II action space: once explored,
    /// costs 2 QIC to immediately and only once gain 2 VP plus 1 additional VP for each Standard
    /// Tech tile owned. Requires the player to have explored T F Mars specifically.
    TFMarsTechBonus,

    /// Lost Fleet expansion, T F Mars spaceship's Appendix II action space: once explored,
    /// costs 2 power to immediately gaiaform a Transdim planet — a flat-cost, once-per-round
    /// alternative to the normal `GaiaFormation` action's Gaia Project track-level-scaled power
    /// cost (and doesn't require having researched the Gaia Project track at all). Requires the
    /// player to have explored T F Mars specifically.
    TFMarsGaiaFormation { coord: HexCoord },

    /// Lost Fleet expansion, Eclipse spaceship's Appendix II action space: once explored, costs
    /// 2 QIC to immediately and only once gain 2 VP plus 1 additional VP for each distinct
    /// planet type the player has colonized. Mirrors `TFMarsTechBonus`'s shape with a different
    /// counted quantity. Requires the player to have explored Eclipse specifically.
    EclipsePlanetTypeBonus,

    /// Lost Fleet expansion, Eclipse spaceship's Appendix II action space: once explored, costs
    /// 3 power + 2 knowledge to immediately advance one research track by 1 step — an
    /// alternative to the normal `ResearchAdvance` action's 4-knowledge cost. Requires the
    /// player to have explored Eclipse specifically.
    EclipseResearchBoost { track: ResearchTrack },

    /// Lost Fleet expansion, Eclipse spaceship's Appendix II action space: once explored, costs
    /// 6 credits to immediately build a Mine on an Asteroid within range — the same target
    /// restrictions as the normal `Build` action's Asteroid branch (requires an available
    /// Gaiaformer, no additional ore/credit cost beyond this action's own 6-credit activation
    /// fee). Requires the player to have explored Eclipse specifically.
    EclipseAsteroidMine { coord: HexCoord },

    /// Lost Fleet expansion, Gleens' Exploration Board special action (`GP_Exp_Rule_EN_V1_Web.pdf`
    /// p.10, "7) Special Actions"): once per round, immediately perform Build a Mine with +2
    /// range. Consumes the turn like any other main action ("cannot combine this special action
    /// with another action"); mirrors `TwilightRangeBuild`'s shape (see `GleensGaiaFormation`/
    /// `GleensExploreSpaceship` for the other two choices this special action offers).
    GleensBuildMine { coord: HexCoord },

    /// Lost Fleet expansion, Gleens' Exploration Board special action: once per round,
    /// immediately start a Gaia Project with +2 range.
    GleensGaiaFormation { coord: HexCoord },

    /// Lost Fleet expansion, Gleens' Exploration Board special action: once per round,
    /// immediately explore a Lost Fleet spaceship with +2 range.
    GleensExploreSpaceship { ship: SpaceshipId },

    /// Lost Fleet expansion, Space Giants' Exploration Board special action
    /// (`GP_Exp_Rule_EN_V1_Web.pdf` p.10): once per round, immediately perform Build a Mine with
    /// exactly 2 free terraforming steps ("you can, if you need to, pay extra ore to add the
    /// third terraforming step" — `validate_build_impl`/`apply_build_impl`'s existing
    /// `free_terraform_steps` subtraction already charges ore for any steps beyond the free 2,
    /// so no extra modeling is needed for that clause). Distinct from the Space Giants'
    /// Planetary Institute one-time tech-tile ability (`GameAction::SpecialAction`).
    SpaceGiantsBuildMine { coord: HexCoord },
}

// ── FederationTokenChoice ────────────────────────────────────────────────────

/// Which Federation token to gain when taking `GameAction::FormFederation` — either any token of
/// a given kind still in the general supply (`ResearchBoard.federation_tokens`), or a specific
/// Lost Fleet spaceship's own token (only available if the player has explored that spaceship and
/// its token hasn't been claimed yet — rulebook expansion p.5: "If you have an Exploration
/// Shuttle on a Lost Fleet spaceship and there is still a Federation token there, you can gain
/// that token when you form a Federation").
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "source", rename_all = "PascalCase")]
pub enum FederationTokenChoice {
    /// `kind` matches `federation_token_kind`'s ids (1-7 base game, 8-11 Lost Fleet).
    Supply {
        kind: u8,
    },
    Spaceship {
        ship: SpaceshipId,
    },
}

// ── TechTileChoice ───────────────────────────────────────────────────────────

/// Which Tech tile to take as part of a `GameAction::Upgrade` (rulebook p.15). `advance_track`
/// is the research track to advance one level in, if any — see `GameAction::Upgrade`'s doc
/// comment for why this engine doesn't restrict it to whichever track a Standard tile happens to
/// sit under. Taking an Advanced tile removes it permanently from that track's level-4/5 slot.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "PascalCase")]
pub enum TechTileChoice {
    Standard {
        tile: TechTile,
        #[serde(default)]
        advance_track: Option<ResearchTrack>,
        /// Required exactly when `tile` resolves to the Lost Fleet "free Build a Mine with up to
        /// 2 free terraforming steps" tile (kind 11) — ignored otherwise.
        #[serde(default)]
        bonus_build_coord: Option<HexCoord>,
    },
    /// `track` identifies which of the 6 currently-filled advanced-tile slots to take — also the
    /// track the player's marker must be on level 4 or 5 of to be eligible. Costs one green
    /// Federation token (flipped to gray) in addition to any `advance_track` cost. `covered_tile`
    /// is one of the player's own uncovered Standard tiles that the advanced tile is placed on
    /// top of — rulebook p.15: "you must have at least one uncovered standard tech tile... place
    /// [the advanced tile] faceup covering one of your standard tech tiles. A covered tech tile
    /// has no effect."
    Advanced {
        track: ResearchTrack,
        covered_tile: TechTile,
        #[serde(default)]
        advance_track: Option<ResearchTrack>,
    },
}

/// Either pool's tile, used where an action can reference a tile the player already owns
/// regardless of which pool it came from (e.g. `GameAction::TechTileSpecialAction`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "pool", rename_all = "PascalCase")]
pub enum TechTileRef {
    Standard { tile: TechTile },
    Advanced { tile: AdvancedTechTile },
}

// ── FreeActionKind ────────────────────────────────────────────────────────────

/// The fixed resource-conversion menu every faction board prints as free
/// actions (rulebook p.15). `OreToPower` is the one exception that doesn't
/// spend into another resource: it adds a fresh power token to bowl1,
/// mirroring how PlanetaryInstitute's bonus power token is granted.
///
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FreeActionKind {
    /// Discard one bowl2 token and move another bowl2 token to bowl3.
    BurnPower,
    /// Hadsch Hallas PI: 4 credits → 1 QIC.
    CreditsToQic,
    /// Hadsch Hallas PI: 3 credits → 1 ore.
    CreditsToOre,
    /// Hadsch Hallas PI: 4 credits → 1 knowledge.
    CreditsToKnowledge,
    /// Bal T'aks: move one available Gaiaformer to the Gaia area → 1 QIC.
    GaiaformerToQic,
    /// Nevlas: move one bowl3 power to the Gaia area → 1 knowledge.
    PowerToGaiaKnowledge,
    /// Lost Fleet Xenos: 1 ore → 1 power directly in bowl3.
    OreToPowerBowl3,
    /// 4 power (bowl3) → 1 QIC.
    PowerToQic,
    /// 3 power (bowl3) → 1 ore.
    PowerToOre,
    /// 1 QIC → 1 ore.
    QicToOre,
    /// 4 power (bowl3) → 1 knowledge.
    PowerToKnowledge,
    /// 1 power (bowl3) → 1 credit.
    PowerToCredit,
    /// 1 knowledge → 1 credit.
    KnowledgeToCredit,
    /// 1 ore → 1 credit.
    OreToCredit,
    /// 1 ore → 1 power token, entering bowl1.
    OreToPower,
}

impl FreeActionKind {
    pub const ALL: [Self; 15] = [
        Self::BurnPower,
        Self::PowerToQic,
        Self::PowerToOre,
        Self::QicToOre,
        Self::PowerToKnowledge,
        Self::PowerToCredit,
        Self::KnowledgeToCredit,
        Self::OreToCredit,
        Self::OreToPower,
        Self::CreditsToQic,
        Self::CreditsToOre,
        Self::CreditsToKnowledge,
        Self::GaiaformerToQic,
        Self::PowerToGaiaKnowledge,
        Self::OreToPowerBowl3,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::BurnPower => "BurnPower",
            Self::CreditsToQic => "CreditsToQic",
            Self::CreditsToOre => "CreditsToOre",
            Self::CreditsToKnowledge => "CreditsToKnowledge",
            Self::GaiaformerToQic => "GaiaformerToQic",
            Self::PowerToGaiaKnowledge => "PowerToGaiaKnowledge",
            Self::OreToPowerBowl3 => "OreToPowerBowl3",
            Self::PowerToQic => "PowerToQic",
            Self::PowerToOre => "PowerToOre",
            Self::QicToOre => "QicToOre",
            Self::PowerToKnowledge => "PowerToKnowledge",
            Self::PowerToCredit => "PowerToCredit",
            Self::KnowledgeToCredit => "KnowledgeToCredit",
            Self::OreToCredit => "OreToCredit",
            Self::OreToPower => "OreToPower",
        }
    }
}

const fn default_free_action_count() -> u8 {
    1
}
