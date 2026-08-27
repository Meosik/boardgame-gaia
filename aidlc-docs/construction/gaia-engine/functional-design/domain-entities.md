# Domain Entities — gaia-engine

## 핵심 원시 타입

```
PlayerId   : u8          — 0..3 (4인 고정)
FactionId  : enum        — 18개 팩션 열거형
RoomCode   : String      — 방 식별 코드
ShipId     : u8          — Lost Fleet 탐사선 보낸 우주선 인덱스
BoosterId  : u8          — 부스터 타일 인덱스
```

---

## HexCoord (Axial 좌표계)

```
HexCoord {
    q: i32,
    r: i32,
}
```

- s = -q - r (파생, 저장 안 함)
- 거리: `max(|q1-q2|, |r1-r2|, |s1-s2|)` (s 파생 후 계산)
- 6 방향 이웃: (±1,0), (0,±1), (±1,∓1)
- 회전 60°: `(q, r) → (-r, q+r)`

---

## PlanetType

```
enum PlanetType {
    // 홈 행성 타입 (7가지)
    Terra,
    Swamp,
    Desert,
    Oxide,
    Titanium,
    Volcanic,
    Ice,
    // 특수 — 기본 게임
    Transdim,    // 가이아 포밍 가능 (Gaiaformer 필요)
    Gaia,        // 포밍 완료된 Transdim
    LostPlanet,  // Lost Fleet 특수 타일 (보드에 1개)
    // 특수 — Lost Fleet 확장
    Asteroid,    // 소행성: Gaiaformer 영구 소모로 식민화
    ProtoPlanet, // 원시행성: 특수 식민화 규칙 (규칙서 상세 참조)
}
```

**테라포밍 거리 매트릭스** (순환 링 구조):

```
환경 링:
  Terra — Swamp — Desert — Oxide — Titanium — Volcanic — Ice — Terra
  
각 단계 이동 = 1 ore (기본)
Terra 트랙 레벨에 따라 비용 감소:
  레벨 1: 3 ore/step
  레벨 2: 2 ore/step  (기본 시작점)
  레벨 3: 1 ore/step

Transdim → Gaia: Gaiaformer 소비 + 파워 4 가이아 보울 → 포밍
LostPlanet: 테라포밍 불가, Mine 1개만 건설 가능
Asteroid:   테라포밍 불가, Gaiaformer 영구 소모 (spent_gaia_formers += 1)
ProtoPlanet: 테라포밍 불가, 특수 식민화 액션 필요
```

---

## StructureType

```
enum StructureType {
    Mine,                    // 파워: 1, 무한 건설 가능
    TradingStation,          // 파워: 2
    ResearchLab,             // 파워: 2
    PlanetaryInstitute,      // 파워: 3, 플레이어당 1개
    Academy(AcademyType),    // 파워: 4, 플레이어당 2개
    Satellite,               // 파워: 0, 연방 연결용
    SpaceStation,            // 파워: ?, Lost Fleet 특수 (팩션별 정의)
}

enum AcademyType {
    Science,  // 과학 아카데미
    Qic,      // QIC 아카데미
}
```

**업그레이드 경로:**
```
Mine → TradingStation → PlanetaryInstitute (1개 한정)
                      ↘ ResearchLab → Academy(Science 또는 Qic) (2개 한정)
```

---

## SpaceTileKind (Lost Fleet 우주 타일 타입)

```
enum SpaceTileKind {
    Single,   // 단일 우주 타일 — 독립 1-hex 타일 (섹터 외부)
    Outer,    // 외곽 우주 타일 — 맵 경계부 타일
}
```

- `SpaceTileKind`를 가진 hex = 우주선 타일 (우주 공간 위치)
- **위성 배치 불가**: `hex.space_tile_kind.is_some()` 이면 Satellite 배치 금지
- 행성 없음 (`planet: None`), 구조물 배치 불가
- 탐사선 파견(`ShipExplored`) 및 우주선 이동의 경로로만 사용

---

## Resources

```
Resources {
    ore:                 u8,
    credits:             u8,
    knowledge:           u8,
    qic:                 u8,
    power:               PowerCycle,
    spent_gaia_formers:  u8,   // 소행성 식민화 시 영구 소모된 Gaiaformer 수
}

PowerCycle {
    bowl1:        u8,  // 비활성 파워
    bowl2:        u8,  // 반활성화
    bowl3:        u8,  // 준비 완료 (사용 가능)
    gaia_bowl:    u8,  // 가이아 파워 (별도 풀)
    gaia_forming: u8,  // 가이아 변환 중 (라운드 종료 후 gaia_bowl로 이동)
}
```

**파워 사이클 규칙:**
```
충전:  bowl1 → bowl2 (1 파워 이동)
       bowl2 → bowl3 (1 파워 이동)
사용:  bowl3에서 N 파워 소비 → bowl1로 이동
가이아: bowl3에서 N 파워 소비 → gaia_forming으로 이동
       라운드 시작 Gaia Phase: gaia_forming → gaia_bowl
       가이아 포밍 완료 시: gaia_bowl → bowl1
```

---

## PlayerState

```
PlayerState {
    player_id:        PlayerId,
    nickname:         String,
    faction:          Option<FactionId>,     // Setup 완료 전 None
    resources:        Resources,
    structures:       Vec<Structure>,
    research_tracks:  ResearchTracks,
    vp:               i32,                   // 음수 가능 (비딩 차감 후)
    passed:           bool,                  // 현재 라운드 패스 여부
    booster:          Option<Booster>,       // 현재 보유 라운드 부스터
    federation_tokens: Vec<FederationToken>,
    alliance_tiles:   Vec<AllianceTile>,
    explored_ships:   Vec<ShipId>,           // Lost Fleet: 탐사선 파견된 우주선
    bid_amount:       u32,                   // 게임 종료 시 차감할 비딩 VP
}

Structure {
    hex:        HexCoord,
    kind:       StructureType,
}

ResearchTracks {
    terraforming:  u8,  // 0-5
    navigation:    u8,
    ai:            u8,
    gaia:          u8,
    economy:       u8,
    science:       u8,
}
```

**explored_ships 제약:**
- 같은 ShipId에 탐사선 1대만 파견 가능
- 파견 비용: VP 5점 (팩션별 예외 있음)
- 탐사선 있어야 해당 우주선의 액션 칸 사용 가능
- LostPlanet 타일은 PlayerState가 아닌 BoardState에서 관리

---

## BoardState

```
BoardState {
    sectors:     Vec<Sector>,
    hexes:       HashMap<HexCoord, Hex>,
    lost_planet: Option<HexCoord>,          // Lost Fleet 특수 타일 위치
}

Sector {
    id:       u8,
    rotation: u8,       // 0-5 (60° 단위)
    origin:   HexCoord, // 섹터 중심 배치 좌표
}

Hex {
    coord:           HexCoord,
    planet:          Option<Planet>,
    space_tile_kind: Option<SpaceTileKind>, // None = 일반 섹터 hex
    structures:      Vec<PlacedStructure>,
    satellites:      Vec<PlayerId>,
}

Planet {
    planet_type:    PlanetType,
    is_gaia_formed: bool,
    owner:          Option<PlayerId>,
}

PlacedStructure {
    owner: PlayerId,
    kind:  StructureType,
}
```

---

## GameState

```
GameState {
    // 메타데이터
    room_code:   RoomCode,
    created_at:  u64,          // Unix 타임스탬프
    version:     u64,          // 낙관적 잠금 버전

    // 게임 상태
    round:       u8,           // 1-6
    phase:       GamePhase,
    players:     [PlayerState; 4],
    board:       BoardState,

    // 타일/트랙
    round_tiles:           [RoundTile; 6],
    boosters:              Vec<Booster>,       // 남은 라운드 부스터
    final_scoring_tiles:   [FinalScoringTile; 2],
    research_board:        ResearchBoard,

    // 턴 관리
    turn_order:     [PlayerId; 4],
    current_player: usize,      // turn_order 인덱스

    // 이벤트 로그
    event_log: Vec<GameEvent>,
}
```

---

## GamePhase

```
enum GamePhase {
    Setup(SetupPhase),
    GaiaPhase,                            // 라운드 시작 전 가이아 처리
    IncomePhase,                          // 수입 단계
    GaiaformingPhase,                     // 가이아포밍 시작 가능
    ActionPhase { active_player: usize }, // 실제 액션 단계
    IncomeOrderPending { ... },           // 행성의회 수입 순서 선택
    GaiaDecisionPending { ... },          // Terrans/Itars 가이아 단계 선택
    RoundScoring { round: u8 },           // 라운드 득점
    FinalScoring,                         // 최종 득점
    Ended,
}
```

---

## SetupPhase (비딩 모드)

```
enum SetupPhase {
    FactionSelection { active_player: PlayerId },
    Bidding { active_player: PlayerId },
    BiddingChoice { winner: PlayerId },
    StartingStructures {
        active_player: PlayerId,
        placement_index: usize,
        kind: StructureType,
    },
    StartingBoosters {
        active_player: PlayerId,
        selection_index: usize,
    },
    Complete,
}
```

---

## BiddingState

```
BiddingState {
    phase:             SetupPhase,
    pairs:             Vec<FactionPair>,              // 랜더마이저 결과 4쌍
    current_bids:      HashMap<PlayerId, u32>,        // 각 플레이어 현재 입찰액
    passed:            HashSet<PlayerId>,             // 이번 경매에서 패스한 플레이어
    remaining_players: Vec<PlayerId>,                 // 아직 팩션 미선택 플레이어
    remaining_pairs:   Vec<FactionPair>,              // 아직 미선택 팩션 페어
    assignments:       Vec<BidAssignment>,            // 낙찰 결과
}

BidAssignment {
    player:    PlayerId,
    faction:   FactionId,
    bid_vp:    u32,
    turn_pos:  u8,
}

FactionPair {
    faction_a: FactionId,
    faction_b: FactionId,
}
```

---

## SetupAction / GameAction

```
enum SetupAction {
    SelectFaction { faction: FactionId },
    PlaceBid { amount: u32 },   // 현재 최고가보다 높아야 함
    PassBid,
    ChooseBidReward {
        faction: FactionId,
        turn_position: u8,
    },
    PlaceStartingStructure { coord: HexCoord },
    SelectStartingBooster { booster_id: BoosterId },
}

enum GameAction {
    Build        { hex: HexCoord, structure: StructureType },
    Upgrade      { hex: HexCoord, to: StructureType },
    ResearchAdvance { track: ResearchTrack },
    FormFederation  { hexes: Vec<HexCoord>, token: FederationToken },
    PowerAction  { id: PowerActionId },
    SpecialAction { id: SpecialActionId },
    GaiaFormation { hex: HexCoord },
    QicAction    { kind: QicActionKind },
    Pass         { booster: BoosterId },
}

enum QicActionKind {
    NavigationBoost,   // QIC 1개 → 이동 범위 +1
    TechTileAccess,    // QIC 1개 → 기술 타일 접근
    FederationToken,   // QIC 2개 → 연방 토큰 획득
}
```

---

## GameEvent

```
enum GameEvent {
    // 셋업 이벤트
    BidPlaced         { player: PlayerId, amount: u32 },
    BidPassed         { player: PlayerId },
    FactionSelected   { player: PlayerId, faction: FactionId },
    TurnOrderSelected { player: PlayerId, position: u8 },
    BoosterSelected   { player: PlayerId, booster: BoosterId },

    // 게임 이벤트
    ActionPerformed   { player: PlayerId, action: GameAction, round: u8 },
    ResourceChanged   { player: PlayerId, delta: ResourceDelta },
    VpAwarded         { player: PlayerId, amount: i32, reason: VpReason },
    StructureBuilt    { player: PlayerId, hex: HexCoord, kind: StructureType },
    StructureUpgraded { player: PlayerId, hex: HexCoord, from: StructureType, to: StructureType },
    FederationFormed  { player: PlayerId, hexes: Vec<HexCoord>, token: FederationToken },
    ResearchAdvanced  { player: PlayerId, track: ResearchTrack, level: u8 },
    GaiaFormingStarted   { player: PlayerId, hex: HexCoord },
    GaiaFormingComplete  { player: PlayerId, hex: HexCoord },
    PlayerPassed         { player: PlayerId, booster: BoosterId },
    // Lost Fleet 이벤트
    ShipExplored         { player: PlayerId, ship_id: ShipId },
    AsteroidColonized    { player: PlayerId, hex: HexCoord },
    ProtoPlanetColonized { player: PlayerId, hex: HexCoord },

    // 페이즈 이벤트
    RoundStarted      { round: u8 },
    RoundEnded        { round: u8 },
    GameEnded         { final_scores: [i32; 4] },
}

struct ResourceDelta {
    ore:       i8,
    credits:   i8,
    knowledge: i8,
    qic:       i8,
    // 파워는 복잡하여 별도 처리
    power_delta: PowerDelta,
}

enum VpReason {
    RoundTile { tile_id: u8 },
    FinalTile { tile_id: u8 },
    ResearchTrack { track: ResearchTrack },
    ResourceConversion,
    BidDeduction,
    FactionSpecial,
    GaiaProject,
    ShipExploration,    // Lost Fleet: 탐사선 파견 VP
    AsteroidColony,     // Lost Fleet: 소행성 식민화 VP
    ProtoPlanetColony,  // Lost Fleet: 원시행성 식민화 VP
}
```

---

## ResearchBoard

```
ResearchBoard {
    tracks:             HashMap<ResearchTrack, TrackState>,
    tech_tiles:         Vec<TechTile>,           // 랜덤 배치된 기본 기술 타일
    advanced_tech_tiles: [Option<AdvancedTechTile>; 6],  // 트랙 상단 고급 타일
    federation_tokens:  Vec<FederationToken>,    // 남은 연방 토큰 풀
}

struct TrackState {
    player_levels:    HashMap<PlayerId, u8>,  // 0-5
    alliance_taken:   [Option<PlayerId>; 3],  // 레벨 3, 4, 5 동맹 칸 (각 1명)
}

enum ResearchTrack {
    Terraforming,
    Navigation,
    ArtificialIntelligence,
    GaiaProject,
    Economy,
    Science,
}
```

---

## FactionData (TOML 로드, 컴파일 타임 임베드)

```
// TOML 스키마 (gaia-engine/data/factions.toml)
// Rust에서는 FactionData로 역직렬화

FactionData {
    id:                 FactionId,
    home_planet:        PlanetType,
    starting_ore:       u8,
    starting_credits:   u8,
    starting_knowledge: u8,
    starting_qic:       u8,
    starting_bowl1:     u8,
    starting_bowl2:     u8,
    starting_bowl3:     u8,
    gaiaformers:        u8,         // 시작 가이아포머 수
    starting_structures: Vec<RelativeStructure>,
    income:             IncomeTable,
    special_action_defs: Vec<SpecialActionDef>,
}

struct RelativeStructure {
    rel_q:  i32,
    rel_r:  i32,
    kind:   StructureType,
}
```

---

## RuleError

```
enum RuleError {
    NotYourTurn,
    WrongPhase { expected: String, actual: String },
    InsufficientResources { resource: ResourceKind, needed: u32, have: u32 },
    InvalidTarget(HexCoord),
    TargetOccupied { hex: HexCoord, owner: PlayerId },
    OutOfRange { hex: HexCoord, range: u8, nav_level: u8 },
    InvalidUpgrade { from: StructureType, to: StructureType },
    StructureLimit { kind: StructureType },
    FederationInsufficientPower { have: u32, needed: u32 },
    FederationDisconnected,
    BidTooLow { current_max: u32, placed: u32 },
    BidExceedsVp { bid: u32, vp: i32 },
    AlreadyPassed,
    ActionNotAllowed(String),
    SatelliteOnSpaceTile(HexCoord),  // 우주선 타일에 위성 배치 불가
    NoGaiaformerAvailable,           // 소행성 식민화 시 Gaiaformer 없음
}
```

---

## FinalScoringCondition (확장 포함 전체 풀)

```
enum FinalScoringCondition {
    // 기본 게임 타일
    MostStructuresInFederation, // 연방에 포함된 건물 수
    MostBuildings,         // 전체 건물 수
    MostPlanetTypes,       // 개척한 서로 다른 행성 유형 수
    MostGaiaPlanets,       // 가이아 행성 수
    MostSectors,           // 개척한 일반 우주 섹터 수
    MostSatellites,        // 위성 + 우주정거장 수
    // Lost Fleet 확장 추가 타일 (3개)
    MostDeepSpaceSectors,  // 개척한 심우주 섹터 수
    MostAsteroids,         // 개척한 소행성 수
    GreatestDistancePiAcademy, // 행성 의회와 아카데미 사이 최장 거리
}

// GameState.final_scoring_tiles = [FinalScoringTile; 2]
// 각 FinalScoringTile은 FinalScoringCondition + 순위별 VP 값 포함
struct FinalScoringTile {
    id: u8,
    condition: FinalScoringCondition,
    vp_1st:    u8,   // 1위 VP (예: 18)
    vp_2nd:    u8,   // 2위 VP (예: 12)
    vp_3rd:    u8,   // 3위 VP (예: 6, 일부 타일만)
}
```
