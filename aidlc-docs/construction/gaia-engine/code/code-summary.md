# Code Summary — Unit 1: gaia-engine

## 생성 완료 파일 목록

| 파일 | 단계 | 설명 |
|---|---|---|
| `Cargo.toml` (workspace) | Step 1 | workspace resolver="2", members: [gaia-engine, gaia-server] |
| `gaia-engine/Cargo.toml` | Step 1, 17 | serde/thiserror/log/toml + proptest dev-dep, clippy lints |
| `gaia-engine/src/error.rs` | Step 2 | `RuleError`, `DeserializeError` — thiserror derive |
| `gaia-engine/src/game_state.rs` | Step 3 | 전체 도메인 타입 (HexCoord, GameState, PlayerState, ...) |
| `gaia-engine/src/map/hex.rs` | Step 4 | Axial 좌표 연산, 거리, 이웃, 회전 |
| `gaia-engine/src/map/engine.rs` | Step 4 | MapEngine: BFS 탐색, 연방 연결성, 섹터 점유 |
| `gaia-engine/src/map/mod.rs` | Step 4 | 모듈 재내보내기 |
| `gaia-engine/data/factions.toml` | Step 5 | 18팩션 정적 데이터 |
| `gaia-engine/data/research_tracks.toml` | Step 5 | 6트랙 × 6레벨 효과 테이블 |
| `gaia-engine/data/sectors.toml` | Step 5 | 10섹터 hex 배치 데이터 |
| `gaia-engine/src/data/factions.rs` | Step 6 | TOML 팩션 로더 |
| `gaia-engine/src/data/research_tracks.rs` | Step 6 | TOML 연구 트랙 로더 |
| `gaia-engine/src/data/sectors.rs` | Step 6 | TOML 섹터 로더 |
| `gaia-engine/src/data/mod.rs` | Step 6 | 로더 통합 모듈 |
| `gaia-engine/src/randomizer.rs` | Step 7 | Mulberry32 PRNG (JS v2.3.2 호환), GameSetup 생성 |
| `gaia-engine/src/faction/ability.rs` | Step 8 | `FactionAbility` trait, `stub_faction_ability!` 매크로 |
| `gaia-engine/src/faction/impls/default.rs` | Step 9 | `DefaultFactionAbility` (전체 스텁) |
| `gaia-engine/src/faction/impls/mod.rs` | Step 9 | 팩션 구현체 모듈 |
| `gaia-engine/src/faction/registry.rs` | Step 10 | `FactionRegistry` — 18팩션 HashMap |
| `gaia-engine/src/faction/mod.rs` | Step 10 | 팩션 모듈 재내보내기 |
| `gaia-engine/src/rules/actions.rs` | Step 11 | `SetupAction`, `GameAction`, `QicActionKind` enum |
| `gaia-engine/src/rules/terraforming.rs` | Step 12 | PLANET_RING, 비용 테이블, ring_distance, get_terraforming_cost |
| `gaia-engine/src/rules/engine.rs` | Step 13 | `RuleEngine`: validate/apply 분리, 모든 GameAction 처리 |
| `gaia-engine/src/rules/mod.rs` | Step 13 | 규칙 모듈 재내보내기 |
| `gaia-engine/src/bidding.rs` | Step 14 | `BiddingEngine`: 경매/팩션 선택/턴 순서 배정 |
| `gaia-engine/src/scoring.rs` | Step 15 | `ScoringEngine`: 라운드/최종 득점, 동점 처리 |
| `gaia-engine/src/test_utils/mod.rs` | Step 16 | test-utils feature gate |
| `gaia-engine/src/test_utils/builders.rs` | Step 16 | `GameStateBuilder` 테스트 빌더 |
| `gaia-engine/src/test_utils/strategies.rs` | Step 16 | proptest Arbitrary 전략 |
| `gaia-engine/src/lib.rs` | Step 17 | 모듈 선언 + 공개 API |
| `gaia-engine/tests/unit/mod.rs` | Step 18 | 단위 테스트 진입점 |
| `gaia-engine/tests/unit/rule_engine.rs` | Step 18 | RuleEngine 단위 테스트 |
| `gaia-engine/tests/unit/scoring.rs` | Step 18 | ScoringEngine 단위 테스트 |
| `gaia-engine/tests/unit/bidding.rs` | Step 18 | BiddingEngine 단위 테스트 |
| `gaia-engine/tests/unit/randomizer.rs` | Step 18 | Randomizer 단위 테스트 |
| `gaia-engine/tests/unit/map.rs` | Step 18 | MapEngine 단위 테스트 |
| `gaia-engine/tests/property/mod.rs` | Step 19 | PBT 테스트 진입점 |
| `gaia-engine/tests/property/serialization.rs` | Step 19 | 직렬화 왕복 불변식 |
| `gaia-engine/tests/property/prng_vectors.rs` | Step 19 | PRNG 구조적 불변식 (동일 시드=동일 결과, [0,1) 범위) |
| `gaia-engine/tests/property/scoring.rs` | Step 19 | 득점 단조성 속성 |
| `gaia-engine/tests/property/terraforming.rs` | Step 19 | 테라포밍 비용 대칭성 |
| `gaia-engine/tests/property/resources.rs` | Step 19 | 파워 토큰 보존 불변식 |
| `gaia-engine/tests/property/actions.rs` | Step 19 | 유효 액션 후 상태 유효성 |
| `gaia-engine/tests/property/federation.rs` | Step 19 | 연방 파워 계산 정확성 |

**총 파일 수**: 44개

---

## 스토리 구현 추적

| User Story | 구현 컴포넌트 | 상태 |
|---|---|---|
| US-01: 게임 룸 생성 | `Randomizer::generate_setup()` | ✅ 완료 (스텁) |
| US-03: 랜더마이저 확인/재생성 | `Randomizer::new()`, `GameSetup` | ✅ 완료 |
| US-05: 팩션 선택 + LLM 조언 | `FactionRegistry::get()` | ✅ 완료 (스텁) |
| US-07: 비딩 경매 | `BiddingEngine` | ✅ 완료 |
| US-08: 게임 보드 확인 | `GameState`, `MapEngine` | ✅ 완료 |
| US-09: 액션 수행 | `RuleEngine::validate/apply_action()` | ✅ 완료 |
| US-10: 라운드 패스 | `RuleEngine` → `GameAction::Pass` | ✅ 완료 |
| US-13: 리소스 현황 확인 | `PlayerState::resources` | ✅ 완료 |
| US-14: 라운드 득점 확인 | `ScoringEngine::calculate_round_scoring()` | ✅ 완료 |
| US-15: 최종 득점 계산/확인 | `ScoringEngine::calculate_final_scoring()` | ✅ 완료 |

---

## 주요 공개 API

### Randomizer
```rust
pub fn Randomizer::new(seed: &str) -> Randomizer
pub fn Randomizer::generate_setup(seed: &str) -> GameSetup
pub fn Randomizer::random(&mut self) -> f64       // [0.0, 1.0)
pub fn Randomizer::shuffle<T>(&mut self, arr: &mut Vec<T>)
pub fn Randomizer::random_int(&mut self, n: usize) -> usize
```

### RuleEngine
```rust
pub fn RuleEngine::validate_action(state: &GameState, player_id: PlayerId, action: &GameAction) -> Result<(), RuleError>
pub fn RuleEngine::apply_action(state: &mut GameState, player_id: PlayerId, action: GameAction) -> Result<Vec<GameEvent>, RuleError>
pub fn RuleEngine::get_valid_actions(state: &GameState, player_id: PlayerId) -> Vec<GameAction>
pub fn RuleEngine::validate_setup_action(state: &GameState, player_id: PlayerId, action: &SetupAction) -> Result<(), RuleError>
pub fn RuleEngine::apply_setup_action(state: &mut GameState, player_id: PlayerId, action: SetupAction) -> Result<Vec<GameEvent>, RuleError>
```

### ScoringEngine
```rust
pub fn ScoringEngine::calculate_round_scoring(state: &GameState, round: u8) -> Vec<(PlayerId, i32)>
pub fn ScoringEngine::calculate_final_scoring(state: &GameState) -> [(PlayerId, i32); 4]
```

### BiddingEngine
```rust
pub fn BiddingEngine::new(player_ids: Vec<PlayerId>, pairs: Vec<FactionPair>) -> BiddingState
pub fn BiddingEngine::place_bid(state: &mut BiddingState, player: PlayerId, pair_index: u8, vp: u32) -> Result<BidEvent, RuleError>
pub fn BiddingEngine::pass_bid(state: &mut BiddingState, player: PlayerId) -> Result<BidEvent, RuleError>
pub fn BiddingEngine::select_faction(state: &mut BiddingState, player: PlayerId, faction: FactionId) -> Result<BidEvent, RuleError>
pub fn BiddingEngine::select_turn_order(state: &mut BiddingState, player: PlayerId, position: u8) -> Result<BidEvent, RuleError>
```

### MapEngine
```rust
pub fn MapEngine::reachable_hexes(board: &BoardState, starts: &[HexCoord], range: u8) -> HashSet<HexCoord>
pub fn MapEngine::is_connected(hexes: &[HexCoord]) -> bool
pub fn MapEngine::federation_power(board: &BoardState, player: PlayerId, hexes: &[HexCoord]) -> u32
pub fn MapEngine::sectors_occupied(board: &BoardState, player: PlayerId) -> usize
```

---

## 주요 수정 사항 (룰북 검증 후)

룰북(EN_Gaia_rulebook_lo.pdf) 검토 후 발견된 규칙 오류 수정:

| 항목 | 수정 전 | 수정 후 | 근거 |
|---|---|---|---|
| 광산 건설 비용 | 1광석만 | 1광석 + 2크레딧 + 테라포밍 광석 | 룰북 p.12 |
| 항법 범위 공식 | `level + 1` | `[1,1,2,2,3,4][level]` | 룰북 p.22 |
| 테라포밍 레벨 3 비용 | 2광석/단계 | 1광석/단계 | 룰북 p.22 |
| 업그레이드 비용 (4종) | 임의값 | 룰북 정확한 비용 | 룰북 p.13 |
| 아카데미 파워 값 | 4 | 3 | 룰북 p.12 |
| 최종 득점 조건 | 잘못된 변형 | 6기본 + 3확장팩 타일 정확 | 룰북 p.18 |
| 가이아 행성 VP | 2VP/광산 포함 | 제거 (기술 타일 보너스, 기본 득점 아님) | 룰북 p.18 |
| 자원 변환 VP | QIC/파워 포함 | 광석+크레딧+지식만 | 룰북 p.18 |
| 가이아 프로젝트 파워 비용 | 없음 | `[∞,6,6,4,3,3][level]` | 룰북 p.22 |
