use sha2::{Digest, Sha256};
use sqlx::PgPool;

use gaia_engine::game_state::PlayerId;

use crate::error::ServerResult;

/// Persists session tokens hashed at rest (PRD FR-1): the plaintext token is
/// returned to the caller once and never stored or logged, only its SHA-256
/// hex digest is. Backed by the `sessions` table rather than an in-memory map
/// so tokens survive a server restart.
pub struct SessionManager {
    pool: PgPool,
}

impl SessionManager {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Creates a new session token for the player and returns the plaintext token.
    pub async fn create_session(
        &self,
        player_id: PlayerId,
        room_code: &str,
    ) -> ServerResult<String> {
        let token = uuid::Uuid::new_v4().to_string();
        let token_hash = hash_token(&token);
        sqlx::query(
            "INSERT INTO sessions (token_hash, room_code, player_id) VALUES ($1, $2, $3)
             ON CONFLICT (token_hash) DO NOTHING",
        )
        .bind(&token_hash)
        .bind(room_code)
        .bind(player_id as i16)
        .execute(&self.pool)
        .await?;
        Ok(token)
    }

    /// Returns `(player_id, room_code)` if the token is valid, touching
    /// `last_seen_at` as a side effect.
    pub async fn validate(&self, token: &str) -> ServerResult<Option<(PlayerId, String)>> {
        let token_hash = hash_token(token);
        let row: Option<(i16, String)> = sqlx::query_as(
            "UPDATE sessions SET last_seen_at = NOW() WHERE token_hash = $1
             RETURNING player_id, room_code",
        )
        .bind(&token_hash)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(|(player_id, room_code)| (player_id as PlayerId, room_code)))
    }

    pub async fn remove(&self, token: &str) -> ServerResult<()> {
        let token_hash = hash_token(token);
        sqlx::query("DELETE FROM sessions WHERE token_hash = $1")
            .bind(&token_hash)
            .execute(&self.pool)
            .await?;
        Ok(())
    }
}

fn hash_token(token: &str) -> String {
    let digest = Sha256::digest(token.as_bytes());
    digest.iter().map(|byte| format!("{byte:02x}")).collect()
}
