# 134-fixed-seed-ladder-rerun-12 — 완료

코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E303 (ㄴ) → E304: 133-fixed-seed-ladder-baseline-12의 같은 코드 재실행 — 재실행 편차(이후 수정을 읽을 잡음 기준) 측정. 133과 명령 · 교사 · 시드 12줄(lab/seeds-fixed-ladder-quartet-e-88365.txt) · 환경이 전부 같고 출력 폴더만 다름(시드 재사용이 이 사전 등록의 목적). teacher_ab run --single(시드당 1판), 4좌석 같은 교사 ships_menu1_all_tier cap60-p2 비교 4, 6R 끝까지. 판정 없음. 볼 것(정리 턴): ① 12/12판 완주 · 폴백 타임아웃 · 결정 시간, manifest의 engine_build_id가 133과 같은지(49318fef… — 다르면 재실행 편차가 아니라 빌드 차이로 적음) ② 133 대 134를 같은 시드 줄 · 같은 좌석끼리 짝지어: 좌석 평균 최종 VP(133 = 101.6)의 차, 좌석별 VP 차의 평균 절댓값 · 최대, 판별 4좌석 VP 합의 차 ③ 만든 연방 수(FormFederation 선택 수) 분포(133 = 1개 32 · 2개 14 · 3개 2, 평균 1.38)와 연방 수가 달라진 좌석 수, 전 좌석 3연방 판 수(133 = 0/12), 3연방 좌석 수(133 = 2/48) ④ 같은 시드에서 두 실행의 결정 로그가 처음 갈리는 step과 그 결정의 시간(상한 60초 근처에서 갈리는지) ⑤ 종족별 값은 2–3좌석이라 적기만 함. 읽는 법: 두 실행의 차이 = 같은 코드 재실행에서 나오는 크기의 한 표본(실행 2개뿐이라 분포가 아님); 이후 교사 수정을 같은 12줄로 재측정한 차이가 이 크기 안이면 '못 가름'으로 적음 — 통과 기준값은 여기서 정하지 않음(사용자 수치). 한계: 맵 하나 · 12판 · 재실행 1회. 판이 실패하면 그 판을 빼고 적음(다시 돌릴지는 정리 턴 제안). 예상 ≈ 4시간(133 = 3시간 52분), 제한 16시간. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-001/game-0-A01", "complete": true, "scores": {"0": 107, "1": 103, "2": 110, "3": 97}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-002/game-0-A03", "complete": true, "scores": {"0": 114, "1": 120, "2": 106, "3": 71}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-003/game-0-A02", "complete": true, "scores": {"0": 114, "1": 135, "2": 93, "3": 74}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-000/game-0-A02", "complete": true, "scores": {"0": 83, "1": 101, "2": 116, "3": 119}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-006/game-0-A02", "complete": true, "scores": {"0": 94, "1": 130, "2": 101, "3": 107}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-005/game-0-A03", "complete": true, "scores": {"0": 105, "1": 75, "2": 131, "3": 114}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-004/game-0-A01", "complete": true, "scores": {"0": 104, "1": 124, "2": 77, "3": 96}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-008/game-0-A03", "complete": true, "scores": {"0": 85, "1": 129, "2": 103, "3": 94}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-007/game-0-A01", "complete": true, "scores": {"0": 105, "1": 97, "2": 89, "3": 98}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-009/game-0-A02", "complete": true, "scores": {"0": 104, "1": 127, "2": 106, "3": 89}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-011/game-0-A03", "complete": true, "scores": {"0": 95, "1": 98, "2": 96, "3": 96}, "failure": null}
{"game": "runs/lab-134-fixed-seed-ladder-rerun-12/pair-010/game-0-A01", "complete": true, "scores": {"0": 117, "1": 133, "2": 105, "3": 108}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 112 / 0 |
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 165 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 168 / 0 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 114 / 54 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 40 / 124 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 107 / 54 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 109 / 0 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 88 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 56 / 53 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 81 / 58 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 175 / 0 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 47 / 46 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 113 / 49 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 51 / 102 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 220 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 59 / 124 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 63 / 138 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 79 / 119 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1374 / 1394 |

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
   "A_decisions": 145,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 112,
   "A_unsearched_comparisons": 11933,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
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
   "B_decisions": 221,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 165,
   "B_unsearched_comparisons": 16244
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 219,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 168,
   "A_unsearched_comparisons": 18165,
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
   "A_decisions": 131,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 114,
   "A_unsearched_comparisons": 11614,
   "B_decisions": 58,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 54,
   "B_unsearched_comparisons": 6141
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 51,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 40,
   "A_unsearched_comparisons": 3794,
   "B_decisions": 163,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 124,
   "B_unsearched_comparisons": 14227
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 139,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 107,
   "A_unsearched_comparisons": 16281,
   "B_decisions": 63,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 54,
   "B_unsearched_comparisons": 11353
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 140,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 109,
   "A_unsearched_comparisons": 11446,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unse
```

<sub>agentmaco · 커밋 385db57 · 2026-11-24T21:37:24+09:00 → 2026-11-25T01:32:14+09:00</sub>
