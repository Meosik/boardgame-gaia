# User Stories Generation Plan — 가이아 프로젝트 온라인

## 실행 체크리스트

- [x] Step 1: 페르소나 정의
- [x] Step 2: 스토리 구성 방식 결정
- [x] Step 3: 스토리 세분화 수준 결정
- [x] Step 4: 핵심 사용자 여정 매핑
- [x] Step 5: 수용 기준 형식 결정
- [x] Step 6: stories.md 생성
- [x] Step 7: personas.md 생성
- [x] Step 8: 스토리 검증 (INVEST 기준)

---

## 방법론

**스토리 구성 방식 옵션:**

- **User Journey-Based** (권장): 게임 셋업 → 팩션 선택 → 턴 진행 → 게임 종료 순서로 사용자 여정에 따라 스토리 구성
- **Feature-Based**: 랜더마이저, 멀티플레이어, AI 코칭, 게임 보드 등 기능 단위로 구성
- **Persona-Based**: 호스트, 참여 플레이어, 관전자 각각의 관점으로 구성
- **Epic-Based**: 대형 에픽(게임 진행, AI 시스템, 셋업) → 세부 스토리로 분해

---

## 질문 파일

아래 질문들에 [Answer]: 태그 다음에 알파벳 선택지를 입력해 주세요.

---

## Question 1
사용자 스토리 구성 방식은 무엇을 선호하나요?

A) User Journey-Based — 게임 흐름(셋업→진행→종료) 순서로 구성

B) Feature-Based — 랜더마이저, 멀티플레이어, AI 등 기능별 구성

C) Epic-Based — 대형 에픽 아래 세부 스토리 계층 구조

D) Hybrid (Journey + Feature) — 사용자 여정을 큰 틀로, 세부는 기능별

E) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 2
게임에서 구분할 사용자 유형(페르소나)은 무엇인가요?

A) 호스트(방장)와 참여 플레이어만 구분 (관전자 없음)

B) 호스트, 참여 플레이어, 관전자 3가지 구분

C) 플레이어 단일 유형 (호스트/참여 구분 없음)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
스토리 세분화 수준은 어느 정도로 할까요?

A) 세밀하게 — 각 게임 액션(마인 건설, 업그레이드, 테라포밍 등)을 개별 스토리로

B) 중간 — 주요 게임 단계(셋업, 라운드 진행, 득점)를 스토리로

C) 큰 단위 — 에픽 수준(게임 시작, 게임 진행, AI 사용, 게임 종료)으로

D) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 4
AI 코칭 기능(Phase 1 LLM)을 별도 스토리 세트로 분리할까요?

A) 예 — AI 코칭을 독립 에픽/스토리 세트로 분리

B) 아니오 — 게임 진행 스토리 안에 AI 코칭 포함

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
수용 기준(Acceptance Criteria) 형식은 어떻게 할까요?

A) Given-When-Then (Gherkin 형식)

B) 체크리스트 형식 (- [ ] 조건1, - [ ] 조건2)

C) 단순 불릿 리스트

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 6
MCTS AI 대전(Phase 2)을 이번 스토리 범위에 포함할까요?

A) 예 — Phase 2 MCTS AI도 스토리에 포함

B) 아니오 — Phase 1 LLM 코칭만 포함 (Phase 2는 추후)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
게임 룸 생성/참가 흐름에서 팩션 선택은 어떻게 이루어지나요?

A) 랜더마이저가 배정한 팩션을 확인 후 동의 (선택권 없음)

B) 랜더마이저 결과에서 플레이어가 자신의 팩션을 직접 선택

C) 호스트가 각 플레이어에게 팩션 배정

D) Other (please describe after [Answer]: tag below)

[Answer]: D 
플레이어 숙련도에 따라 3가지 모드 선택:
   - 초보: AI 추천 팩션 (LLM이 playstyle 기반으로 제안)
   - 초보: 자유 선택 (원하는 팩션 직접 픽)
   - 숙련: 비딩 방식 (시계방향 순차 경매):
1. 시계방향으로 돌아가며 입찰
2. 반드시 현재 최고가보다 높게 입찰하거나 패스
3. 마지막까지 남은 사람이 낙찰
   - 원하는 팩션 선택
   - 원하는 턴 오더 선택
4. 낙찰자 제외하고 남은 플레이어로 다시 경매 반복
5. 모든 플레이어 팩션/순서 확정될 때까지 진행
6. 낙찰 VP는 게임 종료 시 최종 점수에서 차감

---

## Question 8
게임 중 비동기 플레이(자기 턴이 아닐 때 다른 것을 할 수 있는 기능)가 필요한가요?

A) 예 — 자기 턴 대기 중 AI 코칭 조회, 게임 로그 확인 등 가능

B) 아니오 — 단순 턴 대기 (다른 플레이어 화면 관전만)

C) Other (please describe after [Answer]: tag below)

[Answer]: A
