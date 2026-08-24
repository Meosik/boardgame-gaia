use gaia_engine::{game_state::PlayerId, rules::actions::GameAction, RuleEngine};
use gaia_protocol::{CommandId, Revision};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    error::ServerResult,
    services::turn_management::TurnManagementService,
    state::AppState,
};

pub struct GameActionService;

impl GameActionService {
    pub async fn process_action(
        state: &AppState,
        room_code: &str,
        player_id: PlayerId,
        action: GameAction,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let outcome =
            coordinator::apply_command(state, room_code, command_id, expected_revision, |room| {
                let game_state = room
                    .game_state
                    .as_mut()
                    .ok_or(gaia_engine::error::RuleError::WrongPhase)?;
                RuleEngine::apply_action(game_state, player_id, action.clone())
            })
            .await?;

        broadcast_snapshot(state, room_code, outcome.revision).await;

        maybe_end_round(state, room_code).await;

        Ok(outcome)
    }
}

/// Round-advance is a server-initiated follow-up, not part of the client's
/// command outcome — failures here are logged, not surfaced to the acting
/// client (their own action already succeeded).
async fn maybe_end_round(state: &AppState, room_code: &str) {
    let result: ServerResult<()> = TurnManagementService::maybe_end_round(state, room_code).await;
    if let Err(e) = result {
        log::error!("maybe_end_round failed for room {room_code}: {e}");
    }
}
