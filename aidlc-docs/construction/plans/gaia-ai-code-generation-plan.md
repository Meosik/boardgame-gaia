# Code Generation Plan — Unit 4: gaia-ai

## 단위 컨텍스트

| 항목 | 내용 |
|---|---|
| 단위 | Unit 4: gaia-ai |
| 경로 | `/home/sohegi/projects/gaia/gaia-ai/` |
| 유형 | Python 사이드카 서비스 (FastAPI) |
| 의존 단위 | Unit 2 (gaia-server → HTTP 요청 송신) |
| 테스트 전략 | pytest + FastAPI TestClient |
| 배포 | 별도 Docker 컨테이너 (포트 8001) |

## 구현 스토리 (gaia-ai 기여)

| 스토리 | 컴포넌트 |
|---|---|
| US-16 AI 코칭 | CoachingApi, RagRetriever, LlmClient |
| MCTS 스텁 (Phase 2) | MctsApi, MctsEngine |

---

## 실행 체크리스트

### Part 1 — Planning
- [x] Step A: 단위 컨텍스트 분석
- [x] Step B: 코드 생성 계획 수립
- [x] Step C: 계획 저장 (이 파일)
- [x] Step D: 계획 승인 대기

### Part 2 — Generation
- [x] Step 1: 의존성 — `requirements.txt`, `.env.example`
- [x] Step 2: FastAPI 앱 진입점 — `main.py`
- [x] Step 3: LLM 클라이언트 — `coaching/llm_client.py` (ollama HTTP API)
- [x] Step 4: RAG 검색기 — `coaching/rag_retriever.py` (Qdrant 벡터 검색)
- [x] Step 5: 코칭 API — `coaching/api.py` (FastAPI 라우터: analyze, rules, strategy)
- [x] Step 6: MCTS 스텁 — `mcts/engine.py`, `mcts/api.py` (501 Not Implemented)
- [x] Step 7: 룰북 인덱서 — `scripts/index_rulebook.py` (PDF → 청크 → Qdrant)
- [x] Step 8: Dockerfile — 컨테이너 빌드 정의
- [x] Step 9: pytest 테스트 — `tests/` (coaching/mcts 각 엔드포인트)
- [x] Step 10: 코드 요약 문서 — `aidlc-docs/construction/gaia-ai/code/`

---

## 단계별 상세 설명

### Step 1: 의존성 (`requirements.txt`)

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0           # ollama HTTP 클라이언트 (async)
qdrant-client==1.9.1    # Qdrant 벡터 DB 클라이언트
langchain==0.2.5        # 텍스트 분할 유틸리티
langchain-community==0.2.5
pypdf==4.2.0            # PDF 파싱 (룰북 인덱싱)
python-dotenv==1.0.1
pytest==8.2.2
pytest-asyncio==0.23.7
httpx                   # FastAPI TestClient
```

**환경 변수 (.env.example):**
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2:14b
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=gaia_rulebook
EMBED_MODEL=nomic-embed-text
RULEBOOK_EN_PATH=../docs/EN_Gaia_rulebook_lo.pdf
RULEBOOK_EXP_PATH=../docs/GP_Exp_Rule_EN_V1_Web.pdf
```

---

### Step 2: FastAPI 앱 진입점 (`main.py`)

```python
app = FastAPI(title="gaia-ai", version="0.1.0")
app.include_router(coaching_router, prefix="/coach")
app.include_router(mcts_router, prefix="/mcts")

# GET /health → {"status": "ok"}
```

---

### Step 3: LLM 클라이언트 (`coaching/llm_client.py`)

```python
class LlmClient:
    async def generate(self, prompt: str, context: str) -> str:
        # POST {OLLAMA_BASE_URL}/api/generate
        # model: OLLAMA_MODEL, prompt: f"Context:\n{context}\n\nQuestion:\n{prompt}"
        # stream=False, options: {"temperature": 0.3}
```

---

### Step 4: RAG 검색기 (`coaching/rag_retriever.py`)

```python
class RagRetriever:
    def __init__(self):
        self.client = QdrantClient(url=QDRANT_URL)
        self.collection = QDRANT_COLLECTION

    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        # ollama embed → qdrant search → return top_k text chunks
```

---

### Step 5: 코칭 API (`coaching/api.py`)

**엔드포인트:**

`POST /coach/analyze`
```python
class AnalyzeRequest(BaseModel):
    game_state: dict        # gaia-server에서 전달하는 GameState JSON
    question: str           # 플레이어 자유 질문
    player_id: int

# 흐름:
# 1. game_state → 자연어 요약 생성 (간단한 문자열 변환)
# 2. RagRetriever.retrieve(question + state_summary) → context chunks
# 3. LlmClient.generate(question, context) → response
# 4. 반환: {"response": "..."}
```

`POST /coach/rules`
```python
class RulesRequest(BaseModel):
    query: str              # 규칙 질문 ("연방 형성 조건이 뭐야?")

# 흐름: RAG only (game_state 없이 순수 룰북 검색)
```

`POST /coach/faction-suggest`
```python
class FactionSuggestRequest(BaseModel):
    faction_pairs: list[dict]
    player_style: str       # "aggressive", "economic", "tech"

# 흐름: LLM에 팩션 페어 + 스타일 → 추천 이유 반환
```

---

### Step 6: MCTS 스텁 (`mcts/`)

**mcts/engine.py:**
```python
class MctsEngine:
    """Phase 2 구현 대상. 현재는 인터페이스 정의만."""
    def best_action(self, game_state: dict) -> dict:
        raise NotImplementedError
```

**mcts/api.py:**
```python
@router.post("/best-action")
async def best_action(req: MctsRequest):
    raise HTTPException(status_code=501, detail="MCTS not implemented (Phase 2)")
```

---

### Step 7: 룰북 인덱서 (`scripts/index_rulebook.py`)

```python
# 실행: python scripts/index_rulebook.py
# 1. pypdf로 EN_Gaia_rulebook_lo.pdf + GP_Exp_Rule_EN_V1_Web.pdf 파싱
# 2. LangChain RecursiveCharacterTextSplitter (chunk_size=800, overlap=100)
# 3. ollama embed (nomic-embed-text) → 각 청크 임베딩
# 4. Qdrant upsert (collection: gaia_rulebook)
# 5. 완료 메시지 출력 (청크 수, 소요 시간)
```

---

### Step 8: Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

---

### Step 9: 테스트 (`tests/`)

- `tests/conftest.py` — FastAPI TestClient fixture
- `tests/test_coaching.py` — /coach/analyze, /coach/rules, /coach/faction-suggest (LlmClient + RagRetriever mock)
- `tests/test_mcts.py` — /mcts/best-action → 501
- `tests/test_health.py` — /health → 200

---

## 생성 파일 전체 목록

```
gaia-ai/
├── requirements.txt                           ← Step 1
├── .env.example                               ← Step 1
├── main.py                                    ← Step 2
├── coaching/
│   ├── __init__.py                            ← Step 5
│   ├── api.py                                 ← Step 5
│   ├── rag_retriever.py                       ← Step 4
│   └── llm_client.py                          ← Step 3
├── mcts/
│   ├── __init__.py                            ← Step 6
│   ├── api.py                                 ← Step 6
│   └── engine.py                              ← Step 6
├── scripts/
│   └── index_rulebook.py                      ← Step 7
├── Dockerfile                                 ← Step 8
└── tests/
    ├── conftest.py                            ← Step 9
    ├── test_health.py                         ← Step 9
    ├── test_coaching.py                       ← Step 9
    └── test_mcts.py                           ← Step 9
└── aidlc-docs/construction/gaia-ai/code/
    └── code-summary.md                        ← Step 10
```

**총 파일 수**: 17개
