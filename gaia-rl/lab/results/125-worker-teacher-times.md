# 125-worker-teacher-times — 완료

사용자 2026-11-19 「바꾸고 한번에 배포하자」(HANDOFF E194 (ㄱ), E195): 실서버 AI 워커의 교사를 lab 현재 교사로 바꾸기 전의 시간 측정 — 교사 실력 판정 아님, 대국 A/B 아님. E194에서 공장을 guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier로 바꾸니 워커 테스트의 쉬움 수준 40결정이 7분 안에 안 끝났고, 옛 공장의 같은 시간은 안 쟀음. tools/worker_times.py: 공장 2개(옛 = guide_r1_charge3_lf_more_vm_lf_ts_ships, 새 = guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier; ai_worker.py가 GAIA_AI_TEACHER로 고르고 기본값은 옛 공장) × 수준 3개(easy 비교 0·상한 없음, normal 비교 2·5초, hard 비교 4·20초 — ai_worker.py LEVELS 그대로) = 6칸. 칸마다 워커 하나를 띄워 Environment('quartet-e-88365')의 초기 배치부터 워커가 고른 수로 진행, 80결정 또는 벽시계 420초에서 멈춤, 한 결정이 180초를 넘으면 그 칸을 끊고 시간 초과로 기록. 칸마다 진행이 달라 같은 국면 비교가 아님(시간 분포만 봄). 시드 1개·한 번. 예상 ≈ 45분(최대 60분). 볼 것(칸별): ① 결정 수·도달 라운드·멈춘 이유 ② 결정당 벽시계 평균·중앙·p90·최대 ③ 30초 초과 수(서버 가드 GAIA_AI_TIMEOUT_SECS 기본값 — 넘으면 실서버는 대체 수를 둠) ④ 180초 시간 초과·오류 ⑤ normal·hard의 time_capped 수. 읽기(사전 등록): 새 공장의 칸에서 30초 초과 0·시간 초과 0·오류 0이면 그 수준은 상한 변경 없이 교체 가능; 30초 초과가 있으면 그 수준은 그대로는 교체 불가 — 선택지(쉬움 수준에 상한 추가 / 가드 올리기 / 그 수준만 옛 교사 유지)와 수치는 사용자. 옛 공장의 칸은 비교 기준(지금 실서버가 내는 시간). 한계: 초반 80결정(1–2R 부근)뿐이라 후반 라운드의 긴 결정(lab 6R 수집의 검색 전 구간 60–138초, 12/42,148행)은 안 잡힘; lab 기계에서 잰 시간이고 실서버 기계와 다름; 워커 1개·GAIA_AI_PARALLEL 없음. 리플레이 없음.

종료 코드 0

```
3_lf_more_vm_lf_ts_ships easy 80 decisions 2 0.06 0.05 0.13 0.26 0
3_lf_more_vm_lf_ts_ships normal 80 decisions 2 3.18 5.01 5.19 6.13 0
3_lf_more_vm_lf_ts_ships hard 42 seconds 1 10.05 10.07 20.09 20.19 0
_ts_ships_menu1_all_tier easy 8 seconds 0 53.06 51.72 128.58 128.58 6
_ts_ships_menu1_all_tier normal 80 decisions 2 3.76 5.05 5.56 10.17 0
_ts_ships_menu1_all_tier hard 25 seconds 1 17.59 20.04 40.07 40.15 4
```

지표

```json
{
 "seed": "quartet-e-88365",
 "decisions": 80,
 "seconds": 420,
 "decision_timeout": 180,
 "guard": 30,
 "cells": [
  {
   "factory": "guide_r1_charge3_lf_more_vm_lf_ts_ships",
   "level": "easy",
   "stopped": "decisions",
   "error": null,
   "wall_total": 5.29231928603258,
   "decisions": 80,
   "last_round": 2,
   "mean": 0.0643468989568646,
   "median": 0.0453069320647046,
   "p90": 0.12877051904797554,
   "max": 0.2642957589123398,
   "over_guard": 0,
   "timed_out": 0,
   "time_capped": 0,
   "by_round": {
    "0": {
     "n": 11,
     "mean": 0.04461543399586596,
     "max": 0.14894834998995066
    },
    "1": {
     "n": 51,
     "mean": 0.06574820045281347,
     "max": 0.22126084403134882
    },
    "2": {
     "n": 18,
     "mean": 0.07243466219450864,
     "max": 0.2642957589123398
    }
   },
   "rows": [
    {
     "wall": 0.14894834998995066,
     "seconds": 0.064,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 0.03441259206738323,
     "seconds": 0.034,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 0.03235021303407848,
     "seconds": 0.032,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 2
    },
    {
     "wall": 0.031581992050632834,
     "seconds": 0.031,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 0.03573606500867754,
     "seconds": 0.035,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 0.042688144952990115,
     "seconds": 0.042,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 13
    },
    {
     "wall": 0.031234530033543706,
     "seconds": 0.031,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 4
    },
    {
     "wall": 0.03639488003682345,
     "seconds": 0.036,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 7
    },
    {
     "wall": 0.03588793892413378,
     "seconds": 0.035,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 6
    },
    {
     "wall": 0.031878497917205095,
     "seconds": 0.032,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 5
    },
    {
     "wall": 0.029656569939106703,
     "seconds": 0.029,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 0,
     "candidates": 4
    },
    {
     "wall": 0.08426198991946876,
     "seconds": 0.084,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 1,
     "candidates": 50
    },
    {
     "wall": 0.029189124004915357,
     "seconds": 0.029,
     "completed_comparisons": 0,
     "time_capped": false,
     "round": 1,
     
```

<sub>agentmaco · 커밋 d1d6757 · 2026-11-19T12:11:25+09:00 → 2026-11-19T12:42:12+09:00</sub>
