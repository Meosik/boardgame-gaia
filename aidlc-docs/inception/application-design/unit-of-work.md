# Unit of Work — 가이아 프로젝트 온라인

## 개발 순서

```
Unit 1 (gaia-engine)
  → Unit 2 (gaia-server)
    → Unit 3 (gaia-frontend)
      → Unit 4 (gaia-ai)
```

각 단위는 이전 단위 완료 후 시작. Unit 1이 모든 게임 로직의 기반.

---

## Unit 1: gaia-engine

| 항목 | 내용 |
|---|---|
| **유형** | Rust crate (Cargo workspace) |
| **경로** | `gaia-engine/` |
| **책임** | 전체 게임 규칙 로직, 시드 PRNG, 상태 관리 |
| **외부 의존성** | serde, serde_json (직렬화만) — 네트워크/DB 없음 |
| **테스트** | Cargo unit tests + PBT (proptest) |

**포함 컴포넌트:**
- `Randomizer` — 시드 PRNG, 게임 셋업 생성 (Lost Fleet + Center Balance 고정)
- `GameState` — 전체 게임 상태 구조체, serde 직렬화
- `FactionRegistry` — 18팩션 정의 (TOML 데이터 + FactionAbility trait)
- `RuleEngine` — 액션 유효성 검사, 상태 변이
- `ScoringEngine` — 라운드/최종 득점 계산, 비딩 VP 차감
- `MapEngine` — 헥사곤 좌표, 섹터 배치, 충돌 감지, 연방 경로
- `BiddingEngine` — 팩션 비딩 경매 로직

**PBT 대상 (Partial — 순수 함수 + 직렬화):**
- 득점 계산 함수 (ScoringEngine)
- 자원 변환 계산 (RuleEngine)
- 테라포밍 단계 계산 (RuleEngine)
- PRNG 시드 일관성 (Randomizer)
- GameState 직렬화 라운드트립

**코드 구조:**
```
gaia-engine/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── randomizer.rs
│   ├── game_state.rs
│   ├── faction/
│   │   ├── mod.rs
│   │   ├── registry.rs
│   │   ├── ability.rs       # FactionAbility trait
│   │   └── impls/           # 18팩션 개별 구현
│   ├── rules/
│   │   ├── mod.rs
│   │   ├── engine.rs
│   │   ├── actions.rs
│   │   └── terraforming.rs
│   ├── scoring.rs
│   ├── map/
│   │   ├── mod.rs
│   │   ├── engine.rs
│   │   └── hex.rs
│   └── bidding.rs
└── tests/
    ├── unit/
    └── property/             # proptest 기반 PBT
```

---

## Unit 2: gaia-server

| 항목 | 내용 |
|---|---|
| **유형** | Rust crate (Cargo workspace) |
| **경로** | `gaia-server/` |
| **책임** | 실시간 멀티플레이어 서버, REST API, WebSocket, DB 영속성, 프론트엔드 정적 파일 서빙 |
| **외부 의존성** | axum, tokio, serde_json, sqlx, tower-http |
| **테스트** | 통합 테스트 (axum TestClient, sqlx test DB) |
| **의존 단위** | Unit 1 (gaia-engine) |

**포함 컴포넌트:**
- `RoomManager` — 인메모리 룸 관리 (`Arc<RwLock<HashMap>>`)
- `WebSocketHandler` — WebSocket 연결, JSON 메시지 라우팅
- `RestApiHandler` — HTTP 엔드포인트 (Axum 라우터)
- `GameEventBus` — tokio broadcast 채널, 룸 브로드캐스트
- `GameRepository` — sqlx PostgreSQL (이벤트 로그 + 스냅샷)
- `SessionManager` — 닉네임-세션 인메모리 매핑
- 7개 서비스: GameSetupService, FactionSelectionService, GameActionService, TurnManagementService, GameEndService, ReconnectService, CoachingProxyService

**정적 파일 서빙:**
- `tower-http::services::ServeDir`로 `../gaia-frontend/dist/` 서빙
- SPA 라우팅: 404 → index.html 폴백

**코드 구조:**
```
gaia-server/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── router.rs           # Axum 라우터 설정
│   ├── handlers/
│   │   ├── rest.rs
│   │   └── websocket.rs
│   ├── services/
│   │   ├── game_setup.rs
│   │   ├── faction_selection.rs
│   │   ├── game_action.rs
│   │   ├── turn_management.rs
│   │   ├── game_end.rs
│   │   ├── reconnect.rs
│   │   └── coaching_proxy.rs
│   ├── room/
│   │   ├── manager.rs
│   │   └── session.rs
│   ├── repository/
│   │   └── game_repository.rs
│   └── event_bus.rs
├── migrations/             # sqlx 마이그레이션
└── tests/
    └── integration/
```

---

## Unit 3: gaia-frontend

| 항목 | 내용 |
|---|---|
| **유형** | React + TypeScript (Vite) |
| **경로** | `gaia-frontend/` |
| **책임** | 게임 UI, WebSocket 클라이언트, 헥사곤 보드 렌더링 |
| **외부 의존성** | react, typescript, vite, react-hex-grid (또는 honeycomb.js), zustand |
| **테스트** | vitest + React Testing Library (컴포넌트 테스트) |
| **빌드 출력** | `dist/` → gaia-server가 서빙 |
| **의존 단위** | Unit 2 (gaia-server API/WebSocket) |

**포함 컴포넌트:**
- `GameBoard` — 헥사곤 보드, 행성 시각화, 유효 액션 하이라이트
- `GameLobby` — 룸 생성/참가, 대기실, 랜더마이저 결과 표시
- `PlayerDashboard` — 자원, 파워 사이클, 리서치 트랙
- `ActionPanel` — 액션 버튼 (내 턴/대기 상태)
- `CoachingPanel` — AI 코칭 오버레이
- `WebSocketClient` — 자동 재연결 (지수 백오프)

**상태 관리:** Zustand store (gameState, roomState, coachingState)

**코드 구조:**
```
gaia-frontend/
├── package.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── GameBoard/
│   │   ├── GameLobby/
│   │   ├── PlayerDashboard/
│   │   ├── ActionPanel/
│   │   └── CoachingPanel/
│   ├── hooks/
│   │   └── useWebSocket.ts
│   ├── store/
│   │   ├── gameStore.ts
│   │   └── roomStore.ts
│   ├── api/
│   │   ├── rest.ts          # REST API 클라이언트
│   │   └── websocket.ts     # WebSocket 클라이언트
│   └── types/
│       └── game.ts          # 공유 타입 정의
└── tests/
```

---

## Unit 4: gaia-ai

| 항목 | 내용 |
|---|---|
| **유형** | Python 사이드카 서비스 (FastAPI) |
| **경로** | `gaia-ai/` |
| **책임** | LLM 코칭 AI (RAG + Qwen 14B), MCTS 스텁 |
| **외부 의존성** | fastapi, uvicorn, langchain (또는 llama-index), qdrant-client |
| **테스트** | pytest + FastAPI TestClient |
| **배포** | 별도 Docker 컨테이너 (포트 8001) |
| **의존 단위** | Unit 2 (HTTP 요청 수신) |

**포함 컴포넌트 (Phase 1 — LLM 코칭):**
- `CoachingApi` — FastAPI 라우터 (analyze, rules, strategy)
- `RagRetriever` — Qdrant 벡터 검색, 룰북 청크 조회
- `LlmClient` — ollama HTTP API (Qwen 14B)
- `RulebookIndexer` — 룰북 PDF → 청크 → 임베딩 → Qdrant 적재 (초기화 스크립트)

**MCTS 스텁 (Phase 2 준비):**
- `MctsApi` — 빈 엔드포인트 정의 (`POST /mcts/best-action` → 501 Not Implemented)
- `MctsEngine` — 빈 클래스/인터페이스 정의 (향후 구현용)

**코드 구조:**
```
gaia-ai/
├── requirements.txt
├── main.py
├── coaching/
│   ├── api.py              # FastAPI 라우터
│   ├── rag_retriever.py
│   └── llm_client.py
├── mcts/
│   ├── api.py              # MCTS 스텁 엔드포인트
│   └── engine.py           # 빈 MCTS 엔진 클래스
├── scripts/
│   └── index_rulebook.py   # 룰북 인덱싱 초기화 스크립트
└── tests/
```

---

## 프로젝트 루트 구조 (Cargo Workspace)

```
gaia-project/               # Git 저장소 루트
├── Cargo.toml              # workspace 정의
├── Cargo.lock
├── gaia-engine/            # Unit 1
├── gaia-server/            # Unit 2
├── gaia-frontend/          # Unit 3 (Cargo workspace 외부, 별도 node project)
├── gaia-ai/                # Unit 4 (Python, Cargo workspace 외부)
├── docker-compose.yml
├── docker-compose.dev.yml
└── docs/                   # aidlc-docs 심볼릭 링크 또는 복사
```

**Cargo.toml (workspace):**
```toml
[workspace]
members = [
    "gaia-engine",
    "gaia-server",
]
resolver = "2"
```

**Docker Compose 서비스:**
```yaml
services:
  gaia-server:    # Unit 1 + 2 (Rust binary)
  gaia-ai:        # Unit 4 (Python FastAPI)
  postgres:       # PostgreSQL 16
  qdrant:         # 벡터 DB
  ollama:         # LLM 모델 서버 (Qwen 14B)
  # gaia-frontend: Nginx 없음 — gaia-server가 dist/ 서빙
```
