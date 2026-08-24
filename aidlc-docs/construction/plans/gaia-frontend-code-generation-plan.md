# Code Generation Plan — Unit 3: gaia-frontend

## 단위 컨텍스트

| 항목 | 내용 |
|---|---|
| 단위 | Unit 3: gaia-frontend |
| 경로 | `/home/sohegi/projects/gaia/gaia-frontend/` |
| 유형 | React + TypeScript (Vite) |
| 의존 단위 | Unit 2 (gaia-server REST + WebSocket) |
| 테스트 전략 | vitest + React Testing Library |
| 빌드 출력 | `dist/` → gaia-server ServeDir |

## 구현 스토리 (gaia-frontend 기여)

| 스토리 | 컴포넌트 |
|---|---|
| US-01 룸 생성 | GameLobby (CreateRoom) |
| US-02 룸 참가 | GameLobby (JoinRoom) |
| US-03 랜더마이저 확인/재생성 | GameLobby (SetupPreview) |
| US-04 게임 대기 | GameLobby (WaitingRoom) |
| US-05/06 팩션 선택/비딩 | GameLobby (FactionSelect, BiddingView) |
| US-08 게임 보드 확인 | GameBoard |
| US-09/10 액션 수행/패스 | ActionPanel |
| US-11/14 라운드 득점 | ScorePanel (PlayerDashboard 내) |
| US-13 리소스 현황 | PlayerDashboard |
| US-15 최종 득점 | FinalScoreModal |
| US-16 AI 코칭 | CoachingPanel |

---

## 실행 체크리스트

### Part 1 — Planning
- [x] Step A: 단위 컨텍스트 분석
- [x] Step B: 코드 생성 계획 수립
- [x] Step C: 계획 저장
- [x] Step D: 계획 승인 대기

### Part 2 — Generation
- [x] Step 1: 프로젝트 설정 — `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`
- [x] Step 2: 타입 정의 — `src/types/game.ts` (gaia-engine 타입 미러링)
- [x] Step 3: REST API 클라이언트 — `src/api/rest.ts`
- [x] Step 4: WebSocket 클라이언트 — `src/api/websocket.ts` (지수 백오프 재연결)
- [x] Step 5: Zustand 스토어 — `src/store/roomStore.ts`, `src/store/gameStore.ts`
- [x] Step 6: useWebSocket 훅 — `src/hooks/useWebSocket.ts`
- [x] Step 7: GameLobby 컴포넌트 — CreateRoom, JoinRoom, WaitingRoom, FactionSelect
- [x] Step 8: HexGrid 유틸 + GameBoard 컴포넌트 — SVG 헥사곤 렌더링
- [x] Step 9: PlayerDashboard 컴포넌트 — 자원, 파워사이클, 리서치트랙
- [x] Step 10: ActionPanel 컴포넌트 — 액션 버튼, 턴 표시
- [x] Step 11: CoachingPanel 컴포넌트 — AI 코칭 오버레이
- [x] Step 12: App.tsx + main.tsx — 앱 진입점, 라우팅 (뷰 전환)
- [x] Step 13: 전역 스타일 — `src/index.css`
- [x] Step 14: 컴포넌트 테스트 — `src/tests/` (vitest + RTL)
- [x] Step 15: 코드 요약 문서 — `aidlc-docs/construction/gaia-frontend/code/`

---

## 단계별 상세 설명

### Step 1: 프로젝트 설정

**package.json 의존성:**
```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "zustand": "^4",
    "clsx": "^2"
  },
  "devDependencies": {
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "typescript": "^5",
    "vite": "^5",
    "@vitejs/plugin-react": "^4",
    "vitest": "^1",
    "@testing-library/react": "^14",
    "@testing-library/jest-dom": "^6",
    "@testing-library/user-event": "^14",
    "jsdom": "^24"
  }
}
```

헥사곤: 외부 라이브러리 없이 순수 SVG 커스텀 구현.
이유: gaia-project의 특수 섹터 레이아웃을 완전히 제어하기 위해.

---

### Step 2: 타입 정의 (`src/types/game.ts`)

gaia-engine의 Rust 타입을 TypeScript로 미러링:

```typescript
// HexCoord, PlanetType, StructureType, Resources, PowerCycle,
// PlayerState, BoardState, GameState, GameSetup,
// ClientMessage, ServerMessage 등
```

---

### Step 3: REST API 클라이언트 (`src/api/rest.ts`)

```typescript
const api = {
  createRoom(nickname, seed?): Promise<CreateRoomResponse>
  joinRoom(code, nickname, sessionToken?): Promise<JoinRoomResponse>
  getRoom(code): Promise<RoomInfo>
  regenerateSetup(code, sessionToken, seed?): Promise<GameSetup>
  health(): Promise<void>
}
```

---

### Step 4: WebSocket 클라이언트 (`src/api/websocket.ts`)

- 지수 백오프 자동 재연결 (1s → 2s → 4s → ... → 30s 최대)
- 메시지 큐: 연결 끊김 중 발송된 메시지 재전송
- 이벤트 리스너 패턴 (`on`, `off`, `send`)

---

### Step 5: Zustand 스토어

**roomStore.ts:**
```typescript
interface RoomStore {
  roomCode, playerId, sessionToken, playerCount, roomState, gameSetup
  actions: { createRoom, joinRoom, regenerateSetup, setRoomInfo }
}
```

**gameStore.ts:**
```typescript
interface GameStore {
  gameState, myPlayerId, activePlanet, selectedAction, coachingResponse
  actions: { setGameState, selectPlanet, selectAction, sendAction, requestCoaching }
}
```

---

### Step 6: useWebSocket 훅

```typescript
function useWebSocket(roomCode: string): {
  isConnected: boolean
  send: (msg: ClientMessage) => void
  lastMessage: ServerMessage | null
}
```

---

### Step 7: GameLobby

4개 뷰를 단계적으로 표시:
1. `HomeView` — 룸 생성/참가 선택
2. `CreateRoomView` — 닉네임 입력, 셋업 프리뷰 (섹터, 라운드타일 등)
3. `JoinRoomView` — 룸코드 + 닉네임 입력
4. `WaitingRoomView` — 대기실 (참가자 목록, 팩션 선택)
5. `FactionSelectView` — 팩션 쌍 표시, 선택/비딩

---

### Step 8: HexGrid 유틸 + GameBoard

**hex-utils.ts** — Axial → SVG 좌표 변환:
```typescript
function axialToPixel(q: number, r: number, size: number): [number, number]
function hexCorners(cx: number, cy: number, size: number): string  // SVG polygon points
```

**GameBoard.tsx** — SVG 기반 보드:
- 섹터별 헥사곤 렌더링
- 행성 타입별 색상 (Terra=초록, Swamp=보라, Desert=노란, ...)
- 구조물 아이콘 (광산=■, TS=◆, 리서치랩=▲, 아카데미/PI=★)
- 유효 액션 대상 헥스 하이라이트 (클릭 가능)
- 위성/우주선 표시

---

### Step 9: PlayerDashboard

4개 플레이어 패널 (자기 패널 강조):
- 자원: 광석/크레딧/지식/QIC 수치
- 파워 사이클: Bowl1/Bowl2/Bowl3/Gaia 시각화 (원형 아이콘)
- 연구 트랙: 6트랙 × 레벨 0-5 (현재 위치 표시)
- 현재 VP

---

### Step 10: ActionPanel

내 턴일 때:
- 건설/업그레이드/연구/연방/파워액션/가이아형성/QIC액션/패스 버튼
- 선택된 액션에 따른 보드 하이라이트 연동

대기 중:
- "X의 턴입니다" 메시지

---

### Step 11: CoachingPanel

- "AI에게 묻기" 버튼
- 질문 입력 텍스트 박스
- 코칭 응답 표시 (마크다운 렌더링 없이 plain text)
- 로딩 스피너

---

### Step 12: App.tsx + main.tsx

뷰 전환 (React Router 없이 상태 기반):
```
Lobby → (게임 시작) → Game
```

Game 레이아웃:
```
┌─────────────────────────────────────┐
│  PlayerDashboard (상단, 4명)        │
├───────────────────┬─────────────────┤
│                   │  ActionPanel    │
│   GameBoard       ├─────────────────┤
│   (SVG, 중앙)     │  CoachingPanel  │
└───────────────────┴─────────────────┘
```

---

## 생성 파일 전체 목록

```
gaia-frontend/
├── package.json                           ← Step 1
├── vite.config.ts                         ← Step 1
├── tsconfig.json                          ← Step 1
├── tsconfig.node.json                     ← Step 1
├── index.html                             ← Step 1
├── src/
│   ├── main.tsx                           ← Step 12
│   ├── App.tsx                            ← Step 12
│   ├── index.css                          ← Step 13
│   ├── types/
│   │   └── game.ts                        ← Step 2
│   ├── api/
│   │   ├── rest.ts                        ← Step 3
│   │   └── websocket.ts                   ← Step 4
│   ├── store/
│   │   ├── roomStore.ts                   ← Step 5
│   │   └── gameStore.ts                   ← Step 5
│   ├── hooks/
│   │   └── useWebSocket.ts                ← Step 6
│   ├── components/
│   │   ├── GameLobby/
│   │   │   ├── index.tsx                  ← Step 7
│   │   │   ├── HomeView.tsx               ← Step 7
│   │   │   ├── CreateRoomView.tsx         ← Step 7
│   │   │   ├── JoinRoomView.tsx           ← Step 7
│   │   │   ├── WaitingRoomView.tsx        ← Step 7
│   │   │   └── FactionSelectView.tsx      ← Step 7
│   │   ├── GameBoard/
│   │   │   ├── index.tsx                  ← Step 8
│   │   │   ├── HexCell.tsx                ← Step 8
│   │   │   └── hex-utils.ts               ← Step 8
│   │   ├── PlayerDashboard/
│   │   │   ├── index.tsx                  ← Step 9
│   │   │   ├── ResourcePanel.tsx          ← Step 9
│   │   │   ├── PowerCycle.tsx             ← Step 9
│   │   │   └── ResearchTrack.tsx          ← Step 9
│   │   ├── ActionPanel/
│   │   │   └── index.tsx                  ← Step 10
│   │   └── CoachingPanel/
│   │       └── index.tsx                  ← Step 11
│   └── tests/
│       ├── setup.ts                       ← Step 14
│       ├── GameLobby.test.tsx             ← Step 14
│       ├── GameBoard.test.tsx             ← Step 14
│       └── PlayerDashboard.test.tsx       ← Step 14
└── aidlc-docs/construction/gaia-frontend/code/
    └── code-summary.md                    ← Step 15
```

**총 파일 수**: 35개
