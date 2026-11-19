# 127-worker-new-teacher-hard-times — 완료

사용자 2026-11-19 「난이도 관련 코드 하나도 건들지마. 최상의 어려움 교사도 지금 나보다 못하는데. 실시간으로 나랑 겨루는 교사 셋 만들어와」(HANDOFF E207): 난이도 표를 원래 값으로 되돌림(f9f9deb) — 실서버 워커가 GAIA_AI_TEACHER로 새 공장 guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier를 고르고 어려움 수준(비교 4·수입 1회 내다보기·상한 20초 = 실서버와 같은 값)으로 둘 때의 결정 시간 측정 — 교사 실력 판정 아님, 대국 A/B 아님. 125의 새 공장 어려움 칸(420초 제한으로 25결정, 30초 초과 4건 = 시작 부스터 4결정 40초)은 워커 결함(E204, 9170cd7에서 고침)의 값이라 다시 잼. 이 큐: tools/worker_times.py 처음부터 두는 모드, Environment('quartet-e-88365') 셋업부터 워커가 고른 수로 80결정, 새 공장 × hard 1칸, GAIA_AI_PARALLEL=0(compose 기본값), 벽시계 제한 2400초(최악 80 × 20초 = 1600초보다 위), 한 결정 180초 초과면 칸을 끊고 시간 초과로 기록. 시드 1개·한 번(125·126과 같은 시드 — 같은 설계의 재측정). 예상 ≈ 20–30분. 볼 것: ① 결정 수(예정 80)·도달 라운드·멈춘 이유(decisions여야 함)·오류·180초 시간 초과 ② 시작 부스터 4결정이 넷 다 selected가 booster-tier-N·1초 미만·비교 0인지 ③ 결정당 벽시계 평균·중앙·p90·최대, 라운드별, 셋업 합 ④ rows에서 30초 초과 수(서버 가드 GAIA_AI_TIMEOUT_SECS 기본 30초)·20.5초 초과 수·time_capped 수 ⑤ 비교 완료 수 분포(상한 20초·병렬 없음에서 비교 4개 중 몇 개가 끝나는지; 탐색했는데 0개로 끊긴 결정 수 포함). 읽기(사전 등록): 30초 초과 0·오류 0·180초 시간 초과 0이고 ②가 확인되면 「초반 80결정에서는 난이도 코드·가드 변경 없이 GAIA_AI_TEACHER 한 줄로 전환 가능」; 30초 초과가 있으면 그 결정을 따로 보고하고 전환 제안을 미룸(선택지·수치는 사용자). 비교 완료 수는 판정이 아니라 참고(이 설정이 lab의 cap60-p2 교사보다 얼마나 덜 찾는지). 한계: 초반 80결정(셋업–2R 부근)뿐 — 후반 국면은 재생 모드(E199·E201, 규모는 사용자 수치)로 따로; lab 기계 시간이고 실서버 컨테이너 안 측정(E196 (b))은 따로; 워커 1개. 리플레이 없음.

종료 코드 0

```
_ts_ships_menu1_all_tier hard 80 decisions 2 13.25 20.04 20.35 20.53 0
```

지표

```json
{
 "seed": "quartet-e-88365",
 "decisions": 80,
 "seconds": 2400.0,
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
   "wall_total": 1060.461692990968,
   "decisions": 80,
   "last_round": 2,
   "mean": 13.253825145409792,
   "median": 20.036175615503453,
   "p90": 20.349547772086225,
   "max": 20.528797856066376,
   "over_guard": 0,
   "timed_out": 0,
   "time_capped": 51,
   "by_round": {
    "0": {
     "n": 11,
     "mean": 12.57115722797938,
     "max": 20.096891073975712
    },
    "1": {
     "n": 56,
     "mean": 12.975593555643822,
     "max": 20.528797856066376
    },
    "2": {
     "n": 13,
     "mean": 15.030003308381241,
     "max": 20.386522824992426
    }
   },
   "rows": [
    {
     "wall": 20.096891073975712,
     "seconds": 20.041,
     "completed_comparisons": 1,
     "time_capped": true,
     "round": 0,
     "candidates": 6,
     "selected": "current-choice"
    },
    {
     "wall": 20.013101333053783,
     "seconds": 20.013,
     "completed_comparisons": 1,
     "time_capped": true,
     "round": 0,
     "candidates": 6,
     "selected": "current-choice"
    },
    {
     "wall": 17.946988543961197,
     "seconds": 17.947,
     "completed_comparisons": 2,
     "time_capped": false,
     "round": 0,
     "candidates": 2,
     "selected": "root-0"
    },
    {
     "wall": 20.081147763994522,
     "seconds": 20.081,
     "completed_comparisons": 2,
     "time_capped": true,
     "round": 0,
     "candidates": 5,
     "selected": "current-choice"
    },
    {
     "wall": 20.07386097498238,
     "seconds": 20.074,
     "completed_comparisons": 2,
     "time_capped": true,
     "round": 0,
     "candidates": 5,
     "selected": "root-0"
    },
    {
     "wall": 20.0314445910044,
     "seconds": 20.031,
     "completed_comparisons": 3,
     "time_capped": true,
     "round": 0,
     "candidates": 13,
     "selected": "current-choice"
    },
    {
     "wall": 20.029838919988833,
     "seconds": 20.03,
     "completed_comparisons": 2,
     "time_capped": true,
     "round": 0,
     "candidates": 4,
     "selected": "current-choice"
    },
    {
     "wall": 0.002745418925769627,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 7,
     "selected": "booster-tier-2"
    },
    {
     "wall": 0.0022545689716935158,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 6,
     "selected": "booster-tier-12"
    },
    {
     "wall": 0.0023402299266308546,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 5,
     "selected": "booster-tier-13"
    },
    {
     "wall": 0.0021160889882594347,
     "seconds": 0.002,
     "completed_comparisons": 0,
     "t
```

<sub>agentmaco · 커밋 bb39ab4 · 2026-11-19T17:41:15+09:00 → 2026-11-19T17:58:56+09:00</sub>
