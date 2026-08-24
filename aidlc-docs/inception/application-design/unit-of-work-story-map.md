# Unit of Work Story Map — 가이아 프로젝트 온라인

## 스토리-단위 매핑 테이블

| 스토리 | 제목 | Unit 1 Engine | Unit 2 Server | Unit 3 Frontend | Unit 4 AI |
|---|---|---|---|---|---|
| **Epic 1: 게임 셋업** | | | | | |
| US-01 | 게임 룸 생성 | Randomizer | RoomManager, RestApi, GameSetupSvc | GameLobby | — |
| US-02 | 게임 룸 참가 | — | SessionManager, RestApi | GameLobby | — |
| US-03 | 랜더마이저 확인/재생성 | Randomizer, GameSetup | RestApi, GameSetupSvc | GameLobby (셋업 UI) | — |
| US-04 | 팩션 선택 모드 결정 | — | FactionSelectionSvc | GameLobby | — |
| US-05 | 자유 팩션 선택 + LLM 조언 | FactionRegistry | FactionSelectionSvc, CoachingProxy | GameLobby | CoachingApi (조언) |
| US-07 | 비딩 경매 | BiddingEngine | FactionSelectionSvc, GameEventBus | GameLobby (비딩 UI) | — |
| **Epic 2: 게임 진행** | | | | | |
| US-08 | 게임 보드 확인 | GameState, MapEngine | RestApi (상태 조회) | GameBoard, PlayerDashboard | — |
| US-09 | 액션 수행 | RuleEngine, GameState | GameActionSvc, WsHandler | ActionPanel, GameBoard | — |
| US-10 | 라운드 패스 | RuleEngine | TurnManagementSvc | ActionPanel | — |
| US-11 | 턴 대기/관전 | — | GameEventBus | GameBoard (실시간) | CoachingPanel (선택적) |
| US-12 | 게임 로그 확인 | — | GameRepository | GameLobby/LogPanel | — |
| US-13 | 리소스 현황 확인 | GameState | WsHandler (이벤트) | PlayerDashboard | — |
| US-14 | 라운드 득점 확인 | ScoringEngine | TurnManagementSvc | PlayerDashboard | — |
| **Epic 3: 게임 종료** | | | | | |
| US-15 | 최종 득점 계산/확인 | ScoringEngine, BidPenalty | GameEndSvc | ResultScreen | — |
| US-16 | 게임 결과 화면 | — | GameEndSvc | ResultScreen | — |
| **Epic 4: AI 코칭** | | | | | |
| US-17 | AI 코칭 요청 | — | CoachingProxySvc | CoachingPanel | CoachingApi |
| US-18 | 규칙 질문 | — | CoachingProxySvc | CoachingPanel | CoachingApi, RagRetriever |
| US-19 | 전략 조언 | — | CoachingProxySvc | CoachingPanel | CoachingApi, LlmClient |

## 단위별 스토리 책임 요약

### Unit 1 (gaia-engine)
게임 로직 핵심 — 대부분 스토리의 규칙/계산 백엔드
- **전담**: 없음 (항상 Unit 2를 통해 간접 사용)
- **핵심 기여**: US-01(Randomizer), US-07(BiddingEngine), US-09(RuleEngine), US-14/15(ScoringEngine)

### Unit 2 (gaia-server)
서버 오케스트레이션 — 거의 모든 스토리에 참여
- **전담**: US-02(참가), US-04(모드 결정), US-12(로그)
- **핵심 기여**: 모든 Epic 1/2/3 스토리의 서버 처리

### Unit 3 (gaia-frontend)
UI 레이어 — 모든 스토리에 참여
- **전담**: 없음 (항상 Unit 2와 연동)
- **핵심 기여**: 모든 사용자 인터랙션 (US-01~19 전체)

### Unit 4 (gaia-ai)
AI 코칭 — Epic 4 전담
- **전담**: US-18(규칙 질문), US-19(전략 조언)
- **부분 기여**: US-05(팩션 LLM 조언), US-11(대기 중 코칭), US-17(코칭 요청)

## 단위별 스토리 수

| 단위 | 주요 기여 스토리 수 | 비고 |
|---|---|---|
| Unit 1 | 19개 (전체 — 간접) | 게임 로직 기반 |
| Unit 2 | 19개 (전체 — 오케스트레이션) | 서버 레이어 |
| Unit 3 | 19개 (전체 — UI) | 모든 사용자 인터랙션 |
| Unit 4 | 5개 (직접) | Epic 4 + US-05 팩션 조언 |
