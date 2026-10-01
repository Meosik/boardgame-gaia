use gaia_engine::{game_state::PlayerId, rules::actions::SetupAction, GamePhase, SetupPhase};
use gaia_protocol::{CommandId, Revision};

use crate::services::dev_game::{auto_advance_dev_actions, auto_advance_dev_setup};
use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    room::manager::RoomState,
    state::AppState,
};

pub struct FactionSelectionService;

impl FactionSelectionService {
    /// Process one faction choice in the fixed clockwise setup order.
    /// Broadcasts a `Snapshot` on success; the caller (the WS handler) is
    /// responsible for acking `CommandAccepted`/`CommandRejected` directly
    /// to the requesting connection.
    pub async fn process_setup_action(
        state: &AppState,
        room_code: &str,
        player_id: PlayerId,
        action: SetupAction,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let ai_seats = state.ai.is_some();
        let outcome =
            coordinator::apply_command(state, room_code, command_id, expected_revision, |room| {
                if room.state != RoomState::FactionSelection {
                    return Err(gaia_engine::RuleError::WrongPhase);
                }
                let dev_human_player = room.dev_human_player;
                let acting_player = crate::services::dev_game::acting_player(room, player_id);
                let game_state = room
                    .game_state
                    .as_mut()
                    .ok_or(gaia_engine::error::RuleError::WrongPhase)?;

                let mut events = gaia_engine::RuleEngine::apply_setup_action(
                    game_state,
                    acting_player,
                    action.clone(),
                )?;

                if let Some(human_player) = dev_human_player.filter(|_| !ai_seats) {
                    events.extend(auto_advance_dev_setup(game_state, human_player)?);
                }

                if game_state.phase == GamePhase::Setup(SetupPhase::Complete) {
                    room.state = RoomState::InGame;
                    events.extend(gaia_engine::RuleEngine::start_first_round(game_state)?);
                }

                if let Some(human_player) = dev_human_player.filter(|_| !ai_seats) {
                    events.extend(auto_advance_dev_actions(room, human_player)?);
                }

                Ok(events)
            })
            .await?;

        broadcast_snapshot(state, room_code, outcome.revision).await;
        crate::ai::spawn_driver(state.clone(), room_code.to_string());
        Ok(outcome)
    }
}
