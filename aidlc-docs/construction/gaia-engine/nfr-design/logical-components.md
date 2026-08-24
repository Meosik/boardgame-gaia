# Logical Components — gaia-engine

## 범위 노트

gaia-engine은 순수 라이브러리 크레이트입니다. 외부 인프라 컴포넌트(메시지 큐, 캐시, 서킷 브레이커, 로드 밸런서 등)가 없습니다. 이 문서는 **내부 논리 컴포넌트**와 **크레이트 구조 결정**을 다룹니다.

---

## 1. 에러 타입 모듈 구조

```
gaia-engine/src/
├── error.rs           ← RuleError, DeserializeError 정의
└── lib.rs             ← pub use error::{RuleError, DeserializeError};
```

**error.rs 책임:**
- `RuleError` enum (모든 규칙 위반 variant)
- `DeserializeError` enum (역직렬화 실패 variant)
- 두 타입은 서로 독립적 (공통 상위 타입 없음)
- `thiserror::Error` derive로 `Display` 자동 구현

**소비자별 처리 흐름:**
```
gaia-server → apply_action() → RuleError       → WebSocket 에러 메시지 전송
gaia-server → deserialize()  → DeserializeError → DB 복구 로직 / 치명적 로그
```

---

## 2. Clippy Lint 강제 컴포넌트

**위치**: `gaia-engine/Cargo.toml` (또는 workspace root `Cargo.toml`)

```toml
[lints.clippy]
unwrap_used = "deny"
expect_used = "deny"
panic       = "deny"
```

**범위**: `gaia-engine` 크레이트 소스 전체 (`src/`)
**예외**: `tests/` 디렉터리 — 테스트 코드에는 `unwrap()` 허용
```rust
// 테스트 내에서는 lint 억제 가능
#[allow(clippy::unwrap_used)]
fn test_helper() -> GameState { ... }
```

---

## 3. test-utils Feature 모듈

**위치**: `gaia-engine/src/test_utils/`

```
src/test_utils/
├── mod.rs             ← feature gate + 재익스포트
├── strategies.rs      ← proptest Arbitrary 전략 (Resources, HexCoord, PlayerState 등)
└── builders.rs        ← 테스트용 GameState 빌더 (minimal_game_state() 등)
```

**컴파일 조건:**
```rust
// src/lib.rs
#[cfg(any(test, feature = "test-utils"))]
pub mod test_utils;
```

**gaia-server에서 재사용:**
```toml
# gaia-server/Cargo.toml (dev-dependencies)
[dev-dependencies]
gaia-engine = { path = "../gaia-engine", features = ["test-utils"] }
```

**제공 인터페이스:**
```rust
// gaia-engine::test_utils::strategies 네임스페이스
pub fn valid_resources()   -> impl Strategy<Value = Resources>
pub fn valid_hex_coord()   -> impl Strategy<Value = HexCoord>
pub fn valid_player_state() -> impl Strategy<Value = PlayerState>
pub fn minimal_game_state() -> impl Strategy<Value = GameState>

// gaia-engine::test_utils::builders 네임스페이스  
pub struct GameStateBuilder { ... }  // 명시적 필드 설정용
impl GameStateBuilder {
    pub fn new() -> Self
    pub fn with_round(self, round: u8) -> Self
    pub fn with_player(self, idx: usize, player: PlayerState) -> Self
    pub fn build(self) -> GameState
}
```

---

## 4. PBT 테스트 모듈 구조

**위치**: `gaia-engine/tests/property/`

```
tests/
├── unit/
│   ├── rule_engine.rs     ← 단위 테스트 (RuleError 케이스별)
│   ├── scoring.rs
│   ├── bidding.rs
│   ├── randomizer.rs
│   └── map.rs
└── property/
    ├── mod.rs             ← proptest 공통 설정
    ├── serialization.rs   ← GameState 직렬화 라운드트립
    ├── prng_vectors.rs    ← PRNG 시드 일관성 + JS 테스트 벡터
    ├── scoring.rs         ← 득점 단조성
    ├── terraforming.rs    ← 비용 대칭성
    ├── resources.rs       ← 파워 보존 불변식
    ├── actions.rs         ← 액션 후 상태 유효성
    └── federation.rs      ← 연방 파워 계산
```

**proptest 설정** (`tests/property/mod.rs`):
```rust
// PBT 실행 케이스 수 설정
proptest::proptest_config!(ProptestConfig {
    cases: 256,          // 기본 100 → 256으로 증가
    max_shrink_iters: 512,
    ..ProptestConfig::default()
});
```

---

## 5. stub_faction_ability! 매크로 컴포넌트

**위치**: `gaia-engine/src/faction/ability.rs`

**공개 범위**: `#[macro_export]` — 크레이트 루트에서 `gaia_engine::stub_faction_ability!` 로 접근 가능

**내부 사용처:**
- `gaia-engine/src/faction/impls/default.rs` — `DefaultFactionAbility` 18팩션 스텁 구현
- 개별 팩션 구현 파일이 stub_faction_ability!를 거쳐 점진적으로 실제 구현으로 교체됨

**팩션 구현 파일 구조:**
```
src/faction/impls/
├── default.rs         ← DefaultFactionAbility (모든 메서드 stub)
├── terrans.rs         ← Terrans 실제 구현 (stub 교체)
├── lantids.rs         ← Lantids 실제 구현 (stub 교체)
...                    ← 18팩션 순차 구현
```

---

## 6. FactionRegistry 컴포넌트

**위치**: `gaia-engine/src/faction/registry.rs`

**역할**: FactionId → FactionAbility trait object 매핑

```rust
pub struct FactionRegistry {
    abilities: HashMap<FactionId, Box<dyn FactionAbility>>,
}

impl FactionRegistry {
    pub fn new() -> Self {
        // 모든 18팩션을 DefaultFactionAbility로 초기화
        // 실제 구현 완료 시 해당 팩션만 교체
        let mut abilities = HashMap::new();
        for faction in FactionId::all() {
            abilities.insert(faction, Box::new(DefaultFactionAbility { faction_id: faction })
                as Box<dyn FactionAbility>);
        }
        // 완료된 팩션 교체 예시:
        // abilities.insert(FactionId::Terrans, Box::new(TerransAbility));
        Self { abilities }
    }

    pub fn get(&self, faction: FactionId) -> &dyn FactionAbility {
        self.abilities.get(&faction)
            .map(|b| b.as_ref())
            .unwrap_or(&DefaultFactionAbility { faction_id: faction })
            // unwrap_or는 registry 초기화 보장으로 실제로 도달 불가
    }
}
```

---

## 7. TOML 데이터 로더 컴포넌트

**위치**: `gaia-engine/src/data/`

```
src/data/
├── mod.rs
├── factions.rs        ← include_str!() + serde 역직렬화
├── research_tracks.rs ← 트랙별 레벨 효과 TOML 로드
└── sectors.rs         ← 섹터 행성 배치 TOML 로드

data/                  ← 크레이트 루트 기준 (src/ 밖)
├── factions.toml
├── research_tracks.toml
└── sectors.toml
```

**컴파일 타임 임베드 패턴:**
```rust
// src/data/factions.rs
static FACTIONS_TOML: &str = include_str!("../../data/factions.toml");

pub fn load_factions() -> Vec<FactionData> {
    toml::from_str(FACTIONS_TOML)
        .expect("factions.toml is invalid — build-time data error")
    // include_str! + 알려진 정적 데이터이므로 expect() 예외적 허용
    // (런타임 입력이 아닌 컴파일된 데이터)
}
```

**의존성 추가:**
```toml
[dependencies]
toml = "0.8"
```
