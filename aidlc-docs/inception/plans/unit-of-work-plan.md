# Unit of Work Plan — 가이아 프로젝트 온라인

## 실행 체크리스트

- [x] Step 1: 단위 정의 및 경계 확정
- [x] Step 2: 단위별 스토리 매핑
- [x] Step 3: 단위 의존성 매트릭스 작성
- [x] Step 4: unit-of-work.md 생성
- [x] Step 5: unit-of-work-dependency.md 생성
- [x] Step 6: unit-of-work-story-map.md 생성

---

## 예정 단위 구성 (Application Design 기반)

Application Design에서 식별된 4개 단위:

| 단위 | 이름 | 기술 |
|---|---|---|
| Unit 1 | gaia-engine | Rust (pure crate, Cargo workspace) |
| Unit 2 | gaia-server | Rust (Axum + tokio, Cargo workspace) |
| Unit 3 | gaia-frontend | React + TypeScript (Vite) |
| Unit 4 | gaia-ai | LLM 코칭 사이드카 |

---

## 결정 질문

아래 질문들에 [Answer]: 태그 다음에 알파벳 선택지를 입력해 주세요.

---

## Question 1
개발 순서(단위 우선순위)는 어떻게 할까요?

A) Engine → Server → Frontend → AI (권장: 게임 로직 먼저 확립)

B) Engine + Server 동시 → Frontend → AI

C) 모두 동시에 병렬 개발

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
gaia-ai 사이드카의 구현 언어는 무엇으로 할까요?

A) Python — FastAPI + langchain/llama-index (RAG 생태계 풍부)

B) Rust — axum + 외부 LLM API 호출 (언어 통일)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
gaia-frontend의 빌드/서빙 방식은 어떻게 할까요?

A) 별도 Nginx 컨테이너 — React 빌드 결과를 Nginx로 서빙

B) gaia-server가 정적 파일 서빙 — Axum으로 빌드된 JS/CSS 파일 제공

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 4
MCTS 대전 AI (Phase 2)는 이번 구현 범위에서 어떻게 처리할까요?

A) 완전 제외 — gaia-ai는 LLM 코칭만 구현, MCTS는 나중에 별도 단위로

B) 스텁(stub) 포함 — gaia-ai에 MCTS용 빈 엔드포인트/인터페이스만 정의

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
각 단위의 테스트 전략은 어떻게 할까요?

A) 단위별 독립 테스트 — gaia-engine은 unit test + PBT, 나머지는 통합 테스트

B) 전체 E2E 중심 — 단위 테스트 최소화, 게임 시나리오 E2E 테스트 위주

C) Other (please describe after [Answer]: tag below)

[Answer]: A
