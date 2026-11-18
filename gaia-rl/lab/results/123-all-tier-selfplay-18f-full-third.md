# 123-all-tier-selfplay-18f-full-third — 완료

사용자 2026-11-18 「추천대로 해」(HANDOFF E166 (ㄴ), E168): 121a ① — 약 74판 대 37판(같은 스텝 수) 모방 정확도 +2.32pt [+1.68, +2.96], 0 위 = 74판에서도 판 수가 한계 중 하나 — 의 사전 등록 귀결로 같은 방식의 6R 자기대국을 한 번 더 수집: BC·PPO 초기값 자료를 93판에서 약 141판으로. 판 수 48 = 114·119와 같은 값(봇이 따로 수치를 추천한 적은 없어 직전 두 수집의 값을 씀 — 사용자가 다른 수를 말하면 그 수로). teacher_ab run --single(시드당 1판), 4좌석 같은 교사 ships_menu1_all_tier cap60-p2 비교 4, 18종족: 쿼텟 geo 2 · a 10 · b 10 · c 9 · d 9 · e 8 = 48판(114·119와 같은 배분), 6R 끝까지(stop-round 없음). 시드 = 새 시드 48개(시드 파일에서 어떤 큐·결과에도 안 나온 첫 시드들), @order = faction_strength.py 현재 강도식. 환경은 114·119와 같음(GAIA_ENGINE_FIXES_2=1, PYTHONPATH python·baseline-teacher·tools, GAIA_FEDERATION_ONE_ROUTE 끔). 119(71e83b3) 이후 엔진·교사·teacher_ab 변경 없음(바뀐 것은 gaia_rl 정책 쪽 0648874·8939e92·e4e8279와 BC 도구 0370eff·spec 8876ced뿐) → 엔진 빌드 fc19671c4278 그대로일 것(정리 턴에서 확인). 알고 넣는 것(안 고침): 119의 quartet-b 크래시(No eligible continuation, 48판 중 1판)와 검색 전 구간 상한 초과(planned_tasks·root_rank, 폴백 9건/14,257결정)는 원인 미확인 그대로 — 같은 빈도면 1판 손실·폴백 약 10건; 고치면 수집 교사가 114·119와 달라지므로 이번 수집은 같은 교사로 둠. 후보 수가 인코더 용량 2048을 넘는 결정(119에서 1건)은 수집에는 영향 없음(export는 --capacity 4096). 판정 없음. 예상 ≈ 16시간(114 15시간 43분, 119 15시간 56분). 볼 것: ① 48/48판 정상 완료(results.json games_complete·failures, 타임아웃, 폴백 타임아웃 수) ② 결정 로그 전 행에 chosen 기록 ③ 최대 결정 시간·60초 초과 비율·100초 초과 수, 폴백 행의 timing.stages 구간 ④ 완료 뒤 봇 턴에서 bc_dataset.py index → stats: 엄격 재생 통과 수·6R 판 수·결정 수·엔진 빌드 id(114·119와 같은 fc19671c4278인지), 후보 수 최대값 ⑤ 참고: 좌석 평균 최종 VP, 좌석당 연방 수(결정 로그 FormFederation 선택 수)·안 뒤집은 토큰(endgame_tech_counts.py) — 114 100.1·1.50·0.52, 119 99.0·1.52·0.53과 비교. 그 뒤(정리 턴 제안): 인코딩 4 export(--capacity 4096) → 141판으로 자료량 한 단계 더(약 74 → 113판 학습) 측정 + 전체 자료 체크포인트(122가 정한 epoch 규칙). BC 학습·검증은 시드 단위로 나눔. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-031/game-0-A01", "complete": true, "scores": {"0": 86, "1": 79, "2": 107, "3": 115}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-030/game-0-A02", "complete": true, "scores": {"0": 106, "1": 70, "2": 72, "3": 76}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-032/game-0-A03", "complete": true, "scores": {"0": 103, "1": 127, "2": 82, "3": 98}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-033/game-0-A02", "complete": true, "scores": {"0": 102, "1": 106, "2": 101, "3": 86}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-036/game-0-A02", "complete": true, "scores": {"0": 93, "1": 102, "2": 106, "3": 112}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-034/game-0-A01", "complete": true, "scores": {"0": 127, "1": 116, "2": 106, "3": 99}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-035/game-0-A03", "complete": true, "scores": {"0": 92, "1": 82, "2": 86, "3": 83}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-037/game-0-A01", "complete": true, "scores": {"0": 81, "1": 89, "2": 92, "3": 158}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-038/game-0-A03", "complete": true, "scores": {"0": 86, "1": 107, "2": 106, "3": 152}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-039/game-0-A02", "complete": true, "scores": {"0": 93, "1": 87, "2": 103, "3": 134}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-041/game-0-A03", "complete": true, "scores": {"0": 86, "1": 94, "2": 88, "3": 80}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-043/game-0-A01", "complete": true, "scores": {"0": 92, "1": 91, "2": 113, "3": 127}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-040/game-0-A01", "complete": true, "scores": {"0": 122, "1": 124, "2": 95, "3": 95}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-042/game-0-A02", "complete": true, "scores": {"0": 106, "1": 110, "2": 92, "3": 62}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-044/game-0-A03", "complete": true, "scores": {"0": 137, "1": 90, "2": 115, "3": 91}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-045/game-0-A02", "complete": true, "scores": {"0": 75, "1": 110, "2": 94, "3": 118}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-046/game-0-A01", "complete": true, "scores": {"0": 84, "1": 134, "2": 126, "3": 114}, "failure": null}
{"game": "runs/lab-123-all-tier-selfplay-18f-full-third/pair-047/game-0-A03", "complete": true, "scores": {"0": 89, "1": 132, "2": 125, "3": 114}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 301 / 201 |
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 142 / 394 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 276 / 296 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 97 / 334 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 247 / 285 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 162 / 406 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 268 / 288 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 418 / 59 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 385 / 135 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 157 / 495 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 272 / 286 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 218 / 217 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 383 / 158 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 345 / 47 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 270 / 337 |
| Terrans | 0 | — | — | 0 | 0 | 3 / 0 | 0 / 0 | 737 / 314 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 301 / 243 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 200 / 974 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 3 / 0 | 0 / 0 | 5179 / 5469 |

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
   "A_decisions": 405,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 301,
   "A_unsearched_comparisons": 34674,
   "B_decisions": 291,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 201,
   "B_unsearched_comparisons": 24705
  },
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 200,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 142,
   "A_unsearched_comparisons": 17331,
   "B_decisions": 498,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 394,
   "B_unsearched_comparisons": 57043
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 366,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 276,
   "A_unsearched_comparisons": 37393,
   "B_decisions": 387,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 296,
   "B_unsearched_comparisons": 37803
  },
  "Darkanians": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 128,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 97,
   "A_unsearched_comparisons": 11615,
   "B_decisions": 411,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 334,
   "B_unsearched_comparisons": 41782
  },
  "Firaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 332,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 247,
   "A_unsearched_comparisons": 37697,
   "B_decisions": 365,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 285,
   "B_unsearched_comparisons": 43902
  },
  "Geodens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 198,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 162,
   "A_unsearched_comparisons": 31340,
   "B_decisions": 512,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 406,
   "B_unsearched_comparisons": 71889
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 332,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 268,
   "A_unsearched_comparisons": 37518,
   "B_decisions": 365,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_uns
```

<sub>agentmaco · 커밋 f624307 · 2026-11-18T15:33:14+09:00 → 2026-11-19T06:44:15+09:00</sub>
