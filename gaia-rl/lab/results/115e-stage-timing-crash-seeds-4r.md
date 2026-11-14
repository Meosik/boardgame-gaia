# 115e-stage-timing-crash-seeds-4r — 완료

사용자 상시 지시(2026-11-13 「codex 이상 없으면 추천대로 진행해」) + 코덱스 검수 이상 없음(HANDOFF E142 (ㄱ), E143): 115d에서 pair-001(quartet-d-75189@order=1,2,0,3, 좌석 A01) step 111 타클론 결정이 110.65초·완료 비교 0·fallback_timeout 거짓이었던 것(114 pair-037 크래시와 같은 step 번호·좌석, 원인 미확정)의 느린 구간을 재는 실행. 115d와 같은 명령(4좌석 같은 교사 ships_menu1_all_tier cap60-p2, 비교 4, --single, GAIA_FEDERATION_ONE_ROUTE=1을 명령 env 앞머리에)에 --stop-round 3(4R 시작에서 종료; 114에서 step 111은 3R)만 추가. 관찰 대상은 quartet-d 시드 1판이고, quartet-b 시드는 115d와 같은 조건을 맞추려고 같이 돎(--single 좌석 분할은 시드 순서로 정해져 d 시드가 A01이 되려면 둘째여야 함 + 두 판 동시 실행 부하; 시드 재사용은 이 재실행의 목적). 새 기록(계측 커밋 632b63f): 결정 로그 행마다 round·digest·timing{choose = 워커 teacher.choose 전체, search = budget_teacher._choose, cap, published_at = 결과 발표 시각들(첫째가 root 순위), stages{bind_check, root_rank, planned_tasks, prefetch, drop_unfinished, parallel_search, search_call, root_result, state_check}, time_capped, budget_stopped, expired_before_search, audit_fresh}. 판정 없음(n=2, 같은 교사). 사전 등록 읽기: ① 계측 확인 — 2/2판 4R 시작까지 완료·failures 없음, 모든 행에 round·digest·timing이 있고 audit_fresh 참인 행에는 stages가 있음(아니면 계측 수정) ② 느린 결정 = 100초 이상, 또는 30초 이상이면서 완료 비교 0인 결정. 나오면 그 행의 round·digest와 함께 seconds − choose(runner·IPC), choose − search(choose 래퍼), stages·published_at으로 가장 긴 구간을 지목 → 그 구간이 다음 수정 대상(그 결정의 구간일 뿐, 114 pair-037 원인의 확정은 아님) ③ 느린 결정이 안 나오면(시간 예산 탐색이라 다른 줄로 갈 수 있음) 원인 미확정 그대로 — 이 실행은 계측이 동작한다는 것만 보이고, 재현 실패를 해결로 읽지 않음. 보고만: 최대 결정 시간, 60초 이상 결정 수와 그 구간 분포, 폴백 수, d 시드가 115d와 몇 번째 결정까지 같은 수인지. 플래그 켬 자료라 114(끔) BC 자료와 섞지 않음. 예상 35–45분(115d에서 d 시드 step 111까지 30분).

종료 코드 0

```
{"game": "runs/lab-115e-stage-timing-crash-seeds-4r/pair-000/game-0-A02", "complete": true, "scores": {"0": 23, "1": 4, "2": 21, "3": 5}, "failure": null}
{"game": "runs/lab-115e-stage-timing-crash-seeds-4r/pair-001/game-0-A01", "complete": true, "scores": {"0": 16, "1": 12, "2": 22, "3": 17}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 24 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 34 / 0 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 29 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 22 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 20 / 0 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 18 / 0 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 31 / 0 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 27 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 103 / 102 |

```

지표

```json
{
 "factions": {
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 0,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 35,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 24,
   "B_unsearched_comparisons": 2175
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 44,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 34,
   "A_unsearched_comparisons": 4565,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 0,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 40,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 29,
   "B_unsearched_comparisons": 6095
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 0,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 31,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 22,
   "B_unsearched_comparisons": 2504
  },
  "Itars": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 24,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 20,
   "A_unsearched_comparisons": 2532,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Moweyds": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 22,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 18,
   "A_unsearched_comparisons": 3693,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Taklons": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 44,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 31,
   "A_unsearched_comparisons": 8991,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Tinkeroi
```

<sub>agentmaco · 커밋 1bd83d5 · 2026-11-14T16:56:09+09:00 → 2026-11-14T17:29:24+09:00</sub>
