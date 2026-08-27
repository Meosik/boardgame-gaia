use gaia_engine::{game_state::PlayerId, GameSetup, Randomizer, SetupMode};
use gaia_protocol::{CommandId, Revision};

use crate::{
    coordinator::{self, broadcast_snapshot, CommandResult},
    error::{ServerError, ServerResult},
    repository::GameRepository,
    state::AppState,
};

pub struct GameSetupService;

impl GameSetupService {
    /// Creates a new room, persists it, and returns (room_code, player_id, setup).
    pub async fn create_room(
        state: &AppState,
        host_nickname: &str,
        seed: Option<String>,
        setup_mode: SetupMode,
    ) -> ServerResult<(String, PlayerId, GameSetup)> {
        let (code, player_id) = {
            let mut rooms = state.rooms.write().await;
            rooms.create_room(host_nickname, seed, setup_mode)?
        };

        let setup = {
            let rooms = state.rooms.read().await;
            rooms
                .get_room(&code)
                .and_then(|r| r.setup.clone())
                .ok_or_else(|| ServerError::Internal("setup missing after create".into()))?
        };

        let seed_str = {
            let rooms = state.rooms.read().await;
            rooms
                .get_room(&code)
                .map(|r| r.seed.clone())
                .unwrap_or_default()
        };

        let repo = GameRepository::new(state.db.clone());
        repo.save_room(&code, &seed_str, player_id, &setup).await?;

        Ok((code, player_id, setup))
    }

    /// Regenerates the setup with a new (or provided) seed. Host-only.
    /// Broadcasts a `Snapshot` (with the new setup embedded in the lobby
    /// view) on success. Callers that need the resulting `GameSetup` value
    /// itself (the REST `regenerate` endpoint) re-read `room.setup` after
    /// this returns rather than threading it through `CommandOutcome`.
    pub async fn regenerate_setup(
        state: &AppState,
        room_code: &str,
        requesting_player: PlayerId,
        seed: Option<String>,
        command_id: CommandId,
        expected_revision: Revision,
    ) -> CommandResult {
        let setup_mode = {
            let rooms = state.rooms.read().await;
            let room = rooms
                .get_room(room_code)
                .ok_or_else(|| coordinator::CommandError::RoomNotFound(room_code.to_string()))?;
            if !room.is_host(requesting_player) {
                return Err(coordinator::CommandError::Server(ServerError::Unauthorised));
            }
            if room.state != crate::room::manager::RoomState::Lobby {
                return Err(coordinator::CommandError::Server(
                    ServerError::RoomAlreadyStarted,
                ));
            }
            room.setup
                .as_ref()
                .map_or(SetupMode::Sequential, |setup| setup.setup_mode)
        };

        let new_seed = seed.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());
        let setup = match setup_mode {
            SetupMode::Sequential => Randomizer::generate_setup(&new_seed),
            SetupMode::Bidding => Randomizer::generate_bidding_setup(&new_seed),
        }
        .map_err(|e| coordinator::CommandError::Server(ServerError::from(e)))?;

        let outcome =
            coordinator::apply_command(state, room_code, command_id, expected_revision, |room| {
                room.seed.clone_from(&new_seed);
                room.setup = Some(setup.clone());
                Ok(Vec::new())
            })
            .await?;

        broadcast_snapshot(state, room_code, outcome.revision).await;
        Ok(outcome)
    }
}
