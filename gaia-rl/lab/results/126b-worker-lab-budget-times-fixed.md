# 126b-worker-lab-budget-times-fixed — 완료

E204 (ㄱ)(코덱스 이상 없음 → 진행, 사용자 2026-11-13 상시 지시): 126 재측정 — 교사 실력 판정 아님, 대국 A/B 아님. 126에서 워커는 시작 부스터 4결정을 탐색했는데(38.7·33.1·120.0초 비교 0/5·15.2초) lab 교사는 등급 즉시 선택(lab-123 48판 192결정 전부 0.0초·booster-tier-N): ai_worker.py가 요청마다 budget_teacher.install로 TimedPreparationTeacher.choose를 덮어써 공장이 얹은 래퍼가 방의 둘째 요청부터 빠지던 결함. 9170cd7에서 워커 쪽만 고침(install_budget이 래퍼를 되돌림; lab 경로 불변) + worker_times.py 행에 selected 기록. 이 큐: 126과 같은 명령(tools/worker_times.py 처음부터 두는 모드, Environment('quartet-e-88365') 셋업부터 워커가 고른 수로 80결정, 새 공장 guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier × hard 이름(세 수준 같은 값: 비교 4·수입 1회 내다보기·상한 60초), GAIA_AI_PARALLEL=2, 벽시계 제한 5400초, 한 결정 180초 초과면 칸을 끊고 시간 초과로 기록). 시드 재사용은 같은 설계의 재측정이라서; 워커가 고르는 수가 달라지면 국면이 갈라지므로 결정별 짝 비교는 아님. 시드 1개·한 번. 예상 ≈ 40–45분. 볼 것: ① 결정 수(예정 80)·도달 라운드·멈춘 이유(decisions여야 함)·오류·180초 시간 초과 ② 시작 부스터 4결정(셋업 중 후보가 SelectStartingBooster인 결정; 126에서는 8–11번째, 후보 7·6·5·4): 넷 다 selected가 booster-tier-N·1초 미만·비교 0이어야 수정 확인 — 하나라도 탐색했으면 수정 실패로 보고하고 가드 제안을 미룸 ③ 결정당 벽시계 평균·중앙·p90·최대, 라운드별, 셋업 합과 시작 자리 합(126: 386.8초·179.9초) ④ rows에서 30·60·90·120초 초과 수, time_capped 수 ⑤ 1R 전체 합(126: 38결정 20.6분). 읽기(사전 등록): 통과·실패 판정 없음 — ②가 확인되면 관측 최대를 서버 가드 GAIA_AI_TIMEOUT_SECS(기본 30초) 값의 근거로 적음: 가드는 관측 최대보다 위여야 한다는 것까지만, 값은 사용자가 정함. 180초 시간 초과나 오류가 있으면 그 결정을 따로 보고하고 가드 제안을 미룸. 126과 나란히 적되 부스터 선택이 달라지면 뒤 국면도 달라지므로 1R·2R 시간 차이를 수정의 효과로 읽지 않음. 한계: 126과 같음 — 초반 80결정(셋업–2R 부근)뿐, 후반 국면은 재생 모드(E199·E201, 규모는 사용자 수치)로 따로; lab 기계 시간이고 실서버 컨테이너 안 측정(E196 (b))은 따로; 워커 1개. 리플레이 없음.

종료 코드 0

```
_ts_ships_menu1_all_tier hard 80 decisions 3 30.57 31.83 60.04 60.07 41
```

지표

```json
{
 "seed": "quartet-e-88365",
 "decisions": 80,
 "seconds": 5400.0,
 "decision_timeout": 180.0,
 "guard": 30,
 "mode": "play",
 "cells": [
  {
   "factory": "guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier",
   "level": "hard",
   "stopped": "decisions",
   "error": null,
   "planned": null,
   "wall_total": 2446.075317923096,
   "decisions": 80,
   "last_round": 3,
   "mean": 30.573483438350376,
   "median": 31.82867434452055,
   "p90": 60.0370759050129,
   "max": 60.07407371897716,
   "over_guard": 41,
   "timed_out": 0,
   "time_capped": 12,
   "by_round": {
    "0": {
     "n": 11,
     "mean": 16.405843054452404,
     "max": 60.0370759050129
    },
    "1": {
     "n": 41,
     "mean": 40.46028016493145,
     "max": 60.07407371897716
    },
    "2": {
     "n": 24,
     "mean": 20.988665813167852,
     "max": 60.03936076606624
    },
    "3": {
     "n": 4,
     "mean": 25.703733797708992,
     "max": 39.82343334890902
    }
   },
   "rows": [
    {
     "wall": 29.323390008998103,
     "seconds": 29.265,
     "completed_comparisons": 6,
     "time_capped": false,
     "round": 0,
     "candidates": 6,
     "selected": "current-choice"
    },
    {
     "wall": 32.13005171297118,
     "seconds": 32.13,
     "completed_comparisons": 6,
     "time_capped": false,
     "round": 0,
     "candidates": 6,
     "selected": "root-1"
    },
    {
     "wall": 7.152518825954758,
     "seconds": 7.152,
     "completed_comparisons": 2,
     "time_capped": false,
     "round": 0,
     "candidates": 2,
     "selected": "current-choice"
    },
    {
     "wall": 23.85006969794631,
     "seconds": 23.85,
     "completed_comparisons": 5,
     "time_capped": false,
     "round": 0,
     "candidates": 5,
     "selected": "root-4"
    },
    {
     "wall": 27.879467353923246,
     "seconds": 27.879,
     "completed_comparisons": 5,
     "time_capped": false,
     "round": 0,
     "candidates": 5,
     "selected": "root-1"
    },
    {
     "wall": 60.0370759050129,
     "seconds": 60.037,
     "completed_comparisons": 12,
     "time_capped": true,
     "round": 0,
     "candidates": 13,
     "selected": "root-6"
    },
    {
     "wall": 0.08015656098723412,
     "seconds": 0.08,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 4,
     "selected": "local-baseline"
    },
    {
     "wall": 0.003760824096389115,
     "seconds": 0.003,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 7,
     "selected": "booster-tier-2"
    },
    {
     "wall": 0.002454673987813294,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 6,
     "selected": "booster-tier-12"
    },
    {
     "wall": 0.0024227950489148498,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 5,
     "selected": "booster-tier-13"
    },
    {
     "wall": 0.0029052400495
```

<sub>agentmaco · 커밋 24da3f7 · 2026-11-19T16:55:24+09:00 → 2026-11-19T17:36:10+09:00</sub>
