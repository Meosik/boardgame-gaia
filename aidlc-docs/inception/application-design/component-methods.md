# Component Methods — 가이아 프로젝트 온라인

> 상세 비즈니스 로직은 CONSTRUCTION 단계 Functional Design에서 정의됨.
> 여기서는 메서드 시그니처와 고수준 목적만 기술.

---

## gaia-engine 크레이트

### Randomizer

```rust
impl Randomizer {
    pub fn new(seed: &str) -> Self;
    pub fn generate_setup(player_count: u8) -> GameSetup;
    // player_count: 항상 4 (고정)
    // GameSetup: 팩션 쌍, 테크 타일, 라운드 타일, 부스터, 최종 득점 타일, 맵 섹터 배치

    pub fn generate_random_seed() -> String;
    // 새 랜덤 시드 생성 (12자리 숫자 문자열)

    fn shuffle<T>(rng: &mut PrngState, items: &mut Vec<T>);
    // Fisher-Yates 셔플 (기존 랜더마이저 알고리즘 동일)
}
```

### GameState

```rust
impl GameState {
    pub fn new(setup: GameSetup, factions: [FactionId; 4]) -> Self;
    pub fn apply_action(&mut self, action: GameAction) -> Result<Vec<GameEvent>, RuleError>;
    // 액션 적용 후 발생한 이벤트 목록 반환
    pub fn get_valid_actions(&self, player: PlayerId) -> Vec<GameAction>;
    // 현재 플레이어가 수행 가능한 모든 유효 액션
    pub fn serialize(&self) -> serde_json::Value;
    // 스냅샷용 직렬화
    pub fn deserialize(json: serde_json::Value) -> Result<Self, DeserializeError>;
}
```

### FactionRegistry

```rust
impl FactionRegistry {
    pub fn get(faction_id: FactionId) -> &FactionDefinition;
    pub fn all_factions() -> Vec<FactionId>;
    // 18개 팩션 목록
    pub fn get_ability(&self, faction: FactionId) -> Box<dyn FactionAbility>;
    // 팩션 특수 능력 인스턴스 반환
}

// Faction Ability trait (복잡한 특수 능력용)
pub trait FactionAbility {
    fn on_build(&self, state: &GameState, hex: HexCoord) -> Vec<GameEvent>;
    fn on_research(&self, state: &GameState, track: ResearchTrack) -> Vec<GameEvent>;
    fn passive_income(&self, state: &GameState) -> Resources;
    fn special_action(&self, state: &GameState) -> Option<Box<dyn SpecialAction>>;
}
```

### RuleEngine

```rust
impl RuleEngine {
    pub fn validate_action(state: &GameState, action: &GameAction) -> Result<(), RuleError>;
    // 액션 유효성 검사 (상태 변이 없음)
    pub fn apply_action(state: &mut GameState, action: GameAction) -> Result<Vec<GameEvent>, RuleError>;
    // 유효성 검사 + 상태 변이 + 이벤트 생성
    pub fn get_terraforming_cost(from: PlanetType, to: PlanetType, track_level: u8) -> u8;
    // 테라포밍 비용 계산
    pub fn get_navigation_range(state: &GameState, player: PlayerId) -> u8;
    // 현재 항법 사거리 계산
    pub fn can_form_federation(state: &GameState, player: PlayerId, hexes: &[HexCoord]) -> bool;
    // 연방 형성 가능 여부 검사
}
```

### ScoringEngine

```rust
impl ScoringEngine {
    pub fn calculate_round_score(state: &GameState, round: u8) -> HashMap<PlayerId, i32>;
    // 현재 라운드 득점 타일 기준 점수 계산
    pub fn calculate_final_score(state: &GameState) -> FinalScoreBreakdown;
    // 최종 득점: 라운드 합계, 연방, 리서치, 구조물, 최종 타일, 비딩 차감 포함
    pub fn apply_bid_penalties(scores: &mut FinalScoreBreakdown, bids: &BidResults);
    // 비딩 낙찰 VP 차감 적용
}
```

### MapEngine

```rust
impl MapEngine {
    pub fn place_sectors(setup: &GameSetup) -> BoardLayout;
    // 섹터 타일 배치 (Center Balance 적용, 충돌 감지 반복)
    pub fn get_neighbors(hex: HexCoord) -> Vec<HexCoord>;
    pub fn distance(a: HexCoord, b: HexCoord) -> u8;
    pub fn find_federation_path(state: &GameState, player: PlayerId, hexes: &[HexCoord]) -> Option<Vec<HexCoord>>;
    pub fn get_reachable_planets(state: &GameState, player: PlayerId) -> Vec<HexCoord>;
    // 현재 내비게이션 범위 내 도달 가능한 행성
}
```

### BiddingEngine

```rust
impl BiddingEngine {
    pub fn new(players: [PlayerId; 4], faction_pairs: [FactionPair; 4]) -> Self;
    pub fn place_bid(state: &mut BiddingState, player: PlayerId, amount: u32) -> Result<BidEvent, BidError>;
    pub fn pass(state: &mut BiddingState, player: PlayerId) -> Result<BidEvent, BidError>;
    pub fn select_faction(state: &mut BiddingState, player: PlayerId, faction: FactionId, turn_order: u8) -> Result<BidEvent, BidError>;
    // 낙찰 후 팩션 + 턴 순서 선택
    pub fn get_current_bidder(state: &BiddingState) -> PlayerId;
    pub fn is_round_complete(state: &BiddingState) -> bool;
    pub fn get_results(state: &BiddingState) -> Option<BidResults>;
    // 모든 경매 완료 시 최종 결과 반환
}
```

---

## gaia-server 크레이트

### RoomManager

```rust
impl RoomManager {
    pub async fn create_room(host: PlayerSession) -> RoomCode;
    pub async fn join_room(code: RoomCode, player: PlayerSession) -> Result<Room, RoomError>;
    pub async fn get_room(code: &RoomCode) -> Option<Arc<RwLock<Room>>>;
    pub async fn remove_room(code: &RoomCode);
    pub async fn update_room_state(code: &RoomCode, new_state: RoomPhase) -> Result<(), RoomError>;
}
```

### WebSocketHandler

```rust
impl WebSocketHandler {
    pub async fn handle_connection(ws: WebSocket, room_code: RoomCode, player_id: PlayerId);
    // WebSocket 핸드셰이크 후 메시지 루프 시작
    async fn handle_message(msg: WsMessage, ctx: &PlayerContext) -> Result<(), WsError>;
    // 메시지 타입별 라우팅
    async fn send_event(player_id: PlayerId, event: GameEvent);
}

// 메시지 타입
enum WsMessageType {
    GameAction(GameAction),
    BidAction(BidAction),
    CoachingRequest(CoachingRequest),
    Ping,
}
```

### RestApiHandler

```rust
// Axum 라우터 핸들러
async fn create_room(Json(req): Json<CreateRoomRequest>) -> Json<CreateRoomResponse>;
// POST /rooms — 방 생성, 랜더마이저 실행, RoomCode 반환

async fn join_room(Path(code): Path<String>, Json(req): Json<JoinRoomRequest>) -> Result<Json<JoinRoomResponse>, ApiError>;
// POST /rooms/:code/join — 닉네임으로 참가

async fn get_setup(Path(code): Path<String>) -> Result<Json<GameSetup>, ApiError>;
// GET /rooms/:code/setup — 랜더마이저 셋업 조회

async fn regenerate_setup(Path(code): Path<String>) -> Result<Json<GameSetup>, ApiError>;
// POST /rooms/:code/setup/regenerate — 호스트만 호출 가능

async fn get_game_state(Path(code): Path<String>) -> Result<Json<GameStateView>, ApiError>;
// GET /rooms/:code/state — 현재 게임 상태 조회 (재접속용)
```

### GameRepository

```rust
impl GameRepository {
    pub async fn save_snapshot(room_code: &RoomCode, state: &GameState, round: u8) -> Result<(), DbError>;
    pub async fn save_event(room_code: &RoomCode, event: &GameEvent) -> Result<(), DbError>;
    pub async fn load_latest_snapshot(room_code: &RoomCode) -> Result<Option<GameState>, DbError>;
    pub async fn load_events_since(room_code: &RoomCode, after_event_id: i64) -> Result<Vec<GameEvent>, DbError>;
    pub async fn reconstruct_state(room_code: &RoomCode) -> Result<GameState, DbError>;
    // 스냅샷 + 이후 이벤트 재생으로 최신 상태 복원
}
```

---

## gaia-ai 사이드카

### CoachingApi (HTTP 엔드포인트)

```
POST /coach/analyze
  입력: { game_state: GameStateJson, player_id: String }
  출력: { analysis: String, recommended_actions: Vec<ActionSuggestion> }

POST /coach/rules
  입력: { question: String, game_state: GameStateJson }
  출력: { answer: String, rulebook_references: Vec<String> }

POST /coach/strategy
  입력: { game_state: GameStateJson, player_id: String }
  출력: { strategy: String, top3_actions: Vec<ActionSuggestion>, position_summary: String }
```

---

## gaia-frontend (TypeScript)

### WebSocketClient

```typescript
class WebSocketClient {
  connect(roomCode: string, playerId: string): void;
  disconnect(): void;
  sendAction(action: GameAction): void;
  sendBid(bid: BidAction): void;
  onEvent(handler: (event: GameEvent) => void): void;
  onDisconnect(handler: () => void): void;
  reconnect(): void; // 지수 백오프 자동 재연결
}
```

### GameBoard (React Component)

```typescript
interface GameBoardProps {
  boardLayout: BoardLayout;
  gameState: GameStateView;
  validActions: GameAction[];
  onHexClick: (hex: HexCoord) => void;
}
// react-hex-grid 또는 honeycomb.js 기반 렌더링
// 유효 액션 대상 헥스 하이라이트
```

### ActionPanel (React Component)

```typescript
interface ActionPanelProps {
  availableActions: GameAction[];
  isMyTurn: boolean;
  onActionSelect: (action: GameAction) => void;
}
```

### CoachingPanel (React Component)

```typescript
interface CoachingPanelProps {
  gameState: GameStateView;
  playerId: string;
  isOpen: boolean;
  onClose: () => void;
}
// POST /coach/* 호출 후 응답 표시
// 비차단: 게임 진행과 독립
```
