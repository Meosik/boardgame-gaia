//! Live AI seats backed by a pool of Python teacher workers (`gaia-rl/tools/ai_worker.py`).
//!
//! Enabled only when `GAIA_AI_DIR` points at a `gaia-rl` checkout with a built environment.
//! A room is always routed to the same worker so the teacher's plan memory survives between
//! that room's decisions. Workers run one decision at a time; the pool size bounds CPU use.
//!
//! AI moves never run inside a room lock: the driver reads the state, asks a worker, then
//! applies the reply through `coordinator::apply_server_transition` only if the room has not
//! moved on meanwhile. A failed or slow worker falls back to the DEV bots' simple legal move.
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
    /// Committed AI moves and how many of them used the DEV fallback instead of the teacher.
    moves: AtomicUsize,
    fallbacks: AtomicUsize,
}

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
        // Move this version's worker to the end (most recently used), starting it if needed.
        let worker = match guard
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
        guard.push(worker);
        if guard.len() > VERSIONS_PER_SLOT {
            guard.remove(0);
        }
        let worker = &mut guard.last_mut()?.1;
        let level = level.unwrap_or(&self.config.level);
        let request = serde_json::json!({
            "op": "choose", "room": room_code, "player": player,
            "level": level, "state": state,
        });
        let outcome = tokio::time::timeout(
            guard_timeout(self.config.timeout, level),
            exchange(worker, &request),
        )
        .await;
        match outcome {
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
                guard.pop();
                None
            }
            Err(_) => {
                log::error!("AI worker timed out for room {room_code}; restarting it");
                guard.pop();
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
        human,
        state: state.clone(),
        level: room.ai_level.clone(),
        teacher: room.ai_teacher.clone(),
    })
}

async fn drive(app: &AppState, pool: &Arc<AiPool>, room_code: &str) {
    // A full game has a few hundred decisions; this only guards against a logic loop.
    let mut rejected_in_a_row = 0;
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

#[cfg(test)]
mod tests {
    use super::*;

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
