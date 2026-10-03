//! Live AI seats backed by a pool of Python teacher workers (`gaia-rl/tools/ai_worker.py`).
//!
//! Enabled only when `GAIA_AI_DIR` points at a `gaia-rl` checkout with a built environment.
//! A room is always routed to the same worker so the teacher's plan memory survives between
//! that room's decisions. Workers run one decision at a time; the pool size bounds CPU use.
//!
//! AI moves never run inside a room lock: the driver reads the state, asks a worker, then
//! applies the reply through `coordinator::apply_server_transition` only if the room has not
//! moved on meanwhile. A failed or slow worker falls back to the DEV bots' simple legal move.
use std::collections::HashSet;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use gaia_engine::{
    error::RuleError,
    game_state::{GamePhase, PlayerId, SetupPhase},
    rules::engine::AiDecision,
    GameState, RuleEngine,
};
use serde::Deserialize;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use tokio::sync::Mutex;

use crate::{
    coordinator::{self, CommandError},
    room::manager::RoomState,
    services::{
        dev_game::{fallback_step, required_player},
        game_action::apply_logged_action,
        turn_management::TurnManagementService,
    },
    state::AppState,
};

/// Difficulties `tools/ai_worker.py` accepts.
pub const LEVELS: [&str; 3] = ["easy", "normal", "hard"];

#[derive(Debug, Clone)]
pub struct AiConfig {
    pub dir: PathBuf,
    pub python: PathBuf,
    pub workers: usize,
    pub level: String,
    pub timeout: Duration,
}

impl AiConfig {
    /// `GAIA_AI_DIR` (required), `GAIA_AI_PYTHON` (default `<dir>/.venv/bin/python`),
    /// `GAIA_AI_WORKERS` (default 6), `GAIA_AI_LEVEL` (`normal` or `easy`),
    /// `GAIA_AI_TIMEOUT_SECS` (default 30, a hung-worker guard; the teacher caps itself at 5 s).
    pub fn from_env() -> Option<Self> {
        let dir = PathBuf::from(
            std::env::var("GAIA_AI_DIR")
                .ok()
                .filter(|dir| !dir.trim().is_empty())?,
        );
        let python = std::env::var("GAIA_AI_PYTHON")
            .map(PathBuf::from)
            .unwrap_or_else(|_| dir.join(".venv/bin/python"));
        let workers = std::env::var("GAIA_AI_WORKERS")
            .ok()
            .and_then(|value| value.parse().ok())
            .filter(|count: &usize| *count > 0)
            .unwrap_or(6);
        let level = std::env::var("GAIA_AI_LEVEL").unwrap_or_else(|_| "normal".to_string());
        let timeout = std::env::var("GAIA_AI_TIMEOUT_SECS")
            .ok()
            .and_then(|value| value.parse().ok())
            .map(Duration::from_secs)
            .unwrap_or(Duration::from_secs(30));
        Some(Self {
            dir,
            python,
            workers,
            level,
            timeout,
        })
    }
}

struct Worker {
    _child: Child,
    stdin: ChildStdin,
    stdout: BufReader<ChildStdout>,
}

#[derive(Deserialize)]
struct Reply {
    ok: bool,
    decision: Option<AiDecision>,
    error: Option<String>,
}

pub struct AiPool {
    config: AiConfig,
    workers: Vec<Mutex<Option<Worker>>>,
    driving: std::sync::Mutex<HashSet<String>>,
    /// Committed AI moves and how many of them used the DEV fallback instead of the teacher.
    moves: AtomicUsize,
    fallbacks: AtomicUsize,
}

impl AiPool {
    pub fn new(config: AiConfig) -> Self {
        let workers = (0..config.workers).map(|_| Mutex::new(None)).collect();
        Self {
            config,
            workers,
            driving: std::sync::Mutex::new(HashSet::new()),
            moves: AtomicUsize::new(0),
            fallbacks: AtomicUsize::new(0),
        }
    }

    /// (committed AI moves, of which fallback moves) since the pool started.
    pub fn move_counts(&self) -> (usize, usize) {
        (
            self.moves.load(Ordering::Relaxed),
            self.fallbacks.load(Ordering::Relaxed),
        )
    }

    fn spawn_worker(&self) -> std::io::Result<Worker> {
        let pythonpath = ["python", "baseline-teacher-20260917", "tools"]
            .iter()
            .map(|part| self.config.dir.join(part).display().to_string())
            .collect::<Vec<_>>()
            .join(":");
        let mut child = Command::new(&self.config.python)
            .arg(self.config.dir.join("tools/ai_worker.py"))
            .current_dir(&self.config.dir)
            .env("PYTHONPATH", pythonpath)
            .env("GAIA_ENGINE_FIXES_2", "1")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .kill_on_drop(true)
            .spawn()?;
        let stdin = child
            .stdin
            .take()
            .ok_or_else(|| std::io::Error::other("no worker stdin"))?;
        let stdout = child
            .stdout
            .take()
            .ok_or_else(|| std::io::Error::other("no worker stdout"))?;
        Ok(Worker {
            _child: child,
            stdin,
            stdout: BufReader::new(stdout),
        })
    }

    fn slot(&self, room_code: &str) -> usize {
        let hash = room_code.bytes().fold(0xcbf2_9ce4_8422_2325_u64, |h, b| {
            (h ^ u64::from(b)).wrapping_mul(0x0100_0000_01b3)
        });
        (hash % self.workers.len() as u64) as usize
    }

    /// The teacher's move for `player`, or `None` when the worker is unavailable, errs or
    /// exceeds the timeout (the worker is then restarted on the next request).
    pub async fn choose(
        &self,
        room_code: &str,
        state: &GameState,
        player: PlayerId,
        level: Option<&str>,
    ) -> Option<AiDecision> {
        let mut guard = self.workers[self.slot(room_code)].lock().await;
        if guard.is_none() {
            match self.spawn_worker() {
                Ok(worker) => *guard = Some(worker),
                Err(error) => {
                    log::error!("AI worker failed to start: {error}");
                    return None;
                }
            }
        }
        let worker = guard.as_mut()?;
        let request = serde_json::json!({
            "op": "choose", "room": room_code, "player": player,
            "level": level.unwrap_or(&self.config.level), "state": state,
        });
        let exchange = async {
            let mut line = serde_json::to_string(&request).map_err(std::io::Error::other)?;
            line.push('\n');
            worker.stdin.write_all(line.as_bytes()).await?;
            worker.stdin.flush().await?;
            let mut response = String::new();
            if worker.stdout.read_line(&mut response).await? == 0 {
                return Err(std::io::Error::other("AI worker exited"));
            }
            serde_json::from_str::<Reply>(&response).map_err(std::io::Error::other)
        };
        match tokio::time::timeout(self.config.timeout, exchange).await {
            Ok(Ok(Reply {
                ok: true,
                decision: Some(decision),
                ..
            })) => Some(decision),
            Ok(Ok(reply)) => {
                log::warn!(
                    "AI worker declined room {room_code}: {}",
                    reply.error.unwrap_or_default()
                );
                None
            }
            Ok(Err(error)) => {
                log::error!("AI worker failed for room {room_code}: {error}; restarting it");
                *guard = None;
                None
            }
            Err(_) => {
                log::error!("AI worker timed out for room {room_code}; restarting it");
                *guard = None;
                None
            }
        }
    }

    fn try_start_driving(&self, room_code: &str) -> bool {
        self.driving
            .lock()
            .map(|mut rooms| rooms.insert(room_code.to_string()))
            .unwrap_or(false)
    }

    fn stop_driving(&self, room_code: &str) {
        if let Ok(mut rooms) = self.driving.lock() {
            rooms.remove(room_code);
        }
    }
}

/// Plays AI seats of `room_code` until the human must act. Safe to call after every
/// committed transition; at most one driver runs per room.
pub fn spawn_driver(app: AppState, room_code: String) {
    let Some(pool) = app.ai.clone() else {
        return;
    };
    if !pool.try_start_driving(&room_code) {
        return;
    }
    tokio::spawn(async move {
        drive(&app, &pool, &room_code).await;
        pool.stop_driving(&room_code);
    });
}

struct Turn {
    revision: u64,
    player: PlayerId,
    human: PlayerId,
    state: GameState,
    level: Option<String>,
}

async fn next_ai_turn(app: &AppState, room_code: &str) -> Option<Turn> {
    let rooms = app.rooms.read().await;
    let room = rooms.get_room(room_code)?;
    let human = room.dev_human_player?;
    if room.paused {
        return None;
    }
    let state = room.game_state.as_ref()?;
    if state.dev_controller.is_some() || matches!(state.phase, GamePhase::Ended { .. }) {
        return None;
    }
    let player = required_player(state)?;
    if player == human || state.undo_state.pending_request.is_some() {
        return None;
    }
    Some(Turn {
        revision: room.revision,
        player,
        human,
        state: state.clone(),
        level: room.ai_level.clone(),
    })
}

async fn drive(app: &AppState, pool: &Arc<AiPool>, room_code: &str) {
    // A full game has a few hundred decisions; this only guards against a logic loop.
    let mut rejected_in_a_row = 0;
    for _ in 0..2000 {
        let Some(turn) = next_ai_turn(app, room_code).await else {
            return;
        };
        let decision = pool
            .choose(room_code, &turn.state, turn.player, turn.level.as_deref())
            .await;
        let mut used_fallback = false;
        let applied = coordinator::apply_server_transition(app, room_code, |room| {
            if room.revision != turn.revision {
                return Err(RuleError::ActionNotAllowed(
                    "room moved on during AI thinking".into(),
                ));
            }
            let state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
            if required_player(state) != Some(turn.player) {
                return Err(RuleError::NotYourTurn);
            }
            let mut probe = state.clone();
            let (events, fallback) = match apply_decision(&mut probe, turn.player, decision.clone())
            {
                Ok(events) => {
                    *state = probe;
                    (events, false)
                }
                Err(error) => {
                    log::warn!("AI move rejected in room {room_code} ({error}); using fallback");
                    (fallback_step(state, turn.player, turn.human)?, true)
                }
            };
            used_fallback = fallback;
            state.event_log.extend(events);
            if state.phase == GamePhase::Setup(SetupPhase::Complete) {
                room.state = RoomState::InGame;
                let state = room.game_state.as_mut().ok_or(RuleError::WrongPhase)?;
                let events = RuleEngine::start_first_round(state)?;
                state.event_log.extend(events);
            }
            Ok(())
        })
        .await;
        match applied {
            Ok(outcome) => {
                rejected_in_a_row = 0;
                pool.moves.fetch_add(1, Ordering::Relaxed);
                if used_fallback {
                    pool.fallbacks.fetch_add(1, Ordering::Relaxed);
                }
                coordinator::broadcast_snapshot(app, room_code, outcome.revision).await;
                if let Err(error) = TurnManagementService::maybe_end_round(app, room_code).await {
                    log::error!("maybe_end_round failed for room {room_code}: {error}");
                    return;
                }
            }
            // The human or another transition changed the room first: re-read and continue.
            // Repeated rejections of an unchanged room mean even the fallback cannot move.
            Err(CommandError::Rule(_)) | Err(CommandError::RevisionConflict { .. }) => {
                rejected_in_a_row += 1;
                if rejected_in_a_row >= 3 {
                    log::error!("AI seat in room {room_code} cannot move; stopping the driver");
                    return;
                }
            }
            Err(error) => {
                log::error!("AI move could not be committed in room {room_code}: {error}");
                return;
            }
        }
    }
}

fn apply_decision(
    state: &mut GameState,
    player: PlayerId,
    decision: Option<AiDecision>,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, RuleError> {
    match decision {
        Some(AiDecision::Game(action)) => apply_logged_action(state, player, action),
        Some(AiDecision::Setup(action)) => RuleEngine::apply_setup_action(state, player, action),
        None => Err(RuleError::ActionNotAllowed("no AI decision".into())),
    }
}
