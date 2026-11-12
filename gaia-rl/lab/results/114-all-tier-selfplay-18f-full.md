# 114-all-tier-selfplay-18f-full — 완료

사용자 2026-11-12 「ㄱ 대로 해」(HANDOFF E132; 토론 1/1: A = B 좌석 교대는 같은 배치를 두 번 둠): 현재 엔진 6R 자기대국 수집 — BC·PPO 초기값 자료. teacher_ab run --single(8d20dc3, 시드당 1판), 4좌석 같은 교사 ships_menu1_all_tier, 18종족: 쿼텟 geo 2 · a 10 · b 10 · c 9 · d 9 · e 8 = 새 시드 48개(@order = faction_strength.py 현재 강도식) × 1판 = 48판, 6R 끝까지(stop-round 없음), cap60-p2, 비교 4. run_ab와 같은 환경을 env로 줌(GAIA_ENGINE_FIXES_2=1, PYTHONPATH python·baseline-teacher·tools). 판정 없음. 예상 ≈ 1–1.5일(102 기준 24판 14.5시간). 볼 것: ① 48/48판 정상 완료(results.json games_complete, failures, 폴백 타임아웃; 시작 직후 실패면 환경·옵션 문제) ② 결정 로그 전 행에 chosen 기록 ③ 완료 뒤 봇 턴에서 bc_dataset.py index → stats: 이 실행 판의 엄격 재생 통과 수·6R 판 수·결정 수·엔진 빌드 id ④ 참고: 좌석 평균 최종 VP, 좌석당 연방 수(federation_chances.py)·남은 연방 토큰(endgame_tech_counts.py). BC 학습·검증은 시드 단위로 나눔. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-031/game-0-A01", "complete": true, "scores": {"0": 74, "1": 114, "2": 94, "3": 103}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-032/game-0-A03", "complete": true, "scores": {"0": 88, "1": 93, "2": 140, "3": 91}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-030/game-0-A02", "complete": true, "scores": {"0": 133, "1": 99, "2": 104, "3": 110}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-033/game-0-A02", "complete": true, "scores": {"0": 101, "1": 77, "2": 103, "3": 94}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-034/game-0-A01", "complete": true, "scores": {"0": 99, "1": 95, "2": 107, "3": 84}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-036/game-0-A02", "complete": true, "scores": {"0": 78, "1": 105, "2": 90, "3": 141}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-035/game-0-A03", "complete": true, "scores": {"0": 107, "1": 80, "2": 100, "3": 141}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-037/game-0-A01", "complete": false, "scores": null, "failure": "error"}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-040/game-0-A01", "complete": true, "scores": {"0": 123, "1": 114, "2": 73, "3": 93}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-038/game-0-A03", "complete": true, "scores": {"0": 97, "1": 121, "2": 104, "3": 121}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-039/game-0-A02", "complete": true, "scores": {"0": 121, "1": 104, "2": 108, "3": 121}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-041/game-0-A03", "complete": true, "scores": {"0": 104, "1": 122, "2": 112, "3": 116}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-043/game-0-A01", "complete": true, "scores": {"0": 107, "1": 65, "2": 101, "3": 105}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-044/game-0-A03", "complete": true, "scores": {"0": 114, "1": 84, "2": 76, "3": 131}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-042/game-0-A02", "complete": true, "scores": {"0": 123, "1": 83, "2": 129, "3": 108}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-045/game-0-A02", "complete": true, "scores": {"0": 93, "1": 121, "2": 146, "3": 109}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-046/game-0-A01", "complete": true, "scores": {"0": 112, "1": 115, "2": 126, "3": 86}, "failure": null}
{"game": "runs/lab-114-all-tier-selfplay-18f-full/pair-047/game-0-A03", "complete": true, "scores": {"0": 107, "1": 93, "2": 122, "3": 107}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 399 / 118 |
| BalTaks | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 225 / 333 |
| Bescods | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 379 / 162 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 227 / 212 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 101 / 454 |
| Geodens | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 140 / 365 |
| Gleens | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 298 / 231 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 146 / 326 |
| Itars | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 180 / 315 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 409 / 241 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 463 / 90 |
| Moweyds | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 180 / 230 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 221 / 330 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 298 / 160 |
| Taklons | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 300 / 385 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 472 / 602 |
| Tinkeroids | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 376 / 143 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 648 / 596 |
| **전체 (좌석 평균)** | 0 | — | — | 2 | 0 | 0 / 0 | 0 / 0 | 5462 / 5293 |

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
   "A_decisions": 567,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 399,
   "A_unsearched_comparisons": 50051,
   "B_decisions": 166,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 118,
   "B_unsearched_comparisons": 17407
  },
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 293,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 225,
   "A_unsearched_comparisons": 23296,
   "B_decisions": 437,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 333,
   "B_unsearched_comparisons": 41670
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 486,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 379,
   "A_unsearched_comparisons": 57178,
   "B_decisions": 220,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 162,
   "B_unsearched_comparisons": 22862
  },
  "Darkanians": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 279,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 227,
   "A_unsearched_comparisons": 26149,
   "B_decisions": 278,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 212,
   "B_unsearched_comparisons": 30188
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 145,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 101,
   "A_unsearched_comparisons": 14160,
   "B_decisions": 597,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 454,
   "B_unsearched_comparisons": 71139
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 187,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 140,
   "A_unsearched_comparisons": 19724,
   "B_decisions": 490,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 365,
   "B_unsearched_comparisons": 63858
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 372,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 298,
   "A_unsearched_comparisons": 35791,
   "B_decisions": 284,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_un
```

<sub>agentmaco · 커밋 630c068 · 2026-11-12T15:31:32+09:00 → 2026-11-13T07:14:18+09:00</sub>
