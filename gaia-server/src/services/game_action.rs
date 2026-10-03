use gaia_engine::{
    error::RuleError,
    game_state::{GameEvent, GamePhase, PlayerId, UndoCompletedTurn, UndoOpenTurn},
    rules::actions::GameAction,
    GameState, RuleEngine,
};
use gaia_protocol::{CommandId, Revision};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    error::ServerResult,
    services::{dev_game::auto_advance_dev_actions, turn_management::TurnManagementService},
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
        let ai_seats = state.ai.is_some();
        let outcome =
            coordinator::apply_command(state, room_code, command_id, expected_revision, |room| {
                let acting_player = crate::services::dev_game::acting_player(room, player_id);
                let mut events = {
                    let game_state = room
                        .game_state
                        .as_mut()
                        .ok_or(gaia_engine::error::RuleError::WrongPhase)?;
                    apply_tracked_action(
                        game_state,
                        acting_player,
                        action.clone(),
                        expected_revision.get(),
                    )?
                };
                if room.dev_human_player == Some(player_id) && !ai_seats {
                    events.extend(auto_advance_dev_actions(room, player_id)?);
                }
                Ok(events)
            })
            .await?;

        broadcast_snapshot(state, room_code, outcome.revision).await;

        maybe_end_round(state, room_code).await;
        crate::ai::spawn_driver(state.clone(), room_code.to_string());

        Ok(outcome)
    }
}

/// Applies an engine action while maintaining durable undo checkpoints. The
/// checkpoint update lives in the same coordinator transaction as the action,
/// so a rejected action or failed database commit cannot leave phantom undo
/// history behind.
pub(crate) fn apply_tracked_action(
    state: &mut GameState,
    player_id: PlayerId,
    action: GameAction,
    expected_revision: u64,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, RuleError> {
    if state.undo_state.pending_request.is_some() {
        return Err(RuleError::ActionNotAllowed(
            "an undo request is waiting for player responses".into(),
        ));
    }

    let is_free_action = matches!(
        &action,
        GameAction::FreeAction { .. } | GameAction::SpaceGiantsGainTechTile { .. }
    );
    if action_phase_player(state) == Some(player_id) {
        let open_turn = state
            .undo_state
            .open_turn
            .get_or_insert_with(|| UndoOpenTurn {
                player: player_id,
                start_revision: expected_revision,
                free_action_revisions: Vec::new(),
            });
        if open_turn.player != player_id {
            *open_turn = UndoOpenTurn {
                player: player_id,
                start_revision: expected_revision,
                free_action_revisions: Vec::new(),
            };
        }
        if is_free_action {
            open_turn.free_action_revisions.push(expected_revision);
        }
    }

    let events = apply_logged_action(state, player_id, action)?;
    finalize_completed_turn(state, expected_revision.saturating_add(1), is_free_action);
    Ok(events)
}

pub(crate) fn apply_logged_action(
    state: &mut GameState,
    player: PlayerId,
    action: GameAction,
) -> Result<Vec<GameEvent>, RuleError> {
    let action_name = serde_json::to_value(&action)
        .ok()
        .and_then(|value| {
            value
                .get("type")
                .and_then(|tag| tag.as_str())
                .map(str::to_owned)
        })
        .unwrap_or_else(|| "Action".to_owned());
    let mut events = RuleEngine::apply_action(state, player, action)?;
    events.push(GameEvent::ActionLog {
        player,
        action: action_name,
        event_count: events.len(),
    });
    Ok(events)
}

fn action_phase_player(state: &GameState) -> Option<PlayerId> {
    match state.phase {
        GamePhase::ActionPhase { active_player } => state.turn_order.get(active_player).copied(),
        _ => None,
    }
}

fn phase_keeps_turn_open(state: &GameState) -> bool {
    matches!(
        &state.phase,
        GamePhase::ChargePowerPending { .. }
            | GamePhase::LostPlanetPlacementPending { .. }
            | GamePhase::LostPlanetChargePowerPending { .. }
    )
}

fn finalize_completed_turn(state: &mut GameState, completed_revision: u64, is_free_action: bool) {
    if is_free_action {
        return;
    }
    if state.undo_state.open_turn.is_none() {
        return;
    }
    if phase_keeps_turn_open(state) {
        return;
    }
    let open_turn = state
        .undo_state
        .open_turn
        .take()
        .unwrap_or_else(|| unreachable!("open turn was checked above"));
    state.undo_state.recent_turns.push(UndoCompletedTurn {
        player: open_turn.player,
        start_revision: open_turn.start_revision,
        completed_revision,
    });
    if state.undo_state.recent_turns.len() > 2 {
        state.undo_state.recent_turns.remove(0);
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

#[cfg(test)]
mod tests {
    use gaia_engine::{
        game_state::{GamePhase, ResearchTrack, UndoRequestState},
        rules::actions::{FreeActionKind, GameAction},
        test_utils::builders::GameStateBuilder,
    };

    use super::apply_tracked_action;

    #[test]
    fn action_log_boundary_preserves_effects_and_rejected_actions_emit_nothing() {
        use gaia_engine::game_state::GameEvent;
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| p.resources.power.bowl3 = 4)
            .build();
        let action = GameAction::FreeAction {
            kind: FreeActionKind::PowerToQic,
            count: 1,
        };
        let mut reference = state.clone();
        let expected = gaia_engine::RuleEngine::apply_action(&mut reference, 0, action.clone())
            .unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        let events = super::apply_logged_action(&mut state, 0, action.clone())
            .unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        assert_eq!(state.serialize(), reference.serialize());
        assert_eq!(
            serde_json::to_value(&events[..expected.len()])
                .unwrap_or_else(|error| panic!("test value should serialize: {error}")),
            serde_json::to_value(&expected)
                .unwrap_or_else(|error| panic!("test value should serialize: {error}"))
        );
        assert!(
            matches!(events.last(), Some(GameEvent::ActionLog { player: 0, action, event_count })
            if action == "FreeAction" && *event_count == expected.len())
        );
        let before = state.serialize();
        assert!(super::apply_logged_action(&mut state, 0, action).is_err());
        assert_eq!(state.serialize(), before);
        let encoded = serde_json::to_string(&events)
            .unwrap_or_else(|error| panic!("test value should serialize: {error}"));
        let restored: Vec<GameEvent> = serde_json::from_str(&encoded)
            .unwrap_or_else(|error| panic!("saved value should deserialize: {error}"));
        assert_eq!(
            serde_json::to_value(restored)
                .unwrap_or_else(|error| panic!("test value should serialize: {error}")),
            serde_json::to_value(events)
                .unwrap_or_else(|error| panic!("test value should serialize: {error}"))
        );
    }

    #[test]
    fn legacy_space_giants_technology_recovery_keeps_the_turn_open() {
        use gaia_engine::game_state::{FactionId, HexCoord, Structure, StructureType, TechTile};
        use gaia_engine::rules::actions::TechTileChoice;
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |p| {
                p.faction = Some(FactionId::SpaceGiants);
                p.structures.push(Structure {
                    hex: HexCoord::new(0, 0),
                    kind: StructureType::PlanetaryInstitute,
                });
            })
            .with_player(1)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        apply_tracked_action(
            &mut state,
            0,
            GameAction::SpaceGiantsGainTechTile {
                choice: TechTileChoice::Standard {
                    tile: TechTile(2),
                    advance_track: None,
                    bonus_build_coord: None,
                },
            },
            10,
        )
        .unwrap_or_else(|error| panic!("test action should succeed: {error}"));
        assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
        assert!(state.undo_state.open_turn.is_some());
        assert!(state.undo_state.recent_turns.is_empty());
    }

    #[test]
    fn free_action_checkpoint_keeps_the_action_turn_open() {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |player| player.resources.power.bowl3 = 4)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();

        apply_tracked_action(
            &mut state,
            0,
            GameAction::FreeAction {
                kind: FreeActionKind::PowerToQic,
                count: 1,
            },
            10,
        )
        .unwrap_or_else(|error| panic!("free action should succeed: {error}"));

        let open = state
            .undo_state
            .open_turn
            .as_ref()
            .unwrap_or_else(|| panic!("open turn checkpoint should remain"));
        assert_eq!(open.player, 0);
        assert_eq!(open.start_revision, 10);
        assert_eq!(open.free_action_revisions, vec![10]);
        assert_eq!(state.phase, GamePhase::ActionPhase { active_player: 0 });
    }

    #[test]
    fn main_action_closes_the_turn_but_keeps_its_original_pre_free_action_revision() {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |player| {
                player.resources.knowledge = 10;
                player.resources.power.bowl3 = 4;
            })
            .with_player(1)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        apply_tracked_action(
            &mut state,
            0,
            GameAction::FreeAction {
                kind: FreeActionKind::PowerToQic,
                count: 1,
            },
            20,
        )
        .unwrap_or_else(|error| panic!("free action should succeed: {error}"));

        apply_tracked_action(
            &mut state,
            0,
            GameAction::ResearchAdvance {
                track: ResearchTrack::Science,
            },
            21,
        )
        .unwrap_or_else(|error| panic!("main action should succeed: {error}"));

        assert!(state.undo_state.open_turn.is_none());
        assert_eq!(state.undo_state.recent_turns.len(), 1);
        assert_eq!(state.undo_state.recent_turns[0].start_revision, 20);
        assert_eq!(state.undo_state.recent_turns[0].completed_revision, 22);
    }

    #[test]
    fn main_action_is_complete_when_play_returns_to_the_same_player() {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |player| player.resources.knowledge = 10)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();

        apply_tracked_action(
            &mut state,
            0,
            GameAction::ResearchAdvance {
                track: ResearchTrack::Science,
            },
            30,
        )
        .unwrap_or_else(|error| panic!("main action should succeed: {error}"));

        assert!(state.undo_state.open_turn.is_none());
        assert_eq!(state.undo_state.recent_turns[0].player, 0);
        assert_eq!(state.undo_state.recent_turns[0].start_revision, 30);
        assert_eq!(state.undo_state.recent_turns[0].completed_revision, 31);
    }

    #[test]
    fn pending_undo_request_blocks_normal_game_actions() {
        let mut state = GameStateBuilder::new()
            .with_player_fn(0, |player| player.resources.knowledge = 10)
            .with_phase(GamePhase::ActionPhase { active_player: 0 })
            .build();
        state.undo_state.pending_request = Some(UndoRequestState {
            requester: 1,
            target_revision: 4,
            required_approvals: vec![0],
            approvals: vec![],
        });

        let result = apply_tracked_action(
            &mut state,
            0,
            GameAction::ResearchAdvance {
                track: ResearchTrack::Science,
            },
            5,
        );

        assert!(result.is_err());
        assert_eq!(state.players[0].research_tracks.science, 0);
    }
}
