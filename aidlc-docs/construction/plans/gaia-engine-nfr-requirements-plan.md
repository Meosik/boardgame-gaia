# NFR Requirements Plan — Unit 1: gaia-engine

## 실행 체크리스트

- [x] Step 1: Functional Design 아티팩트 분석
- [x] Step 2: NFR 요구사항 계획 생성
- [x] Step 3: 컨텍스트 적합 질문 생성
- [x] Step 4: 계획 저장 (이 파일)
- [x] Step 5: 답변 수집 및 분석
- [x] Step 6: NFR 요구사항 아티팩트 생성
- [x] Step 7: 완료 메시지 제시

---

## 단위 NFR 컨텍스트

**gaia-engine**은 순수 Rust 라이브러리 크레이트입니다:
- 네트워크 없음 → 보안/가용성 NFR 해당 없음
- 외부 서비스 없음 → 확장성 NFR 해당 없음
- **적용 NFR**: 성능, 신뢰성(panic 정책, 에러 전파), 유지보수성(테스트, PBT)

---

## 질문 목록

아래 질문에 `[Answer]:` 태그 다음에 답변을 입력해 주세요.

---

## Q1. 액션 유효성 검사 성능 목표

`RuleEngine::validate_action()` 호출 속도 목표는 어떻게 할까요?
(서버에서 WebSocket 메시지마다 호출됩니다)

A) 명시적 목표 없음 — 충분히 빠르면 됨 (Rust 특성상 기본적으로 빠를 것)

B) 1ms 미만 — 응답성 보장. 벤치마크 테스트 포함

C) 100μs 미만 — 고성능 목표. Criterion 벤치마크 포함

D) Other

[Answer]:A 

---

## Q2. GameState 직렬화 크기 목표

`GameState::serialize()` 결과 JSON 크기에 제한을 둘까요?

A) 제한 없음 — PostgreSQL 및 WebSocket 전송에서 허용 가능한 범위면 됨

B) 64KB 미만 — WebSocket 단일 프레임에 안정적으로 전송 가능한 크기

C) 압축 적용 — serde + gzip/lz4 압축 후 전송, 크기 목표 별도 없음

D) Other

[Answer]: A

---

## Q3. Panic 정책

gaia-engine 내부에서 panic을 어떻게 처리할까요?

A) Panic 허용 — 불변식 위반 시 panic 가능. 서버 레이어에서 catch

B) No-panic 원칙 — 모든 에러는 `Result<_, RuleError>` 반환. `unwrap()` 금지

C) B + `#[no_panic]` 속성 — no_panic 크레이트로 컴파일 타임 검증

D) Other

[Answer]: B

---

## Q4. 정수 오버플로 처리

자원 계산(ore, credits 등 u8)에서 오버플로를 어떻게 처리할까요?

A) Saturating 연산 — `saturating_add/sub`. 최대/최소값에서 정지, panic 없음

B) Checked 연산 — `checked_add/sub`. 오버플로 시 `RuleError::InsufficientResources` 반환

C) 런타임 검증 — 연산 전 범위 확인 후 처리. 오버플로 발생 자체를 막음

D) Other

[Answer]: C 

---

## Q5. PRNG 재현성 보장 범위

동일 시드로 항상 동일한 결과를 보장해야 하는 범위는 어디까지인가요?

A) 단일 버전 내 보장 — 같은 코드 버전에서만 재현성 보장

B) 크로스-버전 보장 — 소프트웨어 업데이트 이후에도 동일 시드 → 동일 결과

C) B + 크로스-플랫폼 — Rust 외 다른 언어(JS 랜더마이저)와도 동일 결과 보장

D) Other

[Answer]: C 

---

## Q6. GameState 역직렬화 에러 처리

저장된 GameState JSON이 손상되었을 때 어떻게 처리할까요?

A) Panic — 치명적 상태이므로 즉시 중단

B) Result 반환 — `DeserializeError` 반환, 서버에서 복구 시도

C) B + 버전 마이그레이션 — 스키마 버전 필드로 구버전 상태 자동 마이그레이션

D) Other

[Answer]: B

---

## Q7. PBT (Property-Based Testing) 적용 범위 확정

요구사항에서 Partial PBT로 결정되었습니다. 구체적으로 어떤 속성을 검사할까요?

A) 최소 — GameState 직렬화 라운드트립 + PRNG 시드 일관성만

B) 표준 — A + 득점 함수 단조성 + 테라포밍 비용 대칭성

C) 포괄적 — B + 자원 보존 불변식 + 액션 후 상태 유효성 + 연방 파워 계산

D) Other

[Answer]: C

---

## Q8. 테스트 커버리지 목표

gaia-engine 단위 테스트 커버리지 목표는 어느 정도로 할까요?

A) 목표 없음 — 중요 경로만 테스트

B) 70% 이상 — 주요 로직 커버

C) 90% 이상 — 거의 모든 분기 커버. CI에서 미달 시 빌드 실패

D) Other

[Answer]: B

---

## Q9. FactionAbility 스텁의 기본 동작 안전성

Q13에서 모든 팩션을 스텁으로 시작하기로 했습니다. 스텁 구현이 게임 진행에 미치는 영향은?

A) 허용 — 스텁 팩션은 특수 능력 없이 게임 진행 가능. 기본 동작(no-op)은 항상 안전

B) 경고 로그 — 스텁 팩션 능력 호출 시 경고 로그 출력 (실제 구현 전 식별용)

C) Other

[Answer]: B 
