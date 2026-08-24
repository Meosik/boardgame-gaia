use sqlx::PgPool;

use gaia_engine::{
    game_state::{GameEvent, PlayerId},
    GameSetup, GameState,
};

use crate::error::{ServerError, ServerResult};

pub struct GameRepository {
    pool: PgPool,
}

impl GameRepository {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    // ── Rooms ─────────────────────────────────────────────────────────────────

    pub async fn save_room(
        &self,
        code: &str,
        seed: &str,
        host_player: PlayerId,
        setup: &GameSetup,
    ) -> ServerResult<()> {
        sqlx::query(
            "INSERT INTO rooms (code, seed, host_player, setup) VALUES ($1, $2, $3, $4)
             ON CONFLICT (code) DO NOTHING",
        )
        .bind(code)
        .bind(seed)
        .bind(host_player as i16)
        .bind(serde_json::to_value(setup)?)
        .execute(&self.pool)
        .await?;
        Ok(())
    }

    /// Loads a room's durable row — `(host_player, state, seed, revision,
    /// setup)` — for rehydration after a restart. `None` if the room
    /// genuinely doesn't exist (never created, or its row was cleaned up).
    pub async fn load_room_row(
        &self,
        code: &str,
    ) -> ServerResult<Option<(PlayerId, String, String, i64, serde_json::Value)>> {
        let row: Option<(i16, String, String, i64, serde_json::Value)> = sqlx::query_as(
            "SELECT host_player, state, seed, revision, setup FROM rooms WHERE code = $1",
        )
        .bind(code)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(|(host, state, seed, revision, setup)| {
            (host as PlayerId, state, seed, revision, setup)
        }))
    }

    // ── Snapshots ─────────────────────────────────────────────────────────────

    /// Loads the most recent snapshot (by revision) for a room, if any —
    /// the sole recovery mechanism (see `commit_command`'s doc comment: every
    /// committed revision gets a full snapshot, so recovery never needs event
    /// replay). Returns the snapshot's revision alongside the deserialized state.
    pub async fn load_latest_snapshot(
        &self,
        room_code: &str,
    ) -> ServerResult<Option<(i64, GameState)>> {
        let row: Option<(i64, serde_json::Value)> = sqlx::query_as(
            "SELECT revision, snapshot FROM game_snapshots
             WHERE room_code = $1
             ORDER BY revision DESC
             LIMIT 1",
        )
        .bind(room_code)
        .fetch_optional(&self.pool)
        .await?;

        match row {
            None => Ok(None),
            Some((revision, json)) => {
                let state = GameState::deserialize(json)
                    .map_err(|e| ServerError::Internal(e.to_string()))?;
                Ok(Some((revision, state)))
            }
        }
    }

    // ── Events ────────────────────────────────────────────────────────────────

    pub async fn load_events_since(
        &self,
        room_code: &str,
        after_snapshot_id: i64,
    ) -> ServerResult<Vec<GameEvent>> {
        let rows: Vec<(serde_json::Value,)> = sqlx::query_as(
            "SELECT payload FROM game_events
             WHERE room_code = $1 AND id > $2
             ORDER BY id",
        )
        .bind(room_code)
        .bind(after_snapshot_id)
        .fetch_all(&self.pool)
        .await?;

        let mut events = Vec::with_capacity(rows.len());
        for (payload,) in rows {
            let event: GameEvent = serde_json::from_value(payload)
                .map_err(|e| ServerError::Internal(e.to_string()))?;
            events.push(event);
        }
        Ok(events)
    }

    // ── Atomic command commit ────────────────────────────────────────────────

    /// Looks up a previously-processed command by `(room_code, command_id)` for
    /// idempotent replay — the coordinator returns this stored result directly
    /// instead of re-running the mutation.
    pub async fn find_processed_command(
        &self,
        room_code: &str,
        command_id: &str,
    ) -> ServerResult<Option<serde_json::Value>> {
        let row: Option<(serde_json::Value,)> = sqlx::query_as(
            "SELECT result FROM processed_commands WHERE room_code = $1 AND command_id = $2",
        )
        .bind(room_code)
        .bind(command_id)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(|(result,)| result))
    }

    /// Atomically advances a room's revision and persists the resulting state:
    /// compare-and-swap `rooms.revision`, insert the new snapshot, insert each
    /// event, and record the command's result for idempotent replay — all in
    /// one transaction. Returns the new revision, or `None` if `expected_revision`
    /// was stale (the CAS matched zero rows; nothing was written).
    #[allow(clippy::too_many_arguments)]
    pub async fn commit_command(
        &self,
        room_code: &str,
        expected_revision: i64,
        round: u8,
        state: &GameState,
        events: &[GameEvent],
        player_id: Option<PlayerId>,
        command_id: &str,
        result: &serde_json::Value,
        room_state: &str,
        setup: &serde_json::Value,
    ) -> ServerResult<Option<i64>> {
        let new_revision = expected_revision + 1;
        let mut tx = self.pool.begin().await?;

        let updated = sqlx::query(
            "UPDATE rooms SET revision = $1, state = $4, setup = $5, updated_at = NOW()
             WHERE code = $2 AND revision = $3",
        )
        .bind(new_revision)
        .bind(room_code)
        .bind(expected_revision)
        .bind(room_state)
        .bind(setup)
        .execute(&mut *tx)
        .await?;

        if updated.rows_affected() == 0 {
            tx.rollback().await?;
            return Ok(None);
        }

        sqlx::query(
            "INSERT INTO game_snapshots (room_code, round, revision, snapshot) VALUES ($1, $2, $3, $4)",
        )
        .bind(room_code)
        .bind(round as i16)
        .bind(new_revision)
        .bind(state.serialize())
        .execute(&mut *tx)
        .await?;

        for event in events {
            let event_type = format!("{:?}", std::mem::discriminant(event));
            let payload = serde_json::to_value(event)?;
            sqlx::query(
                "INSERT INTO game_events (room_code, round, revision, player_id, event_type, payload)
                 VALUES ($1, $2, $3, $4, $5, $6)",
            )
            .bind(room_code)
            .bind(round as i16)
            .bind(new_revision)
            .bind(player_id.map(|p| p as i16))
            .bind(&event_type)
            .bind(payload)
            .execute(&mut *tx)
            .await?;
        }

        sqlx::query(
            "INSERT INTO processed_commands (room_code, command_id, revision, result)
             VALUES ($1, $2, $3, $4)
             ON CONFLICT (room_code, command_id) DO NOTHING",
        )
        .bind(room_code)
        .bind(command_id)
        .bind(new_revision)
        .bind(result)
        .execute(&mut *tx)
        .await?;

        tx.commit().await?;
        Ok(Some(new_revision))
    }

    /// Same as `commit_command` but for commands issued before a `GameState`
    /// exists yet (lobby-phase: `PlayerReady`, `RegenerateSetup`) — CAS the
    /// revision and record the command's result, with no snapshot/events to
    /// write since there is no game state to persist.
    pub async fn commit_lobby_command(
        &self,
        room_code: &str,
        expected_revision: i64,
        command_id: &str,
        result: &serde_json::Value,
        room_state: &str,
        setup: &serde_json::Value,
    ) -> ServerResult<Option<i64>> {
        let new_revision = expected_revision + 1;
        let mut tx = self.pool.begin().await?;

        let updated = sqlx::query(
            "UPDATE rooms SET revision = $1, state = $4, setup = $5, updated_at = NOW()
             WHERE code = $2 AND revision = $3",
        )
        .bind(new_revision)
        .bind(room_code)
        .bind(expected_revision)
        .bind(room_state)
        .bind(setup)
        .execute(&mut *tx)
        .await?;

        if updated.rows_affected() == 0 {
            tx.rollback().await?;
            return Ok(None);
        }

        sqlx::query(
            "INSERT INTO processed_commands (room_code, command_id, revision, result)
             VALUES ($1, $2, $3, $4)
             ON CONFLICT (room_code, command_id) DO NOTHING",
        )
        .bind(room_code)
        .bind(command_id)
        .bind(new_revision)
        .bind(result)
        .execute(&mut *tx)
        .await?;

        tx.commit().await?;
        Ok(Some(new_revision))
    }

    /// Same as `commit_command` but for server-initiated transitions with no
    /// client command behind them (round advance, game end) — CAS the
    /// revision, insert the new snapshot, update `rooms.state`. No events or
    /// `processed_commands` row, since there's no `command_id` to dedupe.
    pub async fn commit_server_transition(
        &self,
        room_code: &str,
        expected_revision: i64,
        round: u8,
        state: &GameState,
        room_state: &str,
        setup: &serde_json::Value,
    ) -> ServerResult<Option<i64>> {
        let new_revision = expected_revision + 1;
        let mut tx = self.pool.begin().await?;

        let updated = sqlx::query(
            "UPDATE rooms SET revision = $1, state = $4, setup = $5, updated_at = NOW()
             WHERE code = $2 AND revision = $3",
        )
        .bind(new_revision)
        .bind(room_code)
        .bind(expected_revision)
        .bind(room_state)
        .bind(setup)
        .execute(&mut *tx)
        .await?;

        if updated.rows_affected() == 0 {
            tx.rollback().await?;
            return Ok(None);
        }

        sqlx::query(
            "INSERT INTO game_snapshots (room_code, round, revision, snapshot) VALUES ($1, $2, $3, $4)",
        )
        .bind(room_code)
        .bind(round as i16)
        .bind(new_revision)
        .bind(state.serialize())
        .execute(&mut *tx)
        .await?;

        tx.commit().await?;
        Ok(Some(new_revision))
    }

    /// Records a rejected command outcome (e.g. a validation error) without
    /// touching the room's revision or state — still keyed by `command_id` so
    /// a retried rejected command replays the same rejection.
    pub async fn record_rejected_command(
        &self,
        room_code: &str,
        command_id: &str,
        revision: i64,
        result: &serde_json::Value,
    ) -> ServerResult<()> {
        sqlx::query(
            "INSERT INTO processed_commands (room_code, command_id, revision, result)
             VALUES ($1, $2, $3, $4)
             ON CONFLICT (room_code, command_id) DO NOTHING",
        )
        .bind(room_code)
        .bind(command_id)
        .bind(revision)
        .bind(result)
        .execute(&self.pool)
        .await?;
        Ok(())
    }

    pub async fn save_final_scores(
        &self,
        room_code: &str,
        scores: &[(PlayerId, i32)],
    ) -> ServerResult<()> {
        let payload = serde_json::to_value(scores)?;
        sqlx::query(
            "INSERT INTO game_events (room_code, round, event_type, payload)
             VALUES ($1, 7, 'FinalScores', $2)",
        )
        .bind(room_code)
        .bind(payload)
        .execute(&self.pool)
        .await?;
        Ok(())
    }
}
