# Application Design — 가이아 프로젝트 온라인 (통합 문서)

## 설계 결정 요약

| 결정 사항 | 선택 |
|---|---|
| 게임 상태 영속성 | Hybrid (이벤트 로그 + 라운드별 스냅샷) |
| 프론트-백엔드 통신 | REST (셋업) + WebSocket (게임 진행) |
| 팩션 구현 | Hybrid (공통 능력: TOML 데이터 주도 / 특수 능력: Rust Trait) |
| AI 코칭 배포 | 사이드카 서비스 (별도 Docker 컨테이너) |
| WebSocket 메시지 | JSON |
| 룸 관리 | 인메모리 (활성 룸) + PostgreSQL (영속 상태) |
| 코드 구성 | Cargo workspace |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                     브라우저 클라이언트                    │
│  [GameLobby] [GameBoard] [PlayerDashboard] [ActionPanel] │
│  [CoachingPanel]  [WebSocketClient]                      │
│         │ REST                  │ WebSocket              │
└─────────┼──────────────────────┼────────────────────────┘
          │                      │
┌─────────▼──────────────────────▼────────────────────────┐
│                  gaia-server (Axum)                      │
│  RestApiHandler    WebSocketHandler    GameEventBus       │
│  GameSetupService  FactionSelectionService               │
│  GameActionService TurnManagementService                  │
│  GameEndService    ReconnectService   CoachingProxyService│
│  RoomManager       SessionManager     GameRepository      │
│         │ Cargo dep               │ HTTP                 │
└─────────┼───────────────────────-┼────────────────────--┘
          │                        │
┌─────────▼────────────┐  ┌────────▼──────────────────────┐
│   gaia-engine        │  │   gaia-ai (사이드카)           │
│   Randomizer         │  │   CoachingApi                  │
│   GameState          │  │   RagRetriever                 │
│   FactionRegistry    │  │   LlmClient                    │
│   RuleEngine         │  └────────┬──────────────────────-┘
│   ScoringEngine      │           │ HTTP
│   MapEngine          │  ┌────────▼──────────────────────┐
│   BiddingEngine      │  │  ollama (Qwen 14B)  │ Qdrant  │
└─────────┬────────────┘  └───────────────────────────────┘
          │ sqlx
┌─────────▼────────────┐
│   PostgreSQL         │
│   game_events        │
│   game_snapshots     │
│   rooms              │
└──────────────────────┘
```

---

## 컴포넌트 목록

**gaia-engine 크레이트:**
- Randomizer — 시드 PRNG, 게임 셋업 생성
- GameState — 게임 상태 단일 소스
- FactionRegistry — 18팩션 정의 (Hybrid: TOML + Trait)
- RuleEngine — 액션 유효성 검사 및 상태 변이
- ScoringEngine — 라운드/최종 득점 계산
- MapEngine — 헥사곤 좌표, 섹터 배치, 연방 경로
- BiddingEngine — 팩션 비딩 경매 로직

**gaia-server 크레이트:**
- RoomManager — 인메모리 룸 관리
- WebSocketHandler — 실시간 연결 및 메시지 라우팅
- RestApiHandler — HTTP 엔드포인트
- GameEventBus — 브로드캐스트 채널
- GameRepository — PostgreSQL 영속성
- SessionManager — 세션 및 재접속 관리
- GameSetupService — 룸 생성·셋업 오케스트레이션
- FactionSelectionService — 팩션 선택 흐름
- GameActionService — 액션 처리 파이프라인
- TurnManagementService — 턴·라운드 진행
- GameEndService — 최종 득점·종료 처리
- ReconnectService — 재접속 상태 복원
- CoachingProxyService — AI 코칭 프록시

**gaia-ai 사이드카:**
- CoachingApi — HTTP 엔드포인트 (analyze/rules/strategy)
- RagRetriever — 룰북 벡터 검색
- LlmClient — Qwen 14B API 클라이언트

**gaia-frontend (React + TypeScript):**
- GameBoard — 헥사곤 보드 렌더링
- GameLobby — 룸 셋업 UI
- PlayerDashboard — 자원·트랙 표시
- ActionPanel — 액션 선택 UI
- CoachingPanel — AI 코칭 오버레이
- WebSocketClient — 실시간 통신

---

## 세부 문서 참조

- 컴포넌트 상세: `components.md`
- 메서드 시그니처: `component-methods.md`
- 서비스 오케스트레이션: `services.md`
- 의존성 및 통신: `component-dependency.md`
