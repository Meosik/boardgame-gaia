# Business Logic Model — gaia-engine

## 1. PRNG 알고리즘 (Randomizer)

JavaScript 랜더마이저와 동일한 시드 → 동일한 출력 보장.

### 시드 해싱 (Mulberry32 변형)

```
입력: seed: &str (UTF-16 코드 포인트 시퀀스로 처리)

초기화:
  h = 1779033703 XOR seed.len()

각 문자 c in seed (UTF-16 charCode):
  h = wrapping_mul(h XOR charCode, 3432918353)
  h = (h << 13) | (h >> 19)    // rotate left 13

random() 호출 시:
  h = h XOR (h >> 16)
  h = wrapping_mul(h, 2246822507)
  h = h XOR (h >> 13)
  h = wrapping_mul(h, 3266489909)
  h = h XOR (h >> 16)
  반환: (h as f64) / 4294967296.0  // [0.0, 1.0)
```

**중요**: 모든 연산은 u32 wrapping (overflow 허용). JavaScript `Math.imul` 동일.

### Fisher-Yates 셔플

```
shuffle(array: &mut Vec<T>, rng: &mut Randomizer):
  for i in (1..array.len()).rev():
    j = (rng.random() * (i + 1) as f64) as usize
    array.swap(i, j)
```

### generate_setup() 흐름

```
1. 팩션 페어 선택:
   - 9쌍 전체 목록 셔플
   - 앞 4쌍 선택

2. 라운드 타일 선택 (6개):
   - Lost Fleet 포함 전체 라운드 타일 셔플
   - 앞 6개 선택, 라운드 1-6에 배치

3. 부스터 선택 (4+3=7개):
   - 전체 부스터 목록 셔플
   - 플레이어 수(4) + 3 = 7개 선택

4. 최종 득점 타일 (2개):
   - Lost Fleet 포함 전체 최종 득점 타일 셔플
   - 앞 2개 선택

5. 기술 타일 배치 (6트랙 × 기본 타일):
   - 트랙별 기본 타일 셔플
   - 각 트랙에 1개씩 배치

6. 맵 섹터 배치:
   - Center Balance 섹터 01-04 고정 배치 (항상 중앙)
   - 나머지 섹터 셔플 → 외곽 위치에 배치
   - 각 섹터 rotation = floor(random() * 6) → 0-5

7. 고급 기술 타일 (6개, 트랙별 1개):
   - 트랙별 고급 타일 중 랜덤 선택

반환: GameSetup {
    faction_pairs: [FactionPair; 4],
    round_tiles: [RoundTileId; 6],
    boosters: Vec<BoosterId>,
    final_scoring: [FinalScoringTileId; 2],
    tech_tiles: HashMap<ResearchTrack, TechTileId>,
    advanced_tech: HashMap<ResearchTrack, AdvancedTechTileId>,
    sector_layout: Vec<SectorPlacement>,
}
```

**테스트 벡터**: 알려진 시드 → 예상 출력값 (JS 랜더마이저로 미리 계산 후 하드코딩).

---

## 2. 게임 셋업 흐름

### 2a. 자유 선택 모드

```
1. generate_setup(seed) → GameSetup
2. 선택 가능한 팩션 보드 면 공개
3. 방장부터 시계 방향으로 SelectFaction(faction)
4. 선택된 팩션의 반대편 보드 면도 후보에서 제거
5. 모두 선택하면 시작 자원을 지급하고 StartingStructures로 전환
```

### 2b. 비딩 모드

```
1. generate_bidding_setup(seed) → 서로 반대편 보드 면이 겹치지 않는 팩션 4개
2. 방장부터 시계 방향으로 PlaceBid(n) 또는 PassBid
   - n은 현재 최고 입찰보다 커야 함
   - 한 번 패스하면 해당 경매에 다시 참가할 수 없음
3. 후보 1명만 남으면 BiddingChoice로 전환
4. 낙찰자가 남은 팩션 하나와 남은 최종 턴 위치 하나를 동시에 선택
5. 다음 경매는 낙찰자의 오른쪽 플레이어부터 최고 입찰 0으로 재시작
6. 세 번의 경매 뒤 마지막 플레이어/팩션/턴 위치는 0 VP로 자동 배정
7. 최종 턴 순서를 적용하고 시작 자원을 지급한 뒤 StartingStructures로 전환
```

### 2c. 시작 구조물 배치

```
1. 첫 배치: 최종 턴 순서의 앞에서 뒤(시계 방향)
   - 시작 구조물이 2개 이상인 팩션만 첫 구조물을 배치
2. 둘째 배치: 최종 턴 순서의 뒤에서 앞(반시계 방향)
   - 일반 팩션은 둘째 구조물
   - Lost Fleet의 1개 구조물 팩션은 이 단계에서 유일한 구조물
   - Ivits는 이 단계에서 제외
3. Xenos의 셋째 Mine 배치
4. Ivits의 PlanetaryInstitute 배치
5. 각 PlaceStartingStructure(coord)는 팩션 홈 행성이고 비점유 상태인지 검증
6. 마지막 배치 뒤 StartingBoosters로 전환
7. 최종 턴 순서의 마지막 플레이어부터 역순으로 SelectStartingBooster(id)
   - 선택한 부스터를 공용 풀에서 제거하고 PlayerState.booster에 저장
8. 모두 선택하면 round=1, Setup::Complete로 전환
9. 서버가 구조물·연구트랙·팩션·선택 부스터의 첫 라운드 수입을 처리
10. 수입 순서 선택이 필요하면 IncomeOrderPending, 아니면 ActionPhase 시작
```

---

## 3. 라운드 흐름

```
라운드 N (1-6):

[Income Phase]
  각 플레이어 → 현재 구조물 구성에 따른 수입 계산
  FactionData.income 테이블 참조
  수입 순서 선택이 필요하면 IncomeOrderPending 진입
  GameEvent::RoundStarted { round: N } 기록

[Gaia Phase]
  이전 라운드에 시작한 Transdim 프로젝트를 Gaia 행성으로 완료
  Gaiaformer를 플레이어 보드로 반환
  일반 진영: gaia_forming → bowl1, Terrans: gaia_forming → bowl2
  Terrans/Itars가 행성의회를 보유하면 GaiaDecisionPending에서 선택 처리

[Gaiaforming Phase]
  GaiaFormation 액션 가능 (Gaiaformer 있는 플레이어만)
  Transdim 행성 대상 → 파워 4 gaia_bowl 소비 → gaia_forming 추가
  행성 표시: is_gaia_formed = false (아직 완료 안 됨)

[Action Phase]
  turn_order 순서로 플레이어 순환
  passed = false인 플레이어만 참여
  각 플레이어: GameAction 1개 수행 또는 Pass
  모든 플레이어 passed=true → 다음 페이즈

[Round Scoring Phase]
  이벤트 기반 득점 계산 (아래 섹션 참조)

[라운드 정리]
  부스터 교체 (Pass 시 받은 부스터 적용)
  passed = false 초기화
  turn_order 재정렬 (Pass 순서 기반)
  GameEvent::RoundEnded { round: N } 기록

라운드 6 완료 → Final Scoring
```

---

## 4. 액션 처리 흐름

### validate_action(state, player_id, action) → Result<(), RuleError>

```
1. 페이즈 확인:
   - state.phase == ActionPhase { active_player } 인지 확인
   - turn_order[active_player] == player_id 인지 확인

2. 패스 여부 확인:
   - player.passed == true → AlreadyPassed 에러

3. 액션별 검증:

   GameAction::Build { hex, structure }:
     a. structure == Mine 인지 확인 (신규 건설은 Mine만)
     b. hex에 행성 있는지 확인
     c. 행성이 건설 가능한지 확인 (다른 플레이어 mine 없음)
     d. 도달 가능한지 확인:
        - 플레이어 구조물에서 BFS로 이동 가능 범위 계산
        - range ≤ player.research_tracks.navigation + 1 (기본 1)
     e. 행성 타입 분기:
        - 홈 타입이면 무료 건설
        - 다른 타입(일반 행성)이면 테라포밍 비용 확인 (ore 충분한지)
        - Asteroid: Gaiaformer 사용 가능 여부 확인 (spent_gaia_formers 기준)
        - ProtoPlanet: 특수 식민화 비용 확인 (규칙서 확정 후 구현)
        - Transdim/Gaia: 테라포밍 경로 없음 → InvalidTarget
     f. Satellite 배치 시: hex.space_tile_kind.is_some() → SatelliteOnSpaceTile 에러
     g. 자원 확인: ore, credits 충분한지

4. 모든 검증 통과 → Ok(())
```

### apply_action(state, player_id, action) → Result<Vec<GameEvent>, RuleError>

```
1. validate_action 호출 (재검증)
2. 상태 변이:
   - 자원 차감
   - 구조물 추가/변경
   - BoardState 업데이트
3. 이벤트 생성 — 행성 타입별 분기:
   - 일반 행성 Mine: StructureBuilt { kind: Mine }
   - Asteroid Mine:  AsteroidColonized { hex }
                     + player.resources.spent_gaia_formers += 1
   - ProtoPlanet Mine: ProtoPlanetColonized { hex }
   - Lost Planet Mine: StructureBuilt + BoardState.lost_planet = None
   - ShipExplored:    ShipExplored { ship_id }
                     + player.explored_ships.push(ship_id)
4. 이벤트를 event_log에 추가
5. 다음 플레이어로 current_player 이동
6. 생성된 이벤트 목록 반환
```

---

## 5. 테라포밍 비용 계산

```
get_terraforming_cost(from: PlanetType, to: PlanetType, track_level: u8) -> u8:

  // 행성 타입 환경 링 인덱스 (0-6)
  RING = [Terra, Swamp, Desert, Oxide, Titanium, Volcanic, Ice]
  
  from_idx = RING.position(from)
  to_idx   = RING.position(to)
  
  // 최단 거리 (양방향 순환)
  linear = |from_idx - to_idx|
  distance = min(linear, 7 - linear)
  
  // 레벨별 1 스텝당 비용
  cost_per_step = match track_level {
    0 => 3,
    1 => 3,
    2 => 2,   // 기본 시작
    3 => 1,
    4 => 1,
    5 => 1,
    _ => 3,
  }
  
  total_cost = distance * cost_per_step
  
  // Transdim: 테라포밍 대상 아님 (GaiaFormation 액션 별도)
  // LostPlanet: 테라포밍 불가, distance 계산 N/A
```

---

## 6. 연방 구성 검증

```
can_form_federation(state, player_id, hexes: &[HexCoord]) -> bool:

1. hexes의 모든 구조물이 player_id 소유인지 확인
   (Satellite 포함, SpaceStation 포함)

2. 연결성 확인 (BFS):
   - hexes 내 인접한 hex들이 하나의 connected component 형성
   - Satellite는 연결 역할 (자신은 파워 0이지만 연결 가능)

3. 파워 합계 확인:
   total_power = sum(structure_power(s) for s in hexes
                     if s.kind != Satellite)
   total_power >= 7

4. 기존 연방 재사용 여부 확인:
   - hexes에 포함된 hex들이 이미 다른 연방에 포함된 hex가 아닌지
   - (Gaia Project 규칙: 연방 확장 시 기존 연방 hex 재사용 가능)
   - 실제 규칙: 연방 토큰 획득 후 해당 구조물들은 재사용 가능
   - connected_structures는 federation token이 없어야 함 (새 연방 한정)

5. 모든 조건 충족 → true
```

---

## 7. 연구 트랙 진행

```
advance_research(state, player_id, track) → Result<Vec<GameEvent>, RuleError>:

1. 비용 확인: player.resources.knowledge >= 4
2. 현재 레벨 확인: current = player.research_tracks[track]
3. 최대 레벨(5) 도달 여부 확인
4. 동맹 칸(3,4,5) 확인:
   - 새 레벨이 3,4,5이면 해당 칸 비어있는지 확인
5. 비용 차감: knowledge -= 4
6. 레벨 증가: track += 1
7. 즉시 자원 효과 (TOML 데이터):
   - track × level → ResourceDelta 적용
8. 지속 효과 (Rust 로직):
   - Terraforming track: get_terraforming_cost 자동 반영 (TrackState 통해)
   - Navigation track: BFS 이동 범위 자동 반영
   - AI track: QIC 자동 지급 (레벨에 따라)
   - Gaia track: Gaiaformer 해금
   - Economy track: 수입 계산 시 자동 반영
   - Science track: 수입 지식 자동 반영
9. 동맹 칸 도달 시:
   - AllianceTile 지급
   - track_state.alliance_taken[level-3] = Some(player_id)
10. 레벨 5 도달 시:
    - FederationToken 지급 (research_board.federation_tokens에서)
    - 추가 VP 지급
11. 이벤트 반환: [ResourceChanged, ResearchAdvanced, ...]
```

---

## 8. 라운드 득점 계산 (이벤트 기반)

```
calculate_round_scoring(state, round: u8) → Vec<(PlayerId, i32)>:

  tile = state.round_tiles[round - 1]
  round_events = state.event_log
    .filter(e.round == round)

  결과 = []
  for player_id in all_players:
    player_events = round_events.filter(player == player_id)
    vp = match tile.condition:
      RoundCondition::BuildMine =>
        count(player_events where StructureBuilt { kind: Mine })
      RoundCondition::Upgrade =>
        count(player_events where StructureUpgraded)
      RoundCondition::ResearchAdvance =>
        count(player_events where ResearchAdvanced)
      RoundCondition::GaiaProject =>
        count(player_events where GaiaFormingComplete)
      RoundCondition::BuildStation =>
        count(player_events where StructureBuilt { kind: TradingStation })
      RoundCondition::FormFederation =>
        count(player_events where FederationFormed)
      // ... 기타 라운드 타일 조건
    vp_total = vp * tile.vp_per_unit
    결과.push((player_id, vp_total))

  return 결과
```

---

## 9. 최종 득점 계산

```
calculate_final_scoring(state) → [(PlayerId, i32)]:

  scores = {player: 0 for each player}

  // 1. 최종 득점 타일 (2개)
  for tile in state.final_scoring_tiles:
    rankings = rank_players_by(state, tile.condition)
    // 1위: tile.vp_1st, 2위: tile.vp_2nd, 동점: 균등 분배
    apply_ranking_vp(scores, rankings, tile)

  // 2. Gaia Project 득점
  for player in players:
    gaia_planets = count(board hexes owned by player where planet.is_gaia_formed)
    vp = gaia_project_vp_table[gaia_planets]  // TOML 데이터
    scores[player] += vp

  // 3. 연구 트랙 VP
  for player in players:
    for track in all_tracks:
      level = player.research_tracks[track]
      vp = max(0, min(level - 2, 3)) * 4
      scores[player] += vp

  // 4. 자원 → VP 변환
  for player in players:
    resources_vp = floor((ore + credits + knowledge) / 3)
    scores[player] += resources_vp

  // 5. Lost Fleet 최종 득점 타일 (FinalScoringCondition 분기)
  //    MostDeepSpaceSectors: 행성을 개척한 심우주 섹터 수 비교
  //    MostAsteroids: 개척한 소행성 수 비교
  //    GreatestDistancePiAcademy: 행성 의회와 가장 먼 아카데미 거리 비교
  //    → 기본 타일과 동일한 ranking + VP 배분 로직 재사용

  // 6. Lost Fleet 팩션 특수 최종 득점
  // (팩션별 FactionAbility.final_scoring() 호출)
  for player in players:
    if player.faction is Some(faction):
      ability = FactionRegistry.get(faction)
      scores[player] += ability.final_scoring(state, player.player_id)

  // 7. 비딩 VP 차감
  for player in players:
    scores[player] -= player.bid_amount as i32

  return scores.iter().map(|(p, s)| (p, player.vp + s)).collect()
```

---

## 10. FactionAbility trait

```
trait FactionAbility {
    // 구조물 건설 시 추가 효과
    fn on_build(&self, state: &GameState, player: PlayerId, hex: HexCoord)
        -> Vec<GameEvent>;

    // 연구 진행 시 추가 효과
    fn on_research(&self, state: &GameState, player: PlayerId, track: ResearchTrack)
        -> Vec<GameEvent>;

    // 파워 수입 단계 추가 수입
    fn passive_income(&self, state: &GameState, player: PlayerId)
        -> ResourceDelta;

    // 특수 액션 (팩션별 1회성 행동)
    fn special_action(&self, state: &GameState, player: PlayerId)
        -> Option<Box<dyn SpecialAction>>;

    // 최종 득점 기여
    fn final_scoring(&self, state: &GameState, player: PlayerId)
        -> i32;

    // 연방 파워 계산 오버라이드 (일부 팩션)
    fn federation_power_override(&self) -> Option<FederationPowerRule> {
        None  // 기본: 표준 규칙
    }
}
```

**구현 방식 (Q13: 전체 스텁 → 순차 구현):**

```
// 기본 스텁 구현 (no-op)
struct DefaultFactionAbility;
impl FactionAbility for DefaultFactionAbility {
    fn on_build(...) -> Vec<GameEvent> { vec![] }
    fn on_research(...) -> Vec<GameEvent> { vec![] }
    fn passive_income(...) -> ResourceDelta { ResourceDelta::zero() }
    fn special_action(...) -> Option<Box<dyn SpecialAction>> { None }
    fn final_scoring(...) -> i32 { 0 }
}

// 18팩션 모두 DefaultFactionAbility 상속으로 시작
// 이후 팩션별 파일에서 능력 구현 (faction/impls/ 디렉터리)
```

---

## 11. 항법 범위 (Navigation BFS)

```
get_reachable_hexes(state, player_id) -> HashSet<HexCoord>:

  nav_level = player.research_tracks.navigation
  range = nav_level + 1  // 기본 범위 1, 레벨 5 → 범위 6

  // 시작점: 플레이어의 모든 구조물 위치
  start_hexes = player.structures.map(s => s.hex)

  // BFS: 우주 공간 통과 가능 (빈 hex 통과), 거리 ≤ range
  reachable = BFS(start_hexes, max_distance=range, board=state.board)

  // 필터: 실제 건설 가능한 행성만
  reachable.filter(hex => {
    state.board.hexes[hex].planet is Some &&
    planet.planet_type != Empty &&
    not already_owned_by(player_id)
  })
```

---

## 12. 파워 충전 계산

```
charge_power(state, player_id, amount: u8) -> Vec<GameEvent>:
  // 인접 구조물 건설 시 다른 플레이어 파워 충전 발생
  // amount = 건설된 구조물의 파워 값 (새 Mine = 1)

  player = state.players[player_id]
  remaining = amount
  events = []

  // bowl1 → bowl2
  bowl1_to_2 = min(player.power.bowl1, remaining)
  player.power.bowl1 -= bowl1_to_2
  player.power.bowl2 += bowl1_to_2
  remaining -= bowl1_to_2
  events.push(ResourceChanged { ... })

  // bowl2 → bowl3
  if remaining > 0:
    bowl2_to_3 = min(player.power.bowl2, remaining)
    player.power.bowl2 -= bowl2_to_3
    player.power.bowl3 += bowl2_to_3
    events.push(ResourceChanged { ... })

  return events
```
