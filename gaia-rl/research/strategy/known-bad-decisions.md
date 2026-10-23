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
| 8 | lab-101-ships-vs-menu-full · pair-002/game-0-A03 · 84 (2R, 프레임 85) | 기오덴 B | Upgrade 1,-1 → 의회(한 수 앞 −7.82, 순위 밖; `selected` = 계획 `Geodens-PI@1,-1-new-type@2,-1`, 45에서도 같은 계획이 TS를 골랐음) | 2R에 의회만 짓고 패스, 3R 연방 없이 1–3R 충전 83 vs A팔 180 | 종족 능력 계획(의회 → 새 행성형 식민)이 비교에서 이겼으나 뒤 절반(2,-1 식민)은 의회 뒤 광석이 없어 93에서 사라짐(93 비교 4개: 연구 3·무료 TS 1, `Geodens-new-type@1,-6`의 첫 수도 연구). 기억 없이 다시 고르면 RL(타일 3) `root-42` 245.94 > `Geodens-PI@2,-7-…` 243.38. 읽기: 지평(계획 뒤 절반의 예산을 한 수입 롤아웃이 못 봄) | 연구소(타일 3) 뒤 식민 | 제안 E74: 능력 계획의 의회 단계는 같은 예측 안에서 식민까지 지불 가능할 때만 비교에 올림 |
| 9 | lab-101-ships-vs-menu-full · pair-002/game-0-A03 · 114 (3R, 프레임 115) | 기오덴 B | AI 연구(`current-choice` 265.89) | 합법 연방(RL+의회+광산 2, 위성 5)을 안 만듦 — "연방 가족이 왜 안 뽑히나" | `federation-2`는 메뉴로 비교에 **올랐고**(밀림 아님) 롤아웃 230.42로 35 패배, 한 수 앞 0.66 — 위성 5개 비용. 순서 문제가 아니라 값·지평 문제 | 유보(위성 5개면 기다리는 게 맞을 수 있음) | 판단 보류; 비교 계획 라벨을 결정 로그에 남겨 판 전체에서 "밀림 vs 패배"를 세는 계측 제안(E74) |
| 7 | lab-095-ships-vs-shipmine-4r · pair-004/game-0-A01 · 48 (1R) | 타클론 A | ExploreSpaceship Eclipse(QIC 2 = 보유 전부; 광석 1·돈 5·지식 4) | "이클립스 입장에 QIC를 2개나? 그냥 광산 두고 가이아 행성 먹는 데 QIC 쓰겠다" | 가이아 광산 −6,−2·6,−2(사거리 1 + 가이아 1 = QIC 2)가 합법인데 한 수 점수가 낮아 비교 4개 밖; 입장 계획 263.19가 1위. 인접 모행성 −1,−2도 사거리 QIC 2라 ship_adjacent_mine의 "QIC 절약" 전제 불성립 | 광산 + 가이아 행성에 QIC | 제안 qic_entry_compare(QIC 입장 결정에 그 QIC 이하 행성 광산을 비교에 추가), E61 사용자 확인 대기 |
| 10 | lab-103-ships-vs-menu80-4r · pair-003/game-1-A02 · 59 (1R, 프레임 60; 64·65·68 같음) | 제노스 B | Upgrade 1,3 → TS(`track-plan-Economy-2`, 253.22) | 1–3R 충전 162 vs A팔 243(쌍 −81); A는 같은 시드에서 `BGG-R1-1AC+3M`으로 1R 아카데미, B는 29에서 RL 뒤 38 항해·50–51 경제 트랙 계획으로 가며 아카데미 없이 2R | 비교 4칸이 `BGG-R1-1RL+1TS+2M`·`current-choice`(같은 첫 수 13, 같은 값 234.46)·`track-plan-Economy-2` **두 번**(같은 첫 수·253.22) = 서로 다른 평가 2개뿐. 기억된 계획을 goals[0]에 넣을 때 같은 이름이 목록에 있어도 지우지 않음(`parallel_search.py:91–95`, preparation.search 같은 구성). 103 전체: 비교 목록 중복 결정 A 390/2634(15%, `Qic`·종족 능력 계획)·B 797/2590(31%, `track-plan-Economy` 258·`colony` 126·`track-plan-Science` 99). 읽기: 순서(비교 칸 낭비) | 아카데미 오프닝 유지 또는 root 후보 비교 | 제안 E90(토론 1/1 수정): 이 사례의 두 번째 사본은 메뉴 2번째 칸이 roots 목록 앞에 들어간 것(`teacher_patches.py:3973`; 3번째 칸은 paired `:3982`)이라 goals만 정리해선 안 없어짐 → 순차 search와 `_planned_tasks` 양쪽에서 **최종 tasks를 만든 뒤, 예산으로 자르기 전에** 같은 계획(이름·첫 수·단계) 제거. 테스트: 기억 계획 = 메뉴 2번째·3번째 칸인 경우 |

추가 규칙: 새 항목은 실험 폴더·pair/game·결정 번호(다시보기 프레임)·좌석·실제 수·기대 수를 반드시 적는다. 결정 번호가
없는 옛 항목은 다시 보기에서 찾으면 채운다.
