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
//! Review of AI turns (optional per room, `Room::ai_review`): the driver records the moves of
//! the AI seat in turn (`note_ai_move`) and, when the seat's turn has ended, stops until the
//! player continues (`continue_after_hold`) or plays on. The finished turn is sent with the
//! snapshot (`ai_hold`). A request to the teacher may leave moves out and ask for spare moves
//! (`Exclusions`); rejecting a held turn is built on these (research/strategy/
//! ai-move-reject-design.md).
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
    rules::{actions::GameAction, engine::AiDecision},
    GameState, RuleEngine,
};
use serde::Deserialize;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, ChildStdout, Command};
use tokio::sync::{watch, Mutex};

use crate::{
    coordinator::{self, CommandError},
    room::manager::{
        AiHold, AiRejected, AiStall, AiStallReason, AiTurn, Excluded, Room, RoomState, Spare,
    },
    services::{
        dev_game::required_player,
        game_action::apply_server_seat_action,
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
    /// Only in the reply to a request with `Exclusions` (see there).
    #[serde(default)]
    spares: Vec<Spare>,
    #[serde(default)]
    excluded: usize,
    #[serde(default)]
    exclude_fallback: bool,
}

/// What a rejected AI turn adds to a teacher request; the default adds nothing, and the
/// request is then the one every ordinary AI move is asked with.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Exclusions {
    /// Moves the teacher must not answer. An entry that is no candidate of the asked decision
    /// is skipped: the list is the same for every decision of the turn.
    pub moves: Vec<Excluded>,
    /// How many moves the reply lists as `Answer::spares` (the worker gives at most 3).
    pub spares: usize,
}

/// The teacher's reply to a request with `Exclusions`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Answer {
    pub decision: AiDecision,
    /// The answer first, then the moves the teacher would play next, each with whether a
    /// completed comparison backs it. Empty unless `Exclusions::spares` asked for them.
    pub spares: Vec<Spare>,
    /// Candidates of the decision the exclusions left out; 0 = no entry matched.
    pub excluded: usize,
    /// The teacher's own pick was an excluded move (a pick made outside its ranking) and the
    /// worker answered the best move left instead.
    pub replaced: bool,
}

/// The request line for one decision. Without exclusions it has exactly the keys it always
/// had, so the worker answers it with the code every AI move has been answered with.
fn choose_request(
    memory: &str,
    player: PlayerId,
    level: &str,
    state: &GameState,
    exclusions: &Exclusions,
) -> serde_json::Value {
    let mut request = serde_json::json!({
        "op": "choose", "room": memory, "player": player,
        "level": level, "state": state,
    });
    if let Some(fields) = request.as_object_mut() {
        if !exclusions.moves.is_empty() {
            let moves: Vec<serde_json::Value> = exclusions
                .moves
                .iter()
                .map(|entry| match entry {
                    Excluded::Move(decision) => serde_json::json!(decision),
                    Excluded::ActionType(kind) => serde_json::json!({ "action_type": kind }),
                })
                .collect();
            fields.insert("exclude".into(), moves.into());
            fields.insert("skip_missing".into(), true.into());
        }
        if exclusions.spares > 0 {
            fields.insert("spares".into(), exclusions.spares.into());
        }
    }
    request
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
    /// Rooms with a running driver. The value is whether a start was asked (`spawn_driver`)
    /// since that driver last read the room: such a request may be for a state the driver did
    /// not see, so the driver reads the room once more before it ends (`finish_driving`).
    driving: std::sync::Mutex<HashMap<String, bool>>,
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
            driving: std::sync::Mutex::new(HashMap::new()),
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
        self.ask(
            room_code,
            memory,
            state,
            player,
            level,
            teacher,
            &Exclusions::default(),
        )
        .await
        .map(|answer| answer.decision)
    }

    /// `choose_in` with the moves a rejected turn leaves out and the spare moves asked for.
    #[allow(clippy::too_many_arguments)]
    pub(crate) async fn ask(
        &self,
        room_code: &str,
        memory: &str,
        state: &GameState,
        player: PlayerId,
        level: Option<&str>,
        teacher: Option<&str>,
        exclusions: &Exclusions,
    ) -> Option<Answer> {
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
        let state = &asked_as(state, player);
        let request = choose_request(memory, player, level, state, exclusions);
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
                spares,
                excluded,
                exclude_fallback,
                ..
            } => Some(Answer {
                decision,
                spares,
                excluded,
                replaced: exclude_fallback,
            }),
            reply => {
                log::warn!(
                    "AI worker declined room {room_code}: {}",
                    reply.error.unwrap_or_default()
                );
                None
            }
        }
    }

    /// `true` = no driver runs for the room and the caller starts one. With a driver running
    /// the request is recorded instead, for that driver to answer (`finish_driving`).
    fn try_start_driving(&self, room_code: &str) -> bool {
        let Ok(mut rooms) = self.driving.lock() else {
            return false;
        };
        match rooms.get_mut(room_code) {
            Some(asked) => {
                *asked = true;
                false
            }
            None => {
                rooms.insert(room_code.to_string(), false);
                true
            }
        }
    }

    /// The driver is about to read the room: that read answers every start asked so far (a
    /// caller changes the room before it asks). Called before the read, never after it, so a
    /// request made between the two stays recorded.
    fn before_room_read(&self, room_code: &str) {
        if let Ok(mut rooms) = self.driving.lock() {
            if let Some(asked) = rooms.get_mut(room_code) {
                *asked = false;
            }
        }
    }

    /// The driver found nothing more to do. `true` = a start was asked since it last read the
    /// room, so it stays the room's driver and drives again; otherwise the room has no driver
    /// from here on. Decided under one lock with `try_start_driving`: a request is either
    /// answered by this driver or starts a new one, never dropped.
    fn finish_driving(&self, room_code: &str) -> bool {
        let Ok(mut rooms) = self.driving.lock() else {
            return false;
        };
        match rooms.get_mut(room_code) {
            Some(asked) if *asked => {
                *asked = false;
                true
            }
            _ => {
                rooms.remove(room_code);
                false
            }
        }
    }
}

/// Plays AI seats of `room_code` until the human must act. Safe to call after every
/// committed transition; at most one driver runs per room. A call made while a driver runs
/// is not lost: that driver looks at the room again before it ends.
pub fn spawn_driver(app: AppState, room_code: String) {
    let Some(pool) = app.ai.clone() else {
        return;
    };
    if !pool.try_start_driving(&room_code) {
        return;
    }
    tokio::spawn(async move {
        loop {
            drive(&app, &pool, &room_code).await;
            if !pool.finish_driving(&room_code) {
                break;
            }
        }
    });
}

struct Turn {
    revision: u64,
    player: PlayerId,
    state: GameState,
    level: Option<String>,
    teacher: Option<String>,
    /// Set when this decision belongs to the replay of a rejected turn (`rejection_for`).
    rejected: Option<AiRejected>,
}

/// The seats the room waits for. The offers of a charge queue and the entries of an
/// income-order queue are answered in any order (the engine takes the answer of any queued
/// seat: each depends only on that seat's own bowls and VP), so all queued seats are waited
/// for at once and nobody waits for the seat ahead. Every other phase waits for one seat.
pub(crate) fn awaited_players(state: &GameState) -> Vec<PlayerId> {
    let mut players: Vec<PlayerId> = match &state.phase {
        GamePhase::ChargePowerPending { queue, .. }
        | GamePhase::LostPlanetChargePowerPending { queue, .. } => {
            queue.iter().map(|entry| entry.player).collect()
        }
        GamePhase::IncomeOrderPending { queue, .. } => {
            queue.iter().map(|entry| entry.player).collect()
        }
        _ => required_player(state).into_iter().collect(),
    };
    // A seat with two queued offers is still one seat (first place kept).
    let mut seen = Vec::new();
    players.retain(|player| {
        let first = !seen.contains(player);
        seen.push(*player);
        first
    });
    players
}

/// `state` as the teacher is asked about it for `player`. The teacher answers for the front
/// of a queue (`RuleEngine::decision_player`), so in the phases where any queued seat may
/// answer (`awaited_players`) the seat's own entry is moved to the front of the copy. The
/// entries are independent, so the question itself is the same.
fn asked_as(state: &GameState, player: PlayerId) -> GameState {
    fn to_front<T>(queue: &mut Vec<T>, is_asked: impl Fn(&T) -> bool) {
        if let Some(position) = queue.iter().position(is_asked) {
            let entry = queue.remove(position);
            queue.insert(0, entry);
        }
    }
    let mut state = state.clone();
    match &mut state.phase {
        GamePhase::ChargePowerPending { queue, .. }
        | GamePhase::LostPlanetChargePowerPending { queue, .. } => {
            to_front(queue, |entry| entry.player == player);
        }
        GamePhase::IncomeOrderPending { queue, .. } => {
            to_front(queue, |entry| entry.player == player);
        }
        _ => {}
    }
    state
}

async fn next_ai_turn(app: &AppState, room_code: &str) -> Option<Turn> {
    let rooms = app.rooms.read().await;
    let room = rooms.get_room(room_code)?;
    let human = room.dev_human_player?;
    if room.paused {
        return None;
    }
    // The player is looking at the AI turn that just ended (`note_ai_move`).
    if room.current_ai_hold().is_some() {
        return None;
    }
    let state = room.game_state.as_ref()?;
    if state.tutorial.is_some()
        || state.dev_controller.is_some()
        || matches!(state.phase, GamePhase::Ended { .. })
    {
        return None;
    }
    // The first AI seat the room waits for: in a charge or income-order queue that is not
    // only the front, so the AI seats answer while the human still decides (and the human
    // answers without waiting for them).
    let player = awaited_players(state)
        .into_iter()
        .find(|player| *player != human)?;
    if state.undo_state.pending_request.is_some() {
        return None;
    }
    Some(Turn {
        revision: room.revision,
        player,
        state: state.clone(),
        level: room.ai_level.clone(),
        teacher: room.ai_teacher.clone(),
        rejected: rejection_for(room, player).cloned(),
    })
}

/// The phases in which every queued seat answers for itself (`awaited_players`): a charge
/// offer or the income order. Such an answer belongs to no seat's turn.
fn answers_a_queue(state: &GameState) -> bool {
    matches!(
        state.phase,
        GamePhase::ChargePowerPending { .. }
            | GamePhase::LostPlanetChargePowerPending { .. }
            | GamePhase::IncomeOrderPending { .. }
    )
}

/// Whether the turn of `player` goes on after `decision`, asked at `asked` and leading to
/// `now`: the seat must decide next, alone, in the same round, and either the move was a free
/// action (the only action that does not end a turn) or the engine waits for the rest of the
/// seat's action (a lost-planet place, a Gaia-phase choice). A new action phase decision after
/// a main action is the seat's next turn (the others have passed), and every setup decision
/// is a turn of its own.
fn turn_goes_on(
    asked: &GameState,
    decision: &AiDecision,
    now: &GameState,
    player: PlayerId,
) -> bool {
    if matches!(asked.phase, GamePhase::Setup(_))
        || now.round != asked.round
        || answers_a_queue(now)
        || matches!(now.phase, GamePhase::Ended { .. })
        || required_player(now) != Some(player)
    {
        return false;
    }
    matches!(decision, AiDecision::Game(GameAction::FreeAction { .. }))
        || !matches!(now.phase, GamePhase::ActionPhase { .. })
}

/// Records a move of an AI seat in the seat's turn (`Room::ai_turn`) and, when the player
/// looks at every AI turn (`Room::ai_review`) and this move ended the turn, makes the AI seats
/// wait at the revision of the move (`Room::ai_hold`). `true` = they wait.
///
/// Called inside the transition that commits the move (`drive`), on the room the move has just
/// been applied to and before its revision advances: the move and the wait are one commit, so
/// no command of the player can come between them. (Noting the move after the commit let a
/// player's answer slip in first and then put the wait on the revision of that answer.)
/// A round end that follows takes the wait along (`Room::advance_by_server`); a command of the
/// player ends it.
///
/// `turn` is the position the move was asked at. The move continues the recorded turn only
/// when it was asked at the revision that turn had reached; anything else (the first move of a
/// turn, a turn broken by an undo or a restart) starts a new record at `turn.revision`, the
/// revision a rejected turn goes back to.
fn note_ai_move(room: &mut Room, turn: &Turn, decision: &AiDecision) -> bool {
    // The revision this transition is committed as: always the next one
    // (`GameRepository::commit_server_transition`).
    let moved = turn.revision + 1;
    let continued = room
        .ai_turn
        .take()
        .filter(|known| known.player == turn.player && known.revision == turn.revision);
    let mut record = continued.unwrap_or_else(|| AiTurn {
        player: turn.player,
        start_revision: turn.revision,
        revision: turn.revision,
        decisions: Vec::new(),
    });
    record.decisions.push(decision.clone());
    record.revision = moved;
    let goes_on = room
        .game_state
        .as_ref()
        .is_some_and(|now| turn_goes_on(&turn.state, decision, now, turn.player));
    let held = room.ai_review && !goes_on;
    if held {
        // A turn that is the replay of a rejected one says how much is left to reject.
        let replay = room.ai_rejected.as_ref().filter(|rejected| {
            rejected.player == record.player && rejected.start_revision == record.start_revision
        });
        let spares_left = replay.and_then(|rejected| rejected.spares.as_ref().map(Vec::len));
        room.ai_hold = Some(AiHold {
            revision: moved,
            turn: record.clone(),
            rejections: replay.map_or(0, |rejected| rejected.rejections),
            spares_left,
            can_reject: !replay.is_some_and(|rejected| rejected.no_alternative)
                && spares_left != Some(0),
        });
    }
    // A finished turn is kept only in the hold: the seat's next decision, even one asked at
    // this very revision (the other seats have passed), starts a new record.
    room.ai_turn = goes_on.then_some(record);
    held
}

/// The human seat of an AI game, the only one that may steer its AI seats.
fn ai_room_of<'a>(
    rooms: &'a mut crate::room::manager::RoomManager,
    room_code: &str,
    player: PlayerId,
) -> Result<&'a mut Room, HintError> {
    let room = rooms
        .get_room_mut(room_code)
        .ok_or(HintError::NotAnAiGame)?;
    if !is_ai_room(room) || room.dev_human_player != Some(player) {
        return Err(HintError::NotAnAiGame);
    }
    Ok(room)
}

/// The player's [continue] after looking at a finished AI turn (`Room::ai_hold`): the AI seats
/// play on. Harmless when they were not waiting.
pub async fn continue_after_hold(
    app: &AppState,
    room_code: &str,
    player: PlayerId,
) -> Result<(), HintError> {
    if app.ai.is_none() {
        return Err(HintError::NotAnAiGame);
    }
    let cleared = {
        let mut rooms = app.rooms.write().await;
        let room = ai_room_of(&mut rooms, room_code, player)?;
        let current = room.current_ai_hold().map(|hold| hold.revision);
        room.ai_hold = None;
        current
    };
    // The buttons go away at once; the next AI move follows when the teacher has it.
    if let Some(revision) = cleared.and_then(|revision| gaia_protocol::Revision::new(revision).ok())
    {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
    spawn_driver(app.clone(), room_code.to_string());
    Ok(())
}

/// Turns the review of AI turns on or off for an AI game (`Room::ai_review`). Turning it off
/// also ends a wait in progress. In memory only, like the rest of the review state.
pub async fn set_review(
    app: &AppState,
    room_code: &str,
    player: PlayerId,
    enabled: bool,
) -> Result<(), HintError> {
    if app.ai.is_none() {
        return Err(HintError::NotAnAiGame);
    }
    let revision = {
        let mut rooms = app.rooms.write().await;
        let room = ai_room_of(&mut rooms, room_code, player)?;
        room.ai_review = enabled;
        if !enabled {
            room.ai_hold = None;
        }
        room.revision
    };
    log::info!("AI turn review of room {room_code} set to {enabled} by seat {player}");
    if let Ok(revision) = gaia_protocol::Revision::new(revision) {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
    spawn_driver(app.clone(), room_code.to_string());
    Ok(())
}

/// Spare moves asked for at the first rejection of a turn (user 2026-11-24: at most 3 per
/// turn; the worker caps the list at the same number).
const MAX_SPARES: usize = 3;

/// Why a held AI turn was not rejected.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RejectError {
    /// Not an AI game or not its human seat.
    NotAnAiGame,
    /// The AI seats do not wait at a finished turn at the asked revision: nothing was held,
    /// the player played on, an undo request is open, or the game is over.
    NothingHeld,
    /// No spare move is left for the turn, or the teacher had no move without the rejected
    /// ones.
    NoAlternative,
    /// The turn's first position could not be loaded or the restored room not saved.
    Server(String),
}

/// The entry that leaves out the move a rejected turn ended with: that move, or every pass
/// when it was a pass (a rejected pass means "do not pass", not "take another booster").
fn excluded_entry(ended_with: &AiDecision) -> Excluded {
    match ended_with {
        AiDecision::Game(GameAction::Pass { .. }) => Excluded::ActionType("Pass".into()),
        other => Excluded::Move(other.clone()),
    }
}

/// Whether `decision` is one of the moves left out (the worker's own test: the move itself, or
/// its `action.type` for a whole type).
fn is_excluded(decision: &AiDecision, excluded: &[Excluded]) -> bool {
    excluded.iter().any(|entry| match entry {
        Excluded::Move(known) => known == decision,
        Excluded::ActionType(kind) => serde_json::to_value(decision)
            .ok()
            .is_some_and(|value| value["action"]["type"].as_str() == Some(kind.as_str())),
    })
}

/// The replay record for rejecting the turn the room holds at (`hold`), or why it cannot be
/// rejected. The replay starts at the revision the restore is committed as, the next one. A
/// turn that is itself a replay carries its exclusions and unplayed spares on; a spare that is
/// one of the rejected moves is dropped.
fn next_rejection(room: &Room, hold: &AiHold) -> Result<AiRejected, RejectError> {
    let ended_with = hold
        .turn
        .decisions
        .last()
        .ok_or(RejectError::NothingHeld)?;
    let earlier = room.ai_rejected.as_ref().filter(|rejected| {
        rejected.player == hold.turn.player && rejected.start_revision == hold.turn.start_revision
    });
    if earlier.is_some_and(|rejected| rejected.no_alternative) {
        return Err(RejectError::NoAlternative);
    }
    let mut excluded = earlier.map_or_else(Vec::new, |rejected| rejected.excluded.clone());
    let entry = excluded_entry(ended_with);
    if !excluded.contains(&entry) {
        excluded.push(entry);
    }
    let spares = earlier
        .and_then(|rejected| rejected.spares.as_ref())
        .map(|spares| {
            spares
                .iter()
                .filter(|spare| !is_excluded(&spare.decision, &excluded))
                .cloned()
                .collect::<Vec<_>>()
        });
    if spares.as_ref().is_some_and(Vec::is_empty) {
        return Err(RejectError::NoAlternative);
    }
    Ok(AiRejected {
        player: hold.turn.player,
        start_revision: room.revision + 1,
        excluded,
        spares,
        rejections: earlier.map_or(0, |rejected| rejected.rejections) + 1,
        no_alternative: false,
    })
}

/// Takes the room back to the first position of the turn it holds at; the body of the
/// transition `reject_turn` commits. Refused when the room is no longer held at `held`.
fn restore_turn(
    room: &mut Room,
    held: u64,
    restored: &GameState,
    rejection: AiRejected,
) -> Result<(), RuleError> {
    if room.revision != held || room.current_ai_hold().is_none() {
        return Err(RuleError::ActionNotAllowed(
            "the position changed before the AI turn was rejected".into(),
        ));
    }
    // A rejected last setup decision takes the room back out of the game proper (`drive`).
    room.state = if matches!(restored.phase, GamePhase::Setup(_)) {
        RoomState::FactionSelection
    } else {
        RoomState::InGame
    };
    room.game_state = Some(restored.clone());
    room.ai_hold = None;
    room.ai_turn = None;
    room.ai_stalled = None;
    room.ai_rejected = Some(rejection);
    Ok(())
}

/// The replay record that applies to the decision `player` is asked for now: the first
/// decision of the replay (the room is at its start) or a later one of the same turn.
fn rejection_for(room: &Room, player: PlayerId) -> Option<&AiRejected> {
    let rejected = room
        .ai_rejected
        .as_ref()
        .filter(|rejected| rejected.player == player)?;
    let first = room.revision == rejected.start_revision;
    let later = room.ai_turn.as_ref().is_some_and(|turn| {
        turn.player == player
            && turn.start_revision == rejected.start_revision
            && turn.revision == room.revision
    });
    (first || later).then_some(rejected)
}

/// How one decision of a replay is found.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Replay {
    /// A spare move the teacher gave earlier is played without asking again; `left` are the
    /// spares still unplayed.
    Spare { decision: AiDecision, left: Vec<Spare> },
    /// The teacher is asked without the rejected moves.
    Ask(Exclusions),
}

/// The replay step for the decision of `turn`; `None` = the teacher is asked as usual (it had
/// no move without the rejected ones).
///
/// The first decision of the replay takes the next spare, or — at the first rejection, when
/// there are none yet — asks the teacher for its move and the spares in one search. Every
/// later decision of the turn is a search without the rejected moves, so that a rejected
/// action does not come back behind another free action.
fn replay_step(turn: &Turn, rejected: &AiRejected) -> Option<Replay> {
    if rejected.no_alternative {
        return None;
    }
    let first = turn.revision == rejected.start_revision;
    if let (true, Some(spares)) = (first, &rejected.spares) {
        if let Some(position) = spares
            .iter()
            .position(|spare| !is_excluded(&spare.decision, &rejected.excluded))
        {
            let mut left = spares.clone();
            let spare = left.remove(position);
            return Some(Replay::Spare {
                decision: spare.decision,
                left,
            });
        }
    }
    Some(Replay::Ask(Exclusions {
        moves: rejected.excluded.clone(),
        spares: if first && rejected.spares.is_none() {
            MAX_SPARES
        } else {
            0
        },
    }))
}

/// The teacher had no move for the replay of `turn` without the rejected ones (they were all
/// that is legal, or the worker failed): the turn is played without exclusions and cannot be
/// rejected again.
async fn give_up_replay(app: &AppState, room_code: &str, turn: &Turn) {
    let mut rooms = app.rooms.write().await;
    let Some(room) = rooms.get_room_mut(room_code) else {
        return;
    };
    let start = turn.rejected.as_ref().map(|rejected| rejected.start_revision);
    if let Some(rejected) = room
        .ai_rejected
        .as_mut()
        .filter(|rejected| rejected.player == turn.player && Some(rejected.start_revision) == start)
    {
        rejected.no_alternative = true;
        log::warn!(
            "AI seat {} of room {room_code} has no move without the rejected ones; \
             its turn is played without exclusions",
            turn.player
        );
    }
}

/// The player rejects the finished AI turn the room holds at (`Room::ai_hold`): the room goes
/// back to the first position of that turn — as a new revision, like an undo — and the seat
/// plays the turn again without the move that ended it (`replay_step`). What other seats did
/// after that turn's start is gone with it. The rejected turn is kept as a record
/// (`GameRepository::record_ai_reject` and the log): positions where the teacher's move was
/// judged wrong.
pub async fn reject_turn(
    app: &AppState,
    room_code: &str,
    player: PlayerId,
    expected_revision: u64,
) -> Result<(), RejectError> {
    if app.ai.is_none() {
        return Err(RejectError::NotAnAiGame);
    }
    let (hold, rejection, level, teacher) = {
        let mut rooms = app.rooms.write().await;
        let room = ai_room_of(&mut rooms, room_code, player)
            .map_err(|_| RejectError::NotAnAiGame)?;
        let hold = room
            .current_ai_hold()
            .filter(|hold| hold.revision == expected_revision)
            .cloned()
            .ok_or(RejectError::NothingHeld)?;
        let open = room.game_state.as_ref().is_some_and(|state| {
            !matches!(state.phase, GamePhase::Ended { .. })
                && state.undo_state.pending_request.is_none()
        });
        if !open {
            return Err(RejectError::NothingHeld);
        }
        let rejection = next_rejection(room, &hold)?;
        (hold, rejection, room.ai_level.clone(), room.ai_teacher.clone())
    };
    let repository = crate::repository::GameRepository::new(app.db.clone());
    let restored = repository
        .load_snapshot_at_revision(room_code, hold.turn.start_revision)
        .await
        .map_err(|error| RejectError::Server(error.to_string()))?
        .ok_or_else(|| {
            RejectError::Server(format!(
                "snapshot revision {} was not found",
                hold.turn.start_revision
            ))
        })?;
    let outcome = coordinator::apply_server_transition(app, room_code, |room| {
        restore_turn(room, expected_revision, &restored, rejection.clone())
    })
    .await
    .map_err(|error| match error {
        CommandError::Rule(_) | CommandError::RevisionConflict { .. } => RejectError::NothingHeld,
        other => RejectError::Server(other.to_string()),
    })?;
    let restored_revision = outcome.revision.get();
    let record = serde_json::json!({
        "accepted": false,
        "kind": "ai_reject",
        "room": room_code,
        "player": hold.turn.player,
        "held_revision": expected_revision,
        "turn_start_revision": hold.turn.start_revision,
        "restored_revision": restored_revision,
        "rejected_turn": hold.turn.decisions,
        "excluded": rejection.excluded,
        "rejections": rejection.rejections,
        "level": level,
        "teacher": teacher,
    });
    log::info!("AI turn rejected {record}");
    if let Err(error) = repository
        .record_ai_reject(room_code, restored_revision, &record)
        .await
    {
        log::error!("the record of the rejected AI turn of room {room_code} was not saved: {error}");
    }
    coordinator::broadcast_snapshot(app, room_code, outcome.revision).await;
    spawn_driver(app.clone(), room_code.to_string());
    Ok(())
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

/// Marks the AI seats as stopped at the revision the room is at now and returns that revision.
/// For a stop that is the server's, not the teacher's (`stall_on_server_error`): the failing
/// step came after the seat's move was read, so the mark cannot go on the revision of a `Turn`.
fn mark_server_stall(room: &mut Room, player: PlayerId) -> u64 {
    room.ai_stalled = Some(AiStall {
        revision: room.revision,
        player,
        reason: AiStallReason::ServerError,
    });
    room.revision
}

/// The driver is about to end on a server error (the round could not be ended after the move
/// of `player`, or that move could not be saved): say so on the game screen, with the retry
/// button, instead of leaving the seats silent. `retry` runs the round end again.
async fn stall_on_server_error(app: &AppState, room_code: &str, player: PlayerId) {
    let revision = {
        let mut rooms = app.rooms.write().await;
        let Some(room) = rooms.get_room_mut(room_code) else {
            return;
        };
        mark_server_stall(room, player)
    };
    if let Ok(revision) = gaia_protocol::Revision::new(revision) {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
}

async fn drive(app: &AppState, pool: &Arc<AiPool>, room_code: &str) {
    // A full game has a few hundred decisions; this only guards against a logic loop.
    let mut conflicts_in_a_row = 0;
    let mut teacher_failures = 0;
    let pause = pool.config.move_pause;
    let mut last_move = std::time::Instant::now();
    for _ in 0..2000 {
        pool.before_room_read(room_code);
        let Some(turn) = next_ai_turn(app, room_code).await else {
            return;
        };
        // The teacher workers do not play the setup auction; AI seats bid with ai_bidding.
        let bid = crate::ai_bidding::decide(&turn.state, turn.player);
        // A move the player may look at and reject (`note_ai_move`): the teacher's own, and
        // not one of the queue answers (charge offers, income order) the AI seats give in
        // between other seats' turns.
        let reviewed = bid.is_none() && !answers_a_queue(&turn.state);
        // A decision of the replay of a rejected turn (`reject_turn`) is a spare move or a
        // search without the rejected moves; the spares still unplayed are saved with the move.
        let replay = turn
            .rejected
            .as_ref()
            .filter(|_| reviewed)
            .and_then(|rejected| replay_step(&turn, rejected));
        let mut spares_left = None;
        let decision = match (bid, replay) {
            (Some(action), _) => Some(AiDecision::Setup(action)),
            (None, Some(Replay::Spare { decision, left })) => {
                log::info!(
                    "AI replay room={room_code} revision={} player={} spare={}",
                    turn.revision,
                    turn.player,
                    serde_json::to_string(&decision).unwrap_or_default()
                );
                spares_left = Some(left);
                Some(decision)
            }
            (None, Some(Replay::Ask(exclusions))) => {
                let answer = pool
                    .ask(
                        room_code,
                        room_code,
                        &turn.state,
                        turn.player,
                        turn.level.as_deref(),
                        turn.teacher.as_deref(),
                        &exclusions,
                    )
                    .await;
                let Some(answer) = answer else {
                    // The pool has logged why. The seat's turn goes on without exclusions.
                    give_up_replay(app, room_code, &turn).await;
                    continue;
                };
                log::info!(
                    "AI replay room={room_code} revision={} player={} excluded={} replaced={} answer={}",
                    turn.revision,
                    turn.player,
                    answer.excluded,
                    answer.replaced,
                    serde_json::to_string(&answer.decision).unwrap_or_default()
                );
                if exclusions.spares > 0 {
                    spares_left = Some(
                        answer
                            .spares
                            .iter()
                            .filter(|spare| spare.decision != answer.decision)
                            .cloned()
                            .collect::<Vec<_>>(),
                    );
                }
                Some(answer.decision)
            }
            (None, None) => {
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
            if !awaited_players(state).contains(&turn.player) {
                return Err(RuleError::NotYourTurn);
            }
            let mut probe = state.clone();
            let events =
                match apply_decision(&mut probe, turn.player, decision.clone(), turn.revision) {
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
            if let (Some(left), Some(rejected)) = (&spares_left, room.ai_rejected.as_mut()) {
                rejected.spares = Some(left.clone());
            }
            if reviewed {
                // Part of this commit: the snapshot of the move already carries the wait.
                note_ai_move(room, &turn, &decision);
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
                    stall_on_server_error(app, room_code, turn.player).await;
                    return;
                }
                // A wait at this turn (`note_ai_move`) came with the commit; the next read of
                // the room finds it and this driver ends.
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
                stall_on_server_error(app, room_code, turn.player).await;
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
    let (cleared, stopped_seat) = {
        let mut rooms = app.rooms.write().await;
        let room = rooms
            .get_room_mut(room_code)
            .ok_or(HintError::NotAnAiGame)?;
        if !is_ai_room(room) || room.dev_human_player != Some(player) {
            return Err(HintError::NotAnAiGame);
        }
        let current = room.current_ai_stall();
        room.ai_stalled = None;
        (
            current.map(|_| room.revision),
            current.map_or(player, |stall| stall.player),
        )
    };
    // The stopped banner goes away at once; the teacher's move follows when it has one.
    if let Some(revision) = cleared.and_then(|revision| gaia_protocol::Revision::new(revision).ok())
    {
        coordinator::broadcast_snapshot(app, room_code, revision).await;
    }
    log::info!("AI retry asked in room {room_code} by seat {player}");
    // A stop on a failed round end leaves no seat to move, so the driver alone would find
    // nothing to do: run that step again first (it does nothing unless the round is over).
    if let Err(error) = TurnManagementService::maybe_end_round(app, room_code).await {
        log::error!("maybe_end_round failed for room {room_code}: {error}");
        stall_on_server_error(app, room_code, stopped_seat).await;
        return Ok(());
    }
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
    if !awaited_players(state).contains(&player) || state.undo_state.pending_request.is_some() {
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

/// `revision` is the room revision the decision is applied at: an AI seat's move keeps the undo
/// history in step with the game (`apply_server_seat_action`).
fn apply_decision(
    state: &mut GameState,
    player: PlayerId,
    decision: AiDecision,
    revision: u64,
) -> Result<Vec<gaia_engine::game_state::GameEvent>, RuleError> {
    match decision {
        AiDecision::Game(action) => apply_server_seat_action(state, player, action, revision),
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
            ai_review: false,
            ai_turn: None,
            ai_hold: None,
            ai_rejected: None,
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

    #[test]
    fn every_seat_of_a_charge_or_income_queue_is_awaited_and_asked_as_its_front() {
        use gaia_engine::game_state::{HexCoord, PendingCharge, PendingIncomeOrder};
        let (room, human) = ai_room_waiting_for_its_human();
        let mut state = room.game_state.expect("the room has a game");
        // One seat outside a queue: only that seat is awaited, and the copy is unchanged.
        assert_eq!(awaited_players(&state), vec![human]);
        assert_eq!(asked_as(&state, human).phase, state.phase);

        let offer = |player| PendingCharge {
            player,
            hex: HexCoord::new(0, 0),
            max_power: 1,
        };
        // Seat 8 has two offers (a nested build): one seat, its first offer first.
        state.phase = GamePhase::ChargePowerPending {
            queue: vec![offer(8), offer(7), offer(8), offer(9)],
            resume_active_player: Some(0),
        };
        assert_eq!(awaited_players(&state), vec![8, 7, 9]);
        let asked = asked_as(&state, 9);
        assert_eq!(RuleEngine::decision_player(&asked).ok().flatten(), Some(9));
        match &asked.phase {
            GamePhase::ChargePowerPending { queue, .. } => assert_eq!(
                queue.iter().map(|entry| entry.player).collect::<Vec<_>>(),
                vec![9, 8, 7, 8]
            ),
            other => panic!("expected ChargePowerPending, got {other:?}"),
        }

        let order = |player| PendingIncomeOrder {
            player,
            charge_amount: 4,
            bonus_tokens: 1,
        };
        state.phase = GamePhase::IncomeOrderPending {
            queue: vec![order(7), order(10)],
            round: 2,
        };
        assert_eq!(awaited_players(&state), vec![7, 10]);
        let asked = asked_as(&state, 10);
        assert_eq!(RuleEngine::decision_player(&asked).ok().flatten(), Some(10));
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
    fn a_server_error_stop_is_marked_at_the_revision_the_room_is_at() {
        let (mut room, _) = ai_room_waiting_for_its_human();
        room.revision = 8;
        assert_eq!(mark_server_stall(&mut room, 2), 8);
        assert_eq!(
            coordinator::room_snapshot_view(&room)["ai_stalled"],
            serde_json::json!({"revision": 8, "player": 2, "reason": "server_error"})
        );
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

    /// The reconnect race: the driver read a paused room and is about to end when the player
    /// comes back and asks for a driver. The request must not be dropped.
    #[test]
    fn a_start_asked_while_the_driver_ends_makes_it_drive_again() {
        let pool = pool_with_teachers(None);
        assert!(pool.try_start_driving("ROOM"));
        // The driver reads the room (paused) and decides to end ...
        pool.before_room_read("ROOM");
        // ... the player reconnects: the room is unpaused and a driver is asked for ...
        assert!(!pool.try_start_driving("ROOM"));
        // ... so the ending driver stays and reads the room again,
        assert!(pool.finish_driving("ROOM"));
        // once: with nothing asked since, it ends and the next request starts a new driver.
        pool.before_room_read("ROOM");
        assert!(!pool.finish_driving("ROOM"));
        assert!(pool.try_start_driving("ROOM"));
    }

    /// A request made before the driver's last read of the room was answered by that read
    /// (every AI move asks for a driver): it does not make the driver go around again.
    #[test]
    fn a_start_asked_before_the_last_room_read_does_not_repeat_the_drive() {
        let pool = pool_with_teachers(None);
        assert!(pool.try_start_driving("ROOM"));
        assert!(!pool.try_start_driving("ROOM"));
        pool.before_room_read("ROOM");
        assert!(!pool.finish_driving("ROOM"));
        // Another room's driver is not affected by this room's requests.
        assert!(pool.try_start_driving("OTHER"));
        assert!(pool.try_start_driving("ROOM"));
        assert!(!pool.try_start_driving("ROOM"));
        assert!(!pool.finish_driving("OTHER"));
        assert!(pool.finish_driving("ROOM"));
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

    // ── Review of AI turns (research/strategy/ai-move-reject-design.md, stage 2a) ──

    fn free_action() -> AiDecision {
        AiDecision::Game(GameAction::FreeAction {
            kind: gaia_engine::rules::actions::FreeActionKind::PowerToCredit,
            count: 1,
        })
    }

    fn pass() -> AiDecision {
        AiDecision::Game(GameAction::Pass { booster_id: None })
    }

    /// The helper room's game in the action phase of `round` with `player` to act.
    fn action_phase(room: &Room, player: PlayerId, round: u8) -> GameState {
        let mut state = room.game_state.clone().expect("the room has a game");
        state.turn_order = vec![7, 8, 9, 10];
        state.round = round;
        let active_player = state
            .turn_order
            .iter()
            .position(|seat| *seat == player)
            .expect("a seat of the game");
        state.phase = GamePhase::ActionPhase { active_player };
        state
    }

    fn asked_at(room: &Room, player: PlayerId, state: &GameState) -> Turn {
        Turn {
            revision: room.revision,
            player,
            state: state.clone(),
            level: None,
            teacher: None,
            rejected: rejection_for(room, player).cloned(),
        }
    }

    /// The helper room with the review on, an AI seat and another seat that is not the human.
    fn reviewed_room() -> (Room, PlayerId, PlayerId) {
        let (mut room, human) = ai_room_waiting_for_its_human();
        room.ai_review = true;
        let mut others = [7, 8, 9, 10].into_iter().filter(|seat| *seat != human);
        let (ai, other) = (others.next().unwrap(), others.next().unwrap());
        (room, ai, other)
    }

    /// What `coordinator::apply_server_transition` does to the in-memory room around a
    /// transition of the server itself: the revision advances and a current wait goes along.
    fn server_transition(room: &mut Room, mutate: impl FnOnce(&mut Room) -> bool) -> bool {
        let waited = room.current_ai_hold().is_some();
        let result = mutate(room);
        let next = room.revision + 1;
        room.advance_by_server(waited, next);
        result
    }

    /// The AI seat's move as `drive` commits it: applied (`after` is the state it leads to),
    /// noted in the same transition, then the revision advances.
    fn commit_ai_move(room: &mut Room, turn: &Turn, decision: &AiDecision, after: GameState) -> bool {
        assert_eq!(room.revision, turn.revision, "the move is applied where it was asked");
        server_transition(room, |room| {
            room.game_state = Some(after);
            note_ai_move(room, turn, decision)
        })
    }

    #[test]
    fn a_free_action_keeps_the_turn_and_the_move_after_it_ends_it() {
        let (mut room, ai, other) = reviewed_room();
        // Revision 5: the AI seat is asked, plays a free action and is still to act at 6.
        let asked = action_phase(&room, ai, 1);
        room.game_state = Some(asked.clone());
        let first = asked_at(&room, ai, &asked);
        assert!(!commit_ai_move(&mut room, &first, &free_action(), asked.clone()));
        assert_eq!((room.revision, room.current_ai_hold()), (6, None));
        // Revision 6: it passes; the room waits for another seat at 7.
        let second = asked_at(&room, ai, &asked);
        let after = action_phase(&room, other, 1);
        assert!(commit_ai_move(&mut room, &second, &pass(), after));
        let hold = room.current_ai_hold().cloned().expect("the AI seats wait");
        assert_eq!(hold.revision, 7);
        assert_eq!(
            hold.turn,
            AiTurn {
                player: ai,
                start_revision: 5,
                revision: 7,
                decisions: vec![free_action(), pass()],
            }
        );
        // The snapshot of that revision carries it; the player playing on ends the wait.
        let view = coordinator::room_snapshot_view(&room);
        assert_eq!(view["ai_review"], true);
        assert_eq!(view["ai_hold"]["turn"]["start_revision"], 5);
        assert_eq!(view["ai_hold"]["turn"]["decisions"][1]["action"]["type"], "Pass");
        room.revision = 8;
        assert_eq!(room.current_ai_hold(), None);
        assert!(coordinator::room_snapshot_view(&room).get("ai_hold").is_none());
    }

    #[test]
    fn without_the_review_the_turn_is_recorded_and_nothing_waits() {
        let (mut room, ai, other) = reviewed_room();
        room.ai_review = false;
        let asked = action_phase(&room, ai, 1);
        room.game_state = Some(asked.clone());
        let first = asked_at(&room, ai, &asked);
        assert!(!commit_ai_move(&mut room, &first, &free_action(), asked.clone()));
        assert_eq!(room.ai_turn.as_ref().map(|turn| turn.decisions.len()), Some(1));
        let second = asked_at(&room, ai, &asked);
        let after = action_phase(&room, other, 1);
        assert!(!commit_ai_move(&mut room, &second, &pass(), after));
        // The finished turn is not kept: nothing waits and nothing could be rejected.
        assert_eq!((room.ai_hold.as_ref(), room.ai_turn.as_ref()), (None, None));
        assert!(coordinator::room_snapshot_view(&room).get("ai_review").is_none());
    }

    #[test]
    fn a_main_action_ends_the_turn_even_when_the_same_seat_acts_next() {
        // The other seats have passed: the seat's next decision is a new turn.
        let (mut room, ai, _) = reviewed_room();
        let asked = action_phase(&room, ai, 1);
        room.game_state = Some(asked.clone());
        let turn = asked_at(&room, ai, &asked);
        let action = AiDecision::Game(GameAction::AcademyQicAction);
        assert!(commit_ai_move(&mut room, &turn, &action, asked.clone()));
        // The next turn of the seat starts its own record at the revision it is asked at.
        room.ai_hold = None;
        let next = asked_at(&room, ai, &asked);
        assert!(commit_ai_move(&mut room, &next, &pass(), asked.clone()));
        let hold = room.current_ai_hold().expect("the AI seats wait");
        assert_eq!((hold.turn.start_revision, hold.turn.decisions.len()), (6, 1));
    }

    #[test]
    fn the_round_end_takes_the_wait_along_and_a_command_of_the_player_ends_it_for_good() {
        // The AI seat passes at revision 5 and the round ends with it.
        let pass_that_ends_the_round = || {
            let (mut room, ai, other) = reviewed_room();
            let asked = action_phase(&room, ai, 1);
            room.game_state = Some(asked.clone());
            let turn = asked_at(&room, ai, &asked);
            let after = action_phase(&room, other, 1);
            assert!(commit_ai_move(&mut room, &turn, &pass(), after));
            assert_eq!(room.current_ai_hold().map(|hold| hold.revision), Some(6));
            (room, other)
        };
        let next_round = |room: &mut Room, first: PlayerId| {
            let state = action_phase(room, first, 2);
            server_transition(room, |room| {
                room.game_state = Some(state);
                true
            });
        };

        // The server starts the next round right away: the player still looks at that pass.
        let (mut room, other) = pass_that_ends_the_round();
        next_round(&mut room, other);
        let hold = room.current_ai_hold().expect("the wait went along");
        assert_eq!((room.revision, hold.revision, hold.turn.start_revision), (7, 7, 5));

        // The player answers before the server gets to the round end (a charge answer between
        // the AI move's broadcast and `maybe_end_round`): that is the same as [continue], and
        // the round end after it must not put the old turn's wait on the player's revision.
        let (mut room, other) = pass_that_ends_the_round();
        room.revision += 1; // the player's command (`coordinator::apply_command`)
        assert_eq!(room.current_ai_hold(), None);
        next_round(&mut room, other);
        assert_eq!((room.revision, room.current_ai_hold()), (8, None));
        assert!(coordinator::room_snapshot_view(&room).get("ai_hold").is_none());
    }

    #[test]
    fn the_turn_ends_with_the_round_and_a_setup_decision_is_a_turn_of_its_own() {
        let (room, ai, _) = reviewed_room();
        let asked = action_phase(&room, ai, 1);
        assert!(turn_goes_on(&asked, &free_action(), &asked, ai));
        // A new round with the same seat first is not the same turn.
        assert!(!turn_goes_on(&asked, &free_action(), &action_phase(&room, ai, 2), ai));
        // Setup: the seat that places again right away is asked as a new turn.
        let setup = room.game_state.clone().expect("the room has a game");
        assert!(matches!(setup.phase, GamePhase::Setup(_)));
        let placing = required_player(&setup).expect("a seat places");
        assert!(!turn_goes_on(&setup, &pass(), &setup, placing));
    }

    #[test]
    fn a_move_asked_elsewhere_than_the_record_reached_starts_a_new_turn() {
        let (mut room, ai, _) = reviewed_room();
        let asked = action_phase(&room, ai, 1);
        room.game_state = Some(asked.clone());
        let first = asked_at(&room, ai, &asked);
        assert!(!commit_ai_move(&mut room, &first, &free_action(), asked.clone()));
        // An undo or a restart in between: the seat is asked at 9, not at 6.
        room.revision = 9;
        let again = asked_at(&room, ai, &asked);
        assert!(!commit_ai_move(&mut room, &again, &free_action(), asked.clone()));
        let record = room.ai_turn.as_ref().expect("a turn is recorded");
        assert_eq!((record.start_revision, record.decisions.len()), (9, 1));
    }

    #[test]
    fn an_ordinary_request_has_the_old_keys_and_a_rejected_turn_adds_its_own() {
        let (room, human) = ai_room_waiting_for_its_human();
        let state = room.game_state.as_ref().expect("the room has a game");
        let plain = choose_request("ROOM", human, "hard", state, &Exclusions::default());
        let mut keys: Vec<&str> = plain
            .as_object()
            .expect("an object")
            .keys()
            .map(String::as_str)
            .collect();
        keys.sort_unstable();
        assert_eq!(keys, ["level", "op", "player", "room", "state"]);

        let exclusions = Exclusions {
            moves: vec![Excluded::Move(pass()), Excluded::ActionType("Pass".into())],
            spares: 3,
        };
        let asked = choose_request("ROOM", human, "hard", state, &exclusions);
        // A move goes out as the worker gave it; the worker matches whole types on `action.type`.
        assert_eq!(asked["exclude"][0], serde_json::json!(pass()));
        assert_eq!(asked["exclude"][0]["phase"], "Game");
        assert_eq!(asked["exclude"][0]["action"]["type"], "Pass");
        assert_eq!(asked["exclude"][1], serde_json::json!({ "action_type": "Pass" }));
        assert_eq!(asked["skip_missing"], true);
        assert_eq!(asked["spares"], 3);
    }

    #[test]
    fn a_reply_carries_spares_only_when_they_were_asked_for() {
        let plain: Reply =
            serde_json::from_value(serde_json::json!({ "ok": true, "decision": pass(), "seconds": 0.4 }))
                .expect("an ordinary reply");
        assert!(plain.spares.is_empty() && plain.excluded == 0 && !plain.exclude_fallback);
        let reply: Reply = serde_json::from_value(serde_json::json!({
            "ok": true, "decision": pass(), "seconds": 9.1, "excluded": 2, "exclude_fallback": true,
            "spares": [{ "decision": pass(), "searched": false }, { "decision": free_action(), "searched": true }],
        }))
        .expect("a reply with spares");
        assert_eq!(reply.excluded, 2);
        assert!(reply.exclude_fallback);
        assert_eq!(
            reply.spares,
            vec![
                Spare { decision: pass(), searched: false },
                Spare { decision: free_action(), searched: true },
            ]
        );
    }

    // ── Rejecting a held AI turn (stage 2b) ──

    fn research() -> AiDecision {
        AiDecision::Game(GameAction::AcademyQicAction)
    }

    fn spare(decision: AiDecision) -> Spare {
        Spare {
            decision,
            searched: false,
        }
    }

    /// The reviewed room held at revision 7 after the AI seat's turn [free action, `ended_with`]
    /// that began at revision 5, and the state the turn began in.
    fn held_room(ended_with: AiDecision) -> (Room, PlayerId, PlayerId, GameState) {
        let (mut room, ai, other) = reviewed_room();
        let start = action_phase(&room, ai, 1);
        room.game_state = Some(start.clone());
        let first = asked_at(&room, ai, &start);
        assert!(!commit_ai_move(&mut room, &first, &free_action(), start.clone()));
        let second = asked_at(&room, ai, &start);
        let after = action_phase(&room, other, 1);
        assert!(commit_ai_move(&mut room, &second, &ended_with, after));
        (room, ai, other, start)
    }

    /// `reject_turn`'s transition on the in-memory room.
    fn reject(room: &mut Room, start: &GameState) -> Result<(), RejectError> {
        let hold = room.current_ai_hold().cloned().ok_or(RejectError::NothingHeld)?;
        let rejection = next_rejection(room, &hold)?;
        let held = room.revision;
        assert!(server_transition(room, |room| {
            restore_turn(room, held, start, rejection).is_ok()
        }));
        Ok(())
    }

    #[test]
    fn a_rejected_pass_leaves_out_every_pass_and_another_move_only_itself() {
        assert_eq!(excluded_entry(&pass()), Excluded::ActionType("Pass".into()));
        assert_eq!(excluded_entry(&research()), Excluded::Move(research()));
        let other_booster = AiDecision::Game(GameAction::Pass { booster_id: Some(3) });
        let no_pass = [excluded_entry(&pass())];
        assert!(is_excluded(&other_booster, &no_pass) && is_excluded(&pass(), &no_pass));
        assert!(!is_excluded(&research(), &no_pass) && !is_excluded(&free_action(), &no_pass));
        let no_research = [excluded_entry(&research())];
        assert!(is_excluded(&research(), &no_research) && !is_excluded(&pass(), &no_research));
    }

    #[test]
    fn rejecting_takes_the_room_back_to_the_turn_start_as_a_new_revision() {
        let (mut room, ai, _, start) = held_room(research());
        assert_eq!(room.current_ai_hold().map(|hold| hold.can_reject), Some(true));
        // A stale request (the room moved on, or nothing is held) changes nothing.
        let hold = room.current_ai_hold().cloned().unwrap();
        let rejection = next_rejection(&room, &hold).unwrap();
        assert!(restore_turn(&mut room.clone(), 6, &start, rejection.clone()).is_err());
        let mut played_on = room.clone();
        played_on.revision = 8;
        assert!(restore_turn(&mut played_on, 8, &start, rejection).is_err());

        assert_eq!(reject(&mut room, &start), Ok(()));
        assert_eq!(room.revision, 8);
        assert_eq!(
            room.game_state.as_ref().map(GameState::serialize),
            Some(start.serialize())
        );
        assert_eq!((room.current_ai_hold(), room.ai_turn.as_ref()), (None, None));
        // Only the move that ended the turn is left out, not the free action before it; the
        // teacher has not been asked for spares yet.
        assert_eq!(
            room.ai_rejected,
            Some(AiRejected {
                player: ai,
                start_revision: 8,
                excluded: vec![Excluded::Move(research())],
                spares: None,
                rejections: 1,
                no_alternative: false,
            })
        );
    }

    #[test]
    fn the_replay_asks_once_for_spares_then_searches_every_later_decision_without_the_move() {
        let (mut room, ai, other, start) = held_room(research());
        reject(&mut room, &start).unwrap();
        // First decision of the replay: one search for the move and the spares.
        let first = asked_at(&room, ai, &start);
        let rejected = first.rejected.clone().expect("the replay applies at its start");
        assert_eq!(
            replay_step(&first, &rejected),
            Some(Replay::Ask(Exclusions {
                moves: vec![Excluded::Move(research())],
                spares: MAX_SPARES,
            }))
        );
        // The teacher answers a free action and two spares; `drive` saves them with the move.
        room.ai_rejected.as_mut().unwrap().spares = Some(vec![spare(pass()), spare(research())]);
        assert!(!commit_ai_move(&mut room, &first, &free_action(), start.clone()));
        // Later decision of the same turn: a search without the rejected move, no spares.
        let later = asked_at(&room, ai, &start);
        let rejected = later.rejected.clone().expect("the replay applies to the whole turn");
        assert_eq!(
            replay_step(&later, &rejected),
            Some(Replay::Ask(Exclusions {
                moves: vec![Excluded::Move(research())],
                spares: 0,
            }))
        );
        // Another seat's decision, or this seat's next turn, is asked as usual.
        assert_eq!(rejection_for(&room, other), None);
        let after = action_phase(&room, other, 1);
        assert!(commit_ai_move(&mut room, &later, &pass(), after));
        assert_eq!(rejection_for(&room, ai), None);
        // The replay is held like any turn and says what is left: one rejection so far and
        // two spares (the rejected move among them is dropped when it is rejected again).
        let hold = room.current_ai_hold().expect("the replay is held");
        assert_eq!((hold.rejections, hold.spares_left, hold.can_reject), (1, Some(2), true));
        assert_eq!(hold.turn.start_revision, 8);
    }

    #[test]
    fn later_rejections_play_the_spares_and_stop_when_none_is_left() {
        let (mut room, ai, other, start) = held_room(research());
        reject(&mut room, &start).unwrap();
        // The first replay ended with a pass; the spares are a pass with another booster and
        // a free action.
        let other_booster = AiDecision::Game(GameAction::Pass { booster_id: Some(3) });
        let first = asked_at(&room, ai, &start);
        room.ai_rejected.as_mut().unwrap().spares =
            Some(vec![spare(other_booster), spare(free_action())]);
        let after = action_phase(&room, other, 1);
        assert!(commit_ai_move(&mut room, &first, &pass(), after.clone()));

        // Second rejection: no pass at all any more, so the pass among the spares is dropped
        // and the free action is played without asking the teacher.
        reject(&mut room, &start).unwrap();
        let rejected = room.ai_rejected.clone().unwrap();
        assert_eq!(rejected.rejections, 2);
        assert_eq!(
            rejected.excluded,
            vec![Excluded::Move(research()), Excluded::ActionType("Pass".into())]
        );
        assert_eq!(rejected.spares, Some(vec![spare(free_action())]));
        let second = asked_at(&room, ai, &start);
        assert_eq!(
            replay_step(&second, &rejected),
            Some(Replay::Spare {
                decision: free_action(),
                left: vec![],
            })
        );
        room.ai_rejected.as_mut().unwrap().spares = Some(vec![]);
        assert!(!commit_ai_move(&mut room, &second, &free_action(), start.clone()));
        let ended = AiDecision::Game(GameAction::FinishGaiaDecision);
        let later = asked_at(&room, ai, &start);
        assert!(commit_ai_move(&mut room, &later, &ended, after));

        // No spare is left: the hold says so and a third rejection is refused, room untouched.
        let hold = room.current_ai_hold().cloned().expect("the replay is held");
        assert_eq!((hold.rejections, hold.spares_left, hold.can_reject), (2, Some(0), false));
        let before = room.clone();
        assert_eq!(reject(&mut room, &start), Err(RejectError::NoAlternative));
        assert_eq!((room.revision, room.current_ai_hold()), (before.revision, Some(&hold)));
    }

    #[test]
    fn a_turn_without_another_move_is_played_as_the_teacher_chose_and_not_rejected_again() {
        let (mut room, ai, other, start) = held_room(pass());
        reject(&mut room, &start).unwrap();
        // The teacher had no move without a pass (`give_up_replay`).
        room.ai_rejected.as_mut().unwrap().no_alternative = true;
        let again = asked_at(&room, ai, &start);
        assert_eq!(replay_step(&again, again.rejected.as_ref().unwrap()), None);
        let after = action_phase(&room, other, 1);
        assert!(commit_ai_move(&mut room, &again, &pass(), after));
        let hold = room.current_ai_hold().expect("the turn is held");
        assert_eq!((hold.rejections, hold.can_reject), (1, false));
        assert_eq!(reject(&mut room, &start), Err(RejectError::NoAlternative));
    }
}
