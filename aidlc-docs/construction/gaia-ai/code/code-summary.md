# Code Summary — Unit 4: gaia-ai

## 생성 완료 파일 목록

| 파일 | 단계 | 설명 |
|---|---|---|
| `requirements.txt` | Step 1 | fastapi 0.111, uvicorn, httpx, qdrant-client 1.9, langchain 0.2, pypdf 4.2, pytest |
| `.env.example` | Step 1 | OLLAMA_BASE_URL/MODEL, EMBED_MODEL, QDRANT_URL/COLLECTION, RULEBOOK_*_PATH |
| `main.py` | Step 2 | FastAPI 앱: /coach + /mcts 라우터 마운트, GET /health, lifespan context manager |
| `coaching/llm_client.py` | Step 3 | `LlmClient`: async `generate()` (ollama /api/generate), async `embed()` (ollama /api/embeddings) |
| `coaching/rag_retriever.py` | Step 4 | `RagRetriever`: AsyncQdrantClient, `retrieve()` (embed→search→top-k), `upsert_chunks()` (배치 50개) |
| `coaching/api.py` | Step 5 | `POST /coach/analyze` (GameState + 질문 → RAG + LLM), `POST /coach/rules` (순수 RAG), `POST /coach/faction-suggest` (팩션 추천) |
| `coaching/__init__.py` | Step 5 | 패키지 선언 |
| `mcts/engine.py` | Step 6 | `MctsEngine` 인터페이스 스텁 (`best_action`, `evaluate` — NotImplementedError) |
| `mcts/api.py` | Step 6 | `POST /mcts/best-action` → 501, `GET /mcts/status` → stub 정보 |
| `mcts/__init__.py` | Step 6 | 패키지 선언 |
| `scripts/index_rulebook.py` | Step 7 | PDF 파싱 (pypdf) → 청크 분할 (LangChain RecursiveCharacterTextSplitter) → ollama 임베딩 → Qdrant upsert |
| `Dockerfile` | Step 8 | python:3.12-slim, EXPOSE 8001, uvicorn CMD |
| `tests/conftest.py` | Step 9 | TestClient fixture, SAMPLE_GAME_STATE, SAMPLE_FACTION_PAIRS 공유 픽스처 |
| `tests/test_health.py` | Step 9 | GET /health → 200 {"status": "ok"} |
| `tests/test_coaching.py` | Step 9 | 5개 테스트: analyze 정상/RAG실패/LLM실패(503), rules, faction-suggest (LlmClient + RagRetriever mock) |
| `tests/test_mcts.py` | Step 9 | POST /mcts/best-action → 501, GET /mcts/status → {implemented: false} |
| `aidlc-docs/construction/gaia-ai/code/code-summary.md` | Step 10 | 이 파일 |

**총 파일 수**: 17개

---

## 스토리 구현 추적

| User Story | 구현 컴포넌트 | 상태 |
|---|---|---|
| US-16: AI 코칭 | `CoachingApi` (analyze/rules/faction-suggest) + `RagRetriever` + `LlmClient` | ✅ |
| MCTS 스텁 (Phase 2 준비) | `MctsEngine` 인터페이스 + `MctsApi` (501) | ✅ |

---

## API 엔드포인트

```
GET  /health                    → {"status": "ok"}

POST /coach/analyze             게임 상태 + 질문 → RAG 검색 + LLM 응답
POST /coach/rules               규칙 질문 → 룰북 RAG 검색 + LLM 응답
POST /coach/faction-suggest     팩션 쌍 + 플레이어 스타일 → 팩션 추천

POST /mcts/best-action          → 501 Not Implemented (Phase 2 대상)
GET  /mcts/status               → {status: "stub", phase: 2, implemented: false}
```

---

## RAG 파이프라인

```
플레이어 질문
  → ollama embed (nomic-embed-text)
  → Qdrant cosine similarity search (top-5)
  → 청크 컨텍스트 조합
  → ollama generate (qwen2:14b, temperature=0.3)
  → 응답 반환
```

**룰북 인덱싱 (초기 1회):**
```bash
python scripts/index_rulebook.py
# 기본 룰북 + Lost Fleet 확장 PDF → 청크(800자/100자 오버랩) → Qdrant upsert
```

---

## 아키텍처 결정사항

| 결정 | 이유 |
|---|---|
| ollama HTTP 직접 호출 (LangChain LLM 래퍼 미사용) | 의존성 최소화, 스트리밍/비스트리밍 직접 제어 |
| AsyncQdrantClient | FastAPI async 환경과 일관성 |
| MCTS 501 스텁 | Phase 1 범위 초과 — 인터페이스만 정의하여 Phase 2 구현 경계 명확화 |
| 배치 upsert (50개) | Qdrant 대용량 upsert 시 메모리/타임아웃 방지 |
| `_summarise_game_state()` | GameState JSON을 LLM 프롬프트에 직접 넣지 않고 자연어 요약으로 변환 → 토큰 절약 |

---

## 실행 방법

```bash
cd gaia-ai
pip install -r requirements.txt
cp .env.example .env  # 환경 변수 설정

# 룰북 인덱싱 (최초 1회, ollama + qdrant 실행 필요)
python scripts/index_rulebook.py

# 서버 시작
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# 테스트 (외부 서비스 불필요 — mock 사용)
pytest tests/ -v
```

**Docker:**
```bash
docker build -t gaia-ai .
docker run -p 8001:8001 --env-file .env gaia-ai
```
