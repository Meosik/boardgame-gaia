use gaia_engine::{RuleEngine, ScoringEngine};

use crate::{
    coordinator,
    error::{ServerError, ServerResult},
    messages::ServerMessage,
    services::dev_game::auto_advance_dev_actions,
    state::AppState,
};

pub struct TurnManagementService;

impl TurnManagementService {
    /// Called after every action to check if the round has ended.
    pub async fn maybe_end_round(state: &AppState, room_code: &str) -> ServerResult<()> {
        let (all_passed, round) = {
            let rooms = state.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| ServerError::RoomNotFound(room_code.to_string()))?;
            let gs = room
                .game_state
                .as_ref()
                .ok_or_else(|| ServerError::Internal("no game state".into()))?;
            let all = gs.players.iter().all(|p| p.passed);
            (all, gs.round)
        };

        if all_passed {
            Self::end_round(state, room_code, round).await?;
        }
        Ok(())
    }

    async fn end_round(state: &AppState, room_code: &str, round: u8) -> ServerResult<()> {
        let scores = {
            let rooms = state.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| ServerError::RoomNotFound(room_code.to_string()))?;
            let gs = room
                .game_state
                .as_ref()
                .ok_or_else(|| ServerError::Internal("no game state".into()))?;
            ScoringEngine::calculate_round_scoring(gs, round)
        };

        // The action that just set the final `passed = true` already went
        // through `coordinator::apply_command`, so this round's end-state is
        // already snapshotted at the current revision — no separate save here.

        state
            .event_bus
            .broadcast(
                room_code,
                ServerMessage::RoundEnded {
                    round,
                    scores: scores.clone(),
                },
            )
            .await;

        if round >= 6 {
            super::game_end::GameEndService::end_game(state, room_code).await?;
        } else {
            Self::start_next_round(state, room_code).await?;
        }

        Ok(())
    }

    /// Runs the Gaia and Income phases and reopens the next round's
    /// `ActionPhase` (`RuleEngine::advance_to_next_round`).
    async fn start_next_round(state: &AppState, room_code: &str) -> ServerResult<()> {
        let outcome = coordinator::apply_server_transition(state, room_code, |room| {
            {
                let gs = room
                    .game_state
                    .as_mut()
                    .ok_or(gaia_engine::error::RuleError::WrongPhase)?;
                RuleEngine::advance_to_next_round(gs)?;
            }
            if let Some(human_player) = room.dev_human_player.filter(|_| state.ai.is_none()) {
                let bot_events = auto_advance_dev_actions(room, human_player)?;
                if !bot_events.is_empty() {
                    room.game_state
                        .as_mut()
                        .ok_or(gaia_engine::error::RuleError::WrongPhase)?
                        .event_log
                        .extend(bot_events);
                }
            }
            Ok(())
        })
        .await
        .map_err(coordinator::command_error_to_server_error)?;

        // The reset `passed` flags, pass-order-derived turn order, and new round number are all
        // visible in this Snapshot; no separate turn-change signal is needed.
        coordinator::broadcast_snapshot(state, room_code, outcome.revision).await;
        crate::ai::spawn_driver(state.clone(), room_code.to_string());

        Ok(())
    }
}
