# 133-fixed-seed-ladder-baseline-12 — 완료

사용자 2026-11-24 「그냥 모든 종족이 3연방이라도 일단 하게 목표를 잡아야할거 같은데」 → 코덱스 이상 없음(사용자 2026-11-13 상시 지시), HANDOFF E297: 고정 시드 사다리 1단계(E177 · E178 · E180 · E181)의 기준선. 맵 · 타일 = quartet-e-88365 고정, 종족 묶음 12개 = lab/fixed-seed-factions-quartet-e-88365.json(추첨 시드 fixed-seed-ladder-1, 18종족 2–3회씩), 좌석 순서는 목록대로, 차례 순서 @order = faction_strength.py 현재 강도식(2026-11-24 작업 트리 빌드에서 계산). 시드 12줄은 lab/seeds-fixed-ladder-quartet-e-88365.txt에 고정 — 교사 수정 전후 같은 12줄을 씀(다시 뽑지 않음). teacher_ab run --single(시드당 1판), 4좌석 같은 교사 = 123 수집과 같은 채택 스택 ships_menu1_all_tier cap60-p2 비교 4(pass_last · shipnow · charge_phase는 A/B 전이라 끔), 6R 끝까지(stop-round 없음). 환경은 114 · 119 · 123과 같음(GAIA_ENGINE_FIXES_2=1, PYTHONPATH python · baseline-teacher · tools, GAIA_FEDERATION_ONE_ROUTE 끔). 판정 없음(기준선). 사다리 기준(사용자 E180, 1–3R 충전 규칙의 예외로 읽음): 12판 전 좌석 3연방 이상 + 좌석 평균 최종 VP 120 이상이면 2단계(타일 돌리기) — 이 실행은 그 기준까지의 거리를 잼. 볼 것(정리 턴): ① 12/12판 정상 완료(results.json games_complete · failures, 타임아웃, 폴백 타임아웃 수), 최대 결정 시간 · 60초 초과 비율 ② 좌석별(48좌석) 만든 연방 수 = 결정 로그의 FormFederation 선택 수(다른 경로로 받은 토큰은 따로 적음): 분포 0 · 1 · 2 · 3개 이상, 전 좌석 3연방 이상인 판 수 ③ 좌석 평균 최종 VP ④ 첫 연방 · 둘째 연방을 만든 라운드 ⑤ 종족별 연방 수 · VP는 2–3좌석이라 차이로 읽지 않고 적기만 함 ⑥ 참고(맵이 달라 직접 비교 아님): 114 좌석 평균 100.1점 · 연방 1.50개, 119 99.0 · 1.52, 93판 372좌석 중 3연방 23좌석. 한계: 맵 하나 · 12판(48좌석); 같은 코드 재실행 편차는 재지 않음 — 수정 뒤 재측정의 차이를 읽을 때 이 점을 적음. 알고 넣는 것(안 고침): 119의 quartet-b 크래시(No eligible continuation)와 검색 전 구간 상한 초과 폴백은 원인 미확인 그대로; 판이 실패하면 그 판을 빼고 적음(다시 돌릴지는 정리 턴 제안). 그 뒤(정리 턴 제안, 큐 안 넣음): 이 12판에서 「건설 가능한데 패스한 횟수」 집계(E296: 건물 위치 × 목표 건물 종류 중복 제거, 분모 = 전체 패스 수) · 연방에 1–2 모자란 좌석 수, 첫 수정 후보 E179 (ㄱ)(5–6R에 연방 밖 파워가 2 이하로 모자라면 파워 올리는 root를 비교 4자리 안에)를 같은 12줄로 재측정. 예상 ≈ 4시간(114 기준 판당 약 20분), 제한 16시간. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-001/game-0-A01", "complete": true, "scores": {"0": 93, "1": 100, "2": 92, "3": 108}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-003/game-0-A02", "complete": true, "scores": {"0": 102, "1": 140, "2": 119, "3": 70}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-002/game-0-A03", "complete": true, "scores": {"0": 107, "1": 102, "2": 102, "3": 102}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-000/game-0-A02", "complete": true, "scores": {"0": 98, "1": 92, "2": 94, "3": 92}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-006/game-0-A02", "complete": true, "scores": {"0": 107, "1": 105, "2": 108, "3": 113}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-004/game-0-A01", "complete": true, "scores": {"0": 129, "1": 119, "2": 75, "3": 78}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-005/game-0-A03", "complete": true, "scores": {"0": 127, "1": 86, "2": 137, "3": 107}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-009/game-0-A02", "complete": true, "scores": {"0": 95, "1": 118, "2": 98, "3": 79}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-008/game-0-A03", "complete": true, "scores": {"0": 90, "1": 99, "2": 87, "3": 110}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-007/game-0-A01", "complete": true, "scores": {"0": 108, "1": 105, "2": 98, "3": 98}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-011/game-0-A03", "complete": true, "scores": {"0": 72, "1": 112, "2": 99, "3": 99}, "failure": null}
{"game": "runs/lab-133-fixed-seed-ladder-baseline-12/pair-010/game-0-A01", "complete": true, "scores": {"0": 122, "1": 121, "2": 89, "3": 75}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 107 / 0 |
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 183 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 166 / 0 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 117 / 58 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 47 / 107 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 108 / 54 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 102 / 0 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 106 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 50 / 56 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 72 / 80 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 183 / 0 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 62 / 47 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 117 / 65 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 48 / 102 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 200 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 66 / 136 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 68 / 140 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 66 / 114 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1379 / 1448 |

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
   "A_decisions": 130,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 107,
   "A_unsearched_comparisons": 11452,
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
   "B_decisions": 228,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 183,
   "B_unsearched_comparisons": 18610
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 220,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 166,
   "A_unsearched_comparisons": 18628,
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
   "A_decisions": 132,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 117,
   "A_unsearched_comparisons": 11529,
   "B_decisions": 66,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 58,
   "B_unsearched_comparisons": 5500
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 62,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 47,
   "A_unsearched_comparisons": 4377,
   "B_decisions": 132,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 107,
   "B_unsearched_comparisons": 12145
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 137,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 108,
   "A_unsearched_comparisons": 15933,
   "B_decisions": 60,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 54,
   "B_unsearched_comparisons": 6523
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 134,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 102,
   "A_unsearched_comparisons": 11302,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsea
```

<sub>agentmaco · 커밋 bdd2fec · 2026-11-24T16:39:44+09:00 → 2026-11-24T20:32:09+09:00</sub>
