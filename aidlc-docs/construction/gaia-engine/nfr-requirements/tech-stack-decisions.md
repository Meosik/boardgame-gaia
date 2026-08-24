# Tech Stack Decisions — gaia-engine

## 확정된 기술 스택

| 레이어 | 기술 | 결정 근거 |
|---|---|---|
| 언어 | Rust (stable) | INCEPTION 단계 결정 |
| 빌드 시스템 | Cargo workspace | INCEPTION 단계 결정 |
| 직렬화 | serde + serde_json | INCEPTION 단계 결정 |
| 테스트 | cargo test | 표준 Rust 테스트 |
| PBT | proptest | Partial PBT 결정 (INCEPTION) |
| 로깅 | log (라이브러리 크레이트용) | NFR-MAINT-03 결정 |

---

## NFR 결정으로 확정된 기술 선택

### TSD-01: Criterion 벤치마크 미포함
- **결정**: Criterion 크레이트 미사용
- 근거: Q1 답변 A — 명시적 성능 목표 없음
- 영향: `benches/` 디렉터리 불생성
- 재고 조건: 실제 성능 문제 발생 시 사후 추가

### TSD-02: no_panic 크레이트 미사용
- **결정**: `no_panic` 크레이트 미적용
- 근거: Q3 답변 B — no-panic 원칙은 코드 규율로 관리
- 대안: 코드 리뷰 + clippy 경고 + `unwrap_used` lint로 강제
- clippy 설정 (`Cargo.toml` 또는 `.cargo/config.toml`):
  ```toml
  [lints.clippy]
  unwrap_used = "deny"
  expect_used = "deny"
  panic = "deny"
  ```

### TSD-03: 명시적 범위 검증 패턴
- **결정**: `saturating_*` / `checked_*` 미사용, 명시적 사전 검사 사용
- 근거: Q4 답변 C — 오버플로 발생 자체를 막는 방어적 설계
- 표준 패턴:
  ```rust
  // 차감 전 검사
  if state.player.resources.ore < needed_ore {
      return Err(RuleError::InsufficientResources {
          resource: ResourceKind::Ore,
          needed: needed_ore as u32,
          have: state.player.resources.ore as u32,
      });
  }
  state.player.resources.ore -= needed_ore;  // 안전한 차감
  ```

### TSD-04: log 크레이트 (라이브러리 크레이트 원칙)
- **결정**: `tracing` 미사용, `log` 크레이트 사용
- 근거: 라이브러리 크레이트는 subscriber를 강제하지 않아야 함
- gaia-engine `Cargo.toml`:
  ```toml
  [dependencies]
  log = "0.4"
  ```
- gaia-server (consumer)에서 subscriber 설정:
  ```toml
  [dependencies]
  env_logger = "0.11"  # 또는 tracing-subscriber
  ```

### TSD-05: proptest Arbitrary 전략
- **결정**: `GameState`에 간소화된 `Arbitrary` 구현
- 범위: 완전한 유효 GameState 생성 (규칙 위반 상태 제외)
- 구현 위치: `gaia-engine/tests/property/`
- 전략 구성:
  ```rust
  // 유효한 Resources 생성
  prop_compose! {
      fn valid_resources()(
          ore in 0u8..=15,
          credits in 0u8..=30,
          knowledge in 0u8..=15,
          qic in 0u8..=6,
          bowl1 in 0u8..=7,
          bowl2 in 0u8..=7,
          bowl3 in 0u8..=7,
      ) -> Resources {
          Resources { ore, credits, knowledge, qic,
              power: PowerCycle { bowl1, bowl2, bowl3,
                  gaia_bowl: 0, gaia_forming: 0 },
              spent_gaia_formers: 0,
          }
      }
  }
  ```

### TSD-06: 테스트 커버리지 측정 도구
- **결정**: `cargo-tarpaulin` (Linux) 또는 `cargo-llvm-cov`
- 목표: 라인 커버리지 ≥ 70%
- CI 명령어 (참고용):
  ```bash
  cargo tarpaulin --out Xml --output-dir coverage/
  ```
- Hard gate 미적용 — 목표값으로만 관리

---

## Cargo.toml 의존성 계획

```toml
[package]
name = "gaia-engine"
version = "0.1.0"
edition = "2021"

[dependencies]
serde      = { version = "1", features = ["derive"] }
serde_json = "1"
log        = "0.4"

[dev-dependencies]
proptest   = "1"

# Criterion은 현재 불포함 — 필요 시 추가
# criterion = { version = "0.5", features = ["html_reports"] }

[lints.clippy]
unwrap_used = "deny"
expect_used = "deny"
```

---

## 기술 스택 결정 요약

| 결정 항목 | 선택 | 제외된 대안 |
|---|---|---|
| 벤치마크 | 없음 (사후 추가 가능) | Criterion |
| Panic 강제 | Clippy lint (deny) | no_panic 크레이트 |
| 오버플로 방지 | 명시적 사전 검사 | saturating_*, checked_* |
| 로깅 | log 크레이트 | tracing |
| PBT 도구 | proptest | quickcheck |
| 커버리지 | cargo-tarpaulin | grcov |
