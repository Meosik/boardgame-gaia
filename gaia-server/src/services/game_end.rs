use gaia_engine::{game_state::GamePhase, RuleEngine};

use crate::{
    coordinator,
    error::{ServerError, ServerResult},
    messages::ServerMessage,
    repository::GameRepository,
    room::manager::RoomState,
    state::AppState,
};

pub struct GameEndService;

impl GameEndService {
    /// Runs `RuleEngine::finalize_game` inside the same atomic transition that flips the room to
    /// `RoomState::Ended`, so the authoritative snapshot itself carries `final_scores`/`winners`
    /// (via `GamePhase::Ended`) instead of only a one-time `GameEnded` broadcast — a client that
    /// reconnects or refreshes after this call still sees the real result straight from the next
    /// snapshot/room load, with no dependency on having been present for the broadcast.
    pub async fn end_game(state: &AppState, room_code: &str) -> ServerResult<()> {
        let outcome = coordinator::apply_server_transition(state, room_code, |room| {
            let gs = room
                .game_state
                .as_mut()
                .ok_or(gaia_engine::error::RuleError::WrongPhase)?;
            RuleEngine::finalize_game(gs)?;
            room.state = RoomState::Ended;
            Ok(())
        })
        .await
        .map_err(coordinator::command_error_to_server_error)?;

        let (final_scores, winners) = {
            let rooms = state.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| ServerError::RoomNotFound(room_code.to_string()))?;
            let gs = room
                .game_state
                .as_ref()
                .ok_or_else(|| ServerError::Internal("no game state".into()))?;
            let GamePhase::Ended {
                final_scores,
                winners,
            } = &gs.phase
            else {
                return Err(ServerError::Internal(
                    "finalize_game committed without reaching GamePhase::Ended".into(),
                ));
            };
            (final_scores.to_vec(), winners.clone())
        };

        let repo = GameRepository::new(state.db.clone());
        repo.save_final_scores(room_code, &final_scores).await?;

        coordinator::broadcast_snapshot(state, room_code, outcome.revision).await;
        state
            .event_bus
            .broadcast(
                room_code,
                ServerMessage::GameEnded {
                    final_scores,
                    winners,
                },
            )
            .await;

        state.event_bus.remove(room_code).await;

        Ok(())
    }
}
