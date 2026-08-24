# Unit of Work Dependencies — 가이아 프로젝트 온라인

## 의존성 매트릭스

| 단위 | Unit 1 gaia-engine | Unit 2 gaia-server | Unit 3 gaia-frontend | Unit 4 gaia-ai |
|---|---|---|---|---|
| **Unit 1 gaia-engine** | — | 제공 | — | — |
| **Unit 2 gaia-server** | **의존** (Cargo dep) | — | 제공 (정적 파일 서빙) | 호출 (HTTP) |
| **Unit 3 gaia-frontend** | — | **의존** (REST + WS) | — | — |
| **Unit 4 gaia-ai** | — | 수신 (HTTP) | — | — |

## 의존성 방향

```
Unit 1 (gaia-engine)
    ↑ Cargo 크레이트 의존성
Unit 2 (gaia-server)
    ↑ REST API + WebSocket         ↓ HTTP 코칭 요청
Unit 3 (gaia-frontend)        Unit 4 (gaia-ai)
```

## 단위별 의존성 상세

### Unit 1 → (없음)
- 외부 네트워크/DB 의존성 없음
- `serde`, `serde_json` (직렬화)
- `proptest` (PBT, dev-dependency)
- 완전 독립 — 가장 먼저 개발 가능

### Unit 2 → Unit 1
- **의존 방식**: Cargo.toml `[dependencies]` (`gaia-engine = { path = "../gaia-engine" }`)
- **사용 내용**: GameState, RuleEngine, ScoringEngine, BiddingEngine, Randomizer 등 모든 게임 로직
- **선행 조건**: Unit 1 API 안정화 필요 (타입 변경 시 Unit 2 영향)

### Unit 2 → PostgreSQL
- **의존 방식**: sqlx 런타임 연결
- **선행 조건**: DB 스키마 마이그레이션 먼저 실행

### Unit 2 → Unit 4
- **의존 방식**: HTTP (reqwest) — `POST http://gaia-ai:8001/coach/*`
- **결합도**: 약결합 (HTTP 인터페이스)
- **장애 처리**: gaia-ai 미응답 시 타임아웃 후 "코칭 서비스 일시 불가" 응답

### Unit 3 → Unit 2
- **의존 방식**:
  - REST: `POST /rooms`, `GET /rooms/:code/setup` 등
  - WebSocket: `ws://server/ws/:room_code`
- **선행 조건**: Unit 2 API 엔드포인트 정의 확정 필요
- **빌드 산출물**: `dist/` → Unit 2 gaia-server가 서빙

### Unit 4 → Qdrant + ollama
- **Qdrant**: 룰북 벡터 검색
- **ollama**: Qwen 14B 모델 추론
- **독립성**: Unit 4는 Unit 1/3과 직접 의존성 없음

## 개발 시퀀스 및 블로킹 관계

```
[Week N]   Unit 1 개발 + 테스트 완료
              ↓
[Week N+1] Unit 2 개발 (Unit 1 의존)
              ↓
[Week N+2] Unit 3 개발 (Unit 2 API 필요)
           Unit 4 개발 병렬 가능 (Unit 2 완료 불필요)
              ↓
[Week N+3] 통합 테스트 (전체 Docker Compose)
```

## 공유 타입 및 계약

| 계약 | 위치 | 소비자 |
|---|---|---|
| `GameState` JSON 스키마 | Unit 1 (Rust 구조체 → serde) | Unit 2, Unit 4 |
| `GameAction` JSON 스키마 | Unit 1 | Unit 2, Unit 3 |
| WebSocket 메시지 타입 | Unit 2 (WsMessageType) | Unit 3 |
| REST API 스펙 | Unit 2 (Axum 핸들러) | Unit 3 |
| 코칭 API 스펙 | Unit 4 (FastAPI 라우터) | Unit 2 |

**타입 불일치 주의**: Unit 3 (TypeScript)는 Unit 1/2의 Rust 타입을 수동으로 미러링해야 함. `gaia-frontend/src/types/game.ts`에 Rust 구조체와 동기화된 TypeScript 타입 정의 유지.
