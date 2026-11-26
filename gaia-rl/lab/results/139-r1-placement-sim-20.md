# 139-r1-placement-sim-20 — 완료

사용자(2026-11-26 「(나) ㄱㄱ」 — 초반 땅도 AI 판단으로 찍어 달라, 이 실행에 한해 실험 보류 해제): 138과 같은 20개 맵(같은 시드를 일부러 재사용 — 표시 시트의 맵을 맞추려고)에서 같은 교사(ships_menu1_all_tier cap60-p2, 비교 4, 4좌석 같은 교사)가 1라운드 끝까지 둔다(--stop-round 1 = 2라운드 시작 때 멈춤). 판정 없음(관찰). 쓰임: 표시 시트(mark_sheet)에 AI 시작 광산 + 1라운드에 새로 지은 건물(= AI의 초반 땅)을 미리 찍고 사용자는 이상한 것만 고침. 정리 턴: 판마다 좌석별 1R 새 광산 수 · 자리(QIC · 테라포밍 단계)만 적고, 138 배치와 시작 광산이 같은 판 수를 센다(탐색이라 달라질 수 있음 — 다르면 시트는 이번 판 기준). 예상 ≈ 2–4시간(실측 없음, 138 셋업만 26분), 제한 8시간. 리플레이는 139r에서 게시.

종료 코드 0

```
{"game": "runs/lab-139-r1-placement-sim-20/pair-002/game-0-A03", "complete": true, "scores": {"0": 8, "1": 2, "2": 3, "3": 0}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-000/game-0-A02", "complete": true, "scores": {"0": 4, "1": 5, "2": 0, "3": 0}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-004/game-0-A01", "complete": true, "scores": {"0": 21, "1": 7, "2": 9, "3": 7}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-005/game-0-A03", "complete": true, "scores": {"0": 10, "1": 9, "2": 4, "3": 11}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-007/game-0-A01", "complete": true, "scores": {"0": 8, "1": 9, "2": 3, "3": 4}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-006/game-0-A02", "complete": true, "scores": {"0": 11, "1": 9, "2": 7, "3": 7}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-008/game-0-A03", "complete": true, "scores": {"0": 2, "1": 7, "2": 2, "3": 4}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-009/game-0-A02", "complete": true, "scores": {"0": 3, "1": 2, "2": 8, "3": 1}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-011/game-0-A03", "complete": true, "scores": {"0": 0, "1": 8, "2": 4, "3": 12}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-012/game-0-A02", "complete": true, "scores": {"0": 13, "1": 3, "2": 13, "3": 7}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-010/game-0-A01", "complete": true, "scores": {"0": 13, "1": 13, "2": 6, "3": 10}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-014/game-0-A03", "complete": true, "scores": {"0": 14, "1": 18, "2": 14, "3": 7}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-015/game-0-A02", "complete": true, "scores": {"0": 15, "1": 11, "2": 0, "3": 16}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-016/game-0-A01", "complete": true, "scores": {"0": 14, "1": 14, "2": 3, "3": 16}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-013/game-0-A01", "complete": true, "scores": {"0": 10, "1": 11, "2": 9, "3": 20}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-017/game-0-A03", "complete": true, "scores": {"0": 12, "1": 7, "2": 3, "3": 6}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-018/game-0-A02", "complete": true, "scores": {"0": 9, "1": 10, "2": 7, "3": 4}, "failure": null}
{"game": "runs/lab-139-r1-placement-sim-20/pair-019/game-0-A01", "complete": true, "scores": {"0": 4, "1": 2, "2": 2, "3": 4}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 7 / 34 |
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 19 / 25 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 42 / 0 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 25 / 8 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 12 / 13 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 34 / 9 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 7 / 29 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 9 / 29 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 12 / 27 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 18 / 17 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 24 / 7 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 5 / 20 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 10 / 38 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 7 / 22 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 21 / 18 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 40 / 21 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 13 / 18 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 48 / 29 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 353 / 364 |

```

지표

```json
{
 "factions": {
  "Ambas": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 14,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 7,
   "A_unsearched_comparisons": 908,
   "B_decisions": 59,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 34,
   "B_unsearched_comparisons": 5544
  },
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 33,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 19,
   "A_unsearched_comparisons": 1734,
   "B_decisions": 45,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 25,
   "B_unsearched_comparisons": 2180
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 59,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 42,
   "A_unsearched_comparisons": 5469,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Darkanians": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 44,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 25,
   "A_unsearched_comparisons": 3301,
   "B_decisions": 13,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 8,
   "B_unsearched_comparisons": 1312
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 22,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 12,
   "A_unsearched_comparisons": 1975,
   "B_decisions": 27,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 13,
   "B_unsearched_comparisons": 1775
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 51,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 34,
   "A_unsearched_comparisons": 4847,
   "B_decisions": 15,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 9,
   "B_unsearched_comparisons": 1953
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 9,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 7,
   "A_unsearched_comparisons": 754,
   "B_decisions": 40,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 29,
   "B_unsearched_comparison
```

<sub>agentmaco · 커밋 adafa33 · 2026-11-26T15:25:52+09:00 → 2026-11-26T17:34:10+09:00</sub>
