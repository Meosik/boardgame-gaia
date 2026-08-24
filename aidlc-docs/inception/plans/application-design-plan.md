# Application Design Plan — 가이아 프로젝트 온라인

## 실행 체크리스트

- [x] Step 1: 컴포넌트 식별 및 경계 정의
- [x] Step 2: 컴포넌트 메서드 시그니처 설계
- [x] Step 3: 서비스 레이어 설계
- [x] Step 4: 컴포넌트 의존성 및 통신 패턴 정의
- [x] Step 5: components.md 생성
- [x] Step 6: component-methods.md 생성
- [x] Step 7: services.md 생성
- [x] Step 8: component-dependency.md 생성
- [x] Step 9: application-design.md (통합 문서) 생성

---

## 설계 질문

아래 질문들에 [Answer]: 태그 다음에 알파벳 선택지를 입력해 주세요.

---

## Question 1
게임 상태 영속성 방식은 무엇을 선택할까요?

A) State Snapshot — 매 액션 후 전체 게임 상태를 DB에 저장 (간단, 복구 용이)

B) Event Sourcing — 개별 게임 이벤트(액션)를 순서대로 저장하고 재생하여 상태 복원 (이력 완전 보존, 복잡)

C) Hybrid — 이벤트 로그 + 주기적 스냅샷 (이벤트 이력 보존 + 빠른 복구)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 2
프론트엔드-백엔드 통신 방식은 어떻게 할까요?

A) WebSocket 단독 — 모든 통신(게임 액션, 셋업, 상태 조회)을 WebSocket으로

B) REST + WebSocket — 초기 로딩/셋업은 REST, 실시간 게임 이벤트는 WebSocket

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 3
18개 팩션의 고유 능력 구현 방식은 무엇을 선택할까요?

A) 데이터 주도(Data-driven) — 팩션 능력을 JSON/TOML 설정 파일로 정의, 범용 규칙 엔진이 해석

B) 트레이트(Trait) 기반 — Rust trait으로 팩션 인터페이스 정의, 각 팩션이 개별 구조체로 구현

C) Hybrid — 공통 능력은 데이터 주도, 복잡한 특수 능력은 트레이트로 구현

D) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 4
LLM 코칭 AI 시스템의 배포 구조는 어떻게 할까요?

A) 사이드카 서비스 — 별도 프로세스/컨테이너로 분리, 백엔드가 HTTP로 호출

B) 백엔드 내장 — Rust 백엔드가 직접 LLM API 호출 (ollama HTTP API 등)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
WebSocket 메시지 형식은 무엇을 선택할까요?

A) JSON — 가독성 좋고 디버깅 용이, 약간 큰 페이로드

B) MessagePack (바이너리) — 작은 페이로드, 빠른 직렬화

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
게임 룸 관리는 어떻게 처리할까요?

A) 인메모리 — 활성 룸을 서버 메모리에 유지, DB에는 영속 상태만 저장

B) DB 전용 — 모든 룸 상태를 PostgreSQL에서 관리

C) Redis + DB — 활성 룸은 Redis 캐시, 종료된 게임은 PostgreSQL에 영속

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 7
게임 엔진(Unit 1)과 백엔드 서버(Unit 2)의 코드 구성은 어떻게 할까요?

A) Cargo workspace — 단일 저장소에 여러 크레이트 (gaia-engine, gaia-server, gaia-frontend 등)

B) 별도 저장소 — 게임 엔진과 서버를 완전히 분리된 저장소로 관리

C) Other (please describe after [Answer]: tag below)

[Answer]: A
