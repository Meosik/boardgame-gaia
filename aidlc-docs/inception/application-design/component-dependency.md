# Component Dependencies — 가이아 프로젝트 온라인

## 의존성 매트릭스

| 컴포넌트 | 의존하는 컴포넌트 | 통신 방식 |
|---|---|---|
| gaia-server | gaia-engine | Cargo 크레이트 의존성 (직접 호출) |
| gaia-server → GameActionService | RuleEngine, ScoringEngine, MapEngine | 직접 함수 호출 |
| gaia-server → GameRepository | PostgreSQL | sqlx 비동기 쿼리 |
| gaia-server → CoachingProxyService | gaia-ai | HTTP (reqwest) |
| gaia-frontend → gaia-server | REST API | HTTP/JSON |
| gaia-frontend → gaia-server | WebSocket | JSON 메시지 |
| gaia-ai → LLM (ollama/vLLM) | HTTP API |
| gaia-ai → Qdrant/pgvector | HTTP API / PostgreSQL |

---

## 데이터 흐름 다이어그램

```
[플레이어 브라우저]
     |
     | HTTP REST (초기 로딩, 룸 생성/참가, 셋업 조회)
     | WebSocket JSON (게임 액션, 코칭 요청, 이벤트 수신)
     v
[gaia-server (Axum + tokio)]
     |                    |
     | Cargo dep          | HTTP (reqwest)
     v                    v
[gaia-engine]        [gaia-ai 사이드카]
  Randomizer              |           |
  GameState          [Qdrant/pgvector] [ollama/vLLM]
  RuleEngine          (룰북 벡터 DB)   (Qwen 14B)
  ScoringEngine
  MapEngine
  BiddingEngine
     |
     | sqlx async
     v
[PostgreSQL]
  game_events
  game_snapshots
  rooms
```

---

## 레이어별 통신 프로토콜

### REST API (HTTP/JSON)
**용도**: 비실시간 요청 (상태가 변하지 않거나 일회성 작업)

| 엔드포인트 | 방향 | 설명 |
|---|---|---|
| POST /rooms | Frontend → Server | 룸 생성 |
| POST /rooms/:code/join | Frontend → Server | 룸 참가 |
| GET /rooms/:code/setup | Frontend → Server | 셋업 조회 |
| POST /rooms/:code/setup/regenerate | Frontend → Server | 셋업 재생성 (호스트) |
| GET /rooms/:code/state | Frontend → Server | 재접속 시 전체 상태 조회 |

### WebSocket (JSON 메시지)
**용도**: 실시간 양방향 통신 (게임 진행 중)

**클라이언트 → 서버 메시지:**
```json
{ "type": "game_action", "payload": { "action_type": "build_mine", "hex": [q, r] } }
{ "type": "bid_action", "payload": { "action": "bid", "amount": 3 } }
{ "type": "coaching_request", "payload": { "request_type": "analyze" } }
{ "type": "ping" }
```

**서버 → 클라이언트 이벤트:**
```json
{ "type": "game_state_update", "payload": { ...GameStateView } }
{ "type": "action_applied", "payload": { "player": "...", "action": {...}, "events": [...] } }
{ "type": "round_ended", "payload": { "round": 3, "scores": {...} } }
{ "type": "game_ended", "payload": { "final_scores": {...}, "winner": "..." } }
{ "type": "bidding_update", "payload": { ...BiddingState } }
{ "type": "coaching_response", "payload": { "analysis": "..." } }
{ "type": "error", "payload": { "code": "...", "message": "..." } }
```

### HTTP (gaia-server → gaia-ai)
```
POST http://gaia-ai:8001/coach/analyze
POST http://gaia-ai:8001/coach/rules
POST http://gaia-ai:8001/coach/strategy
```

---

## 컴포넌트 결합도

| 관계 | 결합도 | 설명 |
|---|---|---|
| gaia-server ↔ gaia-engine | 강결합 (의도적) | 동일 워크스페이스, 타입 공유 |
| gaia-server ↔ gaia-ai | 약결합 | HTTP 인터페이스, 독립 배포 |
| gaia-server ↔ PostgreSQL | 중간 | sqlx 쿼리 추상화 |
| gaia-frontend ↔ gaia-server | 약결합 | REST + WebSocket 프로토콜 |

---

## Docker Compose 서비스 구성

```yaml
services:
  gaia-server:     # Rust binary (gaia-server crate)
  gaia-ai:         # Python/Rust AI sidecar
  postgres:        # PostgreSQL 16
  qdrant:          # 벡터 DB (RAG용)
  ollama:          # LLM 모델 서버 (Qwen 14B)
  gaia-frontend:   # Nginx serving built React app
```
