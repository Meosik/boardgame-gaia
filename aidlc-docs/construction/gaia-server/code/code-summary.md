# Code Summary — Unit 2: gaia-server

## 생성 완료 파일 목록

| 파일 | 단계 | 설명 |
|---|---|---|
| `Cargo.toml` | Step 1 | axum 0.7, tokio, sqlx (postgres), tower-http, uuid, reqwest |
| `src/messages.rs` | Step 2 | WS 프로토콜: ClientMessage / ServerMessage (serde JSON) |
| `src/error.rs` | Step 3 | ServerError, IntoResponse (axum), ServerResult alias |
| `src/state.rs` | Step 3 | AppState (db, rooms, sessions, event_bus, ai_base_url) |
| `src/event_bus.rs` | Step 4 | tokio broadcast, 룸별 채널, get_or_create / broadcast / subscribe |
| `src/room/manager.rs` | Step 5 | RoomManager, Room, RoomState (Lobby/Bidding/InGame/Ended) |
| `src/room/session.rs` | Step 6 | SessionManager: UUID 토큰 → (player_id, room_code) |
| `src/room/mod.rs` | Step 5/6 | 모듈 선언 |
| `migrations/20260522000001_create_rooms.sql` | Step 7 | rooms 테이블 |
| `migrations/20260522000002_create_snapshots.sql` | Step 7 | game_snapshots 테이블 |
| `migrations/20260522000003_create_game_events.sql` | Step 7 | game_events 테이블 |
| `src/repository/game_repository.rs` | Step 8 | sqlx runtime query (no DATABASE_URL needed at compile time) |
| `src/repository/mod.rs` | Step 8 | 모듈 선언 |
| `src/services/game_setup.rs` | Step 9 | create_room, regenerate_setup, start_game |
| `src/services/faction_selection.rs` | Step 9 | process_setup_action (BiddingEngine 연동) |
| `src/services/game_action.rs` | Step 9 | RuleEngine 호출 + DB 저장 + broadcast |
| `src/services/turn_management.rs` | Step 9 | maybe_end_round, end_round, start_next_round |
| `src/services/game_end.rs` | Step 9 | ScoringEngine 최종 득점 + DB + broadcast |
| `src/services/reconnect.rs` | Step 9 | 스냅샷 + 이벤트 재생으로 상태 복원 |
| `src/services/coaching_proxy.rs` | Step 9 | HTTP → gaia-ai, 개인 응답 전송 |
| `src/services/mod.rs` | Step 9 | 모듈 선언 |
| `src/handlers/rest.rs` | Step 10 | POST /api/rooms, POST /join, GET /rooms/:code, POST /regenerate |
| `src/handlers/websocket.rs` | Step 11 | WS 업그레이드, JoinRoom, ClientMessage 루프, EventBus 브로드캐스트 |
| `src/handlers/mod.rs` | Step 10/11 | 모듈 선언 |
| `src/router.rs` | Step 12 | Axum 라우터: /api/*, /ws/:room, /, /health + ServeDir SPA 폴백 |
| `src/main.rs` | Step 13 | dotenvy, PgPool, migrate!, axum::serve, graceful shutdown |
| `.env.example` | Step 13 | DATABASE_URL, AI_BASE_URL, PORT, RUST_LOG |
| `tests/integration/mod.rs` | Step 14 | 통합 테스트 진입점 |
| `tests/integration/room_lifecycle.rs` | Step 14 | 룸 생성/참가/정원초과 테스트 (#[ignore] — DB 필요) |
| `tests/integration/websocket_messaging.rs` | Step 14 | WS 메시지 테스트 플레이스홀더 |
| `tests/integration/game_action_flow.rs` | Step 14 | 액션 흐름 테스트 플레이스홀더 |

**총 파일 수**: 31개

---

## 스토리 구현 추적

| User Story | 구현 컴포넌트 | 상태 |
|---|---|---|
| US-01: 게임 룸 생성 | `GameSetupService::create_room`, `POST /api/rooms` | ✅ |
| US-02: 룸 참가 | `RoomManager::join_room`, `POST /api/rooms/:code/join` | ✅ |
| US-03: 랜더마이저 확인/재생성 | `GameSetupService::regenerate_setup` | ✅ |
| US-04: 게임 대기 | `WebSocketHandler` → `PlayerJoined` broadcast | ✅ |
| US-05/06: 팩션 선택/비딩 | `FactionSelectionService::process_setup_action` | ✅ |
| US-07: 게임 시작 | `GameSetupService::start_game` | ✅ |
| US-08/09: 보드/액션 | `GameActionService::process_action` | ✅ |
| US-10: 라운드 패스 | `GameAction::Pass` → RuleEngine | ✅ |
| US-11/14: 라운드 득점 | `TurnManagementService::end_round` → `ScoringEngine` | ✅ |
| US-12: 게임 종료 | `GameEndService::end_game` | ✅ |
| US-13: 리소스 현황 | `ActionApplied` 브로드캐스트에 game_state 포함 | ✅ |
| US-15: 최종 득점 | `ScoringEngine::calculate_final_scoring` | ✅ |
| US-16: AI 코칭 | `CoachingProxyService::request_analysis` | ✅ |
| US-17: 재접속 | `ReconnectService::reconstruct_state` | ✅ |

---

## 주요 공개 API

### REST
```
POST   /api/rooms                    룸 생성
POST   /api/rooms/:code/join         룸 참가 / 재접속
GET    /api/rooms/:code              룸 상태 조회
POST   /api/rooms/:code/regenerate   셋업 재생성 (호스트)
GET    /health                       헬스체크
GET    /ws/:room_code                WebSocket 업그레이드
GET    /*                            React SPA (ServeDir)
```

### WebSocket Protocol
```
ClientMessage → ServerMessage (JSON, serde tag = "type")

Client → Server:
  join_room         { room_code, nickname, session_token? }
  place_setup_action { action }
  place_game_action  { action }
  regenerate_setup   { seed? }
  request_coaching   { question }

Server → Client (broadcast or individual):
  room_joined        { room_code, player_id, session_token, game_setup }
  player_joined      { player_id, nickname, player_count }
  setup_updated      { game_setup }
  game_started       { game_state }
  action_applied     { player_id, events, game_state }
  turn_changed       { active_player }
  round_ended        { round, scores }
  game_ended         { final_scores, winner }
  coaching_response  { response }
  error              { code, message }
```

---

## 아키텍처 결정사항

| 결정 | 이유 |
|---|---|
| `sqlx::query` (non-macro) | DATABASE_URL 없이도 `cargo check` 통과. CI에서 `cargo sqlx prepare` 사용 |
| 인메모리 RoomManager + DB | 게임 중 빠른 읽기, 영속성은 이벤트/스냅샷으로 분리 |
| tokio broadcast 채널 | 룸별 1:N 브로드캐스트, receiver 독립적 드롭 가능 |
| select! 루프 | 클라이언트 수신 + 룸 브로드캐스트를 단일 루프에서 처리 |
| ServeDir + SPA 폴백 | Nginx 없이 gaia-server가 React dist/를 직접 서빙 |
