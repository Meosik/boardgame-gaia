# NFR Design Plan — Unit 1: gaia-engine

## 실행 체크리스트

- [x] Step 1: NFR 요구사항 분석
- [x] Step 2: NFR Design 계획 생성
- [x] Step 3: 컨텍스트 적합 질문 생성
- [x] Step 4: 계획 저장 (이 파일)
- [x] Step 5: 답변 수집 및 분석
- [x] Step 6: NFR Design 아티팩트 생성
- [x] Step 7: 완료 메시지 제시

---

## NFR 카테고리 적용성 평가

| 카테고리 | 적용 | 근거 |
|---|---|---|
| 복원력 패턴 | 적용 | no-panic 원칙, 에러 전파 체인 설계 필요 |
| 확장성 패턴 | N/A | 순수 라이브러리, 네트워크/인스턴스 없음 |
| 성능 패턴 | 적용 (제한) | BFS 연방 검증, 이벤트 스캔 알고리즘 선택 |
| 보안 패턴 | N/A | 네트워크 경계 없음, 입력 신뢰는 호출자 책임 |
| 논리 컴포넌트 | 적용 (제한) | 에러 타입 계층, PBT 헬퍼, 스텁 로깅 구조 |

---

## 질문 목록

아래 질문에 `[Answer]:` 태그 다음에 답변을 입력해 주세요.

---

## Q1. 에러 타입 계층 — 최상위 에러 통합 여부

`RuleError`와 `DeserializeError`를 하나의 최상위 타입으로 묶을까요?

A) 분리 유지 — `RuleError`와 `DeserializeError` 독립. 호출자(gaia-server)가 각각 처리

B) 통합 — `GameError` enum: `GameError::Rule(RuleError)`, `GameError::Deserialize(DeserializeError)`. 단일 타입으로 전파

C) Other

[Answer]: A

---

## Q2. 복원력 패턴 — 부분 상태 적용 실패 처리

`apply_action()`이 중간에 실패하면(예: 자원 차감 후 구조물 배치 실패) 상태가 부분 변경될 수 있습니다. 어떻게 처리할까요?

A) 사전 검증 보장 — `validate_action()`이 먼저 통과했으면 `apply_action()`은 실패 불가. 부분 적용 방지는 설계로 해결

B) 트랜잭션 복원 — `apply_action()` 시작 시 `GameState` 클론 보관. 실패 시 롤백

C) Other

[Answer]: A

---

## Q3. 성능 패턴 — BFS 연방 검증 인접 그래프

연방 형성 검증 BFS에서 인접 관계를 어떻게 구할까요?

A) 즉석 계산 — BFS마다 모든 hex를 순회하여 인접 여부 계산 (간단, 코드 작음)

B) BoardState 인접 맵 — `BoardState`에 `adjacency: HashMap<HexCoord, Vec<HexCoord>>` 유지. 구조물 변경 시 갱신

C) Other

[Answer]: A

---

## Q4. PBT 테스트 헬퍼 구조

proptest `Arbitrary` 구현과 게임 상태 생성 헬퍼를 어디에 둘까요?

A) 테스트 전용 모듈 — `#[cfg(test)]` 블록에만 존재. 외부에서 접근 불가

B) 별도 `test-utils` feature — `Cargo.toml`에 `test-utils` feature flag. 활성화 시 `Arbitrary` 구현 포함. gaia-server 테스트에서도 재사용 가능

C) Other

[Answer]: B

---

## Q5. 스텁 경고 로그 위치

`FactionAbility` 스텁 경고 로그를 어떻게 출력할까요?

A) trait 기본 구현 — `DefaultFactionAbility` 구조체에 `log::warn!()` 호출. 각 메서드에 명시적 기재

B) 매크로 — `stub_faction_ability!()` 매크로로 경고 + 기본 반환값 자동 생성. 반복 코드 제거

C) Other

[Answer]: B 
