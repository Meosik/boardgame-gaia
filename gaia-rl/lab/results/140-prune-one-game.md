# 140-prune-one-game — 완료

코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E365 (ㄱ) — E362 사용자 「일단 딱 한판 돌려볼래? 무작위 시드에서 젤 잘 풀릴거 같은 종족 4개 골라서」의 합의된 한 판 예외(실험 보류 유지). 140a PICK seedarg e362-20388@factions=Firaks,Itars,BalTaks,Xenos, 4좌석 같은 교사 = 후보 줄이기 스펙 ships_menu1_all_tier_prune cap60-p2 비교 4, teacher_ab run --single 1판, 6R 끝까지. 판정 없음(관찰). 건강 기준: 종료 코드 0, 판 완주, 오류 · 타임아웃 0, 폴백 타임아웃 수와 결정 시간(최대 ≈ 80초 이내) 적기, 전 라운드 막힌 후보 선택 0(결정 로그 prune_blocked와 고른 수 대조). 볼 것(정리 턴): ① 좌석별 최종 VP · 연방 수 · 1–3R 충전(참고) ② prune_blocked 라운드 · 종류별 집계 — 연방 규칙 F1/F2/F5가 한 번이라도 걸리는지(140a · 140b는 0) ③ 후보 수 평균(140a 3R 1784 → 1509와 비교, 계산 절감률 아님). 한계: 1판 · 1맵, 비교 대상 없음 — 강도 판단 아님. E364 원칙(꼭 먹을 종족 타일 · 계획별 가이아 포기)은 미구현이라 이 판에 없음. 예상 ≈ 1–2시간, 제한 4시간. 리플레이 게시는 정리 턴 제안.

종료 코드 0

```
{"game": "runs/lab-140-prune-one-game/pair-000/game-0-A02", "complete": true, "scores": {"0": 86, "1": 96, "2": 83, "3": 110}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 41 / 0 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 50 / 0 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 44 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 86 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 91 / 130 |

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
   "A_decisions": 55,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 41,
   "A_unsearched_comparisons": 5580,
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
   "A_decisions": 75,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 50,
   "A_unsearched_comparisons": 6208,
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
   "B_unsearched_decisions": 44,
   "B_unsearched_comparisons": 6809
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
   "B_decisions": 98,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 86,
   "B_unsearched_comparisons": 24945
  },
  "ALL": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 130,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 91,
   "A_unsearched_comparisons": 11788,
   "B_decisions": 161,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 130,
   "B_unsearched_comparisons": 31754
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

<sub>agentmaco · 커밋 8f6fa17 · 2026-11-26T20:07:32+09:00 → 2026-11-26T21:29:38+09:00</sub>
