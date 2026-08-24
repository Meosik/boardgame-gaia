use gaia_engine::GameState;

use crate::{
    error::{ServerError, ServerResult},
    repository::GameRepository,
    state::AppState,
};

pub struct ReconnectService;

impl ReconnectService {
    /// Reconstruct the current game state from the latest DB snapshot.
    ///
    /// No event replay: `coordinator::apply_command` snapshots the full
    /// state on every committed revision, so the latest snapshot alone is
    /// always the exact committed state — there's nothing to replay on top
    /// of it (see `gaia-engine`: there's no `apply_event`-style function to
    /// replay a `GameEvent` back onto a `GameState`; events are an output log,
    /// not a re-playable input).
    pub async fn reconstruct_state(
        state: &AppState,
        room_code: &str,
    ) -> ServerResult<Option<GameState>> {
        let repo = GameRepository::new(state.db.clone());
        let latest = repo.load_latest_snapshot(room_code).await?;
        Ok(latest.map(|(_revision, game_state)| game_state))
    }

    /// Validate session token and return (player_id, room_code).
    pub async fn validate_session(state: &AppState, token: &str) -> ServerResult<(u8, String)> {
        state
            .sessions
            .validate(token)
            .await?
            .ok_or(ServerError::InvalidSession)
    }
}
