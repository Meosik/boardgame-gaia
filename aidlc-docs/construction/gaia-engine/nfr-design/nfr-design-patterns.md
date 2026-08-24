# NFR Design Patterns — gaia-engine

## 1. 에러 타입 분리 패턴 (Resilience)

### 패턴: Independent Error Types
**근거**: Q1 답변 A — 호출자(gaia-server)가 컨텍스트에 따라 각 에러를 독립적으로 처리

**에러 타입 계층:**
```
gaia-engine 퍼블릭 에러 타입
├── RuleError      — 게임 규칙 위반 (액션 실행 흐름)
└── DeserializeError — 상태 역직렬화 실패 (저장/복원 흐름)
```

**구현 패턴:**
```rust
// lib.rs에서 재익스포트
pub use rules::RuleError;
pub use game_state::DeserializeError;

// 각 에러 타입은 독립적으로 정의
#[derive(Debug, thiserror::Error)]
pub enum RuleError {
    #[error("not your turn")]
    NotYourTurn,
    #[error("insufficient {resource:?}: needed {needed}, have {have}")]
    InsufficientResources { resource: ResourceKind, needed: u32, have: u32 },
    // ... (domain-entities.md 전체 목록)
}

#[derive(Debug, thiserror::Error)]
pub enum DeserializeError {
    #[error("invalid JSON: {0}")]
    InvalidJson(#[from] serde_json::Error),
    #[error("unknown version: {version}")]
    UnknownVersion { version: u64 },
    #[error("missing field: {field}")]
    MissingField { field: &'static str },
}
```

**호출자 처리 (gaia-server 참고):**
```rust
// 액션 처리 흐름
match engine.apply_action(&mut state, player_id, action) {
    Ok(events) => broadcast(events),
    Err(RuleError::NotYourTurn) => send_error(player, "아직 당신의 턴이 아닙니다"),
    Err(RuleError::InsufficientResources { resource, needed, have }) =>
        send_error(player, format!("{:?} 부족: {} 필요, {} 보유", resource, needed, have)),
    Err(e) => send_error(player, e.to_string()),
}

// 상태 복원 흐름 (별도)
match GameState::deserialize(json) {
    Ok(state) => restore_game(state),
    Err(DeserializeError::InvalidJson(e)) => log_critical!("DB 손상: {}", e),
    Err(e) => log_error!("역직렬화 실패: {}", e),
}
```

**의존성 추가** (`thiserror` 크레이트):
```toml
[dependencies]
thiserror = "1"
```

---

## 2. 사전 검증 보장 패턴 (Resilience)

### 패턴: Validation-Application Contract
**근거**: Q2 답변 A — `validate_action()` 통과 → `apply_action()` 실패 불가. 부분 적용 방지는 설계로 보장

**계약 규칙:**
- `validate_action(state, player, action)` 은 읽기 전용 (`&GameState`)
- `apply_action(state, player, action)` 은 내부에서 `validate_action` 재호출 후 진행
- `validate_action()` 이 `Ok(())` 를 반환한 상태에서 `apply_action()` 이 에러를 반환하는 경우 = 버그

**구현 패턴:**
```rust
impl RuleEngine {
    pub fn validate_action(
        state: &GameState,
        player: PlayerId,
        action: &GameAction,
    ) -> Result<(), RuleError> {
        // 모든 검증은 상태를 변경하지 않음
        Self::check_phase(state, player)?;
        Self::check_resources(state, player, action)?;
        Self::check_target(state, player, action)?;
        Ok(())
    }

    pub fn apply_action(
        state: &mut GameState,
        player: PlayerId,
        action: GameAction,
    ) -> Result<Vec<GameEvent>, RuleError> {
        // 재검증으로 계약 보장
        Self::validate_action(state, player, &action)?;
        // 이 시점부터는 실패 불가 — 설계 불변식
        let events = Self::apply_unchecked(state, player, action);
        Ok(events)
    }

    // validate 통과 후 호출 — 절대 실패하지 않는 내부 함수
    fn apply_unchecked(
        state: &mut GameState,
        player: PlayerId,
        action: GameAction,
    ) -> Vec<GameEvent> {
        // 상태 변이만 수행, Result 반환 없음
        // ...
    }
}
```

**검증 순서 불변식:**
```
1. 페이즈/턴 확인 (check_phase)
2. 자원 충분성 확인 (check_resources)  ← 차감 전 검사
3. 대상 유효성 확인 (check_target)     ← 위치/타입/범위
4. 액션별 추가 검증 (check_action_specific)
→ 모두 통과 시 apply_unchecked() 호출
```

---

## 3. 런타임 범위 검증 패턴 (Reliability)

### 패턴: Explicit Pre-Check Before Mutation
**근거**: Q4(NFR) 답변 C — 오버플로 발생 자체를 막는 방어적 설계

**표준 차감 패턴:**
```rust
fn deduct_ore(player: &mut PlayerState, amount: u8) -> Result<(), RuleError> {
    if player.resources.ore < amount {
        return Err(RuleError::InsufficientResources {
            resource: ResourceKind::Ore,
            needed: amount as u32,
            have: player.resources.ore as u32,
        });
    }
    player.resources.ore -= amount;  // 사전 검증 후 안전한 차감
    Ok(())
}
```

**표준 증가 패턴 (u8 한도 포화):**
```rust
fn add_ore(player: &mut PlayerState, amount: u8) {
    // 게임 내 자원 최대값 초과 시 포화 (규칙상 존재함)
    player.resources.ore = player.resources.ore.saturating_add(amount);
    // saturating은 증가에만 허용 — 초과 자원은 버려짐 (게임 규칙)
}
```

**파워 사이클 전용 패턴:**
```rust
// 파워 사이클은 보존 불변식이 있으므로 별도 처리
fn charge_power(power: &mut PowerCycle, amount: u8) -> Result<(), RuleError> {
    // bowl1 → bowl2 이동
    let move_1_2 = amount.min(power.bowl1);
    power.bowl1 -= move_1_2;
    power.bowl2 += move_1_2;
    let remaining = amount - move_1_2;
    // bowl2 → bowl3 이동
    if remaining > 0 {
        let move_2_3 = remaining.min(power.bowl2);
        power.bowl2 -= move_2_3;
        power.bowl3 += move_2_3;
    }
    Ok(())
}
```

---

## 4. PRNG 결정론적 재현 패턴 (Reliability)

### 패턴: Locked Algorithm + Test Vectors
**근거**: NFR-PRNG-01/02 — JS 크로스-언어 재현성

**알고리즘 잠금:**
```rust
// randomizer.rs — 알고리즘 변경 금지 주석 포함
// IMPORTANT: This algorithm is locked to match JavaScript randomizer v2.3.2
// DO NOT modify the hash function or bit operations — cross-language reproducibility
// See: tests/property/prng_vectors.rs for verification test vectors
pub struct Randomizer {
    state: u32,
}

impl Randomizer {
    pub fn new(seed: &str) -> Self {
        let mut h: u32 = 1779033703u32.wrapping_add(seed.len() as u32);
        // seed를 UTF-16 코드 포인트로 처리 (JS String.charCodeAt 동일)
        for ch in seed.encode_utf16() {
            h = h.wrapping_mul(3432918353)
                 .wrapping_add(ch as u32)
                 ^ h;
            // JS: h ^= charCode; h = imul(h, 3432918353); h = h<<13 | h>>>19;
            // Rust: XOR 순서 일치 필요 — 테스트 벡터로 검증
            h = h.rotate_left(13);
        }
        Self { state: h }
    }

    pub fn random(&mut self) -> f64 {
        let mut h = self.state;
        h ^= h >> 16;
        h = h.wrapping_mul(2246822507);
        h ^= h >> 13;
        h = h.wrapping_mul(3266489909);
        h ^= h >> 16;
        self.state = h;
        (h as f64) / 4294967296.0
    }
}
```

**테스트 벡터 (JS 사전 계산값):**
```rust
// tests/property/prng_vectors.rs
#[test]
fn prng_matches_js_randomizer() {
    let cases = [
        ("hello",  [0.123456, 0.654321, ...]),  // JS로 계산한 값
        ("gaiaproject", [...]),
        ("seed123", [...]),
    ];
    for (seed, expected) in cases {
        let mut rng = Randomizer::new(seed);
        for &exp in &expected {
            let got = rng.random();
            assert!((got - exp).abs() < 1e-9, "seed={}", seed);
        }
    }
}
```

---

## 5. PBT 속성 패턴 (Maintainability)

### 패턴: test-utils Feature + Proptest Strategies
**근거**: Q4 답변 B — `test-utils` feature로 gaia-server에서도 재사용

**feature 구조:**
```toml
# Cargo.toml
[features]
test-utils = ["dep:proptest"]

[dependencies]
proptest = { version = "1", optional = true }

[dev-dependencies]
proptest = "1"
```

```rust
// src/test_utils/mod.rs  (feature = "test-utils"로 조건부 컴파일)
#[cfg(feature = "test-utils")]
pub mod strategies {
    use proptest::prelude::*;
    use crate::*;

    pub fn valid_resources() -> impl Strategy<Value = Resources> {
        (0u8..=15, 0u8..=30, 0u8..=15, 0u8..=6,
         0u8..=7, 0u8..=7, 0u8..=7)
            .prop_map(|(ore, credits, knowledge, qic, b1, b2, b3)| {
                Resources {
                    ore, credits, knowledge, qic,
                    power: PowerCycle {
                        bowl1: b1, bowl2: b2, bowl3: b3,
                        gaia_bowl: 0, gaia_forming: 0,
                    },
                    spent_gaia_formers: 0,
                }
            })
    }

    pub fn valid_hex_coord() -> impl Strategy<Value = HexCoord> {
        (-10i32..=10, -10i32..=10).prop_map(|(q, r)| HexCoord { q, r })
    }

    // 추가 전략: valid_player_state(), minimal_game_state() 등
}
```

**7개 PBT 속성 위치:**
```
gaia-engine/tests/property/
├── serialization.rs    # 직렬화 라운드트립
├── prng_vectors.rs     # PRNG 시드 일관성 + JS 테스트 벡터
├── scoring.rs          # 득점 단조성
├── terraforming.rs     # 테라포밍 비용 대칭성
├── resources.rs        # 자원 보존 불변식
├── actions.rs          # 액션 후 상태 유효성
└── federation.rs       # 연방 파워 계산
```

---

## 6. 스텁 팩션 경고 매크로 패턴 (Maintainability)

### 패턴: Declarative Macro for Stub Logging
**근거**: Q5 답변 B — 반복 코드 제거, 매크로로 경고 + 기본 반환값 자동 생성

**매크로 정의:**
```rust
// src/faction/ability.rs
#[macro_export]
macro_rules! stub_faction_ability {
    ($faction:expr, $method:expr, $default:expr) => {{
        log::warn!(
            "[STUB] FactionAbility::{} called on {:?} — not yet implemented",
            $method,
            $faction
        );
        $default
    }};
}
```

**매크로 사용 (DefaultFactionAbility):**
```rust
pub struct DefaultFactionAbility {
    pub faction_id: FactionId,
}

impl FactionAbility for DefaultFactionAbility {
    fn on_build(&self, _state: &GameState, _player: PlayerId, _hex: HexCoord)
        -> Vec<GameEvent>
    {
        stub_faction_ability!(self.faction_id, "on_build", vec![])
    }

    fn on_research(&self, _state: &GameState, _player: PlayerId, _track: ResearchTrack)
        -> Vec<GameEvent>
    {
        stub_faction_ability!(self.faction_id, "on_research", vec![])
    }

    fn passive_income(&self, _state: &GameState, _player: PlayerId)
        -> ResourceDelta
    {
        stub_faction_ability!(self.faction_id, "passive_income", ResourceDelta::zero())
    }

    fn special_action(&self, _state: &GameState, _player: PlayerId)
        -> Option<Box<dyn SpecialAction>>
    {
        stub_faction_ability!(self.faction_id, "special_action", None)
    }

    fn final_scoring(&self, _state: &GameState, _player: PlayerId) -> i32 {
        stub_faction_ability!(self.faction_id, "final_scoring", 0)
    }
}
```
