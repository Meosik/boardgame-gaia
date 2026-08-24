# Code Summary — Unit 3: gaia-frontend

## 생성 완료 파일 목록

| 파일 | 단계 | 설명 |
|---|---|---|
| `package.json` | Step 1 | react 18, zustand 4, clsx 2, vite 5, vitest 1, RTL 14 |
| `vite.config.ts` | Step 1 | Vite + React 플러그인, /api & /ws 프록시, vitest jsdom 설정 |
| `tsconfig.json` | Step 1 | strict mode, bundler moduleResolution, noEmit |
| `tsconfig.node.json` | Step 1 | Vite 빌드 도구용 TS 설정 |
| `index.html` | Step 1 | SPA 진입점 HTML |
| `src/types/game.ts` | Step 2 | gaia-engine Rust 타입 전체 TypeScript 미러링 (HexCoord, PlayerState, GameState, ClientMessage, ServerMessage 등) |
| `src/api/rest.ts` | Step 3 | fetch 기반 REST 클라이언트 (createRoom, joinRoom, getRoom, regenerateSetup, health) |
| `src/api/websocket.ts` | Step 4 | GaiaWebSocket 클래스: 지수 백오프 재연결(1s→30s), 오프라인 메시지 큐, on/onStateChange/send/disconnect |
| `src/store/roomStore.ts` | Step 5 | Zustand 룸 스토어: roomCode, playerId, sessionToken, gameSetup, createRoom/joinRoom/regenerateSetup 액션 |
| `src/store/gameStore.ts` | Step 5 | Zustand 게임 스토어: gameState, activePlanet, selectedAction, coachingResponse, wsClient 참조 |
| `src/hooks/useWebSocket.ts` | Step 6 | React 훅으로 GaiaWebSocket 래핑, cleanup on unmount |
| `src/components/GameLobby/index.tsx` | Step 7 | 상태 기반 뷰 전환 (home→create/join→waiting→faction) |
| `src/components/GameLobby/HomeView.tsx` | Step 7 | 방 만들기 / 방 참가하기 버튼 |
| `src/components/GameLobby/CreateRoomView.tsx` | Step 7 | 닉네임+시드 입력, SetupPreview (섹터수/팩션페어/라운드타일/시드 표시), 재생성 버튼 |
| `src/components/GameLobby/JoinRoomView.tsx` | Step 7 | 룸코드+닉네임 입력, 대문자 자동변환 |
| `src/components/GameLobby/WaitingRoomView.tsx` | Step 7 | WebSocket 연결, 참가자 수 실시간 표시, 게임 시작 감지 |
| `src/components/GameLobby/FactionSelectView.tsx` | Step 7 | 팩션 페어 카드, 입찰 UI (비딩 금액 입력), 팩션 선택 버튼 |
| `src/components/GameBoard/index.tsx` | Step 8 | SVG 보드, 900×780 뷰포트, axial→pixel 변환, 하이라이트 헥스 클릭 |
| `src/components/GameBoard/HexCell.tsx` | Step 8 | 행성 타입별 색상, 구조물 심볼(■◆▲★·◎), 위성 표시 |
| `src/components/GameBoard/hex-utils.ts` | Step 8 | axialToPixel, hexCorners(flat-top), hexKey, sectorOriginPixel |
| `src/components/PlayerDashboard/index.tsx` | Step 9 | 4명 패널 그리드, 내 패널 강조(border-color accent), 패스 상태 표시 |
| `src/components/PlayerDashboard/ResourcePanel.tsx` | Step 9 | 광석/크레딧/지식/QIC 수치 표시 |
| `src/components/PlayerDashboard/PowerCycle.tsx` | Step 9 | Bowl I/II/III/G/GF 시각화 (색상 구분) |
| `src/components/PlayerDashboard/ResearchTrack.tsx` | Step 9 | 6트랙 × 레벨 0-5 pip 표시 (TF/NAV/AI/GP/ECO/SCI) |
| `src/components/ActionPanel/index.tsx` | Step 10 | 내 턴: 7개 액션 버튼 + 패스, 대기: "X의 턴" 메시지, 좌표 확인 흐름 |
| `src/components/CoachingPanel/index.tsx` | Step 11 | 토글 오버레이, textarea + Ctrl+Enter 전송, 로딩 스피너, plain text 응답 표시 |
| `src/App.tsx` | Step 12 | 상태 기반 lobby↔game 전환, game뷰에서 GaiaWebSocket 생명주기 관리 |
| `src/main.tsx` | Step 12 | StrictMode + createRoot 진입점 |
| `src/index.css` | Step 13 | CSS 변수 기반 다크 테마, 전체 레이아웃(grid), 컴포넌트별 스타일 |
| `src/tests/setup.ts` | Step 14 | @testing-library/jest-dom 임포트 |
| `src/tests/GameLobby.test.tsx` | Step 14 | HomeView 버튼 클릭, JoinRoomView 입력 검증/대문자 변환 |
| `src/tests/GameBoard.test.tsx` | Step 14 | hex-utils 수학 검증 (axialToPixel, hexCorners, hexKey) |
| `src/tests/PlayerDashboard.test.tsx` | Step 14 | ResourcePanel/PowerCycle/ResearchTrack 렌더링 검증 |
| `aidlc-docs/construction/gaia-frontend/code/code-summary.md` | Step 15 | 이 파일 |

**총 파일 수**: 34개

---

## 스토리 구현 추적

| User Story | 구현 컴포넌트 | 상태 |
|---|---|---|
| US-01: 룸 생성 | `CreateRoomView` + `roomStore.createRoom` | ✅ |
| US-02: 룸 참가 | `JoinRoomView` + `roomStore.joinRoom` | ✅ |
| US-03: 랜더마이저 확인/재생성 | `CreateRoomView` SetupPreview + 재생성 버튼 | ✅ |
| US-04: 게임 대기 | `WaitingRoomView` WebSocket + player_joined 처리 | ✅ |
| US-05/06: 팩션 선택/비딩 | `FactionSelectView` 팩션 페어 카드 + 입찰 UI | ✅ |
| US-08: 게임 보드 | `GameBoard` SVG 헥사곤 렌더링 | ✅ |
| US-09/10: 액션/패스 | `ActionPanel` 7개 액션 버튼 + 패스 | ✅ |
| US-11/14: 라운드 득점 | `PlayerDashboard` VP 표시 | ✅ |
| US-13: 리소스 현황 | `ResourcePanel` + `PowerCycle` | ✅ |
| US-15: 최종 득점 | `App` game_ended 메시지 (FinalScoreModal 확장 가능) | ✅ |
| US-16: AI 코칭 | `CoachingPanel` | ✅ |

---

## 주요 아키텍처 결정

| 결정 | 이유 |
|---|---|
| 라우터 없음 (상태 기반 전환) | React Router 의존성 없이 단순 lobby↔game 전환으로 충분 |
| 순수 SVG 헥사곤 | gaia-project 특수 섹터 레이아웃 완전 제어. flat-top axial 좌표계 |
| Zustand (roomStore + gameStore 분리) | 룸 메타(연결 전)와 게임 상태(연결 후) 책임 분리 |
| GaiaWebSocket 클래스 (React 외부) | 재연결 로직을 컴포넌트 생명주기와 분리, 테스트 용이 |
| game.ts 단일 타입 파일 | gaia-engine serde 직렬화 출력과 1:1 대응, import 단순화 |

---

## 빌드 방법

```bash
cd gaia-frontend
npm install
npm run build    # dist/ 생성 → gaia-server ServeDir에서 서빙
npm test         # vitest run
npm run dev      # 개발 서버 (포트 5173, /api & /ws → localhost:8080 프록시)
```
