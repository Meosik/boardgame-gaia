//! Live AI seats backed by a pool of Python teacher workers (`gaia-rl/tools/ai_worker.py`).
//!
//! Enabled only when `GAIA_AI_DIR` points at a `gaia-rl` checkout with a built environment.
//! A room is always routed to the same worker so the teacher's plan memory survives between
//! that room's decisions. Workers run one decision at a time; the pool size bounds CPU use.
//!
//! AI moves never run inside a room lock: the driver reads the state, asks a worker, then
//! applies the reply through `coordinator::apply_server_transition` only if the room has not
//! moved on meanwhile. When the teacher gives no usable move (the worker failed, timed out or
//! declined, or the engine refused its move) it is asked once more; after that nothing is
//! played for the seat: the room's AI seats stop (`Room::ai_stalled`, shown on the game
//! screen) until the player asks for another try (`retry`). No other bot ever moves an AI
//! seat, so every AI move of such a game is the teacher's.
//!
//! Teacher versions (optional, `GAIA_AI_TEACHERS_DIR`): a folder outside the image holding one
//! sub-folder per promoted teacher (`tools/teacher_version.py`), each mirroring the repository
//! layout (`<version>/gaia-rl/tools/ai_worker.py`, ...) plus `<version>/teacher.json`, and a
//! one-line file `current` naming the version for new rooms. A room is pinned to the version
//! that was current when it was created and keeps that version's worker until it ends, so a
//! promotion never changes a running game. Without the folder, without `current`, or when the
//! named version does not start, rooms use the teacher built into the image (`GAIA_AI_DIR`).
//! A version carries only Python and data: it runs on the image's native engine module, so a
//! change to the engine still needs a deploy. Each version records the fingerprint of the
//! engine sources it was made from and the image records its own (`engine-fingerprint` in
//! `GAIA_AI_DIR`); the server runs a version only while the two are equal, so a version left
//! as `current` across an engine deploy falls back to the image teacher by itself.
use std::collections::{HashMap, HashSet};
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
use tokio::sync::{watch, Mutex};

use crate::{
    coordinator::{self, CommandError},
    room::manager::{AiStall, AiStallReason, Room, RoomState},
    services::{
        dev_game::required_player,
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
    /// Minimum time between two AI moves of one room (`GAIA_AI_MOVE_PAUSE_MS`, default 1500),
    /// so a human can follow what the AI seats did. 0 = no pause.
    pub move_pause: Duration,
    /// Folder of promoted teacher versions (`GAIA_AI_TEACHERS_DIR`); `None` = image teacher only.
    pub teachers: Option<PathBuf>,
    /// Hash of the engine sources this image's native module was built from
    /// (`<GAIA_AI_DIR>/engine-fingerprint`, written by `tools/engine_fingerprint.py` during the
    /// image build). A teacher version runs only when its `teacher.json` names the same hash.
    pub engine_fingerprint: Option<String>,
}

impl AiConfig {
    /// `GAIA_AI_DIR` (required), `GAIA_AI_PYTHON` (default `<dir>/.venv/bin/python`),
    /// `GAIA_AI_WORKERS` (default 6), `GAIA_AI_LEVEL` (`normal` or `easy`),
    /// `GAIA_AI_TIMEOUT_SECS` (default 30, a hung-worker guard; the teacher caps itself at 5 s;
    /// the "hard" level gets at least 60 s, see `guard_timeout`),
    /// `GAIA_AI_MOVE_PAUSE_MS` (default 1500, minimum time between two AI moves of a room),
    /// `GAIA_AI_TEACHERS_DIR` (optional, see the module comment).
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
        let teachers = std::env::var("GAIA_AI_TEACHERS_DIR")
            .ok()
            .filter(|dir| !dir.trim().is_empty())
            .map(PathBuf::from);
        let engine_fingerprint = std::fs::read_to_string(dir.join("engine-fingerprint"))
            .ok()
            .map(|text| text.trim().to_string())
            .filter(|text| !text.is_empty());
        Some(Self {
            dir,
            python,
            workers,
            level,
            timeout,
            move_pause: move_pause_from(std::env::var("GAIA_AI_MOVE_PAUSE_MS").ok().as_deref()),
            teachers,
            engine_fingerprint,
        })
    }
}

/// A version name is one plain folder name, so it can never point outside the versions folder.
fn valid_version(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with('.')
        && name
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-'))
}

/// `<version>/teacher.json`, written by `tools/teacher_version.py`.
#[derive(Deserialize, Default)]
struct TeacherMeta {
    /// The `teacher_patches` factory; absent = the default of that version's `ai_worker.py`.
    factory: Option<String>,
    /// `tools/engine_fingerprint.py` of the commit the version was made from.
    engine_fingerprint: Option<String>,
}

/// The `teacher.json` beside a version's `gaia-rl` folder; missing or unreadable = empty.
fn teacher_meta(version_gaia_rl: &std::path::Path) -> TeacherMeta {
    std::fs::read_to_string(version_gaia_rl.with_file_name("teacher.json"))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_default()
}

/// How long a version's worker may take to import the teacher and answer its first ping.
const VERSION_START_TIMEOUT: Duration = Duration::from_secs(60);
/// Workers of this many teacher versions may stay alive in one pool slot; the least recently
/// used one is stopped first (its rooms' plan memory is rebuilt if they move again).
const VERSIONS_PER_SLOT: usize = 3;

/// The hung-worker guard for one request. "hard" caps itself at 20 s, but a comparison already
/// running at the cap finishes first (cycle 025: max 33 s on a laptop), so it gets at least 60 s.
fn guard_timeout(configured: Duration, level: &str) -> Duration {
    if level == "hard" {
        configured.max(Duration::from_secs(60))
    } else {
        configured
    }
}

const DEFAULT_MOVE_PAUSE: Duration = Duration::from_millis(1500);

/// `GAIA_AI_MOVE_PAUSE_MS` parsed; missing or unparsable = the default.
fn move_pause_from(value: Option<&str>) -> Duration {
    value
        .and_then(|value| value.trim().parse::<u64>().ok())
        .map(Duration::from_millis)
        .unwrap_or(DEFAULT_MOVE_PAUSE)
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

/// One request line to a worker and its one reply line.
async fn exchange(worker: &mut Worker, request: &serde_json::Value) -> std::io::Result<Reply> {
    let mut line = serde_json::to_string(request).map_err(std::io::Error::other)?;
    line.push('\n');
    worker.stdin.write_all(line.as_bytes()).await?;
    worker.stdin.flush().await?;
    let mut response = String::new();
    if worker.stdout.read_line(&mut response).await? == 0 {
        return Err(std::io::Error::other("AI worker exited"));
    }
    serde_json::from_str::<Reply>(&response).map_err(std::io::Error::other)
}

pub struct AiPool {
    config: AiConfig,
    /// Per slot: the live workers by teacher version (`None` = the image teacher), most
    /// recently used last. The slot lock is held for a whole decision, so the number of slots
    /// still bounds CPU use however many versions are alive.
    workers: Vec<Mutex<Vec<(Option<String>, Worker)>>>,
    /// Versions whose worker started and answered a ping in this server process.
    started_versions: Mutex<HashSet<String>>,
    driving: std::sync::Mutex<HashSet<String>>,
    /// Committed AI moves.
    moves: AtomicUsize,
    /// Teacher hints for the human seat (`hint`), by (room, revision, player): one teacher run
    /// per position however often the player asks, and the answer stays until the room moves on.
    hints: std::sync::Mutex<HashMap<HintKey, HintRun>>,
}

type HintKey = (String, u64, PlayerId);

/// One hint position's teacher run, as seen by a request waiting for it: `None` while the
/// teacher thinks, then `Some(answer)` (`Some(None)` = the teacher gave no answer).
type HintRun = watch::Receiver<Option<Option<AiDecision>>>;

/// Hint runs kept at once (one per room that asked); past it the map starts over.
const MAX_HINT_ROOMS: usize = 256;

impl AiPool {
    pub fn new(config: AiConfig) -> Self {
        let workers = (0..config.workers)
            .map(|_| Mutex::new(Vec::new()))
            .collect();
        Self {
            config,
            workers,
            started_versions: Mutex::new(HashSet::new()),
            driving: std::sync::Mutex::new(HashSet::new()),
            moves: AtomicUsize::new(0),
            hints: std::sync::Mutex::new(HashMap::new()),
        }
    }

    /// The teacher run of one hint position, started with `search` unless one is already known.
    ///
    /// The run is a task of its own, not part of the request that started it: a request that
    /// goes away (closed tab, lost connection) leaves the run going, and the next request for
    /// the same position joins it or reads its answer instead of starting another. Runs of the
    /// room's earlier revisions are forgotten, since a room never returns to them, and so is a
    /// run without an answer, so that the next press tries again.
    fn hint_run<F>(
        self: &Arc<Self>,
        room_code: &str,
        revision: u64,
        player: PlayerId,
        search: impl FnOnce() -> F,
    ) -> HintRun
    where
        F: std::future::Future<Output = Option<AiDecision>> + Send + 'static,
    {
        let mut hints = self
            .hints
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        hints.retain(|(room, run_revision, _), _| room != room_code || *run_revision == revision);
        let key = (room_code.to_string(), revision, player);
        if let Some(run) = hints.get(&key) {
            return run.clone();
        }
        if hints.len() >= MAX_HINT_ROOMS {
            hints.clear();
        }
        let (answered, run) = watch::channel(None);
        hints.insert(key.clone(), run.clone());
        let (pool, search, started) = (Arc::clone(self), search(), run.clone());
        tokio::spawn(async move {
            let answer = search.await;
            if answer.is_none() {
                pool.forget_hint(&key, &started);
            }
            // No request may be waiting any more; the answer is then read from the map's copy.
            answered.send_replace(Some(answer));
        });
        run
    }

    /// Drops `run` from the known hint runs, unless the position already has a newer one.
    fn forget_hint(&self, key: &HintKey, run: &HintRun) {
        let mut hints = self
            .hints
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        if hints.get(key).is_some_and(|known| known.same_channel(run)) {
            hints.remove(key);
        }
    }

    /// Starts one worker of the image teacher and pings it, the way AI games will start it: a
    /// worker resolves its `teacher_patches` factory (`GAIA_AI_TEACHER`) before it reads the
    /// first request, so a mistyped name or a broken import fails here instead of in every
    /// move of a game (each of which would then stop the game's AI seats). `Err` = why not.
    pub async fn check_image_teacher(&self) -> Result<(), String> {
        let ping = async {
            let mut worker = self.spawn_worker(None)?;
            exchange(&mut worker, &serde_json::json!({"op": "ping"})).await
        };
        match tokio::time::timeout(VERSION_START_TIMEOUT, ping).await {
            Ok(Ok(Reply { ok: true, .. })) => Ok(()),
            Ok(Ok(reply)) => Err(format!(
                "it refused a ping ({})",
                reply.error.unwrap_or_default()
            )),
            Ok(Err(error)) => Err(format!("it does not start ({error})")),
            Err(_) => Err(format!(
                "it did not answer a ping in {} s",
                VERSION_START_TIMEOUT.as_secs()
            )),
        }
    }

    /// `check_image_teacher` once at server start, written to the log. The server keeps
    /// running either way: only the AI seats depend on the teacher.
    pub async fn log_image_teacher_check(&self) {
        let named = match std::env::var("GAIA_AI_TEACHER") {
            Ok(name) if !name.trim().is_empty() => format!("GAIA_AI_TEACHER={name}"),
            _ => "the worker's default factory".to_string(),
        };
        match self.check_image_teacher().await {
            Ok(()) => log::info!("AI teacher check passed ({named})"),
            Err(reason) => log::error!(
                "AI teacher check FAILED ({named}): {reason}. Until this is fixed the AI seats \
                 of every AI game stop at their first move; the worker's own error is in the \
                 lines above."
            ),
        }
    }

    /// Committed AI moves since the pool started.
    pub fn move_count(&self) -> usize {
        self.moves.load(Ordering::Relaxed)
    }

    /// The `gaia-rl` folder of a promoted version, or why this server must not run it. A
    /// version is Python on top of the image's native engine module, so besides a valid name
    /// and a worker file it needs the engine fingerprint of this image in its `teacher.json`:
    /// a version made for another engine (an engine deploy with `current` left in place, or a
    /// switch back to an old version) is never started. Checked on every use, not only when
    /// the version was made.
    fn version_dir(&self, version: &str) -> Result<PathBuf, &'static str> {
        let root = self.config.teachers.as_ref().ok_or("no versions folder")?;
        if !valid_version(version) {
            return Err("not a plain folder name");
        }
        let dir = root.join(version).join("gaia-rl");
        if !dir.join("tools/ai_worker.py").is_file() {
            return Err("no worker file in its folder");
        }
        match (
            &self.config.engine_fingerprint,
            teacher_meta(&dir).engine_fingerprint,
        ) {
            (None, _) => Err("this server has no engine fingerprint"),
            (_, None) => Err("its teacher.json has no engine fingerprint"),
            (Some(image), Some(made_for)) if *image == made_for => Ok(dir),
            _ => Err("it was made for another engine than this image's"),
        }
    }

    /// The version named by `<GAIA_AI_TEACHERS_DIR>/current`. `None` = the image teacher: no
    /// versions folder, no `current` file, an empty one, or a version this server must not run.
    pub fn current_teacher(&self) -> Option<String> {
        let root = self.config.teachers.as_ref()?;
        let text = std::fs::read_to_string(root.join("current")).ok()?;
        let version = text.trim();
        if version.is_empty() {
            return None;
        }
        if let Err(reason) = self.version_dir(version) {
            log::error!(
                "teacher version {version:?} named by `current` is not used ({reason}); \
                 new AI rooms use the image teacher"
            );
            return None;
        }
        Some(version.to_string())
    }

    /// The teacher version a new AI room is pinned to. A version is used only after its worker
    /// has started and answered a ping once in this server process (its imports and factory
    /// name are good); otherwise the room gets the image teacher (`None`).
    pub async fn pin_teacher(&self) -> Option<String> {
        let version = self.current_teacher()?;
        let mut started = self.started_versions.lock().await;
        if started.contains(&version) {
            return Some(version);
        }
        let ping = async {
            let mut worker = self.spawn_worker(Some(&version))?;
            exchange(&mut worker, &serde_json::json!({"op": "ping"})).await
        };
        match tokio::time::timeout(VERSION_START_TIMEOUT, ping).await {
            Ok(Ok(Reply { ok: true, .. })) => {
                log::info!("teacher version {version} started; new AI rooms use it");
                started.insert(version.clone());
                Some(version)
            }
            Ok(Ok(reply)) => {
                log::error!(
                    "teacher version {version} refused a ping ({}); new AI rooms use the image teacher",
                    reply.error.unwrap_or_default()
                );
                None
            }
            Ok(Err(error)) => {
                log::error!(
                    "teacher version {version} does not start ({error}); new AI rooms use the image teacher"
                );
                None
            }
            Err(_) => {
                log::error!(
                    "teacher version {version} did not answer a ping in {} s; new AI rooms use the image teacher",
                    VERSION_START_TIMEOUT.as_secs()
                );
                None
            }
        }
    }

    /// Starts a worker of the image teacher (`None`) or of a promoted version.
    fn spawn_worker(&self, version: Option<&str>) -> std::io::Result<Worker> {
        let (dir, factory) = match version {
            None => (self.config.dir.clone(), None),
            Some(version) => {
                let dir = self.version_dir(version).map_err(|reason| {
                    std::io::Error::other(format!("teacher version {version}: {reason}"))
                })?;
                let factory = teacher_meta(&dir).factory;
                (dir, Some(factory))
            }
        };
        let pythonpath = ["python", "baseline-teacher-20260917", "tools"]
            .iter()
            .map(|part| dir.join(part).display().to_string())
            .collect::<Vec<_>>()
            .join(":");
        let mut command = Command::new(&self.config.python);
        command
            .arg(dir.join("tools/ai_worker.py"))
            .current_dir(&dir)
            .env("PYTHONPATH", pythonpath)
            .env("GAIA_ENGINE_FIXES_2", "1");
        // A version names its own factory; the server's GAIA_AI_TEACHER is for the image teacher.
        match factory {
            Some(Some(factory)) => {
                command.env("GAIA_AI_TEACHER", factory);
            }
            Some(None) => {
                command.env_remove("GAIA_AI_TEACHER");
            }
            None => {}
        }
        let mut child = command
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
    /// exceeds the timeout (the worker is then restarted on the next request). `teacher` is
    /// the room's pinned version (`None` = the image teacher); a version this server must not
    /// run (folder removed, made for another engine) is played by the image teacher.
    pub async fn choose(
        &self,
        room_code: &str,
        state: &GameState,
        player: PlayerId,
        level: Option<&str>,
        teacher: Option<&str>,
    ) -> Option<AiDecision> {
        self.choose_in(room_code, room_code, state, player, level, teacher)
            .await
    }

    /// `choose` with the worker's per-room teacher memory kept under `memory` instead of the
    /// room code. The worker slot is still the room's, so a room never runs two searches at once.
    async fn choose_in(
        &self,
        room_code: &str,
        memory: &str,
        state: &GameState,
        player: PlayerId,
        level: Option<&str>,
        teacher: Option<&str>,
    ) -> Option<AiDecision> {
        let teacher = teacher.filter(|version| match self.version_dir(version) {
            Ok(_) => true,
            Err(reason) => {
                log::warn!(
                    "teacher version {version} of room {room_code} is not used ({reason}); \
                     using the image teacher"
                );
                false
            }
        });
        let mut guard = self.workers[self.slot(room_code)].lock().await;
        // This version's worker, started if needed. It is taken out of the slot while it
        // answers and put back (most recently used) only after its whole reply was read: a
        // reply line carries no request id, so a worker left with an unread reply would hand
        // it to the next request. If this future is dropped in between (a cancelled caller),
        // the worker is dropped with it and killed, like one that failed or timed out.
        let (version, mut worker) = match guard
            .iter()
            .position(|(version, _)| version.as_deref() == teacher)
        {
            Some(position) => guard.remove(position),
            None => match self.spawn_worker(teacher) {
                Ok(worker) => (teacher.map(str::to_string), worker),
                Err(error) => {
                    log::error!("AI worker failed to start: {error}");
                    return None;
                }
            },
        };
        let level = level.unwrap_or(&self.config.level);
        let request = serde_json::json!({
            "op": "choose", "room": memory, "player": player,
            "level": level, "state": state,
        });
        let outcome = tokio::time::timeout(
            guard_timeout(self.config.timeout, level),
            exchange(&mut worker, &request),
        )
        .await;
        let reply = match outcome {
            Ok(Ok(reply)) => reply,
            Ok(Err(error)) => {
                log::error!("AI worker failed for room {room_code}: {error}; restarting it");
                return None;
            }
            Err(_) => {
                log::error!("AI worker timed out for room {room_code}; restarting it");
                return None;
            }
        };
        guard.push((version, worker));
        if guard.len() > VERSIONS_PER_SLOT {
            guard.remove(0);
        }
        match reply {
            Reply {
                ok: true,
                decision: Some(decision),
                ..
            } => Some(decision),
            reply => {
                log::warn!(
                    "AI worker declined room {room_code}: {}",
                    reply.error.unwrap_or_default()
                );
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
    state: GameState,
    level: Option<String>,
    teacher: Option<String>,
}

async fn next_ai_turn(app: &AppState, room_code: &str) -> Option<Turn> {
    let rooms = app.rooms.read().await;
    let room = rooms.get_room(room_code)?;
    let human = room.dev_human_player?;
    if room.paused {
        return None;
    }
    let state = room.game_state.as_ref()?;
    if state.tutorial.is_some()
        || state.dev_controller.is_some()
        || matches!(state.phase, GamePhase::Ended { .. })
    {
        return None;
    }
    let player = required_player(state)?;
    if player == human || state.undo_state.pending_request.is_some() {
        return None;
    }
    Some(Turn {
        revision: room.revision,
        player,
        state: state.clone(),
        level: room.ai_level.clone(),
        teacher: room.ai_teacher.clone(),
    })
}

/// How often the teacher is asked again for a position it gave no usable move for, before the
/// room's AI seats stop and wait for the player's retry request (`retry`).
const TEACHER_RETRIES: u32 = 1;

/// Whether a position the teacher failed at `failures` times in a row is given up.
fn gives_up(failures: u32) -> bool {
    failures > TEACHER_RETRIES
}

/// Marks the room's AI seats as waiting at the position of `turn` and tells the clients. No
/// move is played for the seat: a move the teacher did not choose would make the game
/// something other than the teacher's play. `false` = the room has moved on since `turn` was
/// read, so nothing was marked and the caller reads the room again.
async fn stall(app: &AppState, room_code: &str, turn: &Turn, reason: AiStallReason) -> bool {
    {
        let mut rooms = app.rooms.write().await;
        let Some(room) = rooms.get_room_mut(room_code) else {
            return true;
        };
        if room.revision != turn.revision {
            return false;
        }
        room.ai_stalled = Some(AiStall {
            revision: turn.revision,
            player: turn.player,
            reason,
        });
    }
    log::error!(
        "AI seat {} of room {room_code} has no usable teacher move ({reason:?}); \
         the AI seats wait for a retry request",
        turn.player
    );
    if let Ok(revision) = gaia_protocol::Revision::new(turn.revision) {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
    true
}

async fn drive(app: &AppState, pool: &Arc<AiPool>, room_code: &str) {
    // A full game has a few hundred decisions; this only guards against a logic loop.
    let mut conflicts_in_a_row = 0;
    let mut teacher_failures = 0;
    let pause = pool.config.move_pause;
    let mut last_move = std::time::Instant::now();
    for _ in 0..2000 {
        let Some(turn) = next_ai_turn(app, room_code).await else {
            return;
        };
        // The teacher workers do not play the setup auction; AI seats bid with ai_bidding.
        let decision = match crate::ai_bidding::decide(&turn.state, turn.player) {
            Some(action) => Some(AiDecision::Setup(action)),
            None => {
                pool.choose(
                    room_code,
                    &turn.state,
                    turn.player,
                    turn.level.as_deref(),
                    turn.teacher.as_deref(),
                )
                .await
            }
        };
        let Some(decision) = decision else {
            // The pool has logged why (the worker failed, timed out or declined).
            teacher_failures += 1;
            if gives_up(teacher_failures) {
                if stall(app, room_code, &turn, AiStallReason::NoAnswer).await {
                    return;
                }
                teacher_failures = 0;
            }
            continue;
        };
        // Keep every AI move on screen for a moment: the teacher often answers in milliseconds.
        let wait = pause.saturating_sub(last_move.elapsed());
        if !wait.is_zero() {
            tokio::time::sleep(wait).await;
        }
        let mut rejected = None;
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
            let events = match apply_decision(&mut probe, turn.player, decision.clone()) {
                Ok(events) => events,
                Err(error) => {
                    rejected = Some(error.to_string());
                    return Err(error);
                }
            };
            *state = probe;
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
                conflicts_in_a_row = 0;
                teacher_failures = 0;
                pool.moves.fetch_add(1, Ordering::Relaxed);
                coordinator::broadcast_snapshot(app, room_code, outcome.revision).await;
                last_move = std::time::Instant::now();
                if let Err(error) = TurnManagementService::maybe_end_round(app, room_code).await {
                    log::error!("maybe_end_round failed for room {room_code}: {error}");
                    return;
                }
            }
            Err(CommandError::Rule(_)) | Err(CommandError::RevisionConflict { .. }) => {
                let give_up = match rejected {
                    // The engine refused the teacher's move: ask the teacher once more.
                    Some(error) => {
                        log::warn!("AI move rejected in room {room_code} ({error})");
                        teacher_failures += 1;
                        gives_up(teacher_failures)
                    }
                    // The human or another transition changed the room first: re-read and
                    // continue. Repeats on an unchanged room mean the seat cannot move at all.
                    None => {
                        conflicts_in_a_row += 1;
                        conflicts_in_a_row >= 3
                    }
                };
                if give_up {
                    if stall(app, room_code, &turn, AiStallReason::Rejected).await {
                        return;
                    }
                    conflicts_in_a_row = 0;
                    teacher_failures = 0;
                }
            }
            Err(error) => {
                log::error!("AI move could not be committed in room {room_code}: {error}");
                return;
            }
        }
    }
}

/// The player's request to let the AI seats try again after they stopped (`Room::ai_stalled`).
/// Only the human seat of an AI game may ask. It clears the mark and starts the driver, which
/// asks the teacher for the same position again; harmless when the seats were not stalled.
pub async fn retry(app: &AppState, room_code: &str, player: PlayerId) -> Result<(), HintError> {
    if app.ai.is_none() {
        return Err(HintError::NotAnAiGame);
    }
    let cleared = {
        let mut rooms = app.rooms.write().await;
        let room = rooms
            .get_room_mut(room_code)
            .ok_or(HintError::NotAnAiGame)?;
        if !is_ai_room(room) || room.dev_human_player != Some(player) {
            return Err(HintError::NotAnAiGame);
        }
        let current = room.current_ai_stall().is_some();
        room.ai_stalled = None;
        current.then_some(room.revision)
    };
    // The stopped banner goes away at once; the teacher's move follows when it has one.
    if let Some(revision) = cleared.and_then(|revision| gaia_protocol::Revision::new(revision).ok())
    {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
    log::info!("AI retry asked in room {room_code} by seat {player}");
    spawn_driver(app.clone(), room_code.to_string());
    Ok(())
}

/// A room whose other seats are played by the teacher workers: the same test `next_ai_turn`
/// applies (the pool itself must exist too — `AppState::ai`).
pub fn is_ai_room(room: &Room) -> bool {
    room.dev_human_player.is_some()
        && room
            .game_state
            .as_ref()
            .is_some_and(|state| state.tutorial.is_none() && state.dev_controller.is_none())
}

/// Why no hint was given.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HintError {
    /// Not an AI game, not its human seat, or the game is over.
    NotAnAiGame,
    /// The room is at `revision` but waits for another seat (or for an undo answer).
    NotYourDecision,
    /// The room is no longer at the revision the hint was asked for.
    Stale,
    /// The teacher was unavailable, erred or timed out.
    NoAnswer,
}

/// The position a hint is asked for: `room` must be an AI game at `revision`, waiting for its
/// human seat `player`. Checked before the teacher runs and again when it answers.
fn hint_position(room: &Room, player: PlayerId, revision: u64) -> Result<&GameState, HintError> {
    if !is_ai_room(room) || room.dev_human_player != Some(player) {
        return Err(HintError::NotAnAiGame);
    }
    let state = room.game_state.as_ref().ok_or(HintError::NotAnAiGame)?;
    if matches!(state.phase, GamePhase::Ended { .. }) {
        return Err(HintError::NotAnAiGame);
    }
    if room.revision != revision {
        return Err(HintError::Stale);
    }
    if required_player(state) != Some(player) || state.undo_state.pending_request.is_some() {
        return Err(HintError::NotYourDecision);
    }
    Ok(state)
}

/// What the teacher would play for the human seat of an AI game at `revision`. Nothing is
/// applied; the player only reads it.
///
/// The request is tied to the position: it is refused unless the room is at `revision` and
/// waits for `player`, and the answer is dropped (`Stale`) when the room moved on while the
/// teacher was thinking — the rule `drive` applies to an AI move. Requests for one position
/// share one teacher run, which goes on when the request that started it is cancelled
/// (`AiPool::hint_run`).
///
/// The teacher memory is the room's own with a `#hint` suffix, so hints never touch what the
/// AI seats remember; the worker slot is the room's, so a hint waits for that slot like any
/// decision (other rooms share it, and that wait is outside the worker guard).
pub async fn hint(
    app: &AppState,
    room_code: &str,
    player: PlayerId,
    revision: u64,
) -> Result<AiDecision, HintError> {
    let pool = app.ai.clone().ok_or(HintError::NotAnAiGame)?;
    let (state, level, teacher) = {
        let rooms = app.rooms.read().await;
        let room = rooms.get_room(room_code).ok_or(HintError::NotAnAiGame)?;
        let state = hint_position(room, player, revision)?.clone();
        (state, room.ai_level.clone(), room.ai_teacher.clone())
    };
    let key: HintKey = (room_code.to_string(), revision, player);
    let mut run = pool.hint_run(room_code, revision, player, || {
        let (pool, room_code) = (Arc::clone(&pool), room_code.to_string());
        async move {
            // The teacher workers do not play the setup auction (see `drive`).
            match crate::ai_bidding::decide(&state, player) {
                Some(action) => Some(AiDecision::Setup(action)),
                None => {
                    pool.choose_in(
                        &room_code,
                        &format!("{room_code}#hint"),
                        &state,
                        player,
                        level.as_deref(),
                        teacher.as_deref(),
                    )
                    .await
                }
            }
        }
    });
    let answered = run
        .wait_for(|answer| answer.is_some())
        .await
        .map(|answer| answer.clone().flatten());
    let decision = match answered {
        Ok(answer) => answer.ok_or(HintError::NoAnswer)?,
        Err(_) => {
            // The run ended without an answer of any kind (its task died).
            pool.forget_hint(&key, &run);
            return Err(HintError::NoAnswer);
        }
    };
    {
        let rooms = app.rooms.read().await;
        let room = rooms.get_room(room_code).ok_or(HintError::Stale)?;
        hint_position(room, player, revision)?;
    }
    // The record of a hint the player was shown, by the revision it belongs to.
    log::info!(
        "AI hint room={room_code} revision={revision} player={player} decision={}",
        serde_json::to_string(&decision).unwrap_or_default()
    );
    Ok(decision)
}

fn apply_decision(
    state: &mut GameState,
    player: PlayerId,
    decision: AiDecision,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, RuleError> {
    match decision {
        AiDecision::Game(action) => apply_logged_action(state, player, action),
        AiDecision::Setup(action) => RuleEngine::apply_setup_action(state, player, action),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn move_pause_defaults_and_parses() {
        assert_eq!(move_pause_from(None), Duration::from_millis(1500));
        assert_eq!(move_pause_from(Some("abc")), Duration::from_millis(1500));
        assert_eq!(move_pause_from(Some("0")), Duration::ZERO);
        assert_eq!(move_pause_from(Some(" 800 ")), Duration::from_millis(800));
    }

    /// An AI game at revision 5 and the seat it waits for, made the room's human seat.
    fn ai_room_waiting_for_its_human() -> (Room, PlayerId) {
        use gaia_engine::{game_state::FactionId, Randomizer};
        let setup = Randomizer::generate_setup("hint-test")
            .unwrap_or_else(|error| panic!("setup should be generated: {error}"));
        let state = crate::services::dev_game::build_game_state_with_factions(
            "HINT01",
            "hint-test",
            7,
            &[8, 9, 10],
            &setup,
            FactionId::Terrans,
            vec![FactionId::Xenos, FactionId::Taklons, FactionId::HadschHallas],
            false,
        )
        .unwrap_or_else(|error| panic!("ai game should be built: {error}"));
        let to_move = required_player(&state).expect("a seat must act at the start");
        let room = Room {
            code: "HINT01".into(),
            name: "HINT01".into(),
            password_hash: None,
            host_player: to_move,
            players: vec![(to_move, "나".into(), true)],
            state: RoomState::InGame,
            game_state: Some(state),
            setup: Some(setup),
            seed: "hint-test".into(),
            revision: 5,
            connected: HashSet::from([to_move]),
            paused: false,
            dev_human_player: Some(to_move),
            dev_bot_action_counts: HashMap::new(),
            dev_bot_action_round: 0,
            ai_level: Some("hard".into()),
            ai_teacher: None,
            ai_stalled: None,
        };
        (room, to_move)
    }

    #[test]
    fn a_hint_belongs_to_the_human_seat_at_the_asked_revision() {
        let (mut room, human) = ai_room_waiting_for_its_human();
        assert!(is_ai_room(&room));
        assert!(hint_position(&room, human, 5).is_ok());
        // The room moved on (or the request is for a position not reached yet).
        assert_eq!(hint_position(&room, human, 4).err(), Some(HintError::Stale));
        assert_eq!(hint_position(&room, human, 6).err(), Some(HintError::Stale));
        // Another seat is never given a hint, whoever is to move.
        let other = [7, 8, 9, 10]
            .into_iter()
            .find(|seat| *seat != human)
            .unwrap();
        assert_eq!(
            hint_position(&room, other, 5).err(),
            Some(HintError::NotAnAiGame)
        );
        // The human seat while an AI seat is to move.
        room.dev_human_player = Some(other);
        assert_eq!(
            hint_position(&room, other, 5).err(),
            Some(HintError::NotYourDecision)
        );
        // A room without AI seats.
        room.dev_human_player = None;
        assert!(!is_ai_room(&room));
        assert_eq!(
            hint_position(&room, human, 5).err(),
            Some(HintError::NotAnAiGame)
        );
    }

    fn slow_answer() -> AiDecision {
        AiDecision::Setup(gaia_engine::SetupAction::PlaceBid { amount: 1 })
    }

    fn fast_answer() -> AiDecision {
        AiDecision::Setup(gaia_engine::SetupAction::PassBid)
    }

    #[tokio::test]
    async fn hint_requests_for_one_position_share_one_run() {
        let pool = Arc::new(pool_with_teachers(None));
        let answer = |decision: Option<AiDecision>| move || std::future::ready(decision);
        let mut first = pool.hint_run("ROOM01", 5, 7, answer(Some(fast_answer())));
        assert!(first.same_channel(&pool.hint_run("ROOM01", 5, 7, answer(None))));
        let other_room = pool.hint_run("ROOM02", 5, 7, answer(Some(fast_answer())));
        assert!(!first.same_channel(&other_room));
        // The room moved on: its old run is forgotten, the other room's stays.
        let mut next = pool.hint_run("ROOM01", 6, 7, answer(None));
        assert!(!first.same_channel(&next));
        assert!(other_room.same_channel(&pool.hint_run("ROOM02", 5, 7, answer(None))));
        assert_eq!(pool.hints.lock().unwrap().len(), 2);
        // The run of revision 6 ends without an answer: asking again starts another run.
        assert_eq!(*next.wait_for(|answer| answer.is_some()).await.unwrap(), Some(None));
        assert_eq!(pool.hints.lock().unwrap().len(), 1);
        let retried = pool.hint_run("ROOM01", 6, 7, answer(Some(slow_answer())));
        assert!(!next.same_channel(&retried));
        // A forgotten run still answers the requests that wait for it.
        assert_eq!(
            *first.wait_for(|answer| answer.is_some()).await.unwrap(),
            Some(Some(fast_answer()))
        );
    }

    /// A pool whose worker is a shell script in a folder of its own: it adds a line to the
    /// folder's `seen` file for each request it has read, then answers a request of teacher
    /// memory "slow" with `slow_answer` after half a second and any other with `fast_answer`
    /// at once.
    fn pool_with_scripted_worker(test: &str) -> (Arc<AiPool>, PathBuf) {
        let dir = std::env::temp_dir().join(format!("gaia-worker-{}-{test}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        std::fs::create_dir_all(dir.join("tools")).unwrap();
        let reply = |decision: AiDecision| {
            serde_json::json!({"ok": true, "decision": decision}).to_string()
        };
        let script = format!(
            "while IFS= read -r line; do\n  echo request >> seen\n  case \"$line\" in\n    \
             *'\"room\":\"slow\"'*) sleep 0.5; echo '{}' ;;\n    *) echo '{}' ;;\n  esac\ndone\n",
            reply(slow_answer()),
            reply(fast_answer()),
        );
        std::fs::write(dir.join("tools/ai_worker.py"), script).unwrap();
        let pool = AiPool::new(AiConfig {
            dir: dir.clone(),
            python: PathBuf::from("/bin/sh"),
            workers: 1,
            level: "normal".into(),
            timeout: Duration::from_secs(30),
            move_pause: Duration::ZERO,
            teachers: None,
            engine_fingerprint: None,
        });
        (Arc::new(pool), dir)
    }

    #[tokio::test]
    async fn the_start_check_tells_a_worker_that_answers_from_one_that_exits() {
        let (pool, dir) = pool_with_scripted_worker("start-check");
        assert_eq!(pool.check_image_teacher().await, Ok(()));
        // What a mistyped GAIA_AI_TEACHER does: the worker ends before it reads a request.
        std::fs::write(dir.join("tools/ai_worker.py"), "exit 3\n").unwrap();
        let reason = pool
            .check_image_teacher()
            .await
            .expect_err("a worker that exits must fail the check");
        assert!(reason.contains("does not start"), "{reason}");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn a_snapshot_says_the_ai_seats_stopped_only_at_the_revision_they_stopped_at() {
        let (mut room, _) = ai_room_waiting_for_its_human();
        let view = coordinator::room_snapshot_view(&room);
        assert!(view.get("ai_stalled").is_none());
        assert!(view.get("players").is_some());
        room.ai_stalled = Some(AiStall {
            revision: 5,
            player: 9,
            reason: AiStallReason::NoAnswer,
        });
        let view = coordinator::room_snapshot_view(&room);
        assert_eq!(
            view["ai_stalled"],
            serde_json::json!({"revision": 5, "player": 9, "reason": "no_answer"})
        );
        // Any committed move ends the stall: the mark of an earlier revision is not sent.
        room.revision = 6;
        assert_eq!(room.current_ai_stall(), None);
        assert!(coordinator::room_snapshot_view(&room)
            .get("ai_stalled")
            .is_none());
    }

    #[test]
    fn the_teacher_is_asked_once_more_before_the_ai_seats_stop() {
        assert!(!gives_up(1));
        assert!(gives_up(2));
    }

    /// Waits until the scripted worker has read `count` requests.
    async fn worker_has_read(dir: &std::path::Path, count: usize) {
        for _ in 0..1000 {
            let seen = std::fs::read_to_string(dir.join("seen")).unwrap_or_default();
            if seen.lines().count() >= count {
                return;
            }
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
        panic!("the worker did not read {count} request(s)");
    }

    fn requests_read(dir: &std::path::Path) -> usize {
        std::fs::read_to_string(dir.join("seen"))
            .unwrap_or_default()
            .lines()
            .count()
    }

    #[tokio::test]
    async fn a_cancelled_request_does_not_leave_its_reply_to_the_next_one() {
        let (pool, dir) = pool_with_scripted_worker("cancel");
        let (room, human) = ai_room_waiting_for_its_human();
        let state = room.game_state.expect("the room has a game");
        let asked = {
            let (pool, state) = (Arc::clone(&pool), state.clone());
            tokio::spawn(async move {
                pool.choose_in("ROOM01", "slow", &state, human, None, None)
                    .await
            })
        };
        // The worker has the request and is thinking when its caller goes away.
        worker_has_read(&dir, 1).await;
        asked.abort();
        assert!(asked.await.unwrap_err().is_cancelled());
        // The next request gets its own answer, not the one the cancelled request never read.
        assert_eq!(
            pool.choose_in("ROOM01", "fast", &state, human, None, None)
                .await,
            Some(fast_answer())
        );
        // And the worker stays in step with its requests afterwards.
        assert_eq!(
            pool.choose_in("ROOM01", "slow", &state, human, None, None)
                .await,
            Some(slow_answer())
        );
        assert_eq!(requests_read(&dir), 3);
        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[tokio::test]
    async fn a_hint_run_goes_on_when_its_request_is_cancelled() {
        let (pool, dir) = pool_with_scripted_worker("hint-run");
        let (room, human) = ai_room_waiting_for_its_human();
        let state = room.game_state.expect("the room has a game");
        let mut first = pool.hint_run("ROOM01", 5, human, || {
            let pool = Arc::clone(&pool);
            async move {
                pool.choose_in("ROOM01", "slow", &state, human, None, None)
                    .await
            }
        });
        let asked = tokio::spawn(async move {
            let _ = first.wait_for(|answer| answer.is_some()).await;
        });
        // The request is sent to the worker; then the request for the hint is cancelled.
        worker_has_read(&dir, 1).await;
        asked.abort();
        assert!(asked.await.unwrap_err().is_cancelled());
        // Asked again: no second search, and the answer is the one of the run still going on.
        let never = || -> std::future::Ready<Option<AiDecision>> {
            panic!("a second search was started for the same position")
        };
        let mut again = pool.hint_run("ROOM01", 5, human, never);
        assert_eq!(
            *again.wait_for(|answer| answer.is_some()).await.unwrap(),
            Some(Some(slow_answer()))
        );
        // Asked after the answer: it is read from the finished run.
        let after = pool.hint_run("ROOM01", 5, human, never);
        assert_eq!(*after.borrow(), Some(Some(slow_answer())));
        assert_eq!(requests_read(&dir), 1);
        std::fs::remove_dir_all(&dir).unwrap();
    }

    #[test]
    fn hard_level_gets_a_longer_worker_guard() {
        let configured = Duration::from_secs(30);
        assert_eq!(guard_timeout(configured, "normal"), configured);
        assert_eq!(guard_timeout(configured, "hard"), Duration::from_secs(60));
        assert_eq!(
            guard_timeout(Duration::from_secs(90), "hard"),
            Duration::from_secs(90)
        );
    }

    /// A pool whose image was built from engine "engine-a".
    fn pool_with_teachers(teachers: Option<PathBuf>) -> AiPool {
        pool_with_engine(teachers, Some("engine-a"))
    }

    fn pool_with_engine(teachers: Option<PathBuf>, engine: Option<&str>) -> AiPool {
        AiPool::new(AiConfig {
            dir: PathBuf::from("/nonexistent/gaia-rl"),
            python: PathBuf::from("/nonexistent/python"),
            workers: 2,
            level: "normal".into(),
            timeout: Duration::from_secs(30),
            move_pause: Duration::ZERO,
            teachers,
            engine_fingerprint: engine.map(str::to_string),
        })
    }

    fn write_version(root: &std::path::Path, version: &str, teacher_json: Option<&str>) {
        std::fs::create_dir_all(root.join(version).join("gaia-rl/tools")).unwrap();
        std::fs::write(root.join(version).join("gaia-rl/tools/ai_worker.py"), "").unwrap();
        if let Some(text) = teacher_json {
            std::fs::write(root.join(version).join("teacher.json"), text).unwrap();
        }
    }

    /// A versions folder with `v1`, made for engine "engine-a".
    fn versions_folder(test: &str) -> PathBuf {
        let root = std::env::temp_dir().join(format!("gaia-teachers-{}-{test}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        write_version(
            &root,
            "v1",
            Some(r#"{"factory": "f", "engine_fingerprint": "engine-a"}"#),
        );
        root
    }

    #[test]
    fn a_version_made_for_another_engine_is_never_used() {
        let root = versions_folder("engine");
        write_version(&root, "old", Some(r#"{"engine_fingerprint": "engine-b"}"#));
        write_version(&root, "unmarked", Some(r#"{"factory": "f"}"#));
        write_version(&root, "nojson", None);
        let pool = pool_with_teachers(Some(root.clone()));
        assert!(pool.version_dir("v1").is_ok());
        for version in ["old", "unmarked", "nojson"] {
            assert!(pool.version_dir(version).is_err(), "{version}");
            // Neither for new rooms (`current` left in place over an engine deploy, or switched
            // back to an old version) nor for a room already pinned to it.
            std::fs::write(root.join("current"), version).unwrap();
            assert_eq!(pool.current_teacher(), None, "{version}");
            assert!(pool.spawn_worker(Some(version)).is_err(), "{version}");
        }
        // The same folder under an image built from the other engine: only `old` fits.
        let other = pool_with_engine(Some(root.clone()), Some("engine-b"));
        assert!(other.version_dir("old").is_ok());
        assert!(other.version_dir("v1").is_err());
        // An image without a fingerprint runs no version at all.
        let unmarked_image = pool_with_engine(Some(root.clone()), None);
        assert!(unmarked_image.version_dir("v1").is_err());
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn version_names_are_single_plain_folder_names() {
        assert!(valid_version("20261119-3d4588e"));
        assert!(valid_version("v1.2_b"));
        for bad in ["", ".", "..", ".hidden", "a/b", "../v1", "a b", "v1\n"] {
            assert!(!valid_version(bad), "{bad:?}");
        }
    }

    #[test]
    fn current_teacher_needs_a_usable_version_folder() {
        assert_eq!(pool_with_teachers(None).current_teacher(), None);
        let root = versions_folder("current");
        let pool = pool_with_teachers(Some(root.clone()));
        // No `current` file, an empty one, a missing version, a path: all mean the image teacher.
        assert_eq!(pool.current_teacher(), None);
        for (text, expected) in [
            ("", None),
            ("\n", None),
            ("v2\n", None),
            ("../v1\n", None),
            ("v1\n", Some("v1".to_string())),
            ("  v1  ", Some("v1".to_string())),
        ] {
            std::fs::write(root.join("current"), text).unwrap();
            assert_eq!(pool.current_teacher(), expected, "{text:?}");
        }
        assert!(pool.version_dir("v1").is_ok());
        assert!(pool.version_dir("v2").is_err());
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[tokio::test]
    async fn a_version_that_does_not_start_is_not_pinned() {
        // The python path does not exist, so the ping fails and the room gets the image teacher.
        let root = versions_folder("pin");
        std::fs::write(root.join("current"), "v1\n").unwrap();
        let pool = pool_with_teachers(Some(root.clone()));
        assert_eq!(pool.current_teacher(), Some("v1".to_string()));
        assert_eq!(pool.pin_teacher().await, None);
        std::fs::remove_dir_all(&root).unwrap();
    }
}
