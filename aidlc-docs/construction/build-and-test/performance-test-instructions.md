# Performance Test Instructions — Gaia Project Online

## 범위

성능 요구사항은 4인용 실시간 보드게임 규모에 맞게 설정:
- 동시 접속: 최대 10개 게임 룸 × 4명 = 40명
- 응답 시간: REST < 200ms, WS 액션 처리 < 500ms
- AI 코칭: < 30초 (LLM 생성 포함)

---

## 1. gaia-engine 벤치마크 (Cargo criterion)

```bash
# criterion 벤치마크 실행 (gaia-engine/benches/ 추가 시)
cargo bench -p gaia-engine

# 빠른 성능 확인 (criterion 없이)
cargo test -p gaia-engine -- --nocapture bench
```

**핵심 측정 항목:**
- `RuleEngine::validate_action` — 단일 액션 유효성 검사 (< 1ms 목표)
- `ScoringEngine::calculate_final_scoring` — 최종 득점 계산 (< 10ms 목표)
- `Randomizer::generate_setup` — 게임 셋업 생성 (< 50ms 목표)

---

## 2. gaia-server 부하 테스트 (k6)

```bash
# k6 설치: https://k6.io/docs/get-started/installation/

# REST 엔드포인트 부하 테스트
k6 run - <<'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  const res = http.post('http://localhost:8080/api/rooms',
    JSON.stringify({ nickname: `Player_${__VU}` }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(res, {
    'status 201': (r) => r.status === 201,
    'response < 200ms': (r) => r.timings.duration < 200,
  });
  sleep(1);
}
EOF
```

**WebSocket 부하 테스트:**
```bash
# k6 WebSocket 테스트 (동시 40 연결)
k6 run - <<'EOF'
import ws from 'k6/ws';
import { check } from 'k6';

export const options = { vus: 40, duration: '60s' };

export default function () {
  const res = ws.connect('ws://localhost:8080/ws/LOADTEST', null, function (socket) {
    socket.on('open', () => {
      socket.send(JSON.stringify({
        type: 'join_room',
        room_code: 'LOADTEST',
        nickname: `Bot_${__VU}`,
      }));
    });
    socket.on('message', (data) => {
      check(data, { 'received message': (d) => d.length > 0 });
    });
    socket.setTimeout(() => socket.close(), 55000);
  });
  check(res, { 'status 101': (r) => r && r.status === 101 });
}
EOF
```

---

## 3. gaia-ai 응답 시간 측정

```bash
# httpx 기반 간단 측정
python3 - <<'EOF'
import asyncio, time, httpx

async def measure():
    payload = {
        "game_state": {"round": 3, "players": []},
        "question": "Should I build a mine or upgrade?",
        "player_id": 0,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        t0 = time.monotonic()
        r = await client.post("http://localhost:8001/coach/analyze", json=payload)
        elapsed = time.monotonic() - t0
        print(f"Status: {r.status_code}, Time: {elapsed:.2f}s")
        print(f"Response length: {len(r.json().get('response',''))} chars")

asyncio.run(measure())
EOF
```

**목표:** LLM 응답 포함 < 30초 (Qwen 14B on consumer GPU)

---

## 4. 메모리 사용량 모니터링

```bash
# gaia-server 메모리 모니터링 (10개 룸 생성 후)
docker stats gaia-project-gaia-server-1 --no-stream
# 목표: < 256MB RSS (10개 활성 룸 기준)

# gaia-ai 메모리 모니터링
docker stats gaia-project-gaia-ai-1 --no-stream
# 목표: < 512MB RSS (LLM은 ollama 컨테이너가 담당)
```

---

## 5. DB 쿼리 성능 (EXPLAIN ANALYZE)

```bash
# psql 접속
psql postgres://gaia:gaiapass@localhost:5432/gaiaproject

-- 게임 스냅샷 최신 조회 성능 확인
EXPLAIN ANALYZE
SELECT * FROM game_snapshots
WHERE room_code = 'ABCD12'
ORDER BY round DESC
LIMIT 1;
-- 목표: Index Scan, < 5ms

-- 이벤트 로그 범위 조회
EXPLAIN ANALYZE
SELECT * FROM game_events
WHERE room_code = 'ABCD12'
AND id > 0
ORDER BY id;
-- 목표: Index Scan on game_events(room_code, id)
```

---

## 성능 목표 요약

| 항목 | 목표 | 측정 방법 |
|---|---|---|
| REST 룸 생성 (`POST /api/rooms`) | p99 < 200ms | k6 |
| WS 액션 처리 RTT | p99 < 500ms | k6 ws |
| AI 코칭 응답 | < 30s | httpx timer |
| gaia-server RSS (10룸) | < 256MB | docker stats |
| DB 스냅샷 조회 | < 5ms | EXPLAIN ANALYZE |
| cargo test -p gaia-engine | < 30s 전체 | CI 타임아웃 |
