use gaia_engine::{game_state::PlayerId, ScoringEngine};

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
    pub async fn end_game(state: &AppState, room_code: &str) -> ServerResult<()> {
        let scores_arr = {
            let rooms = state.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| ServerError::RoomNotFound(room_code.to_string()))?;
            let gs = room
                .game_state
                .as_ref()
                .ok_or_else(|| ServerError::Internal("no game state".into()))?;
            ScoringEngine::calculate_final_scoring(gs)
        };

        // Find winner (highest VP)
        let winner = scores_arr
            .iter()
            .max_by_key(|(_, vp)| *vp)
            .map(|(pid, _)| *pid)
            .unwrap_or(0);

        let scores_vec: Vec<(PlayerId, i32)> = scores_arr.to_vec();

        let outcome = coordinator::apply_server_transition(state, room_code, |room| {
            room.state = RoomState::Ended;
        })
        .await
        .map_err(coordinator::command_error_to_server_error)?;

        let repo = GameRepository::new(state.db.clone());
        repo.save_final_scores(room_code, &scores_vec).await?;

        coordinator::broadcast_snapshot(state, room_code, outcome.revision).await;
        state
            .event_bus
            .broadcast(
                room_code,
                ServerMessage::GameEnded {
                    final_scores: scores_vec,
                    winner,
                },
            )
            .await;

        state.event_bus.remove(room_code).await;

        Ok(())
    }
}
