# 알려진 나쁜 결정 — 회귀 세트 (HANDOFF 5a E50)

사용자가 리플레이에서 짚은 수와 봇이 explain으로 확인한 원인. 끝값·탐색을 바꿀 때마다 같은 결정을 다시 물어
고쳐졌는지 본다(학습 상태값의 검증 세트로도 쓴다). 다시 묻는 명령(저장소 루트, 봇 허용 접두):

```sh
GAIA_ENGINE_FIXES_2=1 PYTHONPATH=gaia-rl/python:gaia-rl/baseline-teacher-20260917:gaia-rl/tools gaia-rl/.venv/bin/python \
  gaia-rl/tools/explain_decision.py ~/projects/gaia-lab/gaia-rl/runs/<실험 폴더>/<pair>/<game> --step <결정 번호> --spec <spec>
```

| # | 실험 · 판 · 결정 | 좌석 | 실제 수 | 왜 나쁜가(사용자) | 원인(explain) | 기대 수 | 고친 부품 · 확인 |
|---|---|---|---|---|---|---|---|
| 1 | lab-090-ships-vs-tokens-full · pair-003/game-0 · 296 (6R) | 테란 A | 기본 순위 1위(재점수 아님) | QIC 9개를 들고 끝남("쓸 데가 없다는 것도 말이 안 되고") | 6R에도 QIC를 정가 7충전으로 쳐 트와일라잇 재점수(3QIC → 8VP+1QIC)가 −1.33 | 트와일라잇 재점수 | endgame_prices: 같은 결정 +8.00 1위·선택(E34), 096 대기 |
| 2 | lab-084-ships-vs-byfaction-full · pair-001/game-0-A23 · 241 | (한 수 앞 순위) | Pass 0 | 연방이 합법인데 한 번도 안 만듦("연방을 왜 먹지 않지?") | 모든 연방이 한 수 앞 −16(위성 비용)이라 비교 4개에 못 듦 | 연방 결성 비교 | fed_compare: 연방 가능 결정을 안 버림(089 --by-arm), 효과 미확인 |
| 3 | lab-091-byfaction-vs-guide-bc-4r · pair-006/game-0-A02 · 140 (3R) | 테란 A | AI 연구(9.33) | 자료 트랙(항해 2 → 가이아/과학) 대신 AI 쏠림, 항해 0 | 연구 단 16충전 고정 + AI QIC 7 = 즉시 보상 순위, 항해는 값표에 없음, 비교 3개 동률 311.88 | 항해 2 → 식민 계획 | track_plans: 비교에 올라옴(307.21, AI가 이김), 097 대기 |
| 4 | lab-091-byfaction-vs-guide-bc-4r · pair-000/game-1-A13 · 결정 번호 미기록(1–3R 연구소·아카데미 타일 선택) | 아이타 B | 타일 6·8 | 수입 타일 2·5를 한 번도 안 집어 충전 103 vs 194 | tile_prefs가 B7-01의 "의회로 가져갈 기술" 목록을 모든 타일 선택에 적용 | 타일 5 또는 2 | tile_prefs 범위 수정(E39), 098 대기 |
| 5 | lab-052 · pair-006/game-1 · 1R(결정 번호 미기록) | 타클론 | 광산 먼저 | 1R 아카데미 예산을 광산에 써 버림(사용자 "뺏길 걱정 없으면 건물을 빨리") | 오프닝 계획이 광산을 먼저 두고 예산을 안 남김 | 아카데미 먼저 | opening_budget·guard·release(077 +23.6 얇음, 084 미확인) |
| 6 | lab-027-search4-cap10 · pair-004/game-0-A01 · 1R | 기오덴·테란 | 오프닝 선택 | 비교값이 더 높은 계획을 버리고 오프닝 라벨을 따름 | select_forecast가 비교값 무시 | 비교값 1위 | distinct_search(030–033 기각, 삭제) → value_max로 대체 |
| 7 | lab-095-ships-vs-shipmine-4r · pair-004/game-0-A01 · 48 (1R) | 타클론 A | ExploreSpaceship Eclipse(QIC 2 = 보유 전부; 광석 1·돈 5·지식 4) | "이클립스 입장에 QIC를 2개나? 그냥 광산 두고 가이아 행성 먹는 데 QIC 쓰겠다" | 가이아 광산 −6,−2·6,−2(사거리 1 + 가이아 1 = QIC 2)가 합법인데 한 수 점수가 낮아 비교 4개 밖; 입장 계획 263.19가 1위. 인접 모행성 −1,−2도 사거리 QIC 2라 ship_adjacent_mine의 "QIC 절약" 전제 불성립 | 광산 + 가이아 행성에 QIC | 제안 qic_entry_compare(QIC 입장 결정에 그 QIC 이하 행성 광산을 비교에 추가), E61 사용자 확인 대기 |

추가 규칙: 새 항목은 실험 폴더·pair/game·결정 번호(다시보기 프레임)·좌석·실제 수·기대 수를 반드시 적는다. 결정 번호가
없는 옛 항목은 다시 보기에서 찾으면 채운다.
