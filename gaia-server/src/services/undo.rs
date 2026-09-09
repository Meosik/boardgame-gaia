use gaia_engine::{
    error::RuleError,
    game_state::{GameEvent, GamePhase, PlayerId, UndoCompletedTurn, UndoRequestState},
    GameState,
};
use gaia_protocol::{CommandId, Revision};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandError, CommandResult},
    error::ServerError,
    repository::GameRepository,
    state::AppState,
};

pub struct UndoService;

impl UndoService {
    /// Restores the snapshot immediately before the active player's first
    /// free action this turn. This undoes every free action in the current
    /// turn without advancing or consuming the action turn.
    pub async fn undo_free_action(
        app: &AppState,
        room_code: &str,
        player_id: PlayerId,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let target_revision = {
            let rooms = app.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| CommandError::RoomNotFound(room_code.to_string()))?;
            free_action_target(room.game_state.as_ref(), player_id)?
        };
        let restored = load_snapshot(app, room_code, target_revision).await?;

        let outcome = coordinator::apply_command(
            app,
            room_code,
            command_id,
            expected_revision,
            move |room| {
                let current_target = free_action_target(room.game_state.as_ref(), player_id)?;
                if current_target != target_revision {
                    return Err(RuleError::ActionNotAllowed(
                        "the free-action undo checkpoint changed".into(),
                    ));
                }
                room.game_state = Some(restored.clone());
                Ok(vec![GameEvent::UndoApplied {
                    requester: player_id,
                    free_action_only: true,
                }])
            },
        )
        .await?;

        broadcast_snapshot(app, room_code, outcome.revision).await;
        Ok(outcome)
    }

    /// Opens a room-wide approval request for the requester's latest completed
    /// action turn. Development rooms contain only one real room member, so
    /// they apply immediately; virtual opponents never block the test harness.
    pub async fn request_turn_undo(
        app: &AppState,
        room_code: &str,
        requester: PlayerId,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let (target_revision, required_approvals) = {
            let rooms = app.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| CommandError::RoomNotFound(room_code.to_string()))?;
            let game_state = room.game_state.as_ref().ok_or(RuleError::WrongPhase)?;
            if game_state.undo_state.pending_request.is_some() {
                return Err(RuleError::ActionNotAllowed(
                    "another undo request is already pending".into(),
                )
                .into());
            }
            let checkpoint = eligible_completed_turn(game_state, requester)?;
            let approvals = room
                .players
                .iter()
                .map(|(player, _, _)| *player)
                .filter(|player| *player != requester)
                .collect::<Vec<_>>();
            (checkpoint.start_revision, approvals)
        };

        let restored = if required_approvals.is_empty() {
            Some(load_snapshot(app, room_code, target_revision).await?)
        } else {
            None
        };
        let required_for_mutation = required_approvals.clone();

        let outcome = coordinator::apply_command(
            app,
            room_code,
            command_id,
            expected_revision,
            move |room| {
                let game_state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
                if game_state.undo_state.pending_request.is_some() {
                    return Err(RuleError::ActionNotAllowed(
                        "another undo request is already pending".into(),
                    ));
                }
                let checkpoint = eligible_completed_turn(game_state, requester)?;
                if checkpoint.start_revision != target_revision {
                    return Err(RuleError::ActionNotAllowed(
                        "the completed-turn undo checkpoint changed".into(),
                    ));
                }

                if let Some(restored) = &restored {
                    room.game_state = Some(restored.clone());
                    return Ok(vec![GameEvent::UndoApplied {
                        requester,
                        free_action_only: false,
                    }]);
                }

                game_state.undo_state.pending_request = Some(UndoRequestState {
                    requester,
                    target_revision,
                    required_approvals: required_for_mutation.clone(),
                    approvals: Vec::new(),
                });
                Ok(vec![GameEvent::UndoRequested { requester }])
            },
        )
        .await?;

        broadcast_snapshot(app, room_code, outcome.revision).await;
        Ok(outcome)
    }

    pub async fn respond_turn_undo(
        app: &AppState,
        room_code: &str,
        responder: PlayerId,
        approve: bool,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let (requester, target_revision, final_approval) = {
            let rooms = app.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| CommandError::RoomNotFound(room_code.to_string()))?;
            let request = room
                .game_state
                .as_ref()
                .and_then(|state| state.undo_state.pending_request.as_ref())
                .ok_or_else(no_pending_request)?;
            validate_responder(request, responder)?;
            let final_approval = approve
                && request
                    .required_approvals
                    .iter()
                    .all(|player| *player == responder || request.approvals.contains(player));
            (request.requester, request.target_revision, final_approval)
        };

        let restored = if final_approval {
            Some(load_snapshot(app, room_code, target_revision).await?)
        } else {
            None
        };

        let outcome = coordinator::apply_command(
            app,
            room_code,
            command_id,
            expected_revision,
            move |room| {
                let game_state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
                let request = game_state
                    .undo_state
                    .pending_request
                    .as_mut()
                    .ok_or_else(no_pending_request)?;
                if request.requester != requester || request.target_revision != target_revision {
                    return Err(RuleError::ActionNotAllowed(
                        "the undo request changed".into(),
                    ));
                }
                validate_responder(request, responder)?;

                if !approve {
                    game_state.undo_state.pending_request = None;
                    return Ok(vec![GameEvent::UndoRejected {
                        requester,
                        responder,
                    }]);
                }

                request.approvals.push(responder);
                if request
                    .required_approvals
                    .iter()
                    .all(|player| request.approvals.contains(player))
                {
                    let restored = restored.as_ref().ok_or_else(|| {
                        RuleError::ActionNotAllowed("undo snapshot was not loaded".into())
                    })?;
                    room.game_state = Some(restored.clone());
                    return Ok(vec![GameEvent::UndoApplied {
                        requester,
                        free_action_only: false,
                    }]);
                }

                Ok(Vec::new())
            },
        )
        .await?;

        broadcast_snapshot(app, room_code, outcome.revision).await;
        Ok(outcome)
    }
}

fn free_action_target(state: Option<&GameState>, player_id: PlayerId) -> Result<u64, RuleError> {
    let state = state.ok_or(RuleError::WrongPhase)?;
    if state.undo_state.pending_request.is_some() {
        return Err(RuleError::ActionNotAllowed(
            "an undo request is waiting for player responses".into(),
        ));
    }
    let is_active_player = match state.phase {
        GamePhase::ActionPhase { active_player } => {
            state.turn_order.get(active_player).copied() == Some(player_id)
        }
        _ => false,
    };
    let open_turn = state
        .undo_state
        .open_turn
        .as_ref()
        .filter(|turn| turn.player == player_id && is_active_player)
        .ok_or_else(|| RuleError::ActionNotAllowed("no free action can be undone".into()))?;
    open_turn
        .free_action_revisions
        .first()
        .copied()
        .ok_or_else(|| RuleError::ActionNotAllowed("no free action can be undone".into()))
}

fn eligible_completed_turn(
    state: &GameState,
    requester: PlayerId,
) -> Result<&UndoCompletedTurn, RuleError> {
    state
        .undo_state
        .recent_turns
        .iter()
        .rev()
        .find(|turn| turn.player == requester)
        .ok_or_else(|| {
            RuleError::ActionNotAllowed(
                "the latest completed turn is outside the undo window".into(),
            )
        })
}

fn validate_responder(request: &UndoRequestState, responder: PlayerId) -> Result<(), RuleError> {
    if !request.required_approvals.contains(&responder) {
        return Err(RuleError::ActionNotAllowed(
            "this player cannot respond to the undo request".into(),
        ));
    }
    if request.approvals.contains(&responder) {
        return Err(RuleError::ActionNotAllowed(
            "this player already approved the undo request".into(),
        ));
    }
    Ok(())
}

fn no_pending_request() -> RuleError {
    RuleError::ActionNotAllowed("no undo request is pending".into())
}

async fn load_snapshot(
    app: &AppState,
    room_code: &str,
    revision: u64,
) -> Result<GameState, CommandError> {
    GameRepository::new(app.db.clone())
        .load_snapshot_at_revision(room_code, revision)
        .await
        .map_err(CommandError::Server)?
        .ok_or_else(|| {
            CommandError::Server(ServerError::Internal(format!(
                "undo snapshot revision {revision} was not found"
            )))
        })
}

#[cfg(test)]
mod tests {
    use gaia_engine::{
        game_state::{GamePhase, UndoCompletedTurn, UndoOpenTurn},
        test_utils::builders::GameStateBuilder,
    };

    use super::{eligible_completed_turn, free_action_target};

    #[test]
    fn free_action_target_is_the_first_checkpoint_for_the_active_player() {
        let mut state = GameStateBuilder::new()
            .with_player(0)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        state.undo_state.open_turn = Some(UndoOpenTurn {
            player: 0,
            start_revision: 9,
            free_action_revisions: vec![9, 10],
        });

        assert_eq!(free_action_target(Some(&state), 0), Ok(9));
    }

    #[test]
    fn only_the_two_retained_completed_turns_are_requestable() {
        let mut state = GameStateBuilder::new()
            .with_player(0)
            .with_player(1)
            .build();
        state.undo_state.recent_turns = vec![
            UndoCompletedTurn {
                player: 0,
                start_revision: 12,
                completed_revision: 13,
            },
            UndoCompletedTurn {
                player: 1,
                start_revision: 13,
                completed_revision: 14,
            },
        ];

        assert_eq!(
            eligible_completed_turn(&state, 0).map(|turn| turn.start_revision),
            Ok(12)
        );
    }
}
