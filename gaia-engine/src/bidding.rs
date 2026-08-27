use crate::error::RuleError;
use crate::game_state::{FactionId, PlayerId};
use serde::{Deserialize, Serialize};

pub const BIDDING_PLAYER_COUNT: usize = 4;
pub const FIRST_TURN_POSITION: u8 = 1;
pub const LAST_TURN_POSITION: u8 = 4;
/// Not a rulebook limit — the auction has none, a bid may legitimately exceed
/// what the bidder currently holds and just runs their final score negative.
/// This is a sanity ceiling only, generous enough that no real bid ever
/// approaches it, to reject an obvious fat-fingered/garbage input rather than
/// silently accepting it.
pub const MAX_BID: u32 = 100;

/// One completed auction assignment. The bid is retained until final scoring;
/// it is not removed from the player's VP during setup or normal play.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct BidAssignment {
    pub player: PlayerId,
    pub faction: FactionId,
    pub turn_position: u8,
    pub bid_vp: u32,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BiddingStage {
    Auction,
    WinnerChoice { winner: PlayerId, bid_vp: u32 },
    Complete,
}

/// Serializable state for the fixed four-player open auction.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BiddingState {
    /// Immutable clockwise room order, with the host at index 0.
    pub clockwise_order: Vec<PlayerId>,
    /// Players who have not won an earlier auction.
    pub remaining_players: Vec<PlayerId>,
    pub available_factions: Vec<FactionId>,
    pub available_turn_positions: Vec<u8>,
    pub active_player: PlayerId,
    pub highest_bid: u32,
    pub highest_bidder: Option<PlayerId>,
    /// Passing only excludes a player from the current auction.
    pub passed_players: Vec<PlayerId>,
    pub stage: BiddingStage,
    pub assignments: Vec<BidAssignment>,
}

impl BiddingState {
    pub fn current_actor(&self) -> Option<PlayerId> {
        match self.stage {
            BiddingStage::Auction => Some(self.active_player),
            BiddingStage::WinnerChoice { winner, .. } => Some(winner),
            BiddingStage::Complete => None,
        }
    }

    pub fn is_complete(&self) -> bool {
        self.stage == BiddingStage::Complete
    }

    pub fn turn_order(&self) -> Option<Vec<PlayerId>> {
        if !self.is_complete() || self.assignments.len() != BIDDING_PLAYER_COUNT {
            return None;
        }

        let mut ordered = self.assignments.clone();
        ordered.sort_by_key(|assignment| assignment.turn_position);
        Some(
            ordered
                .into_iter()
                .map(|assignment| assignment.player)
                .collect(),
        )
    }
}

pub struct BiddingPolicy;

impl BiddingPolicy {
    pub fn initialize(
        clockwise_order: Vec<PlayerId>,
        available_factions: Vec<FactionId>,
    ) -> Result<BiddingState, RuleError> {
        if clockwise_order.len() != BIDDING_PLAYER_COUNT
            || available_factions.len() != BIDDING_PLAYER_COUNT
        {
            return Err(RuleError::ActionNotAllowed(
                "bidding requires exactly four players and four factions".to_string(),
            ));
        }
        if has_duplicates(&clockwise_order) || has_duplicates(&available_factions) {
            return Err(RuleError::ActionNotAllowed(
                "bidding players and factions must be unique".to_string(),
            ));
        }
        if available_factions.iter().any(|faction| {
            available_factions
                .iter()
                .any(|candidate| candidate != faction && *candidate == faction.other_board_side())
        }) {
            return Err(RuleError::ActionNotAllowed(
                "bidding cannot offer both sides of one faction board".to_string(),
            ));
        }

        Ok(BiddingState {
            active_player: clockwise_order[0],
            remaining_players: clockwise_order.clone(),
            clockwise_order,
            available_factions,
            available_turn_positions: (FIRST_TURN_POSITION..=LAST_TURN_POSITION).collect(),
            highest_bid: 0,
            highest_bidder: None,
            passed_players: Vec::new(),
            stage: BiddingStage::Auction,
            assignments: Vec::new(),
        })
    }

    pub fn place_bid(
        state: &mut BiddingState,
        player: PlayerId,
        bid_vp: u32,
    ) -> Result<(), RuleError> {
        ensure_auction_turn(state, player)?;
        if bid_vp <= state.highest_bid {
            return Err(RuleError::BidTooLow {
                current_max: state.highest_bid,
                placed: bid_vp,
            });
        }
        if bid_vp > MAX_BID {
            return Err(RuleError::BidTooHigh {
                max: MAX_BID,
                placed: bid_vp,
            });
        }

        state.highest_bid = bid_vp;
        state.highest_bidder = Some(player);
        state.active_player = next_clockwise_player(state, player).ok_or_else(|| {
            RuleError::ActionNotAllowed("auction has no eligible next bidder".to_string())
        })?;
        Ok(())
    }

    pub fn pass(state: &mut BiddingState, player: PlayerId) -> Result<(), RuleError> {
        ensure_auction_turn(state, player)?;
        state.passed_players.push(player);

        let eligible: Vec<PlayerId> = state
            .remaining_players
            .iter()
            .copied()
            .filter(|candidate| !state.passed_players.contains(candidate))
            .collect();
        if eligible.len() == 1 {
            let winner = eligible[0];
            let bid_vp = if state.highest_bidder == Some(winner) {
                state.highest_bid
            } else {
                0
            };
            state.active_player = winner;
            state.stage = BiddingStage::WinnerChoice { winner, bid_vp };
            return Ok(());
        }

        state.active_player = next_clockwise_player(state, player).ok_or_else(|| {
            RuleError::ActionNotAllowed("auction has no eligible next bidder".to_string())
        })?;
        Ok(())
    }

    /// Records the auction winner's faction and final turn-order choice. After
    /// the third choice, the fourth player automatically receives every item
    /// left over with a zero bid.
    pub fn choose(
        state: &mut BiddingState,
        player: PlayerId,
        faction: FactionId,
        turn_position: u8,
    ) -> Result<Vec<BidAssignment>, RuleError> {
        let bid_vp = match state.stage {
            BiddingStage::WinnerChoice { winner, bid_vp } if winner == player => bid_vp,
            BiddingStage::WinnerChoice { .. } => return Err(RuleError::NotYourTurn),
            _ => return Err(RuleError::WrongPhase),
        };
        if !state.available_factions.contains(&faction) {
            return Err(RuleError::ActionNotAllowed(format!(
                "faction {faction:?} unavailable"
            )));
        }
        if !state.available_turn_positions.contains(&turn_position) {
            return Err(RuleError::ActionNotAllowed(format!(
                "turn position {turn_position} unavailable"
            )));
        }

        let assignment = BidAssignment {
            player,
            faction,
            turn_position,
            bid_vp,
        };
        state.assignments.push(assignment);
        state
            .remaining_players
            .retain(|candidate| *candidate != player);
        state
            .available_factions
            .retain(|candidate| *candidate != faction);
        state
            .available_turn_positions
            .retain(|candidate| *candidate != turn_position);

        let mut created = vec![assignment];
        if state.assignments.len() == BIDDING_PLAYER_COUNT - 1 {
            let final_assignment = BidAssignment {
                player: state.remaining_players[0],
                faction: state.available_factions[0],
                turn_position: state.available_turn_positions[0],
                bid_vp: 0,
            };
            state.assignments.push(final_assignment);
            state.remaining_players.clear();
            state.available_factions.clear();
            state.available_turn_positions.clear();
            state.highest_bid = 0;
            state.highest_bidder = None;
            state.passed_players.clear();
            state.stage = BiddingStage::Complete;
            created.push(final_assignment);
            return Ok(created);
        }

        let next_start = next_remaining_clockwise(state, player).ok_or_else(|| {
            RuleError::ActionNotAllowed("auction has no remaining player".to_string())
        })?;
        state.active_player = next_start;
        state.highest_bid = 0;
        state.highest_bidder = None;
        state.passed_players.clear();
        state.stage = BiddingStage::Auction;
        Ok(created)
    }
}

fn ensure_auction_turn(state: &BiddingState, player: PlayerId) -> Result<(), RuleError> {
    if state.stage != BiddingStage::Auction {
        return Err(RuleError::WrongPhase);
    }
    if state.active_player != player {
        return Err(RuleError::NotYourTurn);
    }
    if state.passed_players.contains(&player) {
        return Err(RuleError::AlreadyPassed);
    }
    Ok(())
}

fn next_clockwise_player(state: &BiddingState, after: PlayerId) -> Option<PlayerId> {
    clockwise_candidates(&state.clockwise_order, after).find(|candidate| {
        state.remaining_players.contains(candidate)
            && !state.passed_players.contains(candidate)
            && state.highest_bidder != Some(*candidate)
    })
}

fn next_remaining_clockwise(state: &BiddingState, after: PlayerId) -> Option<PlayerId> {
    clockwise_candidates(&state.clockwise_order, after)
        .find(|candidate| state.remaining_players.contains(candidate))
}

fn clockwise_candidates(
    clockwise_order: &[PlayerId],
    after: PlayerId,
) -> impl Iterator<Item = PlayerId> + '_ {
    let start = clockwise_order
        .iter()
        .position(|candidate| *candidate == after)
        .map_or(0, |index| index + 1);
    clockwise_order
        .iter()
        .cycle()
        .skip(start)
        .take(clockwise_order.len())
        .copied()
}

fn has_duplicates<T: PartialEq>(values: &[T]) -> bool {
    values
        .iter()
        .enumerate()
        .any(|(index, value)| values[index + 1..].contains(value))
}

#[cfg(test)]
mod tests {
    use super::{BiddingPolicy, BiddingStage};
    use crate::error::RuleError;
    use crate::game_state::FactionId;

    fn initialized() -> super::BiddingState {
        BiddingPolicy::initialize(
            vec![7, 3, 9, 1],
            vec![
                FactionId::Terrans,
                FactionId::Xenos,
                FactionId::Taklons,
                FactionId::HadschHallas,
            ],
        )
        .unwrap_or_else(|error| panic!("valid four-player auction: {error}"))
    }

    #[test]
    fn host_starts_and_current_highest_bidder_is_skipped() {
        let mut state = initialized();

        BiddingPolicy::place_bid(&mut state, 7, 1)
            .unwrap_or_else(|error| panic!("host can open: {error}"));
        assert_eq!(state.active_player, 3);
        BiddingPolicy::place_bid(&mut state, 3, 2)
            .unwrap_or_else(|error| panic!("next player can raise: {error}"));
        assert_eq!(state.active_player, 9);
        BiddingPolicy::pass(&mut state, 9)
            .unwrap_or_else(|error| panic!("active player can pass: {error}"));
        assert_eq!(state.active_player, 1);
        BiddingPolicy::pass(&mut state, 1)
            .unwrap_or_else(|error| panic!("active player can pass: {error}"));
        assert_eq!(state.active_player, 7);
        BiddingPolicy::pass(&mut state, 7)
            .unwrap_or_else(|error| panic!("outbid player can pass: {error}"));

        assert_eq!(
            state.stage,
            BiddingStage::WinnerChoice {
                winner: 3,
                bid_vp: 2
            }
        );
    }

    #[test]
    fn a_passed_player_cannot_rejoin_current_auction() {
        let mut state = initialized();

        BiddingPolicy::pass(&mut state, 7).unwrap_or_else(|error| panic!("host can pass: {error}"));
        let result = BiddingPolicy::place_bid(&mut state, 7, 1);

        assert!(matches!(result, Err(RuleError::NotYourTurn)));
        assert!(state.passed_players.contains(&7));
    }

    #[test]
    fn bid_must_raise_above_the_current_highest() {
        let mut state = initialized();

        assert!(matches!(
            BiddingPolicy::place_bid(&mut state, 7, 0),
            Err(RuleError::BidTooLow {
                current_max: 0,
                placed: 0
            })
        ));
    }

    #[test]
    fn a_bid_may_exceed_the_bidder_s_current_vp() {
        // No rulebook cap tied to VP: a bid this large simply goes negative
        // at final scoring, same as any other VP expenditure exceeding
        // what's on hand. Still under the flat sanity ceiling (MAX_BID).
        let mut state = initialized();

        BiddingPolicy::place_bid(&mut state, 7, 50)
            .unwrap_or_else(|error| panic!("an uncapped bid should be accepted: {error}"));
        assert_eq!(state.highest_bid, 50);
        assert_eq!(state.highest_bidder, Some(7));
    }

    #[test]
    fn a_bid_above_the_sanity_ceiling_is_rejected() {
        let mut state = initialized();

        assert!(matches!(
            BiddingPolicy::place_bid(&mut state, 7, super::MAX_BID + 1),
            Err(RuleError::BidTooHigh {
                max: super::MAX_BID,
                placed,
            }) if placed == super::MAX_BID + 1
        ));
    }
}
