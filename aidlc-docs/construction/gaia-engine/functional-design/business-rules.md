# Business Rules — gaia-engine

## 1. 페이즈 규칙

### BR-P01: 페이즈별 허용 액션
- `GamePhase::Setup(SetupPhase::Bidding)` → `SetupAction::PlaceBid`, `SetupAction::PassBid`만 허용
- `GamePhase::Setup(SetupPhase::BiddingChoice)` → `SetupAction::ChooseBidReward`만 허용 (낙찰자만)
- `GamePhase::Setup(SetupPhase::FactionSelection)` → `SetupAction::SelectFaction`만 허용 (현재 플레이어만)
- `GamePhase::Setup(SetupPhase::StartingStructures)` → `SetupAction::PlaceStartingStructure`만 허용 (현재 배치 플레이어만)
- `GamePhase::ActionPhase` → `GameAction` 전체 허용 (단, 개별 액션 조건 별도 확인)
- 비 해당 페이즈에서 액션 시도 → `RuleError::WrongPhase`

### BR-P02: 턴 순서 준수
- `turn_order[current_player] == player_id` 이어야만 GameAction 수행 가능
- 위반 시 → `RuleError::NotYourTurn`

### BR-P03: 패스한 플레이어 제외
- `player.passed == true`이면 추가 GameAction 불가
- 위반 시 → `RuleError::AlreadyPassed`

---

## 2. 비딩 규칙

### BR-B01: 최고가 초과 원칙
- `PlaceBid(n)` 시 `n > max(current_bids.values())` 이어야 함
- 위반 시 → `RuleError::BidTooLow { current_max, placed }`

### BR-B02: VP 한도
- `PlaceBid(n)` 시 `n <= player.vp as u32` 이어야 함 (보유 VP 초과 불가)
- 위반 시 → `RuleError::BidExceedsVp { bid, vp }`

### BR-B03: 경매 탈락
- `PassBid` 시 해당 경매의 `passed` 집합에 추가
- 경매 탈락 후 재입찰 불가 (당 경매 한정)

### BR-B04: 낙찰 조건
- `remaining_players`에서 `passed` 제외 시 1명만 남으면 → 즉시 낙찰
- 또는 `remaining_players` 전원이 `passed` → 마지막으로 `PlaceBid`한 플레이어 낙찰

### BR-B05: 자동 배정
- 세 번의 낙찰 뒤 마지막 1명에게 남은 팩션과 턴 위치를 자동 배정
- `setup_bid_vp = 0` 설정

### BR-B06: 팩션 선택 범위
- `ChooseBidReward`의 `faction_id`는 아직 선택되지 않은 공개 팩션이어야 함
- 위반 시 → `RuleError::ActionNotAllowed`

### BR-B07: 턴 순서 선택 범위
- `ChooseBidReward`의 `turn_position`은 1-4 중 아직 선택되지 않은 값이어야 함
- 위반 시 → `RuleError::ActionNotAllowed`

---

## 2a. 시작 구조물 배치 규칙

### BR-S01: 배치 순서
- 첫 구조물은 최종 턴 순서대로 시계 방향 배치
- 둘째 구조물은 역순으로 반시계 방향 배치
- Xenos의 셋째 Mine은 모든 둘째 배치 뒤에 배치
- Ivits의 PlanetaryInstitute는 모든 Mine 배치 뒤 마지막으로 배치
- 시작 구조물이 하나인 Lost Fleet 팩션은 첫 배치를 건너뛰고 반시계 방향 단계에서 배치

### BR-S02: 배치 대상
- 팩션 데이터의 `home_planet`과 같은 타입의 행성에만 배치 가능
- Gaia 형성 행성, 이미 소유자가 있는 행성, 구조물이 있는 hex에는 배치 불가
- 위반 시 → `RuleError::InvalidTarget` 또는 `RuleError::TargetOccupied`

### BR-S03: 배치 효과
- `PlayerState.structures`, `Planet.owner`, `Hex.structures`를 하나의 액션에서 함께 갱신
- 자원과 건설 비용은 소모하지 않으며 셋업 중 파워 충전도 발생하지 않음
- 마지막 배치 뒤에는 `StartingBoosters`로 전환하며 아직 첫 라운드 수입을 지급하지 않음

### BR-S04: 초기 부스터 선택
- 최종 턴 순서의 마지막 플레이어부터 역순으로 하나씩 선택
- 선택 대상은 `GameState.boosters`에 남아 있어야 하며 중복 선택 불가
- 전원 선택 완료 후에만 `round=1`, `Setup::Complete`로 전환
- 서버는 완료 직후 구조물·연구트랙·팩션·부스터 수입을 적용하고 액션 단계를 시작

---

## 3. 건설 규칙

### BR-C01: 신규 건설은 Mine만
- `Build { structure }` 시 `structure == StructureType::Mine`이어야 함
- `LostPlanet`도 Mine만 건설 가능 (테라포밍 없이)
- 위반 시 → `RuleError::InvalidUpgrade`

### BR-C02: 대상 행성 존재
- `hex`에 `Planet`이 있어야 함
- `PlanetType::Empty`인 hex에 건설 불가
- 위반 시 → `RuleError::InvalidTarget`

### BR-C03: 점령 여부
- 이미 Mine이 있는 행성은 동일 플레이어도 재건설 불가
- 위반 시 → `RuleError::TargetOccupied`

### BR-C04: 도달 범위
- BFS 기준 최단 거리 ≤ `player.research_tracks.navigation + 1`
- 위반 시 → `RuleError::OutOfRange`

### BR-C05: 테라포밍 비용
- 홈 행성 타입이면 테라포밍 비용 없음
- 다른 타입이면 환경 링 거리 × 레벨별 ore 비용
- `Transdim`는 테라포밍 불가 (GaiaFormation 별도 액션)
- 자원 부족 시 → `RuleError::InsufficientResources`

### BR-C06: 건설 비용 (Mine)
- `ore: 2` + `credits: 0` (기본, 부스터/기술 효과 별도)
- 자원 부족 시 → `RuleError::InsufficientResources`

### BR-C07: 타인 파워 충전
- 건설 시 인접(거리 1-3) 타 플레이어 구조물 보유자에게 파워 충전 발생
- 거리 1: 해당 플레이어에게 파워 충전 제안 (수락/거부 가능, 비용 없음)
  - 규칙상 VP 1 지불로 거부 가능 (선택적 구현)
- 거리 2: 자동 파워 충전 없음 (가이아 프로젝트 규칙상 거리 1만)

---

## 4. 업그레이드 규칙

### BR-U01: 유효 업그레이드 경로
```
Mine → TradingStation (ore 3, credits 0)
TradingStation → PlanetaryInstitute (ore 3, credits 0)  [플레이어당 1개]
TradingStation → ResearchLab (ore 2, knowledge 0)
ResearchLab → Academy (ore 3, knowledge 0)  [플레이어당 2개]
```
- 경로 외 업그레이드 → `RuleError::InvalidUpgrade`

### BR-U02: 고유 구조물 한도
- `PlanetaryInstitute`: 플레이어당 1개
- `Academy`: 플레이어당 2개 (Science 1개, Qic 1개)
- 한도 초과 시 → `RuleError::StructureLimit`

### BR-U03: 인접 보너스
- `TradingStation` 업그레이드 시: 인접 타 플레이어 구조물 수에 따른 credits 보너스
- 인접 없음: credits 3, 있음: credits 6 (표준 규칙)

---

## 5. 연방 구성 규칙

### BR-F01: 최소 파워 7
- 연방 내 구조물 파워 합계 ≥ 7 (Satellite 제외)
- 미달 시 → `RuleError::FederationInsufficientPower`

### BR-F02: 연결성
- 제출한 모든 hex가 단일 connected component 형성
- Satellite는 연결 역할 포함
- 위반 시 → `RuleError::FederationDisconnected`

### BR-F03: 소유권
- 모든 hex의 구조물이 해당 플레이어 소유여야 함
- 위반 시 → `RuleError::InvalidTarget`

### BR-F04: 연방 토큰 필요
- `state.research_board.federation_tokens`에 토큰이 남아 있어야 함
- 없으면 연방 구성 불가

### BR-F05: Satellite 배치
- Satellite는 빈 우주 hex에만 배치 (행성 hex에는 배치 불가)
- Satellite 배치 비용: QIC 1개

---

## 6. 연구 트랙 규칙

### BR-R01: 진행 비용
- `knowledge: 4` 소비
- 자원 부족 시 → `RuleError::InsufficientResources`

### BR-R02: 최대 레벨
- 레벨 5 이상 진행 불가
- 위반 시 → `RuleError::ActionNotAllowed`

### BR-R03: 동맹 칸 선점
- 레벨 3, 4, 5 도달 시 해당 동맹 칸에 플레이어 말 배치
- 이미 점유 중인 칸은 건너뜀 (진행은 가능, 동맹 타일만 못 받음)

### BR-R04: 레벨 5 연방 토큰
- 레벨 5 최초 도달 시 연방 토큰 1개 지급
- 토큰 풀이 비어있으면 미지급 (에러 아님)

---

## 7. 가이아 포밍 규칙

### BR-G01: 대상 행성
- 대상 hex의 `planet.planet_type == PlanetType::Transdim` 이어야 함
- 다른 타입 → `RuleError::InvalidTarget`

### BR-G02: Gaiaformer 보유
- 플레이어가 사용 가능한 Gaiaformer를 보유해야 함 (Gaia 트랙 레벨에 따라 해금)
  - Gaia 트랙 레벨 1: Gaiaformer 1개
  - 레벨 2: 2개
  - 레벨 3: 3개

### BR-G03: 비용
- 사용 가능한 Gaiaformer 1개를 배치하고 Gaia Project 연구 레벨에 따른 파워(6/4/3)를 I/II/III 구역에서 `gaia_forming`으로 이동
- 자원 부족 시 → `RuleError::InsufficientResources`

### BR-G04: 완료 조건
- 가이아 프로젝트를 시작한 다음 라운드 Gaia Phase에 행성 `is_gaia_formed = true`
- 배치한 Gaiaformer는 행성 완료 시 플레이어 보드로 돌아가며, 해당 플레이어가 광산을 지을 수 있음
- 일반 진영의 Gaia 구역 파워는 I 구역으로, Terrans는 II 구역으로 반환
- Terrans 행성의회: 반환할 파워 값만큼 파워→자원 자유행동 비율을 선택적으로 적용하며 토큰은 모두 II 구역으로 이동
- Itars 행성의회: Gaia 구역 파워 4개를 버릴 때마다 기술 타일 1개를 반복 획득 가능

---

## 8. 파워 액션 규칙

### BR-PA01: 1라운드 1회
- 각 파워 액션 칸은 라운드 당 1회만 사용 가능
- 이미 사용된 칸 → `RuleError::ActionNotAllowed`

### BR-PA02: 파워 비용
- 파워 액션별 `power.bowl3`에서 소비
- 소비된 파워는 `bowl1`으로 이동
- 자원 부족 시 → `RuleError::InsufficientResources`

---

## 9. Pass 규칙

### BR-PS01: 부스터 교환
- `Pass { booster }` 시 현재 보유 부스터 반납 + 선택한 booster 획득
- 선택한 booster는 남은 부스터 풀에 있어야 함
- 1-5라운드에는 새 booster 선택 필수, 6라운드에는 새 booster를 선택하지 않음
- 패스 시 반납하는 기존 booster의 패스 VP를 즉시 계산
- 첫 라운드 시작과 이후 Income Phase에 현재 booster의 수입 적용
- 시작 booster 선택 UI가 생기기 전까지는 역순 턴 순서에 따라 셔플 결과를 결정론적으로 배정

### BR-PS02: 라운드 패스
- `player.passed = true` 설정
- 해당 라운드 다시 액션 불가

### BR-PS03: 마지막 패스 보너스
- 라운드에서 가장 마지막으로 패스한 플레이어 → VP 보너스 없음 (가이아 프로젝트 표준)
- (부스터 효과에 따라 다를 수 있음)

---

## 10. 자원 불변식

### BR-RES01: 비음수 자원 (u8)
- `ore`, `credits`, `knowledge`, `qic` 는 0 미만 불가
- 사용 전 충분성 확인 필수
- `power.bowl1/2/3/gaia_bowl/gaia_forming` 모두 0 이상

### BR-RES02: VP 음수 허용
- `player.vp: i32` — 비딩 차감 후 음수 가능
- 게임 종료 시 음수 VP는 최종 점수에 반영

### BR-RES03: 파워 보존
- `bowl1 + bowl2 + bowl3 + gaia_bowl + gaia_forming` = 상수 (팩션별 초기값 고정)
- 파워는 생성되거나 소멸되지 않음 (일부 팩션 특수 능력 제외)

---

## 11. Lost Fleet 탐사선 규칙

### BR-LF01: 탐사선 배치 비용
- VP 5점 소비 (기본)
- 일부 팩션 특수 능력으로 비용 감소 가능

### BR-LF02: 1우주선 1탐사선
- 같은 `ShipId`에 탐사선 중복 배치 불가
- `player.explored_ships.contains(ship_id)` 이면 불가

### BR-LF03: 우주선 액션 조건
- 탐사선이 파견된 우주선만 해당 우주선의 액션 칸 사용 가능

### BR-LF04: Lost Planet 건설
- `BoardState.lost_planet`이 Some(hex)이면 해당 hex에 Mine 건설 가능
- 테라포밍 불필요, 단 도달 범위 확인 필요
- 건설 후 Lost Planet 타일 제거 (`BoardState.lost_planet = None`)

### BR-LF05: 우주 타일에 위성 배치 금지
- `hex.space_tile_kind.is_some()` 인 hex에는 `Satellite` 배치 불가
- 위반 시 → `RuleError::SatelliteOnSpaceTile(hex)`
- 우주 타일(단일/외곽)은 탐사선 이동 경로이며 위성 고정 불가

### BR-LF06: 소행성 식민화 — Gaiaformer 영구 소모
- `AsteroidColonized` 발생 조건: 대상 hex의 `planet.planet_type == PlanetType::Asteroid`
- 사용 가능한 Gaiaformer 수 = `gaia_track_level` 기반 총 Gaiaformer - `spent_gaia_formers` - 현재 파견 중인 Gaiaformer 수
- 식민화 시 `player.resources.spent_gaia_formers += 1` (영구 소모)
- 소행성은 테라포밍 불필요, Mine 1개 건설 가능
- Gaiaformer 부족 시 → `RuleError::NoGaiaformerAvailable`

### BR-LF07: 원시행성 식민화
- `ProtoPlanetColonized` 발생 조건: 대상 hex의 `planet.planet_type == PlanetType::ProtoPlanet`
- 식민화 비용: 규칙서 상세 참조 (QIC 또는 특수 액션 소모, 향후 확정)
- Mine 1개 건설 가능 (테라포밍 불필요)

---

## 12. 득점 불변식

### BR-SC01: 이벤트 기반 라운드 득점
- 라운드 N의 득점은 `event_log.filter(round == N)` 기반
- 라운드 변경 후 과거 라운드 이벤트 수정 불가

### BR-SC02: 비딩 차감 최종 적용
- `player.bid_amount`는 최종 득점 단계에서만 차감 (`VpReason::BidDeduction`)
- 게임 진행 중 `player.vp`에서 즉시 차감하지 않음

### BR-SC03: 최종 득점 타일 동점 처리
- 동점자가 있으면 해당 순위 VP를 균등 분배 (반올림 없음, 정수 나눔)
- 예: 1위 VP=18, 2위 VP=12, 동점 2명 → 각 (18+12)/2 = 15점

### BR-SC04: 자원 → VP 변환
- `floor((ore + credits + knowledge) / 3)` VP 지급
- 변환 후 남은 자원은 무시

### BR-SC05: Lost Fleet 최종 득점 타일 풀 확장
- 전체 최종 득점 타일 풀 = 기본 6개 + Lost Fleet 3개 = 9개
- 랜더마이저가 9개 중 2개를 랜덤 선택하여 `GameState.final_scoring_tiles`에 배치
- 3개 Lost Fleet 조건: `MostDeepSpaceSectors`, `MostAsteroids`, `GreatestDistancePiAcademy`
- 각 조건 계산 방식:
  - `MostDeepSpaceSectors`: 하나 이상의 행성을 개척한 심우주 섹터 수 비교
  - `MostAsteroids`: 개척한 소행성 수 비교
  - `GreatestDistancePiAcademy`: 행성 의회에서 가장 먼 아카데미까지의 거리 비교

### BR-SC06: spent_gaia_formers 최종 득점 미반영
- `player.resources.spent_gaia_formers`는 사용 가능 Gaiaformer 수 계산에만 사용
- 최종 득점 계산에서 별도 VP 부여 없음 (비용 역할만)
