// gaia-engine: pure game logic crate — no network, no DB
// All errors returned as Result<_, E>; no panics in library code.

pub mod bidding;
pub mod data;
pub mod error;
pub mod faction;
pub mod game_state;
pub mod map;
pub mod randomizer;
pub mod rules;
pub mod scoring;
pub mod setup_policy;

#[cfg(any(test, feature = "test-utils"))]
pub mod test_utils;

pub use bidding::{BidAssignment, BiddingPolicy, BiddingStage, BiddingState};
pub use error::{DeserializeError, RuleError, SetupError};
pub use faction::registry::FactionRegistry;
pub use game_state::{
    BoardState, GamePhase, GameState, PlayerState, ResearchTrack, Resources, SetupPhase,
};
pub use map::MapEngine;
pub use randomizer::{GameSetup, Randomizer, SetupMode};
pub use rules::actions::{GameAction, SetupAction};
pub use rules::engine::RuleEngine;
pub use scoring::{FinalScoreBreakdown, ScoringEngine};
pub use setup_policy::SetupPolicy;
