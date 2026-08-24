# Build Instructions — Gaia Project Online

## 전체 빌드 순서

```
1. gaia-engine  (Unit 1) — Rust crate
2. gaia-server  (Unit 2) — Rust binary (depends on 1)
3. gaia-frontend (Unit 3) — React SPA → dist/ 생성
4. gaia-ai      (Unit 4) — Python FastAPI (독립)
```

---

## 사전 요구 사항

| 도구 | 버전 | 설치 |
|---|---|---|
| Rust + Cargo | ≥ 1.78 | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` |
| Node.js | ≥ 20 | https://nodejs.org |
| Python | ≥ 3.12 | https://python.org |
| Docker + Compose | ≥ 24 | https://docs.docker.com/get-docker/ |
| PostgreSQL client | (선택) | `apt install postgresql-client` |

---

## Unit 1+2: Rust (gaia-engine + gaia-server)

```bash
# 프로젝트 루트에서
cargo check                    # 컴파일 오류 확인 (빠름, 0초 실행 필요 없음)
cargo build                    # 디버그 빌드
cargo build --release          # 릴리스 빌드 (배포용)
cargo build -p gaia-engine     # 엔진만
cargo build -p gaia-server     # 서버만 (엔진 자동 포함)
```

**sqlx offline 모드 준비 (CI 환경):**
```bash
# DATABASE_URL 있는 환경에서 한 번만 실행
export DATABASE_URL=postgres://gaia:gaiapass@localhost:5432/gaiaproject
cd gaia-server
cargo sqlx prepare
# 생성된 .sqlx/ 디렉토리를 git에 커밋하면 CI에서 DB 없이 빌드 가능
```

**환경 변수 (.env):**
```bash
cd gaia-server
cp .env.example .env
# DATABASE_URL, AI_BASE_URL, PORT, RUST_LOG 설정
```

**개발 서버 실행:**
```bash
cd gaia-server
cargo run
# → http://localhost:8080
# → WebSocket: ws://localhost:8080/ws/{room_code}
```

---

## Unit 3: gaia-frontend

```bash
cd gaia-frontend
npm install

# 개발 서버 (포트 5173, /api + /ws → localhost:8080 프록시)
npm run dev

# 프로덕션 빌드 (dist/ 생성)
npm run build

# 타입 체크
npx tsc --noEmit
```

**빌드 출력:** `gaia-frontend/dist/`
gaia-server가 `ServeDir::new("../gaia-frontend/dist/")` 로 정적 서빙.

---

## Unit 4: gaia-ai

```bash
cd gaia-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # 환경 변수 설정

# 룰북 인덱싱 (최초 1회, ollama + qdrant 실행 필요)
python scripts/index_rulebook.py

# 개발 서버 (포트 8001)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Docker Compose 빌드 (전체 스택)

### 개발 환경 (인프라만)
```bash
# 포트 5432 (postgres), 6333 (qdrant), 11434 (ollama) 필요
docker compose -f docker-compose.dev.yml up -d

# 상태 확인
docker compose -f docker-compose.dev.yml ps
```

### 프로덕션 빌드 (전체)
```bash
# 1. 프론트엔드 dist/ 먼저 빌드
cd gaia-frontend && npm run build && cd ..

# 2. 전체 스택 빌드 + 실행
docker compose build
docker compose up -d

# 3. 서버 상태 확인
curl http://localhost:8080/health
curl http://localhost:8001/health
```

### LLM 모델 다운로드 (최초 1회)
```bash
# ollama 컨테이너가 실행 중인 상태에서
docker compose exec ollama ollama pull qwen2:14b
docker compose exec ollama ollama pull nomic-embed-text

# 또는 로컬 ollama 사용 시
ollama pull qwen2:14b
ollama pull nomic-embed-text
```

### 룰북 인덱싱 (Docker, 최초 1회)
```bash
docker compose run --rm gaia-ai python scripts/index_rulebook.py
```

---

## 빌드 검증 체크리스트

```
[ ] cargo check → 0 errors, 0 warnings (또는 known dead-code warnings only)
[ ] cargo build --release → 성공
[ ] npm run build → dist/ 생성
[ ] pip install -r requirements.txt → 성공
[ ] docker compose build → 성공
[ ] curl http://localhost:8080/health → {"status":"ok"} 또는 유사
[ ] curl http://localhost:8001/health → {"status":"ok"}
```
