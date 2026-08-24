# Code Generation Plan — Unit 2: gaia-server

## 단위 컨텍스트

| 항목 | 내용 |
|---|---|
| 단위 | Unit 2: gaia-server |
| 경로 | `/home/sohegi/projects/gaia/gaia-server/` |
| 유형 | Rust crate (Cargo workspace member) |
| 의존 단위 | Unit 1 (gaia-engine) |
| 테스트 전략 | Axum 통합 테스트 (TestClient) + sqlx test DB |

## 구현 스토리 (gaia-server 기여)

| 스토리 | 제목 | 담당 컴포넌트 |
|---|---|---|
| US-01 | 게임 룸 생성 | GameSetupService, RoomManager |
| US-02 | 룸 참가 | RoomManager, SessionManager |
| US-03 | 랜더마이저 확인/재생성 | GameSetupService |
| US-04 | 게임 대기 | RoomManager, WebSocketHandler |
| US-05 | 팩션 선택 | FactionSelectionService |
| US-06 | 비딩 경매 | FactionSelectionService, BiddingEngine |
| US-07 | 게임 시작 | GameSetupService |
| US-08 | 게임 보드 | GameActionService, WebSocketHandler |
| US-09 | 액션 수행 | GameActionService |
| US-10 | 라운드 패스 | GameActionService, TurnManagementService |
| US-11 | 라운드 득점 | TurnManagementService, ScoringEngine |
| US-12 | 게임 종료 | GameEndService |
| US-13 | 리소스 현황 | WebSocketHandler (상태 브로드캐스트) |
| US-14 | 라운드 득점 확인 | TurnManagementService |
| US-15 | 최종 득점 | GameEndService |
| US-16 | AI 코칭 | CoachingProxyService |
| US-17 | 재접속 | ReconnectService |

---

## 실행 체크리스트

### Part 1 — Planning
- [x] Step A: 단위 컨텍스트 분석
- [x] Step B: 코드 생성 계획 수립
- [x] Step C: 계획 저장 (이 파일)
- [x] Step D: 계획 승인 대기

### Part 2 — Generation
- [x] Step 1: Cargo.toml 업데이트 (axum, tokio, serde_json, sqlx, tower-http, uuid, dotenvy)
- [x] Step 2: 메시지 타입 — `src/messages.rs` (ClientMessage, ServerMessage WS 프로토콜)
- [x] Step 3: AppState — `src/state.rs` (공유 앱 상태: DB pool, RoomManager, EventBus)
- [x] Step 4: EventBus — `src/event_bus.rs` (tokio broadcast 채널, 룸별 분리)
- [x] Step 5: RoomManager — `src/room/manager.rs` (Arc<RwLock<HashMap>>, 룸 생명주기)
- [x] Step 6: SessionManager — `src/room/session.rs` (닉네임-세션 인메모리 매핑)
- [x] Step 7: DB 마이그레이션 — `migrations/` (rooms, game_events, game_snapshots 테이블)
- [x] Step 8: GameRepository — `src/repository/game_repository.rs` (sqlx PostgreSQL CRUD)
- [x] Step 9: Services (7개) — `src/services/`
- [x] Step 10: REST 핸들러 — `src/handlers/rest.rs` (룸 생성/참가/상태 엔드포인트)
- [x] Step 11: WebSocket 핸들러 — `src/handlers/websocket.rs` (연결/메시지 라우팅/브로드캐스트)
- [x] Step 12: 라우터 — `src/router.rs` (Axum 라우터 조립)
- [x] Step 13: main.rs — Axum 앱 초기화, DB 연결, graceful shutdown
- [x] Step 14: 통합 테스트 — `tests/integration/`
- [x] Step 15: 코드 요약 문서 — `aidlc-docs/construction/gaia-server/code/`

---

## 단계별 상세 설명

### Step 1: Cargo.toml

**의존성:**
```toml
[dependencies]
gaia-engine = { path = "../gaia-engine" }
axum = { version = "0.7", features = ["ws", "macros"] }
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sqlx = { version = "0.8", features = ["runtime-tokio", "postgres", "uuid", "json", "migrate"] }
tower-http = { version = "0.5", features = ["fs", "cors", "trace"] }
uuid = { version = "1", features = ["v4", "serde"] }
dotenvy = "0.15"
log = "0.4"
env_logger = "0.11"
thiserror = "1"
tokio-stream = "0.1"

[dev-dependencies]
axum-test = "15"
tokio = { version = "1", features = ["full", "test-util"] }
```

---

### Step 2: 메시지 타입 (`src/messages.rs`)

WebSocket JSON 프로토콜:

**ClientMessage** (프론트엔드 → 서버):
- `JoinRoom { room_code, nickname }` — 룸 참가/재접속
- `PlaceSetupAction { action: SetupAction }` — 비딩/팩션 선택
- `PlaceGameAction { action: GameAction }` — 게임 액션
- `RegenerateSetup { seed: Option<String> }` — 셋업 재생성 (호스트만)
- `RequestCoaching { question: String }` — AI 코칭 요청

**ServerMessage** (서버 → 프론트엔드):
- `RoomJoined { room_code, player_id, game_setup }` — 룸 참가 확인
- `SetupUpdated { game_setup }` — 셋업 변경 브로드캐스트
- `GameStarted { game_state_view }` — 게임 시작
- `ActionApplied { player_id, events, game_state_view }` — 액션 결과
- `TurnChanged { active_player }` — 턴 변경
- `RoundEnded { round, scores }` — 라운드 종료
- `GameEnded { final_scores, winner }` — 게임 종료
- `CoachingResponse { response }` — AI 코칭 응답
- `Error { code, message }` — 오류

---

### Step 3: AppState (`src/state.rs`)

```rust
#[derive(Clone)]
pub struct AppState {
    pub db: sqlx::PgPool,
    pub rooms: Arc<RwLock<RoomManager>>,
    pub event_bus: Arc<EventBus>,
    pub ai_base_url: String,
}
```

---

### Step 4: EventBus (`src/event_bus.rs`)

```rust
pub struct EventBus {
    // 룸별 broadcast 채널: room_code → sender
    channels: RwLock<HashMap<String, broadcast::Sender<ServerMessage>>>,
}

impl EventBus {
    pub fn get_or_create(&self, room_code: &str) -> broadcast::Sender<ServerMessage>;
    pub fn broadcast(&self, room_code: &str, msg: ServerMessage);
    pub fn subscribe(&self, room_code: &str) -> broadcast::Receiver<ServerMessage>;
    pub fn remove(&self, room_code: &str);
}
```

---

### Step 5: RoomManager (`src/room/manager.rs`)

```rust
pub enum RoomState { Lobby, Bidding, InGame, Ended }

pub struct Room {
    pub code: String,
    pub host_player: PlayerId,
    pub players: Vec<(PlayerId, String)>,  // (id, nickname)
    pub state: RoomState,
    pub game_state: Option<GameState>,
    pub setup: Option<GameSetup>,
    pub seed: String,
}

pub struct RoomManager {
    rooms: HashMap<String, Room>,
}

impl RoomManager {
    pub fn create_room(&mut self, host_nickname: &str, seed: &str) -> (String, PlayerId);
    pub fn join_room(&mut self, code: &str, nickname: &str) -> Result<PlayerId, ServerError>;
    pub fn get_room(&self, code: &str) -> Option<&Room>;
    pub fn get_room_mut(&mut self, code: &str) -> Option<&mut Room>;
    pub fn remove_room(&mut self, code: &str);
}
```

---

### Step 6: SessionManager (`src/room/session.rs`)

```rust
pub struct SessionManager {
    // session_token → (player_id, room_code)
    sessions: HashMap<String, (PlayerId, String)>,
}

impl SessionManager {
    pub fn create_session(&mut self, player_id: PlayerId, room_code: &str) -> String;
    pub fn validate(&self, token: &str) -> Option<(PlayerId, String)>;
    pub fn remove(&mut self, token: &str);
}
```

---

### Step 7: DB 마이그레이션 (`migrations/`)

**20260522000001_create_rooms.sql:**
```sql
CREATE TABLE rooms (
    code VARCHAR(8) PRIMARY KEY,
    seed VARCHAR(64) NOT NULL,
    host_player_id SMALLINT NOT NULL,
    state VARCHAR(16) NOT NULL DEFAULT 'lobby',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**20260522000002_create_game_snapshots.sql:**
```sql
CREATE TABLE game_snapshots (
    id BIGSERIAL PRIMARY KEY,
    room_code VARCHAR(8) NOT NULL REFERENCES rooms(code),
    round SMALLINT NOT NULL,
    snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON game_snapshots (room_code, round DESC);
```

**20260522000003_create_game_events.sql:**
```sql
CREATE TABLE game_events (
    id BIGSERIAL PRIMARY KEY,
    room_code VARCHAR(8) NOT NULL REFERENCES rooms(code),
    round SMALLINT NOT NULL,
    player_id SMALLINT,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX ON game_events (room_code, id);
```

---

### Step 8: GameRepository (`src/repository/game_repository.rs`)

```rust
pub struct GameRepository {
    pool: PgPool,
}

impl GameRepository {
    pub async fn save_setup(&self, code: &str, seed: &str, host: PlayerId) -> Result<()>;
    pub async fn save_snapshot(&self, code: &str, round: u8, state: &GameState) -> Result<()>;
    pub async fn load_latest_snapshot(&self, code: &str) -> Result<Option<GameState>>;
    pub async fn save_event(&self, code: &str, round: u8, player: Option<PlayerId>, event: &GameEvent) -> Result<()>;
    pub async fn load_events_since(&self, code: &str, snapshot_id: i64) -> Result<Vec<GameEvent>>;
    pub async fn update_room_state(&self, code: &str, state: &str) -> Result<()>;
    pub async fn save_final_scores(&self, code: &str, scores: &[(PlayerId, i32)]) -> Result<()>;
}
```

---

### Step 9: Services (7개, `src/services/`)

각 서비스 파일은 `services.md` 흐름 기반 구현:

| 파일 | 서비스 | 핵심 책임 |
|---|---|---|
| `game_setup.rs` | GameSetupService | 룸 생성, 셋업 재생성, 게임 시작 |
| `faction_selection.rs` | FactionSelectionService | 자유 선택 / 비딩 경매 처리 |
| `game_action.rs` | GameActionService | RuleEngine 호출, 이벤트 저장, 브로드캐스트 |
| `turn_management.rs` | TurnManagementService | 턴 진행, 라운드 종료, 라운드 시작 |
| `game_end.rs` | GameEndService | 최종 득점, 게임 종료 이벤트 |
| `reconnect.rs` | ReconnectService | 세션 검증, 상태 재전송 |
| `coaching_proxy.rs` | CoachingProxyService | HTTP → gaia-ai, 개인 전송 |

---

### Step 10: REST 핸들러 (`src/handlers/rest.rs`)

엔드포인트:
- `POST /api/rooms` — 룸 생성 (GameSetupService.create_room)
- `POST /api/rooms/{code}/join` — 룸 참가
- `GET /api/rooms/{code}` — 룸 상태 조회
- `POST /api/rooms/{code}/regenerate` — 셋업 재생성 (호스트만)
- `GET /health` — 헬스체크

---

### Step 11: WebSocket 핸들러 (`src/handlers/websocket.rs`)

- `GET /ws/{room_code}` — WebSocket 업그레이드
- 연결 후 ClientMessage 수신 루프
- EventBus.subscribe()로 ServerMessage 수신 → 클라이언트 전송

---

### Step 12: 라우터 (`src/router.rs`)

```rust
pub fn build_router(state: AppState) -> Router {
    Router::new()
        .route("/api/rooms", post(rest::create_room))
        .route("/api/rooms/:code/join", post(rest::join_room))
        .route("/api/rooms/:code", get(rest::get_room))
        .route("/api/rooms/:code/regenerate", post(rest::regenerate_setup))
        .route("/ws/:room_code", get(websocket::ws_handler))
        .route("/health", get(rest::health))
        .nest_service("/", ServeDir::new("../gaia-frontend/dist")
            .fallback(ServeFile::new("../gaia-frontend/dist/index.html")))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
```

---

### Step 13: main.rs

- `dotenvy::dotenv()` — `.env` 로드
- `sqlx::PgPool::connect()` — DB 연결
- `sqlx::migrate!()` — 마이그레이션 실행
- `AppState` 초기화
- `axum::serve()` — 포트 8080
- `tokio::signal::ctrl_c()` — graceful shutdown

---

### Step 14: 통합 테스트 (`tests/integration/`)

- `room_lifecycle.rs` — 룸 생성 → 참가 → 게임 시작 전체 흐름
- `websocket_messaging.rs` — WS 연결, 메시지 송수신
- `game_action_flow.rs` — 액션 처리 및 상태 브로드캐스트

---

### Step 15: 코드 요약 문서

`aidlc-docs/construction/gaia-server/code/code-summary.md`

---

## 생성 파일 전체 목록

```
gaia-server/
├── Cargo.toml                              ← Step 1
├── .env.example                            ← Step 13
├── migrations/
│   ├── 20260522000001_create_rooms.sql     ← Step 7
│   ├── 20260522000002_create_snapshots.sql ← Step 7
│   └── 20260522000003_create_events.sql    ← Step 7
├── src/
│   ├── main.rs                             ← Step 13
│   ├── router.rs                           ← Step 12
│   ├── state.rs                            ← Step 3
│   ├── messages.rs                         ← Step 2
│   ├── error.rs                            ← Step 3
│   ├── event_bus.rs                        ← Step 4
│   ├── handlers/
│   │   ├── mod.rs                          ← Step 10
│   │   ├── rest.rs                         ← Step 10
│   │   └── websocket.rs                    ← Step 11
│   ├── services/
│   │   ├── mod.rs                          ← Step 9
│   │   ├── game_setup.rs                   ← Step 9
│   │   ├── faction_selection.rs            ← Step 9
│   │   ├── game_action.rs                  ← Step 9
│   │   ├── turn_management.rs              ← Step 9
│   │   ├── game_end.rs                     ← Step 9
│   │   ├── reconnect.rs                    ← Step 9
│   │   └── coaching_proxy.rs               ← Step 9
│   ├── room/
│   │   ├── mod.rs                          ← Step 5
│   │   ├── manager.rs                      ← Step 5
│   │   └── session.rs                      ← Step 6
│   └── repository/
│       ├── mod.rs                          ← Step 8
│       └── game_repository.rs              ← Step 8
└── tests/
    └── integration/
        ├── mod.rs                          ← Step 14
        ├── room_lifecycle.rs               ← Step 14
        ├── websocket_messaging.rs          ← Step 14
        └── game_action_flow.rs             ← Step 14
```

**총 파일 수**: 31개 (소스 27개 + 마이그레이션 3개 + 문서 1개)
