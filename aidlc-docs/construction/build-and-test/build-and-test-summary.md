# Build and Test Summary — Gaia Project Online

## 전체 파일 생성 현황

| 파일 | 위치 |
|---|---|
| `build-instructions.md` | `aidlc-docs/construction/build-and-test/` |
| `unit-test-instructions.md` | `aidlc-docs/construction/build-and-test/` |
| `integration-test-instructions.md` | `aidlc-docs/construction/build-and-test/` |
| `performance-test-instructions.md` | `aidlc-docs/construction/build-and-test/` |
| `docker-compose.yml` | 프로젝트 루트 |
| `docker-compose.dev.yml` | 프로젝트 루트 |
| `gaia-server/Dockerfile` | gaia-server/ |
| `gaia-ai/Dockerfile` | gaia-ai/ (기존 생성) |

---

## 빠른 시작 (개발 환경)

```bash
# 1. 인프라 실행 (postgres + qdrant + ollama)
docker compose -f docker-compose.dev.yml up -d

# 2. LLM 모델 다운로드 (최초 1회, ~10GB)
ollama pull qwen2:14b
ollama pull nomic-embed-text

# 3. DB 마이그레이션
export DATABASE_URL=postgres://gaia:gaiapass@localhost:5432/gaiaproject
cd gaia-server && cargo sqlx migrate run && cd ..

# 4. 룰북 인덱싱 (최초 1회)
cd gaia-ai && python scripts/index_rulebook.py && cd ..

# 5. 서비스 실행 (별도 터미널 3개)
cargo run -p gaia-server                    # 터미널 1: 포트 8080
cd gaia-ai && uvicorn main:app --port 8001  # 터미널 2: 포트 8001
cd gaia-frontend && npm run dev             # 터미널 3: 포트 5173
```

브라우저: http://localhost:5173

---

## 전체 단위 테스트 실행

```bash
# Rust (gaia-engine + gaia-server)
cargo test -p gaia-engine -p gaia-server

# Frontend
cd gaia-frontend && npm test && cd ..

# AI
cd gaia-ai && pytest tests/ -v && cd ..
```

---

## 전체 통합 테스트 실행 (인프라 실행 필요)

```bash
# DB 의존 통합 테스트 해제
export DATABASE_URL=postgres://gaia:gaiapass@localhost:5432/gaiaproject
cargo test -p gaia-server --test integration -- --include-ignored

# E2E 스택 테스트
docker compose up -d --build
curl http://localhost:8080/health && curl http://localhost:8001/health
# REST 룸 생성/참가 smoke test (integration-test-instructions.md 참조)
docker compose down
```

---

## 4개 Unit 완성 현황

| Unit | 기술 스택 | 상태 | 파일 수 |
|---|---|---|---|
| Unit 1: gaia-engine | Rust (pure logic) | ✅ 완료 | ~44개 |
| Unit 2: gaia-server | Rust + Axum + sqlx | ✅ 완료 | 31개 |
| Unit 3: gaia-frontend | React + TypeScript + Vite | ✅ 완료 | 33개 |
| Unit 4: gaia-ai | Python + FastAPI + Qdrant | ✅ 완료 | 17개 |
| **합계** | | | **~125개** |

---

## 아키텍처 다이어그램

```
브라우저 (포트 5173 dev / 8080 prod)
    │
    ├── HTTP REST  ──→  gaia-server (:8080)
    │                      │
    ├── WebSocket  ──→  gaia-server     ├── gaia-engine (in-process)
    │                      │            └── PostgreSQL (:5432)
    └── SPA (dist/)        │
                           └── HTTP  ──→  gaia-ai (:8001)
                                              │
                                         ├── ollama (:11434)  [Qwen 14B]
                                         └── Qdrant (:6333)   [룰북 벡터]
```

---

## 다음 단계 (Operations Phase)

Operations 단계는 현재 플레이스홀더입니다. 향후 확장 시:
- CI/CD 파이프라인 (GitHub Actions)
- 프로덕션 VPS 배포 가이드
- 모니터링 (Prometheus + Grafana)
- 백업 전략 (PostgreSQL dump, Qdrant snapshot)
- MCTS Phase 2 구현 계획
