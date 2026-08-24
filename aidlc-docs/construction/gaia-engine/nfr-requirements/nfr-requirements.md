# NFR Requirements — gaia-engine

## 범위 및 적용 가능성

| NFR 카테고리 | 적용 여부 | 근거 |
|---|---|---|
| 성능 | 적용 (제한적) | 명시적 목표 없음, Rust 기본 성능 신뢰 |
| 확장성 | 해당 없음 | 순수 라이브러리, 네트워크 없음 |
| 가용성 | 해당 없음 | 라이브러리 크레이트 (서버 레이어 책임) |
| 보안 | 해당 없음 | 입력 신뢰 경계는 Unit 2 (gaia-server) |
| 신뢰성 | 적용 | No-panic 원칙, 런타임 범위 검증 |
| 유지보수성 | 적용 | 70%+ 커버리지, 포괄적 PBT |
| PRNG 재현성 | 적용 | 크로스-언어 (Rust ↔ JS) 동일 결과 보장 |

---

## 1. 성능 요구사항

### NFR-PERF-01: 명시적 성능 목표 없음
- `RuleEngine::validate_action()` 등 핵심 연산에 수치 목표를 두지 않음
- 근거: Rust 컴파일 언어 특성상 기본 성능이 충분할 것으로 기대
- **Criterion 벤치마크 불포함** (성능 문제 발생 시 사후 추가)
- 단, 알고리즘 복잡도는 합리적이어야 함:
  - BFS 연방 검증: O(n) where n = hexes in component
  - 이벤트 기반 득점: O(e) where e = round events
  - PRNG generate_setup: O(tile_count log tile_count) Fisher-Yates

### NFR-PERF-02: 직렬화 크기 제한 없음
- `GameState::serialize()` JSON 크기에 명시적 상한 없음
- PostgreSQL JSONB 및 WebSocket 전송 레이어가 처리 가능한 범위면 됨
- 압축(gzip/lz4) 미적용 — gaia-server 레이어에서 필요 시 처리

---

## 2. 신뢰성 요구사항

### NFR-REL-01: No-Panic 원칙
- **gaia-engine 내부에서 panic 금지**
- 모든 에러 경로는 `Result<T, E>` 반환
- 금지 패턴:
  - `unwrap()`, `expect()` — `?` 연산자 또는 명시적 매칭으로 대체
  - `panic!()`, `assert!()` — 검증 로직으로 대체
  - 배열 인덱스 직접 접근(`arr[i]`) — `get(i).ok_or(...)` 사용
- 허용 예외: `unreachable!()` — 컴파일러가 도달 불가능한 것을 증명할 수 없는 exhaustive match에서만
- `#[no_panic]` 크레이트 미적용 (컴파일 타임 검증 오버헤드 불필요)

### NFR-REL-02: 런타임 범위 검증으로 오버플로 방지
- `u8` 자원 필드(`ore`, `credits`, `knowledge`, `qic`) 오버플로 방지:
  - 연산 **전** 범위 확인 후 처리 — 오버플로 발생 자체를 막음
  - 차감 전: `if player.resources.ore < needed { return Err(...) }`
  - 증가 전: `if player.resources.ore > u8::MAX - amount { 포화 처리 또는 에러 }`
- `saturating_*` 또는 `checked_*` 연산 미사용 — 명시적 범위 검사 선호
- `i32` VP 필드는 오버플로 위험 없음 (비딩 차감 후 최대 수백 VP)

### NFR-REL-03: GameState 역직렬화 에러 처리
- 손상된 또는 잘못된 형식의 JSON 입력 시:
  - `GameState::deserialize()` → `Err(DeserializeError)` 반환
  - panic 금지
- 버전 마이그레이션 미적용 (현 스코프 외):
  - `GameState.version` 필드는 낙관적 잠금 전용
  - 스키마 변경 시 DB 마이그레이션으로 처리 (gaia-server 책임)

---

## 3. PRNG 재현성 요구사항

### NFR-PRNG-01: 크로스-언어 재현성 (Rust ↔ JavaScript)
- 동일한 시드 문자열 → Rust `Randomizer`와 JS 랜더마이저가 동일한 출력 생성
- 보장 범위:
  - 동일 시드 → 동일 팩션 페어 순서
  - 동일 시드 → 동일 라운드 타일 순서
  - 동일 시드 → 동일 섹터 배치 및 회전
- 구현 방법: JS `imul`을 Rust `u32::wrapping_mul`로 1:1 포팅
- 검증: 알려진 시드-출력 테스트 벡터 (JS로 사전 계산 후 하드코딩)

### NFR-PRNG-02: 버전 간 재현성
- 소프트웨어 업데이트 후에도 동일 시드 → 동일 결과 유지
- PRNG 알고리즘 변경 금지 (변경 필요 시 새 시드 생성으로 처리)

---

## 4. 유지보수성 요구사항

### NFR-MAINT-01: 테스트 커버리지 70% 이상
- `cargo tarpaulin` (또는 `cargo llvm-cov`)으로 측정
- 목표: 라인 커버리지 ≥ 70%
- CI에서 측정하되 강제 실패는 적용 안 함 (목표값, Hard gate 아님)
- 우선 커버 대상:
  - `RuleEngine::validate_action()` — 모든 RuleError variant
  - `ScoringEngine` — 라운드/최종 득점 계산
  - `BiddingEngine` — 경매 상태 전환
  - `Randomizer` — 시드 해싱 및 generate_setup()

### NFR-MAINT-02: 포괄적 PBT (proptest)
PBT 적용 대상 속성 (모두 포함):

| 속성 | 검사 내용 |
|---|---|
| 직렬화 라운드트립 | `deserialize(serialize(state)) == state` |
| PRNG 시드 일관성 | 동일 시드 → 동일 출력 (여러 호출에 걸쳐) |
| 득점 함수 단조성 | 더 많은 구조물 → VP ≥ 적은 구조물 VP |
| 테라포밍 비용 대칭성 | `cost(A→B) == cost(B→A)` |
| 자원 보존 불변식 | `bowl1 + bowl2 + bowl3 + gaia_bowl + gaia_forming = 상수` |
| 액션 후 상태 유효성 | `apply_action(state, valid_action)` → 결과 state가 invariant 만족 |
| 연방 파워 계산 | Satellite 제외 구조물 파워 합계 = 예상값 |

- proptest 전략: `GameState`에 `Arbitrary` 구현 (간소화된 유효 상태 생성)

### NFR-MAINT-03: FactionAbility 스텁 식별 로깅
- 미구현 팩션 능력 호출 시 경고 로그 출력:
  ```
  [WARN] FactionAbility::on_build called on stub faction {faction_id} — not yet implemented
  ```
- 로깅 크레이트: `log` 크레이트 (`tracing` 불사용 — 라이브러리 크레이트 원칙)
- gaia-server에서 `env_logger` 등으로 subscriber 설정
- 스텁 경고는 프로덕션에서도 출력 (미구현 팩션 식별 목적)
