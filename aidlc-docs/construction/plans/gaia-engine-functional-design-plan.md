# Functional Design Plan — Unit 1: gaia-engine

## 실행 체크리스트

- [x] Step 1: 단위 컨텍스트 분석 (unit-of-work.md + story-map.md)
- [x] Step 2: Functional Design 계획 생성
- [x] Step 3: 컨텍스트 적합 질문 생성
- [x] Step 4: 계획 저장 (이 파일)
- [x] Step 5: 답변 수집 및 분석
- [x] Step 6: Functional Design 아티팩트 생성
- [x] Step 7: 완료 메시지 제시

---

## 단위 요약

**Unit 1 (gaia-engine)**: 순수 Rust crate. 네트워크/DB 없음. 전체 게임 로직의 핵심.
- Randomizer, GameState, FactionRegistry, RuleEngine, ScoringEngine, MapEngine, BiddingEngine
- 외부 의존성: serde, serde_json, proptest (dev)

---

## 질문 목록

아래 질문에 `[Answer]:` 태그 다음에 답변을 입력해 주세요.

---

## Q1. GameState 최상위 구조 — 어떤 필드를 포함해야 하나요?

GameState는 직렬화(serde)되어 DB에 저장됩니다. 아래 후보 필드 중 포함할 항목을 선택해 주세요.

A) 핵심 필드만 — `round` (1-6), `phase`, `players: [PlayerState; 4]`, `board: BoardState`, `round_tiles`, `final_scoring_tiles`, `research_board`

B) 핵심 + 이벤트 로그 포함 — A의 내용 + `event_log: Vec<GameEvent>` (재현용)

C) 핵심 + 이벤트 로그 + 메타데이터 — B의 내용 + `room_code`, `created_at`, `version` (낙관적 잠금용)

D) Other (답변 태그 아래 설명해 주세요)

[Answer]: C

---

## Q2. PlayerState 필드 구성

각 플레이어 상태에 포함할 항목을 선택해 주세요.

A) 기본 — `player_id`, `nickname`, `faction`, `resources: Resources`, `structures: Vec<Structure>`, `research_tracks: ResearchTracks`, `vp: i32`, `passed: bool`

B) 기본 + 연결 정보 — A + `federation_tokens: Vec<FederationToken>`, `alliance_tiles: Vec<AllianceTile>`, `lost_planet: bool`, `connected_mines: Vec<HexCoord>`

C) 기본 + 연결 + 입찰 기록 — B + `bid_amount: u32` (팩션 선택 시 차감할 VP)

D) Other

[Answer]: D
C 기반에서 lost_planet: bool 제거.
대신 explored_ships: Vec<ShipId> 추가 (확장팩 Lost Fleet 메카닉).
같은 우주선에 탐사선 1대 제한, 최대 2~3개 우주선 탐사 가능.

---

## Q3. Resources 구조체 세부 구성

가이아 프로젝트의 자원 체계를 어떻게 모델링할까요?

A) 단순 — `ore: u8`, `credits: u8`, `knowledge: u8`, `qic: u8`, `power_bowls: (u8, u8, u8)` (bowl1/2/3)

B) 파워 사이클 명시 — A와 동일하되 `power: PowerCycle { bowl1: u8, bowl2: u8, bowl3: u8, gaia_bowl: u8 }` 별도 구조체

C) B + 가이아 변환 대기 추적 — `power: PowerCycle { bowl1, bowl2, bowl3, gaia_bowl, gaia_forming: u8 }` (가이아 변환 중인 파워 별도 추적)

D) Other

[Answer]: C

---

## Q4. GameAction 열거형 — 포함할 액션 종류

가이아 프로젝트 액션을 어떻게 분류할까요? 기본 액션 목록:

A) 핵심 7개 — Build (구조물 건설), Upgrade (구조물 업그레이드), ResearchAdvance (연구 트랙 진행), FormFederation (연방 구성), PowerAction (파워 액션), SpecialAction (팩션 특수 액션), Pass (라운드 패스)

B) A + 자원 교환 — A + GaiaFormation (가이아 행성 변환 시작), QicAction (QIC 사용 행동)

C) B + 비딩 페이즈 액션 포함 — B + BiddingActions (PlaceBid, PassBid, SelectFaction, SelectTurnOrder) 별도 enum variant로 포함

D) Other

[Answer]: D SetupAction과 GameAction을 분리.
SetupAction: PlaceBid(u32), PassBid, SelectFaction(FactionId), SelectTurnOrder(u8)
GameAction: Build, Upgrade, ResearchAdvance, FormFederation, 
            PowerAction, SpecialAction, GaiaFormation, QicAction, Pass
비딩은 게임 시작 전 별도 페이즈라 GameAction에 포함하지 않음.

---

## Q5. 맵 좌표계 — 헥사곤 좌표 시스템

헥사곤 좌표 표현 방식을 선택해 주세요.

A) Cube 좌표 — `(q, r, s)` where `q + r + s = 0`. 회전/거리 계산에 최적. 표준적

B) Offset 좌표 — `(col, row)` 짝수/홀수 행 오프셋. 직관적이지만 계산 복잡

C) Axial 좌표 — `(q, r)` (s는 파생). Cube의 경량 버전. 대부분 연산 가능

D) Other

[Answer]: C

---

## Q6. 섹터 및 맵 구성

4인 게임 고정 맵 구성을 어떻게 표현할까요?

A) 정적 데이터 — TOML 파일에 섹터별 행성 배치 하드코딩. Randomizer가 회전/배치만 결정

B) 절차적 생성 — 섹터 ID + 회전 각도로 런타임에 맵 계산. PRNG로 배치 순서 결정

C) 하이브리드 — 섹터 행성 타입은 TOML 정적 데이터, 실제 배치 (위치 + 회전)은 PRNG 결정

D) Other

[Answer]: C

---

## Q7. 연방 구성 규칙 — 어떻게 검증할까요?

연방 형성 가능 조건 검증 방식을 선택해 주세요.

A) BFS/DFS 연결성 — 플레이어 구조물이 인접 연결되어 있고, 총 파워 합계 ≥ 7 확인

B) A + 섹터 규칙 — A + 같은 섹터에 다른 플레이어의 구조물이 없어야 함 (섹터 완전 지배 필요)

C) A + 위성 포함 — A + 위성(Satellite)으로 연결 확장 가능. 위성은 파워 계산에 포함 안 됨

D) Other

[Answer]: C

---

## Q8. 연구 트랙 — 레벨 효과 모델링

6개 연구 트랙(Terra, Nav, AI, Gaia, Eco, Sci)의 레벨별 효과를 어떻게 표현할까요?

A) 하드코딩 함수 — 트랙/레벨을 인자로 받아 효과 반환하는 match 구문

B) 데이터 테이블 — TOML/JSON으로 트랙×레벨 효과 정의. 런타임에 로드

C) 하이브리드 — 즉시 적용 효과(자원)는 TOML 데이터, 지속 효과(예: Nav 레벨 → 이동범위)는 Rust 로직으로 계산

D) Other

[Answer]: C

---

## Q9. 득점 계산 — 라운드 득점 타일 처리

6개 라운드 각각의 득점 조건을 어떻게 계산할까요? (예: "이번 라운드에 테라포밍한 행성 수 × 2VP")

A) 이벤트 기반 — 라운드 종료 시 해당 라운드의 GameEvent 목록을 스캔하여 득점 조건 계산

B) 상태 스냅샷 비교 — 라운드 시작 GameState vs 종료 GameState diff로 계산

C) 실시간 추적 — PlayerState에 라운드별 카운터(예: `round_built: u8`) 포함, 매 액션마다 업데이트

D) Other

[Answer]: A

---

## Q10. 최종 득점 — 계산 항목

게임 종료 시 최종 득점 항목은 어떻게 처리할까요?

A) 고정 항목만 — 최종 득점 타일 2개 (가장 많은 섹터, 가장 많은 위성 등), Gaia 프로젝트 득점, 리서치 트랙 VP, 자원 → VP 변환

B) A + Lost Fleet 항목 — A + 로스트 플릿 팩션 특수 최종 득점 (Lost Planet 보유 여부 등)

C) B + 비딩 차감 — B + 각 플레이어의 `bid_amount` 차감 처리

D) Other

[Answer]: C

---

## Q11. BiddingEngine 상태 머신 — 경매 흐름

비딩 경매의 상태를 어떻게 모델링할까요?

A) 단순 상태 — `BiddingState { current_bids: HashMap<PlayerId, u32>, passed: HashSet<PlayerId>, winner: Option<PlayerId> }`

B) 단계별 상태 — `BiddingPhase` enum: `Bidding` → `FactionSelection` → `TurnOrderSelection` → `Complete`. 각 단계별 유효 액션 다름

C) B + 페어 연결 — 4개 팩션 페어(랜더마이저 결과) 각각에 독립 입찰. 가장 높게 입찰한 플레이어가 해당 페어 선택권 획득

D) Other

[Answer]: B

---

## Q12. PRNG 시드 알고리즘 — 구현 방식

기존 랜더마이저 JavaScript PRNG를 Rust로 이식하는 방식을 선택해 주세요.

A) 완전 동일 포팅 — JavaScript의 `imul`, 비트 연산을 Rust `u32` wrapping 연산으로 1:1 변환. 동일한 시드로 동일한 결과 보장

B) A + 테스트 벡터 — A + 알려진 시드에 대한 예상 출력값 테스트 벡터 포함 (JS 결과와 비교 검증)

C) Other

[Answer]: B

---

## Q13. 팩션 특수 능력 — 구현 복잡도 우선순위

18개 팩션의 특수 능력을 모두 구현하기에는 범위가 넓습니다. 어떻게 접근할까요?

A) 완전 구현 — 모든 18팩션 특수 능력 FactionAbility trait 구현 (가장 시간 소요)

B) 핵심 8팩션 먼저 — 가이아 프로젝트 기본 팩션 9쌍 중 복잡도 낮은 4쌍(8팩션)을 먼저 완전 구현, 나머지는 능력 없는 기본 구현

C) 모든 팩션 스텁 — 18팩션 모두 FactionAbility trait 구현하되, 특수 능력은 기본 동작(no-op)으로 스텁. 이후 팩션별로 능력 구현

D) Other

[Answer]: C

---

## Q14. 에러 핸들링 — RuleError 세분화

규칙 위반 에러를 어떻게 분류할까요?

A) 단순 — `RuleError(String)` — 메시지만 포함

B) 열거형 — `RuleError::InsufficientResources { needed, have }`, `RuleError::InvalidTarget(HexCoord)`, `RuleError::NotYourTurn`, `RuleError::ActionNotAllowed` 등 세분화

C) B + 컨텍스트 — B + `RuleError::with_context(...)` 로 추가 디버그 정보 첨부

D) Other

[Answer]: B

---

## Q15. 팩션 데이터 저장 형식

팩션 기본 속성 (홈 행성 타입, 시작 자원, 초기 구조물 위치 등)을 어디에 저장할까요?

A) Rust 상수 — `const FACTION_DATA: &[FactionData]` 소스코드 내 하드코딩

B) TOML 파일 — `gaia-engine/data/factions.toml`. `include_str!()` 매크로로 컴파일 타임 임베드

C) JSON 파일 — `gaia-engine/data/factions.json`. serde_json으로 파싱. `include_str!()` 로 임베드

D) Other

[Answer]: B
