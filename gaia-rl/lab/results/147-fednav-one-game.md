# 147-fednav-one-game — 완료

사용자 11-28 「일단 다시 실험해봐」(HANDOFF E387 뒤, 이론 단계의 한 판 예외): 팩토리 ..._fedplan_balance_formedmine_fednav(fed_absorb · fed_prep · nav_good · good_by_cost · fed_group2, E383–E387) cap60-p2 비교 4, 4좌석 같은 교사, teacher_ab run --single 1판 6R 끝까지. 맵 · 종족은 146-fedplan-one-game과 같은 e362-20388 Firaks · Itars · BalTaks · Xenos라 146과 나란히 본다. 146 대비 차이는 부품 다섯(+ 그 사이 balance · formedmine)이라 변화를 한 부품의 효과로 읽지 않는다. 1판이라 강도 판단 아님. 판정 없음(관찰). 건강 기준: 종료 코드 0, 판 완주, 오류 · 타임아웃 0, 폴백 타임아웃 수와 최대 결정 시간(≈ 80초 이내). 볼 것(정리 턴): ① 좌석별 연방 수 · 라운드별 연방 시점 · 최종 VP · 1–3R 충전(참고), 146과 나란히 ② fed_group2 활성: 거리 2 묶음(파워 4–6)으로 federation-plan-* 가 후보로 나온 횟수 · 이긴 횟수 · 끝까지 실행된 계획 수 · 묶음 안 위성 수 ③ 서로 다른 연방에 쓸 건물이 한 묶음에 묶인 사례(사용자 E387 우려)가 줄었는지 리플레이로. 예상 ≈ 1–2시간, 제한 4시간. 리플레이 게시는 정리 턴 제안.

종료 코드 0

```
{"game": "runs/lab-147-fednav-one-game/pair-000/game-0-A02", "complete": false, "scores": null, "failure": "error"}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BalTaks | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 3 / 0 |
| Firaks | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 2 / 0 |
| Itars | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 0 / 3 |
| Xenos | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 0 / 1 |
| **전체 (좌석 평균)** | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 5 / 4 |

```

지표

```json
{
 "factions": {
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 4,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 3,
   "A_unsearched_comparisons": 105,
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
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 7,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 2,
   "A_unsearched_comparisons": 244,
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
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 0,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 8,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 3,
   "B_unsearched_comparisons": 501
  },
  "Xenos": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 0,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 7,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 1,
   "B_unsearched_comparisons": 187
  },
  "ALL": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 11,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 5,
   "A_unsearched_comparisons": 349,
   "B_decisions": 15,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 4,
   "B_unsearched_comparisons": 688
  }
 },
 "failures": {
  "error": 1
 },
 "games_planned": 1,
 "games_complete": 0,
 "pairs_complete": 0,
 "seeds_repeated": 0,
 "single": true,
 "pairs": []
}
```

<sub>agentmaco · 커밋 7e93256 · 2026-11-28T21:09:46+09:00 → 2026-11-28T21:16:29+09:00</sub>
