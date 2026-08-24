# 가이아 프로젝트 온라인 — 요구사항 문서

## 인텐트 분석 요약

| 항목 | 내용 |
|---|---|
| **사용자 요청** | 가이아 프로젝트 보드게임을 온라인으로 구현 (기존 랜더마이저 요소 활용, 4인 고정) |
| **요청 유형** | New Project (Greenfield) |
| **범위 추정** | System-wide (전체 게임 시스템) |
| **복잡도 추정** | Complex — 복잡한 게임 메커니즘, 실시간 멀티플레이어, 이중 AI 시스템 |
| **참조 랜더마이저** | https://uiqoo.kr/boardgames/gaiaproject/randomizer.html (v2.3.2) |

---

## 기술 스택

| 레이어 | 기술 |
|---|---|
| **백엔드** | Rust (Axum 또는 Actix-web + tokio) |
| **프론트엔드** | React + TypeScript |
| **실시간 통신** | WebSocket |
| **헥사곤 렌더링** | 헥사곤 라이브러리 (react-hex-grid 또는 honeycomb.js) |
| **데이터베이스** | PostgreSQL (게임 상태 영구 저장) |
| **LLM 코칭** | MACO Qwen 14B (RAG) |
| **대전 AI** | MCTS (Rust 구현) |
| **배포** | 자체 서버 (VPS / Docker Compose) |

---

## 기능 요구사항

### FR-01: 플레이어 구성

- **FR-01-1**: **4인 고정** — 2인/3인 모드 없음
- **FR-01-2**: 게스트 플레이 (닉네임 기반, 로그인 불필요)
- **FR-01-3**: 게임 룸 생성 → 룸 코드/링크 공유 → 4인 입장 후 시작

---

### FR-02: 게임 셋업 랜더마이저

> 기존 랜더마이저(uiqoo.kr v2.3.2)의 로직과 요소를 기반으로 구현

#### FR-02-1: 시드 기반 PRNG

- 시드 문자열(숫자)을 입력받아 결정론적 랜덤 시퀀스 생성
- 동일 시드 → 동일 게임 셋업 재현 (링크 공유 가능)
- 알고리즘: 기존 랜더마이저와 동일한 Mulberry32 변형 해시 PRNG
  ```
  h = 1779033703 ^ seed.length
  각 문자: h = imul(h ^ charCode, 3432918353), h = (h << 13) | (h >>> 19)
  random(): h = imul(h ^ h>>>16, 2246822507); h = imul(h ^ h>>>13, 3266489909); return (h ^= h>>>16) >>> 0 / 4294967296
  ```
- 랜덤 시드 생성 기능

#### FR-02-2: 팩션 선택

**기본 게임 — 7쌍 (14팩션):**

| 쌍 | 팩션 A | 팩션 B |
|---|---|---|
| 1 | Ambas | Taklons |
| 2 | Bal Taks | Geodens |
| 3 | Gleens | Xenos |
| 4 | Hadsch Hallas | Ivits |
| 5 | Itars | Nevlas |
| 6 | Lantids | Terrans |
| 7 | Bescods | Firaks |

**로스트 플릿 확장 — 추가 2쌍 (4팩션):**

| 쌍 | 팩션 A | 팩션 B |
|---|---|---|
| 8 | Moweyds | Space Giants |
| 9 | Darkanians | Tinkeroids |

- **항상 로스트 플릿 확장 포함** — 9쌍 전체에서 셔플 후 4쌍 선택
- 각 쌍에서 1개 팩션 랜덤 선택 → 4인에 1개씩 배정

#### FR-02-3: 표준 테크 타일 (9개 전체 사용)

| 코드 | 설명 |
|---|---|
| `1o1q` | 광석 1 + QIC 1 |
| `big` | 빅 빌딩 |
| `planetk` | 행성 지식 |
| `gaia` | 가이아 |
| `4pw` | 파워 4 |
| `1k1c` | 지식 1 + 크레딧 1 |
| `4c` | 크레딧 4 |
| `7vp` | 승리 포인트 7 |
| `1o1pw` | 광석 1 + 파워 1 |

- **항상 로스트 플릿 확장 테크 타일 사용** — `planetk_lostfleet` 버전 적용
- 9개를 셔플 후 6개 트랙 컬럼(+3 추가)에 배치

#### FR-02-4: 어드밴스드 테크 타일 (로스트 플릿 21개 중 7개 — 항상)

```
1q5c, 3k, 3o, fed, fedpass, gaia, labpass, mine, mineb,
planetpass_lostfleet, sector, sectoro, adv, trade, tradeb,
asteroidpass, big, deep, deeppass, qaction, terra
```
- 셔플 후 앞 7개 선택 (각 리서치 트랙 상단 + 1개 추가)

#### FR-02-5: 라운드 득점 타일 (로스트 플릿 13개 중 6개 — 항상)

```
big5(×2), fed5, gaia3, gaia4, mine2, adv2, terra2, trade3, trade4,
lab4, sector3, planet3
```
- 셔플 후 앞 6개 선택 (6라운드에 1개씩)

#### FR-02-6: 라운드 부스터 (로스트 플릿 14개 중 7개 — 4인+3, 항상)

```
1o1k, big, gaia, rl, m, range, q, terra, pwt, ts,
deep, former, instant, planet
```
- 셔플 후 앞 7개 선택 (4인 기준 player+3 = 7개)

#### FR-02-7: 최종 득점 타일 (로스트 플릿 9개 중 2개 — 항상)

```
building, fed, gaia, planet_lostfleet, satellite, sector,
asteroid, deep, distance
```
- 셔플 후 앞 2개 선택

**로스트 플릿 확장 추가 (9개 중 2개):**
```
(기존 6개) + asteroid, deep, distance
```

#### FR-02-8: 연방 토큰 (6종 중 1개 공개)

```
c(크레딧), k(지식), o(광석), q(QIC), pwt(파워토큰), vp(승리점수)
```

#### FR-02-9: 맵 배치 (4인 — 로스트 플릿, 항상)

**항상 로스트 플릿 맵 사용:**
```
기본 섹터 01-07 + 딥 스페이스 섹터 11a/11b ~ 16a/16b 각 쌍 중 랜덤 1개 선택
```

**Center Balance 항상 활성화:**
- 타일 01-04(소형 섹터)와 나머지를 분리 셔플 후 교차 배치 (균형 보장)
- 비활성화 옵션 없음 — 항상 Center Balance 적용

**맵 회전:**
- 각 섹터 타일 개별 회전 (60도 단위, 0-5)
- 충돌 감지 알고리즘으로 유효한 맵 배치 보장
- 회전 상태를 rotation 파라미터(10자리 숫자 문자열)로 인코딩

#### FR-02-10: 셋업 링크 공유

- 게임 셋업을 URL/코드 파라미터로 인코딩 (시드만으로 재현 가능):
  `seed=<seed>&rotation=<10digits>`
- Lost Fleet + Center Balance는 항상 고정이므로 파라미터 불필요
- 링크로 동일한 랜덤 셋업 재현 가능

---

### FR-03: 게임 보드 및 맵

- **FR-03-1**: 헥사고날 그리드 렌더링 (react-hex-grid 또는 honeycomb.js)
- **FR-03-2**: 10개 섹터 타일 배치 (4인 기준)
- **FR-03-3**: 행성 유형 시각화: 테란(Earth), 화성(Mars/Volcano), 사막(Desert), 볼캐닉, 글레이셔(Ice), 스웜(Swamp), 트랜스다임(Titanium/Acid), 가이아, 랜드리스
- **FR-03-4**: 구조물 표시: 마인, 트레이딩 스테이션, 리서치 랩, 아카데미, 플래닛러리, 가이아 포머

---

### FR-04: 팩션 시스템 (18개 전체 — 로스트 플릿 포함)

- **FR-04-1**: 18개 팩션 모두 구현 (9쌍 기반, 로스트 플릿 항상 포함)
- **FR-04-2**: 각 팩션의 고유 능력, 홈 행성 타입, 특수 규칙 구현
- **FR-04-3**: 팩션 카드 UI 표시

---

### FR-05: 핵심 게임 메커니즘

- **FR-05-1**: 6라운드 구조
- **FR-05-2**: 액션 시스템 (건설, 업그레이드, 테라포밍+건설, 파워 액션, 특수 액션, 패스, 가이아 프로젝트)
- **FR-05-3**: 파워 사이클 관리 (Braintrust 1/2/3 + Gaia Area)
- **FR-05-4**: 자원 관리: 광석(Ore), 지식(Knowledge), 크레딧(Credit), QIC
- **FR-05-5**: 테라포밍 트랙 (0~5단계)
- **FR-05-6**: 가이아 포머 배치 및 가이아 행성 변환
- **FR-05-7**: 6개 리서치 트랙 (Terraforming, Navigation, AI, Gaia Project, Economy, Science)
- **FR-05-8**: 테크 타일 획득 및 어드밴스드 테크 타일
- **FR-05-9**: 연방 형성 규칙
- **FR-05-10**: 라운드/최종 득점 계산

---

### FR-06: 실시간 멀티플레이어

- **FR-06-1**: 4인 고정 온라인 실시간 멀티플레이어
- **FR-06-2**: 게임 룸 생성 (룸 코드 공유)
- **FR-06-3**: WebSocket 기반 게임 상태 실시간 동기화
- **FR-06-4**: 연결 끊김 처리 및 재접속 지원 (DB에 게임 상태 저장)
- **FR-06-5**: 턴 순서 관리 및 알림

---

### FR-07: AI 시스템 (2단계)

**Phase 1 — LLM 코칭 AI:**
- **FR-07-1**: RAG 기반 규칙 검색 (가이아 프로젝트 룰북 벡터 DB화)
- **FR-07-2**: MACO Qwen 14B 기반 코칭 어시스턴트
- **FR-07-3**: 현재 게임 상태 분석 + 조언 제공
- **FR-07-4**: 룰 질문 응답

**Phase 2 — MCTS 대전 AI:**
- **FR-07-5**: Monte Carlo Tree Search 기반 AI 플레이어 (Rust 구현)
- **FR-07-6**: AI 난이도 설정 (시뮬레이션 횟수)
- **FR-07-7**: AI vs Human 게임 모드

---

### FR-08: 게임 상태 관리

- **FR-08-1**: PostgreSQL에 게임 상태 영구 저장
- **FR-08-2**: 전체 행동 로그 (게임 히스토리)
- **FR-08-3**: 게임 관전 모드

---

### FR-09: UI/UX

- **FR-09-1**: 직관적인 헥사곤 보드 인터랙션 (클릭, 유효 액션 하이라이트)
- **FR-09-2**: 게임 로그 패널
- **FR-09-3**: 플레이어 대시보드 (자원, 파워 사이클, 리서치 트랙)
- **FR-09-4**: 셋업 화면 (랜더마이저 결과 표시)

---

## 비기능 요구사항

### NFR-01: 성능
- WebSocket 메시지 레이턴시 < 100ms
- 게임 상태 DB 저장 < 50ms
- MCTS AI 응답 시간 < 5초 (기본 난이도)

### NFR-02: 신뢰성
- 연결 끊김 시 게임 상태 보존
- 서버 재시작 후 진행 중 게임 복구

### NFR-03: 유지보수성
- 게임 규칙 로직과 통신 레이어 분리
- 팩션별 모듈화

### NFR-04: 테스트 (Partial PBT)
- 속성 기반 테스트: 순수 함수 (득점 계산, 자원 변환, 테라포밍 단계, PRNG)
- 속성 기반 테스트: 직렬화 라운드트립 (게임 상태)

---

## Extension 설정

| Extension | 활성화 | 결정 시점 |
|---|---|---|
| Security Baseline | No | Requirements Analysis |
| Property-Based Testing | Partial (순수 함수 + 직렬화) | Requirements Analysis |

---

## 아키텍처 고려사항

1. **Rust 백엔드**: Axum + tokio + WebSocket (`axum::extract::ws`)
2. **게임 엔진 크레이트**: 순수 Rust 게임 로직 (`gaia-engine`) — 랜더마이저 PRNG 포함
3. **LLM 통합**: MACO Qwen 14B (ollama 또는 vLLM), 벡터 DB (qdrant 또는 pgvector)
4. **MCTS 엔진**: 별도 Rust 모듈
5. **프론트엔드**: React + TypeScript + react-hex-grid
6. **DB**: PostgreSQL
7. **배포**: 자체 VPS, Docker Compose

---

## 프로젝트 성공 기준

- [ ] 랜더마이저 시드로 게임 셋업 재현 가능 (동일 시드 → 동일 배치)
- [ ] 14개 팩션으로 완전한 6라운드 게임 진행 가능
- [ ] 4인 실시간 멀티플레이어 안정적 동작
- [ ] LLM 코칭 AI가 게임 상태 기반 조언 제공
- [ ] MCTS AI가 유효한 게임 액션 선택
- [ ] 게임 상태 DB 저장 및 재접속 후 복구
