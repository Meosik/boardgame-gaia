# 146-fedplan-one-game — 완료

사용자 11-27 「한번 해봐」(HANDOFF E372 (ㄱ), 이론 단계 보류의 한 판 예외): 연방 사전 계획 부품 fed_plan(E371)을 켠 팩토리 ..._tier_prune_fedplan cap60-p2 비교 4, 4좌석 같은 교사, teacher_ab run --single 1판 6R 끝까지. 맵 · 종족은 140-prune-one-game과 같은 e362-20388 Firaks · Itars · BalTaks · Xenos라 140(8f6fa17 실행본, fed_plan 없음)과 같은 맵 · 종족으로 나란히 본다. 단 140 뒤 기본 prune 팩토리에도 power_first가 더해져(teacher_patches.py:6330–6331) 차이는 fed_plan 하나가 아니다 — 140 대비 변화를 연방 계획만의 효과로 읽지 않는다(토론 1/1). 1판이라 강도 판단 아님. 판정 없음(관찰). 건강 기준: 종료 코드 0, 판 완주, 오류 · 타임아웃 0, 폴백 타임아웃 수와 최대 결정 시간(≈ 80초 이내). 볼 것(정리 턴): ① 좌석별 연방 수 · 라운드별 연방 시점 · 최종 VP · 1–3R 충전(참고), 140과 나란히 ② 활성: 결정 로그에서 federation-plan-{mines,institute,station}(-upfirst 포함) · ts3 계획이 후보로 나온 횟수 · 이긴 횟수 · _plans로 기억된 계획이 끝까지 실행됐는지 ③ 예산 검사(E86)로 걸러진 연방 계획 수. 예상 ≈ 1–2시간, 제한 4시간. 리플레이 게시는 정리 턴 제안.

종료 코드 0

```
{"game": "runs/lab-146-fedplan-one-game/pair-000/game-0-A02", "complete": true, "scores": {"0": 88, "1": 78, "2": 109, "3": 89}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 55 / 0 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 53 / 0 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 41 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 62 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 108 / 103 |

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
   "A_decisions": 78,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 55,
   "A_unsearched_comparisons": 6506,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 73,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 53,
   "A_unsearched_comparisons": 5399,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Itars": {
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
   "B_decisions": 63,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 41,
   "B_unsearched_comparisons": 4523
  },
  "Xenos": {
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
   "B_decisions": 77,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 62,
   "B_unsearched_comparisons": 8501
  },
  "ALL": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 151,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 108,
   "A_unsearched_comparisons": 11905,
   "B_decisions": 140,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 103,
   "B_unsearched_comparisons": 13024
  }
 },
 "failures": {},
 "games_planned": 1,
 "games_complete": 1,
 "pairs_complete": 0,
 "seeds_repeated": 0,
 "single": true,
 "pairs": []
}
```

<sub>agentmaco · 커밋 905b91a · 2026-11-27T02:51:34+09:00 → 2026-11-27T03:52:54+09:00</sub>
