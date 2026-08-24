# Map Data Model — Full Redesign (4인 + Lost Fleet 고정)

> **Status**: arch 설계 문서  
> **고정 요구사항**: 4인 플레이 + Lost Fleet 확장 항상 포함. player_count 분기 없음.  
> **문제**: 현재 `sectors.toml`이 반경-1 (7헥스)로 구현됨. 실제 게임은 반경-2 (19헥스).  
> **범위**: sectors.toml 스키마, Interspace 타일 타입, randomizer.rs 좌표 체계 재설계  
> **보드 구성 (고정)**: Standard Sector 10개 + Interspace 10개 + Deep Space Sector 8개 = 224 hexes

---

## 1. 현상 분석 (AS-IS 문제점)

### 1.1 sectors.toml — 잘못된 반경

| 항목 | 현재 (잘못됨) | 정확한 값 |
|------|-------------|----------|
| 섹터 반경 | 1 (7헥스) | 2 (19헥스) |
| 섹터 01-10 | 7 hexes/sector | 19 hexes/sector |
| Deep Space Sector | 없음 (9-10을 `is_lost_fleet`로 표기) | 별도 타입 11-18 (3헥스/타일) |
| Interspace 타일 | 없음 | 3종류 (Spaceship/Planet/Blank) |

### 1.2 randomizer.rs — 잘못된 섹터 간격

현재 섹터 origin 좌표:
```
center: (0,0), (3,-2), (-3,2), (0,-3)    ← 간격 3, 반경-1 기준
outer:  (3,1), (-3,-1), (0,3), (3,-3)... ← 겹침 발생
```

반경-2 섹터는 폭 5칸이므로 **최소 간격 5** 필요.

---

## 2. 섹터 모델 (TO-BE)

### 2.1 좌표계 기초: 반경-2 헥스 섹터

반경-2 섹터는 19개 헥스로 구성:

```
Ring 0 (1 hex):  (0,0)

Ring 1 (6 hex):  (1,0)  (0,1)  (-1,1)
                 (-1,0) (0,-1) (1,-1)

Ring 2 (12 hex): (2,0)  (1,1)  (0,2)  (-1,2) (-2,2) (-2,1)
                 (-2,0) (-1,-1)(0,-2) (1,-2) (2,-2) (2,-1)

Total: 1 + 6 + 12 = 19 hexes
```

헥사곤 경계의 6개 변(edge):
```
Edge 0 (→ v1 방향): (2,0), (2,-1), (2,-2)
Edge 1 (→ v2 방향): (2,0), (1,1),  (0,2)
Edge 2:             (0,2), (-1,2), (-2,2)
Edge 3 (← v1 방향): (-2,2),(-2,1),(-2,0)
Edge 4 (← v2 방향): (-2,0),(-1,-1),(0,-2)
Edge 5:             (0,-2),(1,-2), (2,-2)
```

### 2.2 격자 기저 벡터 (Lattice Basis)

**핵심 발견**: 반경-2 헥스 타일이 **변(edge) 전체를 공유**하며 맞닿으려면
단순 `(5,0)` 방향이 아니라 **`v1=(5,-2)`, `v2=(2,3)`** 방향으로 배치해야 한다.

`(5,0)` 방향은 꼭짓점(vertex) 접촉이라 인접 1쌍만 생기고,
`(5,-2)` 방향은 변(edge) 접촉이라 인접 5쌍(3+3 border hex)이 생긴다.

```
v1 = (5, -2)    # 기저벡터 1
v2 = (2,  3)    # 기저벡터 2

6개 인접 방향 (edge-sharing):
 v1      = ( 5, -2)
 v2      = ( 2,  3)
 v2 - v1 = (-3,  5)
-v1      = (-5,  2)
-v2      = (-2, -3)
 v1 - v2 = ( 3, -5)
```

검증:
```
섹터 A=(0,0), 섹터 B=(5,-2) 일 때:
- A의 Edge 0 hex: (2,0), (2,-1), (2,-2)
- 이들의 이웃 (3,0), (3,-1), (3,-2)가 모두 B 내부 (거리 ≤2 from B center)
- A∩B = ∅ (겹침 없음)
→ 변 전체 공유 확인 ✓
```

### 2.3 Standard Sectors (01-10): 19 hexes

#### sectors.toml 스키마 변경

```toml
[[sectors]]
id = 1
category = "standard"        # NEW: "standard" | "deep_space"
side = "a"                    # NEW: 양면 타일용 (05-07은 "a"/"b")

# Ring 0
[[sectors.hexes]]
rel_q = 0; rel_r = 0; planet = "Oxide"

# Ring 1
[[sectors.hexes]]
rel_q = 1; rel_r = 0; planet = ""
[[sectors.hexes]]
rel_q = 0; rel_r = 1; planet = "Transdim"
[[sectors.hexes]]
rel_q = -1; rel_r = 1; planet = "Terra"
[[sectors.hexes]]
rel_q = -1; rel_r = 0; planet = ""
[[sectors.hexes]]
rel_q = 0; rel_r = -1; planet = "Swamp"
[[sectors.hexes]]
rel_q = 1; rel_r = -1; planet = ""

# Ring 2 (12 hexes 추가 — 현재 누락됨)
[[sectors.hexes]]
rel_q = 2; rel_r = 0; planet = ""
[[sectors.hexes]]
rel_q = 1; rel_r = 1; planet = "Ice"
[[sectors.hexes]]
rel_q = 0; rel_r = 2; planet = ""
[[sectors.hexes]]
rel_q = -1; rel_r = 2; planet = "Volcanic"
[[sectors.hexes]]
rel_q = -2; rel_r = 2; planet = ""
[[sectors.hexes]]
rel_q = -2; rel_r = 1; planet = ""
[[sectors.hexes]]
rel_q = -2; rel_r = 0; planet = "Titanium"
[[sectors.hexes]]
rel_q = -1; rel_r = -1; planet = ""
[[sectors.hexes]]
rel_q = 0; rel_r = -2; planet = ""
[[sectors.hexes]]
rel_q = 1; rel_r = -2; planet = "Desert"
[[sectors.hexes]]
rel_q = 2; rel_r = -2; planet = ""
[[sectors.hexes]]
rel_q = 2; rel_r = -1; planet = ""
```

> **NOTE**: 위 Ring 2 행성 배치는 **예시**입니다.  
> 실제 각 섹터(01-10)의 19헥스 행성 데이터는 물리 게임 타일에서 전사해야 합니다.  
> 섹터 05, 06, 07은 양면(`side = "a"` / `side = "b"`)으로 각각 등록합니다.

### 2.4 Deep Space Sectors (11-18): 3 hexes

확장팩(Lost Fleet)에서 추가되는 소형 타일. 8개(양면), 외곽 빈 공간에 배치.

```toml
[[sectors]]
id = 11
category = "deep_space"
side = "a"

[[sectors.hexes]]
rel_q = 0; rel_r = 0; planet = "Asteroid"
[[sectors.hexes]]
rel_q = 1; rel_r = 0; planet = ""
[[sectors.hexes]]
rel_q = 0; rel_r = 1; planet = "ProtoPlanet"

[[sectors]]
id = 11
category = "deep_space"
side = "b"

[[sectors.hexes]]
rel_q = 0; rel_r = 0; planet = ""
[[sectors.hexes]]
rel_q = 1; rel_r = 0; planet = "Asteroid"
[[sectors.hexes]]
rel_q = 0; rel_r = 1; planet = ""
```

> 8개 타일 × 2면 = 16 설정. 실제 행성 데이터는 물리 타일에서 전사.

### 2.5 Rust 파서 타입 변경 (`data/sectors.rs`)

```rust
#[derive(Debug, Deserialize)]
pub struct SectorTemplate {
    pub id:       u8,
    pub category: SectorCategory,   // NEW
    #[serde(default = "default_side")]
    pub side:     String,            // NEW: "a" or "b"
    pub hexes:    Vec<HexTemplate>,
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum SectorCategory {
    Standard,
    DeepSpace,
}
```

---

## 3. Interspace 타일

### 3.1 타입 정의

확장팩에서 섹터 사이 구멍(1헥스)에 배치하는 단일 헥스 타일.

```rust
// gaia-engine/src/game_state.rs 에 추가

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum InterspaceKind {
    Spaceship(SpaceshipId),       // 4개: Twilight(1), Rebellion(2), TFMars(3), Eclipse(4)
    Planet(PlanetType),           // Asteroid 또는 Protoplanet
    Blank,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SpaceshipId {
    Twilight  = 1,
    Rebellion = 2,
    TFMars    = 3,
    Eclipse   = 4,
}
```

### 3.2 타일 구성 (4인 고정)

| 종류 | 수량 | 설명 |
|------|------|------|
| Spaceship | 4 | Twilight, Rebellion, T F Mars, Eclipse (각 1개) |
| Planet | 3 | Asteroid ×2, Protoplanet ×1 |
| Blank | 3 | 빈 타일 |
| **합계** | **10** | — |

> 4인 전용이므로 4개 우주선 보드 전부 사용.  
> 우주선 4개 + 비우주선 6개 = 10개 (hole 수와 일치).

### 3.3 배치 제약 조건

```
CONSTRAINT: 우주선 간 최소 거리 ≥ 3 hexes
```

룰북 (p.5): "no two spaceship tiles should be within 3 spaces of another spaceship tile"

이 규칙은 우주선 타일끼리만 적용. 행성/빈 타일 간에는 거리 제약 없음.

### 3.4 데이터 파일 (`interspace_tiles.toml`)

```toml
# 4인 + Lost Fleet 고정 — 10 tiles, 분기 없음

[[tiles]]
kind = "spaceship"
ship = "Twilight"

[[tiles]]
kind = "spaceship"
ship = "Rebellion"

[[tiles]]
kind = "spaceship"
ship = "TFMars"

[[tiles]]
kind = "spaceship"
ship = "Eclipse"

[[tiles]]
kind = "planet"
planet = "Asteroid"

[[tiles]]
kind = "planet"
planet = "Asteroid"

[[tiles]]
kind = "planet"
planet = "ProtoPlanet"

[[tiles]]
kind = "blank"

[[tiles]]
kind = "blank"

[[tiles]]
kind = "blank"
```

---

## 4. 좌표 체계 및 레이아웃

### 4.1 격자 좌표계 (Lattice Coordinates)

섹터 위치를 격자 좌표 `(a, b)`로 표현. 실제 헥스 좌표로 변환:

```
hex_origin(a, b) = a × v1 + b × v2
                 = a × (5, -2) + b × (2, 3)
                 = (5a + 2b, -2a + 3b)
```

### 4.2 10-섹터 배치 (4인 고정)

격자 좌표로 표현한 10개 섹터 위치 (3-4-3 배열):

```
격자 좌표 (a, b):

Row b=1:   (-1,1)  (0,1)  (1,1)        ← 3 sectors
Row b=0:   (-1,0)  (0,0)  (1,0)  (2,0) ← 4 sectors
Row b=-1:          (0,-1) (1,-1) (2,-1) ← 3 sectors
```

실제 헥스 좌표 변환:

| 격자 (a,b) | 헥스 origin (q,r) | 비고 |
|-----------|------------------|------|
| (0, 0) | (0, 0) | 중앙 |
| (1, 0) | (5, -2) | 중앙 우측 |
| (-1, 0) | (-5, 2) | 좌측 |
| (2, 0) | (10, -4) | 우측 |
| (0, 1) | (2, 3) | 상단 중앙 |
| (1, 1) | (7, 1) | 상단 우 |
| (-1, 1) | (-3, 5) | 상단 좌 |
| (0, -1) | (-2, -3) | 하단 중앙 |
| (1, -1) | (3, -5) | 하단 우 |
| (2, -1) | (8, -7) | 하단 우측 끝 |

전체 보드 범위: `q ∈ [-7, 12]`, `r ∈ [-9, 7]` (섹터 반경 포함)

### 4.3 셋업 시퀀스 (고정)

룰북 (확장팩 p.5) + pm 지시 기반. **항상 이 시퀀스로 실행.**

```
단계 ①: 섹터 01-04 중 2개를 랜덤 선택 → 중앙에 나란히 배치
        C1 = (0, 0),  C2 = (5, -2)   [격자 (0,0), (1,0)]

단계 ②: 나머지 8개 섹터(01-04 잔여 2개 + 05-10)를 주변 8개 위치에 랜덤 배치
        각 외곽 섹터를 1헥스 탄젠셜 방향으로 밀어서(shift)
        외곽이 내부 섹터와 2칸만 접하게 함
        → 10개의 1헥스 구멍(hole) 생성

단계 ③: 구멍 10개에 Interspace 타일 10개 랜덤 배치
        고정 구성: Spaceship×4 + Planet×3 + Blank×3
        제약: 우주선 타일 간 거리 ≥ 3

단계 ④: 외곽 빈 공간에 Deep Space Sector 8개 전부 배치 (랜덤 면)

총 헥스: 10×19 + 10×1 + 8×3 = 190 + 10 + 24 = 224 (고정)
```

### 4.4 외곽 섹터 시프트 (Shift) 상세

모든 외곽 섹터를 동일한 회전 방향으로 1헥스 이동.
각 위치별 시프트 벡터 (시계 방향 기준):

| 격자 (a,b) | 기본 헥스 origin | 시프트 벡터 | 시프트된 origin | 인접 중앙 섹터 |
|-----------|----------------|----------|--------------|-----------|
| (-1, 0) | (-5, 2) | (0, -1) | (-5, 1) | C1 |
| (2, 0) | (10, -4) | (0, 1) | (10, -3) | C2 |
| (0, 1) | (2, 3) | (1, 0) | (3, 3) | C1, C2 |
| (1, 1) | (7, 1) | (-1, 1) | (6, 2) | C2 |
| (-1, 1) | (-3, 5) | (1, 0) | (-2, 5) | C1 |
| (0, -1) | (-2, -3) | (-1, 0) | (-3, -3) | C1, C2 |
| (1, -1) | (3, -5) | (1, 0) | (4, -5) | C1, C2 |
| (2, -1) | (8, -7) | (-1, 1) | (7, -6) | C2 |

> 시프트 벡터는 해당 변의 탄젠셜 방향(hex direction 6개 중 하나).  
> 구현 시: 각 외곽 위치별 시프트 벡터를 상수 테이블로 정의.  
> 반시계 방향은 각 벡터를 반전.

### 4.5 구멍(Hole) 탐지 알고리즘

```
fn find_interspace_holes(placements: &[SectorPlacement]) -> Vec<HexCoord> {
    let all_sector_hexes: HashSet<HexCoord> = /* 모든 배치된 섹터의 헥스 */;

    let mut holes = Vec::new();
    for hex in all_sector_hexes.iter() {
        for neighbor in hex.neighbors() {
            if !all_sector_hexes.contains(&neighbor) {
                // 이웃이 비어있고, 2개 이상의 다른 섹터 헥스와 인접하면 hole
                let adj_count = neighbor.neighbors().iter()
                    .filter(|n| all_sector_hexes.contains(n))
                    .count();
                if adj_count >= 2 {
                    holes.push(neighbor);
                }
            }
        }
    }
    holes.sort();
    holes.dedup();
    // 항상 정확히 10개 (4인 + Lost Fleet 고정)
    assert_eq!(holes.len(), 10);
    holes
}
```

### 4.6 Deep Space Sector 배치 위치

외곽 빈 공간 = 외곽 섹터 사이의 보드 경계 틈새.

```
fn find_deep_space_slots(placements: &[SectorPlacement]) -> Vec<HexCoord> {
    // 1. 전체 보드의 볼록 껍질(convex hull) 근사 계산
    // 2. 외곽 섹터 사이의 틈새 위치 탐색
    // 3. 각 틈새의 중심 좌표 = Deep Space Sector origin
    // 4. 8개 슬롯 반환
}
```

틈새 위치는 외곽 섹터 간 경계에서 탐색:

```
인접한 외곽 섹터 쌍 사이에 1개의 Deep Space 슬롯:
(-1,0)↔(-1,1), (-1,1)↔(0,1), (0,1)↔(1,1),
(1,1)↔(2,0), (2,0)↔(2,-1), (2,-1)↔(1,-1),
(1,-1)↔(0,-1), (0,-1)↔(-1,0)
= 8개 슬롯 ✓
```

---

## 5. Randomizer 재설계

### 5.1 `GameSetup` 구조체 확장

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GameSetup {
    pub faction_pairs:       Vec<FactionPair>,
    pub round_tile_ids:      Vec<u8>,
    pub boosters:            Vec<Booster>,
    pub final_scoring:       [FinalScoringTile; 2],
    pub tech_tile_ids:       Vec<u8>,
    pub sector_layout:       Vec<SectorPlacement>,       // 10 sectors
    pub interspace_tiles:    Vec<InterspacePlacement>,    // 10 tiles (항상 포함)
    pub deep_space_layout:   Vec<SectorPlacement>,       // 8 deep space sectors (항상 포함)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterspacePlacement {
    pub coord: HexCoord,
    pub kind:  InterspaceKind,
}
```

### 5.2 `SectorPlacement` 변경

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SectorPlacement {
    pub sector_id: u8,
    pub side:      String,        // NEW: "a" or "b"
    pub origin:    HexCoord,
    pub rotation:  u8,
}
```

### 5.3 `build_sector_layout()` 재설계 — 4인 + Lost Fleet 전용

```rust
// 격자 기저벡터
const V1: HexCoord = HexCoord::new(5, -2);
const V2: HexCoord = HexCoord::new(2, 3);

// 10개 격자 위치 (4인 Lost Fleet 고정 layout)
const LATTICE_POSITIONS: [(i32, i32); 10] = [
    // center pair
    (0, 0), (1, 0),
    // outer ring
    (-1, 0), (2, 0),
    (0, 1), (1, 1), (-1, 1),
    (0, -1), (1, -1), (2, -1),
];

// Lost Fleet shift vectors (clockwise)
const SHIFT_VECTORS: [((i32,i32), HexCoord); 8] = [
    ((-1, 0), HexCoord::new(0, -1)),
    (( 2, 0), HexCoord::new(0,  1)),
    (( 0, 1), HexCoord::new(1,  0)),
    (( 1, 1), HexCoord::new(-1, 1)),
    ((-1, 1), HexCoord::new(1,  0)),
    (( 0,-1), HexCoord::new(-1, 0)),
    (( 1,-1), HexCoord::new(1,  0)),
    (( 2,-1), HexCoord::new(-1, 1)),
];

fn lattice_to_hex(a: i32, b: i32) -> HexCoord {
    HexCoord::new(5 * a + 2 * b, -2 * a + 3 * b)
}
```

### 5.4 전체 셋업 의사코드

```
fn build_setup(&mut self) -> MapSetup:
    // 4인 + Lost Fleet 고정. player_count 분기 없음.

    // ── 단계 ① 중앙 쌍 ──
    center_ids = [1, 2, 3, 4]
    shuffle(center_ids)
    center_pair = center_ids[0..2]
    remaining_center = center_ids[2..4]

    C1_origin = lattice_to_hex(0, 0)  // = (0, 0)
    C2_origin = lattice_to_hex(1, 0)  // = (5, -2)

    place(center_pair[0], C1_origin, random_rotation())
    place(center_pair[1], C2_origin, random_rotation())

    // ── 단계 ② 외곽 8개 (시프트 적용) ──
    // 05-07은 4인 면("a"=white numbers) 사용
    outer_ids = remaining_center + [5, 6, 7, 8, 9, 10]  // 항상 8개
    shuffle(outer_ids)

    for i in 0..8:
        (lat_a, lat_b) = OUTER_LATTICE_POSITIONS[i]
        base_origin = lattice_to_hex(lat_a, lat_b)
        shift = lookup_shift(lat_a, lat_b)
        shifted_origin = base_origin + shift
        side = if outer_ids[i] in [5,6,7] { "a" } else { "a" }
        rotation = random_rotation()
        place(outer_ids[i], shifted_origin, rotation, side)

    // ── 단계 ③ Interspace 10개 배치 ──
    holes = find_interspace_holes(all_placements)
    assert(holes.len() == 10)

    tiles = INTERSPACE_TILES  // 고정 10개: Spaceship×4 + Planet×3 + Blank×3
    shuffle(tiles)
    placement = place_with_ship_constraint(holes, tiles, min_distance=3)

    // ── 단계 ④ Deep Space Sector 8개 배치 ──
    edge_slots = find_deep_space_slots(all_placements)
    assert(edge_slots.len() == 8)

    ds_ids = [11, 12, 13, 14, 15, 16, 17, 18]  // 전부 사용
    shuffle(ds_ids)

    for i in 0..8:
        side = if random() < 0.5 { "a" } else { "b" }
        place_deep_space(ds_ids[i], edge_slots[i], side)
```

### 5.5 우주선 거리 제약 배치 알고리즘

```
fn place_with_ship_constraint(
    holes: Vec<HexCoord>,
    tiles: Vec<InterspaceKind>,
    min_distance: u32,
) -> Vec<InterspacePlacement>:

    // 타일을 우주선 먼저 정렬 (제약이 있는 것 우선)
    ship_tiles = tiles.filter(|t| t.is_spaceship())
    other_tiles = tiles.filter(|t| !t.is_spaceship())

    ship_positions = []

    // 우주선 타일을 하나씩 배치하며 거리 검사
    for ship in ship_tiles:
        candidates = holes.filter(|h|
            !already_placed(h) &&
            ship_positions.all(|sp| h.distance(sp) >= min_distance)
        )
        if candidates.is_empty():
            // 백트래킹 또는 전체 재셔플
            retry_placement()
        pos = candidates.random_choice()
        place(ship, pos)
        ship_positions.push(pos)

    // 나머지 타일은 남은 구멍에 배치 (제약 없음)
    for tile in other_tiles:
        pos = remaining_holes.pop()
        place(tile, pos)
```

---

## 6. 게임 상태 타입 변경

### 6.1 Rust (`game_state.rs`)

```rust
// BoardState 확장
pub struct BoardState {
    pub sectors:           Vec<Sector>,
    pub hexes:             HashMap<HexCoord, Hex>,
    pub lost_planet:       Option<HexCoord>,
    // ── NEW ──
    pub interspace_tiles:  Vec<InterspaceTile>,
    pub deep_space_sectors: Vec<Sector>,   // category로 구분
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterspaceTile {
    pub coord: HexCoord,
    pub kind:  InterspaceKind,
}

// Hex 구조체에 소속 구분 추가
pub struct Hex {
    pub coord:           HexCoord,
    pub planet:          Option<Planet>,
    pub space_tile_kind: Option<SpaceTileKind>,
    pub structures:      Vec<PlacedStructure>,
    pub satellites:      Vec<PlayerId>,
    // ── NEW ──
    pub hex_source:      HexSource,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HexSource {
    Sector(u8),           // sector_id
    Interspace,
    DeepSpace(u8),        // deep_space_sector_id
}
```

### 6.2 TypeScript (`types/game.ts`)

```typescript
// NEW types
export type SpaceshipId = 'Twilight' | 'Rebellion' | 'TFMars' | 'Eclipse';

export type InterspaceKind =
  | { type: 'Spaceship'; ship_id: SpaceshipId }
  | { type: 'Planet'; planet_type: PlanetType }
  | { type: 'Blank' };

export interface InterspaceTile {
  coord: HexCoord;
  kind: InterspaceKind;
}

export type HexSource =
  | { type: 'Sector'; sector_id: number }
  | { type: 'Interspace' }
  | { type: 'DeepSpace'; sector_id: number };

// GameSetup — 4인 + Lost Fleet 고정
export interface GameSetup {
  sectors: Sector[];                        // 10개 standard sectors
  faction_pairs: FactionPair[];
  round_tiles: number[];
  final_scoring_tiles: FinalScoringTile[];
  available_boosters: number[];
  seed: string;
  interspace_tiles: InterspaceTile[];       // 10개 (항상 포함)
  deep_space_sectors: Sector[];             // 8개 (항상 포함)
}

// Hex 확장
export interface Hex {
  coord: HexCoord;
  planet: Planet | null;
  space_tile_kind: SpaceTileKind | null;
  structures: PlacedStructure[];
  satellites: PlayerId[];
  hex_source: HexSource;  // NEW
}
```

---

## 7. `map/engine.rs` 영향 분석

### 7.1 `sector_hexes()` 수정

현재 `h.distance(&sector.origin) <= 2`로 소속 판단 → 이미 반경-2 기준. **수정 불필요.**
단, Deep Space Sector는 반경 ≤ 1 이므로 `hex_source` 필드로 소속 판별하는 것이 더 정확.

### 7.2 `sectors_occupied()` 수정

Deep Space Sector도 "sector" 카운트에 포함해야 함 (최종 점수 타일에 영향).
단, 룰북 확인 필요: "Interspace tiles do not count as sectors" (p.13, p.14).

```rust
pub fn sectors_occupied(board: &BoardState, player: PlayerId) -> usize {
    let standard = /* 기존 로직 */;
    let deep_space = board.deep_space_sectors.iter()
        .filter(|ds| /* 해당 DS 내에 player 구조물 존재 */)
        .count();
    standard + deep_space
}
```

---

## 8. 마이그레이션 체크리스트

| # | 파일 | 변경 내용 |
|---|------|---------|
| 1 | `gaia-engine/data/sectors.toml` | 섹터 01-10: 7→19 hexes, Deep Space 11-18 추가, `category`/`side` 필드 |
| 2 | `gaia-engine/data/interspace_tiles.toml` | **신규** — 4인 고정 타일 세트 (10개) |
| 3 | `gaia-engine/src/data/sectors.rs` | `SectorCategory`, `side` 파싱 |
| 4 | `gaia-engine/src/game_state.rs` | `InterspaceKind`, `InterspaceTile`, `HexSource`, `BoardState` 확장 |
| 5 | `gaia-engine/src/randomizer.rs` | 격자 기저벡터, `build_lost_fleet_4p_setup()`, 시프트/홀/DS 로직 |
| 6 | `gaia-engine/src/map/engine.rs` | `sectors_occupied()` — DS 포함, `hex_source` 기반 판별 |
| 7 | `gaia-frontend/src/types/game.ts` | TS 미러 타입 추가 |
| 8 | `gaia-frontend/src/components/GameBoard/` | Deep Space, Interspace 렌더링 |

---

## 9. 검증 기준

- [ ] 10개 Standard Sector × 19 hexes = 190 hexes
- [ ] 어떤 두 Standard Sector도 겹치지 않음
- [ ] 시프트 후 정확히 10개 hole 생성
- [ ] Interspace 타일 10개 전부 배치됨 (Spaceship×4 + Planet×3 + Blank×3)
- [ ] 우주선 Interspace 타일 간 거리 ≥ 3
- [ ] Deep Space Sector 8개 전부 외곽 틈새에 배치됨
- [ ] 전체 헥스 수 = 224 (고정)
- [ ] 기존 PRNG 호환성 유지 (동일 seed → 동일 결과)
