use crate::game_state::{FactionId, HexCoord, ResearchTrack, StructureType};
use serde::{Deserialize, Serialize};

// ── Type aliases ──────────────────────────────────────────────────────────────

/// Index into the shared power-action board (1-based, matches rulebook slots).
pub type PowerActionId = u8;

/// Faction-specific special-action identifier (1-based per faction).
pub type SpecialActionId = u8;

// ── SetupAction ───────────────────────────────────────────────────────────────

/// Actions that may only occur during the faction-selection setup phase.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "PascalCase")]
pub enum SetupAction {
    /// Choose one available side of a faction board on the player's setup turn.
    SelectFaction { faction: FactionId },
}

// ── GameAction ────────────────────────────────────────────────────────────────

/// Actions that may occur during normal game rounds.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "PascalCase")]
pub enum GameAction {
    /// Build a Mine on an unoccupied planet.
    Build { coord: HexCoord },

    /// Upgrade an existing structure one step up the upgrade path.
    Upgrade { coord: HexCoord, to: StructureType },

    /// Advance one level on a research track.
    ResearchAdvance { track: ResearchTrack },

    /// Form a new federation from a connected set of structures.
    FormFederation { hexes: Vec<HexCoord> },

    /// Spend power tokens to take a power action from the shared board.
    PowerAction { id: PowerActionId },

    /// Activate the faction's unique special action.
    SpecialAction { id: SpecialActionId },

    /// Begin gaiaforming on a Transdim planet.
    GaiaFormation { coord: HexCoord },

    /// Spend QIC for a board-wide QIC action.
    QicAction { kind: QicActionKind },

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

    /// Choose whether this round's PlanetaryInstitute power charge is
    /// applied before or after gaining the faction's per-round bonus power
    /// token. Only valid while `GamePhase::IncomeOrderPending` names this
    /// player in its queue. `charge_first: true` applies the charge (which
    /// can carry the fresh token from bowl1 to bowl2) before the token
    /// enters bowl1; `false` lets the token enter bowl1 first, so it is not
    /// swept up in this round's charge.
    ChooseIncomeOrder { charge_first: bool },

    /// The repeatable action granted by an Academy(Qic) (rulebook p.13):
    /// "gain one Q.I.C." Requires the player to have built an
    /// Academy(Qic). BalTaks' board replaces this with a different
    /// resource/amount (`factions.toml`'s `academy_qic_action`). Like other
    /// special/power/QIC action spaces, the rulebook limits this to once
    /// per round — that exclusivity isn't tracked yet (see README "Known
    /// migration work"), so it is currently repeatable every turn.
    AcademyQicAction,
}

// ── QicActionKind ─────────────────────────────────────────────────────────────

/// The distinct actions that consume QIC on the QIC-action board.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum QicActionKind {
    /// Gain ore by spending QIC (1 QIC → 1 ore, quantity per action slot).
    GainOre,

    /// Advance on any research track as if levelling up (1 QIC).
    ResearchStep,

    /// Build a federation satellite on an adjacent hex (3 QIC).
    BuildSatellite { coord: HexCoord },

    /// Colonise a Lost Planet (2 QIC).
    ColoniseLostPlanet { coord: HexCoord },
}
