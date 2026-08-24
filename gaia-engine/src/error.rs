use crate::game_state::{HexCoord, ResourceKind, StructureType};
use thiserror::Error;

#[derive(Debug, Error, Clone, PartialEq)]
pub enum RuleError {
    #[error("not your turn")]
    NotYourTurn,

    #[error("wrong phase")]
    WrongPhase,

    #[error("insufficient {0:?}")]
    InsufficientResources(ResourceKind),

    #[error("invalid target hex ({0:?})")]
    InvalidTarget(HexCoord),

    #[error("hex ({0:?}) already occupied")]
    TargetOccupied(HexCoord),

    #[error("hex {hex:?} out of range: have nav {nav_level}, need {range}")]
    OutOfRange {
        hex: HexCoord,
        range: u8,
        nav_level: u8,
    },

    #[error("cannot upgrade {from:?} to {to:?}")]
    InvalidUpgrade {
        from: StructureType,
        to: StructureType,
    },

    #[error("structure limit reached for {0:?}")]
    StructureLimit(StructureType),

    #[error("federation power insufficient")]
    FederationInsufficientPower,

    #[error("federation hexes are not connected")]
    FederationDisconnected,

    #[error("bid too low: current max {current_max}, placed {placed}")]
    BidTooLow { current_max: u32, placed: u32 },

    #[error("bid {bid} exceeds current VP {vp}")]
    BidExceedsVp { bid: u32, vp: i32 },

    #[error("already passed this round")]
    AlreadyPassed,

    #[error("satellites cannot be placed on space tiles ({0:?})")]
    SatelliteOnSpaceTile(HexCoord),

    #[error("no gaiaformer available")]
    NoGaiaformerAvailable,

    #[error("action not allowed: {0}")]
    ActionNotAllowed(String),
}

#[derive(Debug, Error, Clone, PartialEq)]
pub enum SetupError {
    #[error("invalid seed: {0}")]
    InvalidSeed(String),
}

#[derive(Debug, Error)]
pub enum DeserializeError {
    #[error("invalid JSON: {0}")]
    InvalidJson(#[from] serde_json::Error),

    #[error("unknown schema version: {version}")]
    UnknownVersion { version: u64 },

    #[error("missing required field: {field}")]
    MissingField { field: &'static str },

    #[error("invalid enum variant: {value} for {type_name}")]
    InvalidVariant {
        value: String,
        type_name: &'static str,
    },
}
