# 115d-fed-on-crash-seeds-full — 완료

사용자 2026-11-13 「진행해」(HANDOFF E140 (ㄱ), E141): 연방 후보 줄이기 플래그 `GAIA_FEDERATION_ONE_ROUTE=1`이 교사 안에서 6R 끝까지 도는 첫 실행(스모크) — 114에서 검색 전 상한 초과로 죽은 2판(pair-012 quartet-b-68171@order=0,2,3,1 좌석 A02, pair-037 quartet-d-75189@order=1,2,0,3 좌석 A01)을 같은 시드·같은 좌석 분할로 재실행(시드 재사용은 이 재실행의 목적; --single 2판이라 pair-000 = A02, pair-001 = A01). 114와 같은 명령(teacher_ab run --single, 4좌석 같은 교사 ships_menu1_all_tier, cap60-p2, 비교 4, 6R 끝까지)에 플래그만 추가. 플래그는 spec의 env가 아니라 명령 env 앞머리에 둠: spec env는 교사 워커 프로세스에만 적용되고(teacher_ab.py:348) 판을 진행하는 runner의 Environment(:397)는 받지 못함 → 한쪽만 켜지면 스냅샷 digest 불일치로 판이 오류 남. 판정 없음(n=2; 탐색이 시간 예산이라 114와 같은 줄로 가지 않음 — 114와의 수치 비교는 참고). 사전 등록 통과 기준: ① 2/2판 6R 완주(results.json games_complete 2, failures 없음; `worker native state diverged from runner`나 `teacher returned a decision for another state`가 나오면 runner와 워커의 플래그가 다른 것 → 환경 전달 수정) ② 결정 시간 최대 100초 미만(114 완주 46판 최대 80.4초, cap60 범위 약 80초) ③ 워커 타임아웃 0. 보고만(기준 아님): 폴백 타임아웃 결정 수, 60초 이상 결정 수, federation_limit_hits, 좌석당 연방 수·최종 VP(114 46판 좌석 평균 VP 100.1·연방 1.50과 나란히). 발동 확인은 정리 턴: 작업 트리 엔진이 재빌드돼 있으면(사용자 명령) 플래그 켬으로 엄격 재생 통과 + 연방 후보가 묶음당 1개인지 집계, 재빌드 전이면 미확인으로 적음. 주의: 7cb307b 뒤라 검색 전 상한 초과는 플래그와 무관하게 크래시 대신 root 1위(폴백으로 계수) — 완주만으로 플래그 효과를 말하지 않음. 이 2판은 플래그 켬 자료라 114(끔) BC 자료와 섞지 않음(E140 (ㄷ)). 예상 1–2시간(114 판당 44–122분, 중앙값 74분).

종료 코드 0

```
{"game": "runs/lab-115d-fed-on-crash-seeds-full/pair-001/game-0-A01", "complete": true, "scores": {"0": 135, "1": 60, "2": 107, "3": 73}, "failure": null}
{"game": "runs/lab-115d-fed-on-crash-seeds-full/pair-000/game-0-A02", "complete": true, "scores": {"0": 136, "1": 101, "2": 85, "3": 74}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 51 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 72 / 0 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 54 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 53 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 40 / 0 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 52 / 0 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 70 / 0 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 66 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 234 / 224 |

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
   "B_decisions": 72,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 51,
   "B_unsearched_comparisons": 5865
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 90,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 72,
   "A_unsearched_comparisons": 8883,
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
   "B_decisions": 67,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 54,
   "B_unsearched_comparisons": 9051
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
   "B_decisions": 68,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 53,
   "B_unsearched_comparisons": 6672
  },
  "Itars": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 50,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 40,
   "A_unsearched_comparisons": 5476,
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
   "A_decisions": 58,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 52,
   "A_unsearched_comparisons": 8651,
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
   "A_decisions": 90,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 70,
   "A_unsearched_comparisons": 20549,
   "B_decisions": 0,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 0,
   "B_unsearched_comparisons": 0
  },
  "Tinkero
```

<sub>agentmaco · 커밋 3e3c29f · 2026-11-13T14:24:59+09:00 → 2026-11-13T15:22:55+09:00</sub>
