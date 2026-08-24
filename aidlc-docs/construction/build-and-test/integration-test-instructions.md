# Integration Test Instructions — Gaia Project Online

## 개요

통합 테스트는 실제 PostgreSQL, Qdrant, ollama 서비스가 필요합니다.
개발 환경에서는 `docker-compose.dev.yml`로 인프라만 실행 후 진행합니다.

---

## 사전 준비

```bash
# 인프라 서비스 실행
docker compose -f docker-compose.dev.yml up -d

# 서비스 준비 확인
until docker compose -f docker-compose.dev.yml ps | grep -E "healthy|running" | wc -l | grep -q 3; do sleep 2; done

# DB 마이그레이션 실행
export DATABASE_URL=postgres://gaia:gaiapass@localhost:5432/gaiaproject
cd gaia-server && cargo sqlx migrate run && cd ..
```

---

## Integration 1: gaia-server ↔ PostgreSQL

**대상:** `gaia-server/tests/integration/`

```bash
export DATABASE_URL=postgres://gaia:gaiapass@localhost:5432/gaiaproject

# #[ignore] 해제하여 실행
cargo test -p gaia-server --test integration -- --include-ignored

# 특정 테스트
cargo test -p gaia-server --test integration room_lifecycle -- --include-ignored
cargo test -p gaia-server --test integration websocket_messaging -- --include-ignored
cargo test -p gaia-server --test integration game_action_flow -- --include-ignored
```

**테스트 시나리오:**
| 파일 | 시나리오 |
|---|---|
| `room_lifecycle.rs` | POST /api/rooms → 201, 두 번째 join → player_count 증가, 5번째 join → 409 |
| `websocket_messaging.rs` | WS 연결 → JoinRoom 메시지 → RoomJoined 응답 확인 |
| `game_action_flow.rs` | 4명 입장 → 팩션 선택 → 게임 시작 → 액션 → 상태 브로드캐스트 |

---

## Integration 2: gaia-server ↔ gaia-ai (HTTP)

```bash
# gaia-ai 서버 실행 (별도 터미널)
cd gaia-ai
source .venv/bin/activate
OLLAMA_BASE_URL=http://localhost:11434 QDRANT_URL=http://localhost:6333 \
  uvicorn main:app --port 8001

# gaia-server의 AI 코칭 프록시 테스트
AI_BASE_URL=http://localhost:8001 cargo test -p gaia-server coaching -- --include-ignored
```

**테스트 시나리오:**
- `CoachingProxyService::request_analysis` → gaia-ai `/coach/analyze` → CoachingResponse WS 메시지 반환

---

## Integration 3: gaia-ai ↔ Qdrant + ollama

```bash
cd gaia-ai
source .venv/bin/activate

# 룰북 인덱싱 확인 (이미 완료된 경우 skip)
python scripts/index_rulebook.py

# 실제 서비스 연결 통합 테스트
pytest tests/ -v -m integration
```

**참고:** `pytest -m integration` 마커는 현재 미구현. 필요 시 아래 방식으로 실행:
```bash
# LLM/Qdrant mock 해제 버전 테스트 (실제 연결)
INTEGRATION=1 pytest tests/test_coaching.py::test_analyze_real -v
```

---

## Integration 4: 전체 스택 E2E (Docker Compose)

```bash
# 1. 프론트엔드 빌드
cd gaia-frontend && npm run build && cd ..

# 2. 전체 스택 실행
docker compose up -d --build

# 3. 서비스 준비 대기
until curl -sf http://localhost:8080/health && curl -sf http://localhost:8001/health; do
  echo "Waiting for services..."
  sleep 5
done

# 4. 핵심 REST 흐름 테스트
echo "=== 룸 생성 ==="
ROOM=$(curl -sf -X POST http://localhost:8080/api/rooms \
  -H 'Content-Type: application/json' \
  -d '{"nickname":"TestHost"}' | tee /dev/stderr)
CODE=$(echo $ROOM | python3 -c "import sys,json; print(json.load(sys.stdin)['code'])")
echo "Room code: $CODE"

echo "=== 룸 참가 ==="
curl -sf -X POST "http://localhost:8080/api/rooms/$CODE/join" \
  -H 'Content-Type: application/json' \
  -d '{"nickname":"Player2"}'

echo "=== 룸 상태 조회 ==="
curl -sf "http://localhost:8080/api/rooms/$CODE" | python3 -m json.tool

echo "=== AI 코칭 헬스 ==="
curl -sf http://localhost:8001/health

echo "=== SPA 서빙 확인 ==="
curl -sf http://localhost:8080/ | grep -q "<div id=\"root\">" && echo "SPA OK"

# 5. 정리
docker compose down
```

---

## WebSocket 통합 테스트 (wscat)

```bash
# wscat 설치
npm install -g wscat

# WS 연결 및 JoinRoom 전송
wscat -c "ws://localhost:8080/ws/TESTCD" \
  --execute '{"type":"join_room","room_code":"TESTCD","nickname":"WSTest"}'
# 예상 응답: {"type":"room_joined","room_code":"TESTCD","player_id":0,...}
```

---

## 통합 테스트 합격 기준

| 시나리오 | 기준 |
|---|---|
| 룸 생성/참가 | 201 / player_count 증가 / 5번째 409 |
| WS 연결 | RoomJoined 메시지 수신 |
| AI 코칭 프록시 | CoachingResponse WS 메시지 전달 |
| SPA 서빙 | GET / → index.html 반환 |
| 헬스체크 | 두 서비스 모두 200 |
