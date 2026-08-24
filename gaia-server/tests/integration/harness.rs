/// Shared test harness for `gaia-server` integration tests that need a real
/// `TestServer` backed by a live, migrated Postgres pool — the same app the
/// production binary builds in `main.rs`.
///
/// Extracted out of `faction_selection_flow.rs` so other integration test
/// files (e.g. `room_lifecycle.rs`) can drive the real app instead of
/// hand-rolling their own stub.
use std::time::Duration;

use axum_test::{TestServer, TestServerConfig, TestWebSocket};
use serde_json::{json, Value};
use sqlx::PgPool;

use gaia_server::protocol::SCHEMA_HASH;

/// Builds a `TestServer` around the real `gaia_server::router::build_router`
/// app — a live Postgres pool (migrated) plus the real in-memory room/session
/// state, exactly as `main.rs` builds it for production. `http_transport()`
/// is required: axum-test's default mock transport doesn't support HTTP
/// protocol upgrades, so WebSocket routes need a real bound port.
///
/// Also loads `gaia-server/.env` (via `dotenvy`) as a side effect, so
/// `DATABASE_URL` is available in the process environment afterwards for
/// anything else that needs it (e.g. [`RoomCleanupGuard`]).
pub async fn spawn_test_app() -> TestServer {
    let _ = dotenvy::from_path(concat!(env!("CARGO_MANIFEST_DIR"), "/.env"));
    let database_url = std::env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set (see gaia-server/.env / docker-compose.dev.yml)");

    let pool = PgPool::connect(&database_url).await.expect(
        "failed to connect to PostgreSQL — is `docker compose -f docker-compose.dev.yml up -d postgres` running?",
    );

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("failed to run database migrations");

    let app_state = gaia_server::state::AppState::new(pool);
    let app = gaia_server::router::build_router(app_state);

    TestServerConfig::builder()
        .http_transport()
        .build_server(app)
        .expect("failed to start axum-test server")
}

// ── Enveloped WS command helpers ─────────────────────────────────────────────
//
// Shared by every test that drives the gaia-protocol envelope wire format
// (`command`/`command_accepted`/`command_rejected`/`snapshot`) over a real
// WebSocket connection.

/// Deterministic, human-readable command_id generator for tests that send
/// several commands in sequence and don't need real randomness. `prefix`
/// scopes the sequence (e.g. per test, or per helper function) so two
/// generators sharing a room don't collide on the same command_id — a
/// collision replays the *first* command's recorded outcome instead of
/// applying the second one, per `coordinator::apply_command`'s idempotency
/// contract.
pub fn next_command_id(prefix: &str, counter: &mut u32) -> String {
    *counter += 1;
    format!("{prefix}-{counter}")
}

/// Builds the wire JSON for one enveloped command.
pub fn command_msg(room_code: &str, command_id: &str, revision: u64, command: Value) -> Value {
    json!({
        "type": "command",
        "protocol_version": 1,
        "schema_hash": SCHEMA_HASH.to_string(),
        "room_id": room_code,
        "command_id": command_id,
        "expected_revision": revision,
        "command": command,
    })
}

/// Reads JSON messages off `ws` until one with `"type" == expected_type` is
/// found, skipping any others (lobby/player-joined chatter, or another
/// player's broadcast, unrelated to the step currently being driven).
pub async fn receive_until(ws: &mut TestWebSocket, expected_type: &str) -> Value {
    for _ in 0..40 {
        let msg = tokio::time::timeout(Duration::from_secs(5), ws.receive_json::<Value>())
            .await
            .unwrap_or_else(|_| panic!("timed out waiting for a `{expected_type}` message"));
        if msg["type"] == expected_type {
            return msg;
        }
    }
    panic!("did not receive a `{expected_type}` message within 40 messages");
}

/// Like `receive_until`, but for `snapshot` messages specifically, matching
/// on `revision` rather than just `type` — a connection that hasn't sent a
/// command itself since some point may have several earlier snapshot
/// broadcasts (from other players' commands) queued ahead of the one it's
/// actually looking for.
pub async fn receive_until_revision(ws: &mut TestWebSocket, expected_revision: u64) -> Value {
    for _ in 0..40 {
        let msg = tokio::time::timeout(Duration::from_secs(5), ws.receive_json::<Value>())
            .await
            .unwrap_or_else(|_| {
                panic!("timed out waiting for a snapshot at revision {expected_revision}")
            });
        if msg["type"] == "snapshot" && msg["revision"].as_u64() == Some(expected_revision) {
            return msg;
        }
    }
    panic!("did not receive a snapshot at revision {expected_revision} within 40 messages");
}

/// Sends `command` on `ws` at `revision` with a fresh command_id, awaits
/// `command_accepted` on the same connection, and returns the new revision.
pub async fn send_command_and_await_accept(
    ws: &mut TestWebSocket,
    room_code: &str,
    command_id: &str,
    revision: u64,
    command: Value,
) -> u64 {
    ws.send_json(&command_msg(room_code, command_id, revision, command))
        .await;
    let accepted = receive_until(ws, "command_accepted").await;
    assert_eq!(
        accepted["command_id"], command_id,
        "command_accepted should echo back the command_id it acknowledges"
    );
    accepted["revision"]
        .as_u64()
        .expect("command_accepted should carry the new revision")
}

/// RAII guard that deletes a room row (and, via `ON DELETE CASCADE` on
/// `game_snapshots`/`game_events`, all of its dependent rows) from the
/// database when dropped — including when the test panics or an assertion
/// fails partway through, since `Drop::drop` still runs during unwinding.
///
/// Without this, every integration test run leaves a `rooms` row behind
/// permanently on a shared dev database (reviewer measured `rooms` growing
/// from 8 -> 9 after a single run of `faction_selection_flow.rs`).
///
/// Deliberately opens its own single, dedicated `PgConnection` for the
/// delete rather than reusing the app's shared `PgPool`: at the point this
/// guard drops, the `TestServer` (and its live WS connections, event bus,
/// etc.) is typically still alive and holding pool connections checked out,
/// so acquiring from that same pool here raced with the app and hit sqlx's
/// 30s "pool timed out while waiting for an open connection" error in
/// practice. A standalone connection sidesteps that contention entirely.
///
/// Cleanup runs on a dedicated OS thread with its own minimal Tokio runtime
/// rather than calling `block_on` directly in `drop`: `drop` can run while
/// already inside a `#[tokio::test]`'s (single-threaded) runtime — e.g.
/// during panic unwinding — where nesting another `block_on` on the same
/// thread would itself panic ("Cannot start a runtime from within a
/// runtime"). A separate thread sidesteps that entirely.
pub struct RoomCleanupGuard {
    room_code: String,
}

impl RoomCleanupGuard {
    pub fn new(room_code: impl Into<String>) -> Self {
        Self {
            room_code: room_code.into(),
        }
    }
}

impl Drop for RoomCleanupGuard {
    fn drop(&mut self) {
        let room_code = self.room_code.clone();

        let cleanup = std::thread::spawn(move || {
            let rt = tokio::runtime::Builder::new_current_thread()
                .enable_all()
                .build()
                .expect("RoomCleanupGuard: failed to build cleanup runtime");
            rt.block_on(async move {
                let database_url = std::env::var("DATABASE_URL")
                    .expect("RoomCleanupGuard: DATABASE_URL must be set for cleanup");
                let mut conn = <sqlx::PgConnection as sqlx::Connection>::connect(&database_url)
                    .await
                    .map_err(|e| format!("connect failed: {e}"))?;
                sqlx::query("DELETE FROM rooms WHERE code = $1")
                    .bind(&room_code)
                    .execute(&mut conn)
                    .await
                    .map_err(|e| format!("delete failed: {e}"))
            })
        })
        .join();

        match cleanup {
            Ok(Ok(_)) => {}
            Ok(Err(e)) => eprintln!("RoomCleanupGuard: failed to delete room row: {e}"),
            Err(_) => eprintln!("RoomCleanupGuard: cleanup thread panicked"),
        }
    }
}
