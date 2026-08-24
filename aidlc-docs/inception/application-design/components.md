# Components — 가이아 프로젝트 온라인

## 시스템 구성 개요

```
Cargo Workspace (gaia-project/)
├── gaia-engine/        # Pure Rust 게임 로직 크레이트
├── gaia-server/        # Axum 백엔드 서버 크레이트
└── gaia-ai/            # LLM 코칭 사이드카 서비스 (별도 컨테이너)

gaia-frontend/          # React + TypeScript (별도 디렉토리)
```

---

## Crate 1: gaia-engine (Pure Game Logic)

**목적**: 가이아 프로젝트의 모든 게임 규칙과 상태를 담당하는 순수 로직 크레이트. 네트워크/DB 의존성 없음. 독립적 테스트 가능.

### Component 1.1: Randomizer
| 항목 | 내용 |
|---|---|
| **책임** | 시드 기반 PRNG로 게임 셋업 생성 |
| **입력** | seed: String, player_count: u8 (고정 4) |
| **출력** | GameSetup 구조체 |
| **포함 요소** | 팩션 쌍 셔플/선택, 테크 타일, 라운드 타일, 부스터, 최종 득점 타일, 맵 섹터 배치 |
| **특이사항** | 항상 Lost Fleet + Center Balance 적용 |

### Component 1.2: GameState
| 항목 | 내용 |
|---|---|
| **책임** | 전체 게임 상태의 단일 진실 소스(Single Source of Truth) |
| **포함 요소** | 보드 상태, 플레이어 상태 4개, 라운드 정보, 페이즈 정보 |
| **직렬화** | serde JSON 직렬화 지원 (스냅샷용) |

### Component 1.3: FactionRegistry
| 항목 | 내용 |
|---|---|
| **책임** | 18개 팩션 정의 및 능력 관리 |
| **구현 방식** | Hybrid — 공통 속성은 TOML 데이터, 복잡한 특수 능력은 FactionAbility trait |
| **팩션 수** | 18개 (기본 14 + Lost Fleet 4) |

### Component 1.4: RuleEngine
| 항목 | 내용 |
|---|---|
| **책임** | 게임 액션 유효성 검사 및 상태 변이 적용 |
| **핵심 기능** | 액션 가능 여부 판단, 자원 차감, 구조물 배치, 테라포밍 단계 계산 |
| **보장** | 불변 규칙 위반 시 에러 반환 (상태 변이 없음) |

### Component 1.5: ScoringEngine
| 항목 | 내용 |
|---|---|
| **책임** | 라운드 득점 및 최종 득점 계산 |
| **계산 항목** | 라운드 타일 보너스, 연방 VP, 리서치 트랙 VP, 구조물 VP, 최종 득점 타일, 비딩 VP 차감 |

### Component 1.6: MapEngine
| 항목 | 내용 |
|---|---|
| **책임** | 헥사곤 그리드 좌표 계산, 섹터 배치, 충돌 감지 |
| **알고리즘** | 오프셋 좌표계 → 큐브 좌표계 변환, 섹터 충돌 감지 |
| **범위 계산** | 내비게이션 사거리 계산, 연방 연결 경로 탐색 |

### Component 1.7: BiddingEngine
| 항목 | 내용 |
|---|---|
| **책임** | 팩션 비딩 경매 로직 관리 |
| **규칙** | 시계방향 순차 입찰, 현재 최고가 초과 또는 패스, 낙찰 시 팩션+턴오더 선택 |

---

## Crate 2: gaia-server (Backend Server)

**목적**: 실시간 멀티플레이어 서버. Axum + tokio + WebSocket. gaia-engine을 라이브러리로 사용.

### Component 2.1: RoomManager
| 항목 | 내용 |
|---|---|
| **책임** | 활성 게임 룸 인메모리 관리 |
| **저장소** | `Arc<RwLock<HashMap<RoomCode, Room>>>` |
| **룸 상태** | Waiting(대기) → FactionSelect(팩션선택) → InGame(게임중) → Ended(종료) |

### Component 2.2: WebSocketHandler
| 항목 | 내용 |
|---|---|
| **책임** | WebSocket 연결 수락, 메시지 파싱, 이벤트 라우팅 |
| **메시지 형식** | JSON (`{ "type": "...", "payload": {...} }`) |
| **연결 관리** | 플레이어별 `tokio::sync::mpsc` 채널 |

### Component 2.3: RestApiHandler
| 항목 | 내용 |
|---|---|
| **책임** | REST 엔드포인트 처리 (룸 생성, 참가, 셋업 조회) |
| **주요 엔드포인트** | POST /rooms, POST /rooms/:code/join, GET /rooms/:code/setup |

### Component 2.4: GameEventBus
| 항목 | 내용 |
|---|---|
| **책임** | 게임 이벤트를 룸 내 모든 플레이어에게 브로드캐스트 |
| **구현** | tokio broadcast channel |

### Component 2.5: GameRepository
| 항목 | 내용 |
|---|---|
| **책임** | PostgreSQL 영속성 — 이벤트 로그 + 스냅샷 |
| **스냅샷 주기** | 매 라운드 종료 시 + 명시적 요청 시 |
| **이벤트 로그** | 모든 게임 액션을 순서대로 저장 |

### Component 2.6: SessionManager
| 항목 | 내용 |
|---|---|
| **책임** | 플레이어 닉네임-세션 매핑, 재접속 처리 |
| **저장소** | 인메모리 (세션 토큰 → 플레이어 정보) |

---

## Service 3: gaia-ai (LLM Coaching Sidecar)

**목적**: LLM 기반 코칭 AI. 별도 Docker 컨테이너로 실행. gaia-server가 HTTP로 호출.

### Component 3.1: CoachingApi
| 항목 | 내용 |
|---|---|
| **책임** | 코칭 요청 수신 및 응답 반환 |
| **엔드포인트** | POST /coach/analyze, POST /coach/rules, POST /coach/strategy |
| **입력** | 게임 상태 JSON + 플레이어 질문 |

### Component 3.2: RagRetriever
| 항목 | 내용 |
|---|---|
| **책임** | 룰북 벡터 DB에서 관련 규칙 검색 |
| **벡터 DB** | Qdrant 또는 pgvector |
| **임베딩** | 쿼리 벡터화 후 유사도 검색 |

### Component 3.3: LlmClient
| 항목 | 내용 |
|---|---|
| **책임** | MACO Qwen 14B 모델 API 호출 |
| **연동** | ollama HTTP API 또는 vLLM |
| **컨텍스트** | 게임 상태 + RAG 검색 결과 + 대화 이력 |

---

## Application 4: gaia-frontend (React + TypeScript)

**목적**: 웹 클라이언트. Vite + React + TypeScript. react-hex-grid 또는 honeycomb.js 사용.

### Component 4.1: GameBoard
| 항목 | 내용 |
|---|---|
| **책임** | 헥사곤 게임 보드 렌더링 및 인터랙션 |
| **라이브러리** | react-hex-grid 또는 honeycomb.js |
| **기능** | 행성 시각화, 구조물 표시, 유효 액션 하이라이트, 클릭 이벤트 |

### Component 4.2: GameLobby
| 항목 | 내용 |
|---|---|
| **책임** | 룸 생성/참가, 대기실, 랜더마이저 결과 표시 |
| **기능** | 팩션 선택 모드 UI, 시드 공유 |

### Component 4.3: PlayerDashboard
| 항목 | 내용 |
|---|---|
| **책임** | 플레이어 자원·파워·리서치 트랙 표시 |
| **실시간 업데이트** | WebSocket 이벤트로 즉시 반영 |

### Component 4.4: ActionPanel
| 항목 | 내용 |
|---|---|
| **책임** | 현재 턴에 수행 가능한 액션 표시 및 선택 |
| **상태** | 내 턴/대기 중에 따라 활성화/비활성화 |

### Component 4.5: CoachingPanel
| 항목 | 내용 |
|---|---|
| **책임** | AI 코칭 오버레이 UI |
| **기능** | 상황 분석, 규칙 질문, 전략 조언 요청 |
| **비차단** | 게임 진행과 독립적으로 동작 |

### Component 4.6: WebSocketClient
| 항목 | 내용 |
|---|---|
| **책임** | WebSocket 연결 관리, 메시지 수신/발신 |
| **재연결** | 자동 재연결 로직 (지수 백오프) |
| **상태 관리** | Zustand 또는 React Context로 게임 상태 관리 |
