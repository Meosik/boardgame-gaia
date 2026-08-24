use crate::error::RuleError;
use crate::game_state::{FactionAssignment, FactionId, FactionSelectionState, GameEvent, PlayerId};

/// Applies the fixed first-release setup policy: players choose factions once,
/// in clockwise room order, without bidding or selecting a separate turn slot.
pub struct SetupPolicy;

impl SetupPolicy {
    pub fn initialize(
        player_order: Vec<PlayerId>,
        available_factions: Vec<FactionId>,
    ) -> FactionSelectionState {
        FactionSelectionState {
            available_factions,
            player_order,
            current_index: 0,
            assignments: Vec::new(),
        }
    }

    pub fn select_faction(
        state: &mut FactionSelectionState,
        player: PlayerId,
        faction: FactionId,
    ) -> Result<GameEvent, RuleError> {
        if state.current_player() != Some(player) {
            return Err(RuleError::NotYourTurn);
        }
        if !state.available_factions.contains(&faction) {
            return Err(RuleError::ActionNotAllowed(format!(
                "faction {faction:?} unavailable"
            )));
        }

        let other_side = faction.other_board_side();
        state
            .available_factions
            .retain(|candidate| *candidate != faction && *candidate != other_side);
        state
            .assignments
            .push(FactionAssignment { player, faction });
        state.current_index += 1;

        Ok(GameEvent::FactionSelected { player, faction })
    }
}
