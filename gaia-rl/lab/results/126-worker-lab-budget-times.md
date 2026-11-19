# 126-worker-lab-budget-times — 완료

사용자 2026-11-19 「난이도 일단 정리하자. 나중에 결정하고 일단 전부 최선의 자원으로 최대한의 점수」(HANDOFF E202, 코덱스 이상 없음 → 진행): 실서버 워커가 새 교사로 전환됐을 때 쓰게 될 설정의 결정 시간 측정 — 교사 실력 판정 아님, 대국 A/B 아님. ai_worker.py(b8dbd7a)는 GAIA_AI_TEACHER가 새 공장 guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier일 때 쉬움·보통·어려움 전부 lab 예산(비교 4·수입 1회 내다보기·결정당 상한 60초)으로 두고, 환경 변수가 없으면 옛 공장·옛 수준 예산 그대로다. 이 큐: tools/worker_times.py 처음부터 두는 모드, 125와 같은 설계(Environment('quartet-e-88365') 셋업부터 워커가 고른 수로 80결정) — 새 공장 × 한 수준(hard 이름으로 요청; 새 공장에선 세 수준이 같은 값) = 1칸, GAIA_AI_PARALLEL=2(lab spec cap60-p2의 병렬 2), 벽시계 제한 5400초(최악 추정 84분 = 시작 자리 7 × 60초 + 시작 부스터 4 × 120초 + 69 × 60초보다 위 — 80결정 전에 끊기지 않게), 한 결정 180초 초과면 칸을 끊고 시간 초과로 기록. 시드 1개·한 번. 예상 ≈ 1–1.5시간. 볼 것: ① 결정 수(예정 80)·도달 라운드·멈춘 이유(decisions여야 함; seconds·decision timeout·error면 그대로 보고) ② 결정당 벽시계 평균·중앙·p90·최대, 라운드별 ③ 셋업 11결정의 합과 시작 자리·시작 부스터 각각의 시간 ④ rows에서 30·60·90·120초 초과 수 ⑤ 180초 시간 초과·오류 ⑥ 비교 완료 수와 time_capped 수(셋업에서 비교가 끝나는지 — 125 보통은 0개였음). 읽기(사전 등록): 통과·실패 판정 없음 — 서버 가드 GAIA_AI_TIMEOUT_SECS(기본 30초) 값의 근거를 내는 측정. 가드는 관측 최대보다 위여야 한다는 것까지만 적고 값은 사용자가 정함. 180초 시간 초과나 오류가 있으면 그 결정을 따로 보고하고 가드 제안을 미룸. 125의 새 공장 어려움 칸(상한 20초·병렬 없음: 셋업 평균 27.16초·최대 40.15초, 1R 평균 10.06초)과 나란히 적되 상한과 병렬이 함께 달라 차이를 한 원인으로 읽지 않음. 한계: 초반 80결정(1–2R 부근)뿐 — 후반 국면은 재생 모드(E199·E201, 규모는 사용자 수치)로 따로; lab 기계 시간이고 실서버 컨테이너 안 측정(E196 (b))은 따로; 워커 1개(방 여러 개가 동시에 돌 때의 시간은 안 봄). 리플레이 없음.

종료 코드 0

```
_ts_ships_menu1_all_tier hard 80 decisions 2 31.94 31.82 58.29 120.03 44
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
   "wall_total": 2555.6722005130723,
   "decisions": 80,
   "last_round": 2,
   "mean": 31.943894079916937,
   "median": 31.816435221000575,
   "p90": 58.288334318087436,
   "max": 120.02770590898581,
   "over_guard": 44,
   "timed_out": 0,
   "time_capped": 4,
   "by_round": {
    "0": {
     "n": 11,
     "mean": 35.165869770201176,
     "max": 120.02770590898581
    },
    "1": {
     "n": 38,
     "mean": 32.54992848203371,
     "max": 60.039561158046126
    },
    "2": {
     "n": 31,
     "mean": 30.05773150335036,
     "max": 60.05491082696244
    }
   },
   "rows": [
    {
     "wall": 29.04173450602684,
     "seconds": 28.982,
     "completed_comparisons": 6,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 31.955502018914558,
     "seconds": 31.955,
     "completed_comparisons": 6,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 7.093588680960238,
     "seconds": 7.093,
     "completed_comparisons": 2,
     "time_capped": false,
     "round": 0,
     "candidates": 2
    },
    {
     "wall": 23.778333876049146,
     "seconds": 23.778,
     "completed_comparisons": 5,
     "time_capped": false,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 27.87748312507756,
     "seconds": 27.877,
     "completed_comparisons": 5,
     "time_capped": false,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 60.036582518951036,
     "seconds": 60.036,
     "completed_comparisons": 12,
     "time_capped": true,
     "round": 0,
     "candidates": 13
    },
    {
     "wall": 0.08010000607464463,
     "seconds": 0.08,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 4
    },
    {
     "wall": 38.70037199603394,
     "seconds": 38.7,
     "completed_comparisons": 7,
     "time_capped": false,
     "round": 0,
     "candidates": 7
    },
    {
     "wall": 33.07951225806028,
     "seconds": 33.079,
     "completed_comparisons": 6,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 120.02770590898581,
     "seconds": 120.027,
     "completed_comparisons": 0,
     "time_capped": true,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 15.153652577078901,
     "seconds": 15.153,
     "completed_comparisons": 4,
     "time_capped": false,
     "round": 0,
     "candidates": 4
    },
    {
     "wall": 33.45795531698968,
     "seconds": 33.458,
     "completed_comparisons": 4,
     "time_capped": false,
     "round": 1,
     "candidates": 56
    },
    {
     "wall": 48.07764869707171,
     "seconds": 48.077,
     "completed_comparisons": 4,
     "time_capp
```

<sub>agentmaco · 커밋 bc9d0b9 · 2026-11-19T15:57:42+09:00 → 2026-11-19T16:40:18+09:00</sub>
