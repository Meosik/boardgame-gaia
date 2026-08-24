# Unit Test Instructions — Gaia Project Online

## 개요

| 단위 | 테스트 프레임워크 | 외부 의존성 |
|---|---|---|
| gaia-engine | Cargo test + proptest (PBT) | 없음 |
| gaia-server | Cargo test (단위 레이어) | 없음 (통합 테스트는 별도) |
| gaia-frontend | vitest + React Testing Library | 없음 |
| gaia-ai | pytest + mock | 없음 (LLM/Qdrant mock) |

---

## Unit 1: gaia-engine

```bash
# 프로젝트 루트에서
cargo test -p gaia-engine

# 상세 출력
cargo test -p gaia-engine -- --nocapture

# 특정 테스트 모듈
cargo test -p gaia-engine scoring
cargo test -p gaia-engine randomizer
cargo test -p gaia-engine map

# PBT (proptest) — 기본값 256 케이스, 느릴 수 있음
PROPTEST_CASES=1000 cargo test -p gaia-engine -- property

# 커버리지 (cargo-llvm-cov 필요)
cargo llvm-cov --package gaia-engine --html
# → target/llvm-cov/html/index.html
```

**주요 테스트 대상:**
- `scoring::tests::*` — 라운드/최종 득점 계산
- `randomizer::tests::*` — PRNG 시드 일관성
- `map::hex::tests::*` — 헥사곤 좌표 연산
- `rules::engine::tests::*` — 액션 유효성
- `bidding::tests::*` — 비딩 경매 로직
- PBT: `game_state` 직렬화 라운드트립, 자원 변환 결과 항상 ≥ 0

---

## Unit 2: gaia-server

```bash
# 단위 레이어 테스트 (DB 불필요)
cargo test -p gaia-server

# 통합 테스트 제외 (DB 필요한 테스트는 #[ignore])
cargo test -p gaia-server -- --skip integration

# 특정 모듈
cargo test -p gaia-server room
cargo test -p gaia-server session
cargo test -p gaia-server event_bus
```

**모듈별 단위 테스트 대상:**
- `room::manager` — 룸 생성, 참가, 정원초과(409)
- `room::session` — UUID 토큰 생성/검증
- `event_bus` — broadcast 채널 생성/제거
- `messages` — serde 직렬화/역직렬화 (ClientMessage, ServerMessage)

---

## Unit 3: gaia-frontend

```bash
cd gaia-frontend

# 단위 테스트 (watch 모드 없음, 한 번 실행)
npm test
# 또는
npx vitest run

# Watch 모드 (개발 중)
npx vitest

# 커버리지
npx vitest run --coverage
```

**테스트 파일 위치:** `src/tests/`

| 파일 | 대상 |
|---|---|
| `GameLobby.test.tsx` | HomeView 클릭, JoinRoomView 입력 검증/대문자변환 |
| `GameBoard.test.tsx` | hex-utils 수학 (axialToPixel, hexCorners, hexKey) |
| `PlayerDashboard.test.tsx` | ResourcePanel/PowerCycle/ResearchTrack 렌더링 |

**참고:** `jsdom` 환경으로 실행. 브라우저 API (WebSocket, fetch) 는 통합 테스트에서 검증.

---

## Unit 4: gaia-ai

```bash
cd gaia-ai
source .venv/bin/activate

# 전체 단위 테스트 (외부 서비스 불필요 — mock 사용)
pytest tests/ -v

# 특정 파일
pytest tests/test_health.py -v
pytest tests/test_coaching.py -v
pytest tests/test_mcts.py -v

# 커버리지
pytest tests/ --cov=coaching --cov=mcts --cov-report=html
# → htmlcov/index.html
```

**테스트 전략:**
- `LlmClient.generate()` / `LlmClient.embed()` → `AsyncMock`으로 대체
- `RagRetriever.retrieve()` → `AsyncMock`으로 대체
- 실제 ollama/Qdrant 연결 없이 100% 테스트 가능

---

## 전체 단위 테스트 한 번에 실행

```bash
# 프로젝트 루트
cargo test -p gaia-engine -p gaia-server 2>&1 | tee /tmp/rust-tests.log

cd gaia-frontend && npm test 2>&1 | tee /tmp/frontend-tests.log && cd ..

cd gaia-ai && pytest tests/ -v 2>&1 | tee /tmp/ai-tests.log && cd ..

echo "=== Results ==="
grep -E "^(test result|FAILED|ok|PASSED)" /tmp/rust-tests.log /tmp/frontend-tests.log /tmp/ai-tests.log
```

---

## 합격 기준

| 단위 | 기준 |
|---|---|
| gaia-engine | 모든 테스트 PASS, 0 failures |
| gaia-server | 모든 단위 테스트 PASS (통합은 별도) |
| gaia-frontend | 모든 vitest 테스트 PASS |
| gaia-ai | 모든 pytest 테스트 PASS |
