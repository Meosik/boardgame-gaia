# 119-all-tier-selfplay-18f-full-more — 완료

사용자 2026-11-16 「추천 대로 해」(HANDOFF E156 (ㄷ) 보류 해제, E157): 114와 같은 설정으로 6R 자기대국 추가 수집 — BC·PPO 초기값 자료를 46판에서 약 94판으로. teacher_ab run --single(시드당 1판), 4좌석 같은 교사 ships_menu1_all_tier cap60-p2 비교 4, 18종족: 쿼텟 geo 2 · a 10 · b 10 · c 9 · d 9 · e 8 = 48판(114와 같은 배분), 6R 끝까지(stop-round 없음). 시드 = 새 시드 46개 + 114에서 크래시로 빠진 두 시드(quartet-b-68171, quartet-d-75189; 114 자료에 없음, 7cb307b 뒤라 검색 전 상한 초과는 root 1위·폴백으로 처리), @order = faction_strength.py 현재 강도식(두 재실행 시드의 순서는 114와 같음). 환경은 114와 같음(GAIA_ENGINE_FIXES_2=1, PYTHONPATH python·baseline-teacher·tools, GAIA_FEDERATION_ONE_ROUTE 끔). 114 이후 교사 쪽 변경: 7cb307b(검색 전 상한 초과 시 root 1위·폴백 계수), 632b63f·f683e19(결정 로그 round·digest·timing), 엔진 966e9ea(플래그 끔이면 후보 목록 불변 — 115c). 판정 없음. 예상 ≈ 16시간(114: 48판 15시간 43분). 볼 것: ① 48/48판 정상 완료(results.json games_complete·failures, 타임아웃, 폴백 타임아웃 수; 두 재실행 시드가 완주하는지) ② 결정 로그 전 행에 chosen 기록 ③ 최대 결정 시간·60초 초과 비율·100초 초과 수(115d의 110초 경로가 플래그 끔에서 나오는지) ④ 완료 뒤 봇 턴에서 bc_dataset.py index → stats: 이 실행 판의 엄격 재생 통과 수·6R 판 수·결정 수·엔진 빌드 id; 114 46판과 합쳐 쓰려면 114 판이 같은 빌드에서 엄격 재생되는지도 확인 ⑤ 참고: 좌석 평균 최종 VP, 좌석당 연방 수(federation_chances.py)·안 뒤집은 토큰(endgame_tech_counts.py) — 114 값 100.1·1.50·0.52와 비교. 그 뒤(정리 턴 제안): 114+119를 인코딩 4로 export해 117·118과 같은 판 단위 교차 검증으로 자료량 효과를 다시 잼. BC 학습·검증은 시드 단위로 나눔. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-031/game-0-A01", "complete": true, "scores": {"0": 137, "1": 64, "2": 88, "3": 79}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-032/game-0-A03", "complete": true, "scores": {"0": 122, "1": 85, "2": 85, "3": 97}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-029/game-0-A03", "complete": true, "scores": {"0": 96, "1": 89, "2": 103, "3": 82}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-033/game-0-A02", "complete": true, "scores": {"0": 100, "1": 135, "2": 92, "3": 107}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-034/game-0-A01", "complete": true, "scores": {"0": 107, "1": 111, "2": 93, "3": 70}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-035/game-0-A03", "complete": true, "scores": {"0": 106, "1": 103, "2": 99, "3": 121}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-036/game-0-A02", "complete": true, "scores": {"0": 85, "1": 113, "2": 114, "3": 95}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-039/game-0-A02", "complete": true, "scores": {"0": 81, "1": 130, "2": 113, "3": 63}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-038/game-0-A03", "complete": true, "scores": {"0": 104, "1": 80, "2": 144, "3": 95}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-037/game-0-A01", "complete": true, "scores": {"0": 78, "1": 108, "2": 107, "3": 101}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-040/game-0-A01", "complete": true, "scores": {"0": 147, "1": 106, "2": 96, "3": 145}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-042/game-0-A02", "complete": true, "scores": {"0": 87, "1": 108, "2": 75, "3": 105}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-041/game-0-A03", "complete": true, "scores": {"0": 82, "1": 124, "2": 118, "3": 106}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-043/game-0-A01", "complete": true, "scores": {"0": 82, "1": 113, "2": 107, "3": 81}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-044/game-0-A03", "complete": true, "scores": {"0": 167, "1": 114, "2": 83, "3": 88}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-045/game-0-A02", "complete": true, "scores": {"0": 112, "1": 123, "2": 114, "3": 69}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-047/game-0-A03", "complete": true, "scores": {"0": 113, "1": 136, "2": 85, "3": 114}, "failure": null}
{"game": "runs/lab-119-all-tier-selfplay-18f-full-more/pair-046/game-0-A01", "complete": true, "scores": {"0": 122, "1": 137, "2": 112, "3": 92}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 1 | 0 / 0 | 266 / 217 |
| BalTaks | 0 | — | — | 1 | 0 | 1 / 0 | 0 / 0 | 207 / 253 |
| Bescods | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 238 / 284 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 261 / 150 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 242 / 354 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 308 / 250 |
| Gleens | 0 | — | — | 1 | 0 | 4 / 0 | 0 / 0 | 233 / 232 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 275 / 220 |
| Itars | 0 | — | — | 1 | 0 | 0 / 0 | 0 / 0 | 233 / 205 |
| Ivits | 0 | — | — | 0 | 0 | 1 / 0 | 0 / 0 | 477 / 180 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 302 / 290 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 318 / 119 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 228 / 351 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 102 / 361 |
| Taklons | 0 | — | — | 0 | 0 | 1 / 0 | 0 / 0 | 404 / 234 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 528 / 554 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 121 / 418 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 1 | 0 / 0 | 551 / 679 |
| **전체 (좌석 평균)** | 0 | — | — | 1 | 0 | 7 / 2 | 0 / 0 | 5294 / 5351 |

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
   "A_decisions": 375,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 266,
   "A_unsearched_comparisons": 35528,
   "B_decisions": 326,
   "B_fallback_timeouts": 1,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 217,
   "B_unsearched_comparisons": 29934
  },
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 252,
   "A_fallback_timeouts": 1,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 207,
   "A_unsearched_comparisons": 21912,
   "B_decisions": 331,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 253,
   "B_unsearched_comparisons": 28586
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 306,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 238,
   "A_unsearched_comparisons": 37021,
   "B_decisions": 363,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 284,
   "B_unsearched_comparisons": 43113
  },
  "Darkanians": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 342,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 261,
   "A_unsearched_comparisons": 29592,
   "B_decisions": 199,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 150,
   "B_unsearched_comparisons": 20695
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 307,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 242,
   "A_unsearched_comparisons": 30433,
   "B_decisions": 464,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 354,
   "B_unsearched_comparisons": 65430
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 393,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 308,
   "A_unsearched_comparisons": 52187,
   "B_decisions": 304,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 250,
   "B_unsearched_comparisons": 49213
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 1,
   "timeout_games": 0,
   "A_decisions": 300,
   "A_fallback_timeouts": 4,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 233,
   "A_unsearched_comparisons": 29085,
   "B_decisions": 293,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_un
```

<sub>agentmaco · 커밋 71e83b3 · 2026-11-16T16:21:05+09:00 → 2026-11-17T08:17:02+09:00</sub>
