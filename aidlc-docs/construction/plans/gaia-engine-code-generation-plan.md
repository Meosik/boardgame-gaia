# Code Generation Plan — Unit 1: gaia-engine

## 단위 컨텍스트

| 항목 | 내용 |
|---|---|
| 단위 | Unit 1: gaia-engine |
| 경로 | `/home/sohegi/projects/gaia/gaia-engine/` |
| 유형 | Rust crate (Cargo workspace member) |
| 의존 단위 | 없음 (독립) |
| 테스트 전략 | Cargo unit tests + proptest PBT |

## 구현 스토리 (gaia-engine 기여)

| 스토리 | 제목 | 담당 컴포넌트 |
|---|---|---|
| US-01 | 게임 룸 생성 | Randomizer |
| US-03 | 랜더마이저 확인/재생성 | Randomizer, GameState |
| US-05 | 자유 팩션 선택 + LLM 조언 | FactionRegistry |
| US-07 | 비딩 경매 | BiddingEngine |
| US-08 | 게임 보드 확인 | GameState, MapEngine |
| US-09 | 액션 수행 | RuleEngine, GameState |
| US-10 | 라운드 패스 | RuleEngine |
| US-13 | 리소스 현황 확인 | GameState |
| US-14 | 라운드 득점 확인 | ScoringEngine |
| US-15 | 최종 득점 계산/확인 | ScoringEngine, BidPenalty |

---

## 실행 체크리스트

### Part 1 — Planning
- [x] Step A: 단위 컨텍스트 분석
- [x] Step B: 코드 생성 계획 수립
- [ ] Step C: 계획 저장 (이 파일)
- [ ] Step D: 계획 승인 대기

### Part 2 — Generation
- [x] Step 1: 프로젝트 구조 설정 (Cargo workspace + gaia-engine 스켈레톤)
- [x] Step 2: 에러 타입 — `src/error.rs`
- [x] Step 3: 핵심 도메인 타입 — `src/game_state.rs`
- [x] Step 4: 맵 모듈 — `src/map/`
- [x] Step 5: TOML 데이터 파일 — `data/`
- [x] Step 6: 데이터 로더 — `src/data/`
- [x] Step 7: Randomizer — `src/randomizer.rs`
- [x] Step 8: FactionAbility trait + stub 매크로 — `src/faction/ability.rs`
- [x] Step 9: DefaultFactionAbility (전체 스텁) — `src/faction/impls/`
- [x] Step 10: FactionRegistry — `src/faction/registry.rs`
- [x] Step 11: Action 열거형 — `src/rules/actions.rs`
- [x] Step 12: 테라포밍 비용 — `src/rules/terraforming.rs`
- [x] Step 13: RuleEngine — `src/rules/engine.rs`
- [x] Step 14: BiddingEngine — `src/bidding.rs`
- [x] Step 15: ScoringEngine — `src/scoring.rs`
- [x] Step 16: test-utils feature 모듈 — `src/test_utils/`
- [x] Step 17: lib.rs 모듈 선언 + Cargo.toml 최종 확정
- [x] Step 18: 단위 테스트 — `tests/unit/`
- [x] Step 19: PBT 속성 테스트 — `tests/property/`
- [x] Step 20: 코드 요약 문서 — `aidlc-docs/construction/gaia-engine/code/`

---

## 단계별 상세 설명

### Step 1: 프로젝트 구조 설정
**생성 파일:**
```
/home/sohegi/projects/gaia/
├── Cargo.toml                    ← workspace 정의 (members: engine, server)
├── Cargo.lock
└── gaia-engine/
    ├── Cargo.toml                ← 크레이트 의존성 + lint 설정
    └── src/
        └── lib.rs                ← (빈 파일, Step 17에서 채움)
```
**내용**: workspace `Cargo.toml` (resolver="2"), `gaia-engine/Cargo.toml` (serde, serde_json, log, thiserror, toml + dev: proptest)

---

### Step 2: 에러 타입
**파일**: `gaia-engine/src/error.rs`
**내용**: `RuleError` enum (domain-entities.md 전체 variant), `DeserializeError` enum. `thiserror::Error` derive.

---

### Step 3: 핵심 도메인 타입
**파일**: `gaia-engine/src/game_state.rs`
**내용**: 아래 모든 타입 정의 (domain-entities.md 기반)
- `PlayerId`, `RoomCode`, `ShipId`, `BoosterId` newtype
- `PlanetType`, `StructureType`, `AcademyType`, `SpaceTileKind`
- `HexCoord` (Axial), 기본 연산 메서드
- `Resources`, `PowerCycle`
- `PlayerState`, `Structure`, `ResearchTracks`
- `BoardState`, `Sector`, `Hex`, `Planet`, `PlacedStructure`
- `GameState` (전체 필드 + `serialize()`, `deserialize()`)
- `GamePhase`, `SetupPhase`
- `BiddingState`, `BidAssignment`, `FactionPair`
- `ResearchBoard`, `TrackState`, `ResearchTrack`
- `GameEvent`, `ResourceDelta`, `VpReason`, `PowerDelta`
- `FinalScoringCondition`, `FinalScoringTile`
- `ResourceKind` (RuleError용)

---

### Step 4: 맵 모듈
**파일**: `gaia-engine/src/map/hex.rs`, `src/map/engine.rs`, `src/map/mod.rs`
**내용**:
- `hex.rs`: HexCoord distance, neighbors(6방향), rotate_60, axial_to_cube
- `engine.rs`: MapEngine — BFS 탐색(항법 범위), 연방 연결성 BFS, 섹터 hex 좌표 생성 (섹터 원점 + 회전 적용)

---

### Step 5: TOML 데이터 파일
**파일**: `gaia-engine/data/factions.toml`, `data/research_tracks.toml`, `data/sectors.toml`
**내용**:
- `factions.toml`: 18팩션 데이터 (홈 행성, 시작 자원, 시작 구조물, 수입 테이블, 가이아포머 수)
- `research_tracks.toml`: 6트랙 × 레벨 0-5 즉시 자원 효과 테이블
- `sectors.toml`: 각 섹터 ID별 hex 배치 (행성 타입 + 상대 좌표), Center Balance 섹터 01-04 포함

---

### Step 6: 데이터 로더
**파일**: `gaia-engine/src/data/factions.rs`, `src/data/research_tracks.rs`, `src/data/sectors.rs`, `src/data/mod.rs`
**내용**: `include_str!()` + toml 역직렬화. `FactionData`, `ResearchTrackEffects`, `SectorTemplate` 구조체.

---

### Step 7: Randomizer
**파일**: `gaia-engine/src/randomizer.rs`
**내용**:
- `Randomizer { state: u32 }` struct
- `new(seed: &str)` — Mulberry32 변형 해시 (JS 랜더마이저 동일)
- `random() -> f64` — [0.0, 1.0)
- `shuffle<T>(arr: &mut Vec<T>)` — Fisher-Yates
- `generate_setup(seed: &str) -> GameSetup` — 7단계 셋업 생성
- `GameSetup` 구조체 (faction_pairs, round_tiles, boosters, final_scoring, tech_tiles, advanced_tech, sector_layout)
- **스토리 적용**: US-01(Randomizer), US-03(Randomizer)

---

### Step 8: FactionAbility trait + stub 매크로
**파일**: `gaia-engine/src/faction/ability.rs`
**내용**:
- `FactionAbility` trait (on_build, on_research, passive_income, special_action, final_scoring, federation_power_override)
- `SpecialAction` trait (dyn 객체)
- `stub_faction_ability!` declarative macro (`log::warn!` + 기본값 반환)
- `FederationPowerRule` enum

---

### Step 9: DefaultFactionAbility + 18팩션 스텁
**파일**: `gaia-engine/src/faction/impls/default.rs`, `src/faction/impls/mod.rs`
**내용**:
- `DefaultFactionAbility { faction_id: FactionId }` struct
- 모든 `FactionAbility` 메서드를 `stub_faction_ability!` 매크로로 구현
- 18팩션 `FactionId` enum 정의 (기본 14팩션 + Lost Fleet 4팩션)
- **스토리 적용**: US-05(FactionRegistry)

---

### Step 10: FactionRegistry
**파일**: `gaia-engine/src/faction/registry.rs`, `src/faction/mod.rs`
**내용**:
- `FactionRegistry` struct + `HashMap<FactionId, Box<dyn FactionAbility>>`
- `new()` — 18팩션 모두 DefaultFactionAbility로 초기화
- `get(faction: FactionId) -> &dyn FactionAbility`
- `FactionData` 로드 연동
- **스토리 적용**: US-05(FactionRegistry)

---

### Step 11: Action 열거형
**파일**: `gaia-engine/src/rules/actions.rs`
**내용**:
- `SetupAction` enum (PlaceBid, PassBid, SelectFaction, SelectTurnOrder)
- `GameAction` enum (Build, Upgrade, ResearchAdvance, FormFederation, PowerAction, SpecialAction, GaiaFormation, QicAction, Pass)
- `QicActionKind` enum
- `PowerActionId`, `SpecialActionId` type alias

---

### Step 12: 테라포밍 비용
**파일**: `gaia-engine/src/rules/terraforming.rs`
**내용**:
- `PLANET_RING: [PlanetType; 7]` 상수 (환경 링 순서)
- `get_terraforming_cost(from: PlanetType, to: PlanetType, track_level: u8) -> u8`
- 순환 최단 거리 계산 + 레벨별 비용 매핑

---

### Step 13: RuleEngine
**파일**: `gaia-engine/src/rules/engine.rs`, `src/rules/mod.rs`
**내용**:
- `RuleEngine` struct (상태 없음, 모든 메서드 static)
- `validate_action(state, player, action) -> Result<(), RuleError>` — 페이즈/턴/자원/대상 검증
- `apply_action(state, player, action) -> Result<Vec<GameEvent>, RuleError>` — 내부 apply_unchecked 패턴
- `apply_unchecked(state, player, action) -> Vec<GameEvent>` — 실패 없는 상태 변이
- `get_valid_actions(state, player) -> Vec<GameAction>`
- 각 GameAction별 private 검증 + 적용 함수
- 파워 충전 계산 (`charge_power`)
- 항법 BFS 호출 (MapEngine 사용)
- **스토리 적용**: US-09(RuleEngine), US-10(RuleEngine)

---

### Step 14: BiddingEngine
**파일**: `gaia-engine/src/bidding.rs`
**내용**:
- `BiddingEngine` struct
- `new(players, faction_pairs) -> (BiddingEngine, BiddingState)`
- `place_bid(state, player, amount) -> Result<BidEvent, RuleError>`
- `pass_bid(state, player) -> Result<BidEvent, RuleError>`
- `select_faction(state, player, faction) -> Result<BidEvent, RuleError>`
- `select_turn_order(state, player, position) -> Result<BidEvent, RuleError>`
- `check_auction_complete(state) -> Option<PlayerId>` — 낙찰자 결정
- `BidEvent` enum
- **스토리 적용**: US-07(BiddingEngine)

---

### Step 15: ScoringEngine
**파일**: `gaia-engine/src/scoring.rs`
**내용**:
- `ScoringEngine` struct
- `calculate_round_scoring(state, round) -> Vec<(PlayerId, i32)>` — 이벤트 기반
- `calculate_final_scoring(state) -> [(PlayerId, i32); 4]`
  - 최종 득점 타일 2개 (기본 6 + Lost Fleet 3 = 9개 풀)
  - Gaia Project 득점
  - 연구 트랙 VP
  - 자원 → VP 변환
  - 팩션 특수 최종 득점 (FactionAbility.final_scoring)
  - 비딩 VP 차감
- 동점 처리 (균등 분배)
- **스토리 적용**: US-14(ScoringEngine), US-15(ScoringEngine, BidPenalty)

---

### Step 16: test-utils feature 모듈
**파일**: `gaia-engine/src/test_utils/mod.rs`, `src/test_utils/strategies.rs`, `src/test_utils/builders.rs`
**내용**:
- feature gate: `#[cfg(any(test, feature = "test-utils"))]`
- `strategies.rs`: proptest 전략 (valid_resources, valid_hex_coord, valid_player_state, minimal_game_state)
- `builders.rs`: `GameStateBuilder` (테스트용 명시적 빌더)

---

### Step 17: lib.rs 모듈 선언 + Cargo.toml 최종 확정
**파일**: `gaia-engine/src/lib.rs`, `gaia-engine/Cargo.toml`
**내용**:
- `lib.rs`: 모든 모듈 선언 (`pub mod`, `pub use`)
- `Cargo.toml`: 모든 의존성 확정, `[lints.clippy]` unwrap_used/expect_used/panic = "deny", `[features]` test-utils

---

### Step 18: 단위 테스트
**파일**: `gaia-engine/tests/unit/rule_engine.rs`, `scoring.rs`, `bidding.rs`, `randomizer.rs`, `map.rs`, `mod.rs`
**내용**: 각 컴포넌트 핵심 경로 + 모든 RuleError variant 검증. 70%+ 커버리지 목표.

---

### Step 19: PBT 속성 테스트
**파일**: `gaia-engine/tests/property/` (7개 파일)
**내용**:
- `serialization.rs`: `deserialize(serialize(state)) == state`
- `prng_vectors.rs`: JS 랜더마이저 테스트 벡터 비교 (3개 이상 시드)
- `scoring.rs`: 득점 단조성
- `terraforming.rs`: `cost(A→B) == cost(B→A)`
- `resources.rs`: 파워 보존 불변식 (`bowl1+bowl2+bowl3+gaia_bowl+gaia_forming = 상수`)
- `actions.rs`: 유효 액션 후 상태 유효성
- `federation.rs`: 연방 파워 계산 정확성

---

### Step 20: 코드 요약 문서
**파일**: `aidlc-docs/construction/gaia-engine/code/code-summary.md`
**내용**: 생성된 파일 목록, 스토리 구현 추적, 주요 공개 API 목록

---

## 생성 파일 전체 목록

```
/home/sohegi/projects/gaia/
├── Cargo.toml                                    ← Step 1
├── gaia-engine/
│   ├── Cargo.toml                                ← Step 1, 17
│   ├── data/
│   │   ├── factions.toml                         ← Step 5
│   │   ├── research_tracks.toml                  ← Step 5
│   │   └── sectors.toml                          ← Step 5
│   ├── src/
│   │   ├── lib.rs                                ← Step 17
│   │   ├── error.rs                              ← Step 2
│   │   ├── game_state.rs                         ← Step 3
│   │   ├── randomizer.rs                         ← Step 7
│   │   ├── bidding.rs                            ← Step 14
│   │   ├── scoring.rs                            ← Step 15
│   │   ├── map/
│   │   │   ├── mod.rs                            ← Step 4
│   │   │   ├── hex.rs                            ← Step 4
│   │   │   └── engine.rs                         ← Step 4
│   │   ├── data/
│   │   │   ├── mod.rs                            ← Step 6
│   │   │   ├── factions.rs                       ← Step 6
│   │   │   ├── research_tracks.rs                ← Step 6
│   │   │   └── sectors.rs                        ← Step 6
│   │   ├── faction/
│   │   │   ├── mod.rs                            ← Step 10
│   │   │   ├── ability.rs                        ← Step 8
│   │   │   ├── registry.rs                       ← Step 10
│   │   │   └── impls/
│   │   │       ├── mod.rs                        ← Step 9
│   │   │       └── default.rs                    ← Step 9
│   │   ├── rules/
│   │   │   ├── mod.rs                            ← Step 13
│   │   │   ├── actions.rs                        ← Step 11
│   │   │   ├── terraforming.rs                   ← Step 12
│   │   │   └── engine.rs                         ← Step 13
│   │   └── test_utils/
│   │       ├── mod.rs                            ← Step 16
│   │       ├── strategies.rs                     ← Step 16
│   │       └── builders.rs                       ← Step 16
│   └── tests/
│       ├── unit/
│       │   ├── mod.rs                            ← Step 18
│       │   ├── rule_engine.rs                    ← Step 18
│       │   ├── scoring.rs                        ← Step 18
│       │   ├── bidding.rs                        ← Step 18
│       │   ├── randomizer.rs                     ← Step 18
│       │   └── map.rs                            ← Step 18
│       └── property/
│           ├── mod.rs                            ← Step 19
│           ├── serialization.rs                  ← Step 19
│           ├── prng_vectors.rs                   ← Step 19
│           ├── scoring.rs                        ← Step 19
│           ├── terraforming.rs                   ← Step 19
│           ├── resources.rs                      ← Step 19
│           ├── actions.rs                        ← Step 19
│           └── federation.rs                     ← Step 19
└── aidlc-docs/construction/gaia-engine/code/
    └── code-summary.md                           ← Step 20
```

**총 파일 수**: 39개 (소스 38개 + 문서 1개)
