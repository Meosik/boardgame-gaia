# WebSocket Protocol — Gaia Project

> 클라이언트↔서버 간 WebSocket 메시지 타입 정의
>
> - **서버 소스**: `gaia-server/src/messages.rs`
> - **클라이언트 소스**: `gaia-frontend/src/types/game.ts`
> - **직렬화**: JSON (`serde(tag = "type", rename_all = "snake_case")`)

---

## 연결 흐름

1. 클라이언트가 `ws(s)://{host}/ws/{room_code}` 로 연결
2. **첫 메시지는 반드시 `join_room`** — 그 외 메시지는 `PROTOCOL` 에러 반환
3. 서버가 `room_joined` 응답 후 양방향 메시지 루프 시작
4. 재접속 시 `session_token` 포함하여 `join_room` 재전송

---

## Client → Server 메시지

| type | 설명 | 주요 페이로드 | 전송 시점 |
|------|------|--------------|-----------|
| `join_room` | 방 입장 / 재접속 | `room_code`, `nickname`, `session_token?` | 연결 직후 (필수 첫 메시지) |
| `place_setup_action` | 셋업 단계 액션 (입찰/팩션 선택) | `action: SetupAction` | 비딩·팩션선택·턴순서 단계 |
| `place_game_action` | 인게임 액션 | `action: GameAction` | 액션 페이즈 |
| `regenerate_setup` | 맵/셋업 재생성 (호스트 전용) | `seed?` | 로비 |
| `request_coaching` | AI 코칭 질문 | `question` | 게임 중 언제든 |

### SetupAction 하위 타입

| type | 설명 | 페이로드 |
|------|------|----------|
| `PlaceBid` | 팩션 쌍에 VP 입찰 | `pair_index`, `vp` |
| `PassBid` | 입찰 패스 | — |
| `SelectFaction` | 팩션 선택 | `faction: FactionId` |
| `SelectTurnOrder` | 턴 순서 선택 | `position` |

### GameAction 하위 타입

| type | 설명 | 페이로드 |
|------|------|----------|
| `BuildMine` | 광산 건설 | `coord` |
| `UpgradeStructure` | 건물 업그레이드 | `coord`, `to` |
| `AdvanceResearch` | 연구 트랙 진행 | `track` |
| `FormFederation` | 연맹 형성 | `hexes[]` |
| `UsePowerAction` | 파워 액션 사용 | `action_id` |
| `StartGaiaProject` | 가이아 프로젝트 시작 | `coord` |
| `UseQicAction` | QIC 액션 사용 | `action_id` |
| `Pass` | 패스 (부스터 선택) | `booster_id` |
| `PlaceSatellite` | 위성 배치 | `coord` |
| `ExploreWithShip` | 함선 탐사 | `ship_id`, `coord` |
| `ColonizeAsteroid` | 소행성 식민 | `coord` |

---

## Server → Client 메시지

| type | 설명 | 주요 페이로드 | 수신 대상 |
|------|------|--------------|-----------|
| `room_joined` | 입장 성공 응답 | `room_code`, `player_id`, `session_token`, `game_setup` | 입장한 플레이어만 |
| `player_joined` | 플레이어 입장 알림 | `player_id`, `nickname`, `player_count` | 방 전체 브로드캐스트 |
| `setup_updated` | 셋업 재생성 결과 | `game_setup` | 방 전체 브로드캐스트 |
| `game_started` | 게임 시작 | `game_state` (전체 초기 상태) | 방 전체 브로드캐스트 |
| `action_applied` | 액션 적용 완료 | `player_id`, `events[]`, `game_state` | 방 전체 브로드캐스트 |
| `turn_changed` | 활성 플레이어 변경 | `active_player` | 방 전체 브로드캐스트 |
| `round_ended` | 라운드 종료 | `round`, `scores` | 방 전체 브로드캐스트 |
| `game_ended` | 게임 종료 | `final_scores`, `winner` | 방 전체 브로드캐스트 |
| `coaching_response` | AI 코칭 응답 | `response` | 요청한 플레이어만 |
| `error` | 서버 에러 | `code`, `message` | 해당 플레이어만 |

### 에러 코드

| code | 의미 |
|------|------|
| `JOIN_FAILED` | 방 입장 실패 |
| `PROTOCOL` | 프로토콜 위반 (첫 메시지가 `join_room`이 아님, 이미 입장 등) |
| `PARSE_ERROR` | JSON 파싱 실패 |
| `ACTION_ERROR` | 게임 액션 처리 실패 |

---

## 메시지 요약 (수량)

| 방향 | 최상위 타입 수 | 하위 액션 타입 수 |
|------|---------------|-----------------|
| Client → Server | 5 | SetupAction 4 + GameAction 11 = 15 |
| Server → Client | 10 | — |
| **합계** | **15** | **15** |
