# 138-setup-placement-sim-20 — 완료

사용자(2026-11-26 「배치 시뮬레이션 + 초반에 건설할 만한 땅 찝어주기까지는 될듯? … 거기서 너가 패턴을 찾아봐」 → 무작위 맵 20개 · 쿼텟 a–e 섞기 · 이 시뮬레이션에 한해 실험 보류 해제에 「그렇게 해」). 시작 배치만 두고 멈추는 판(teacher_ab run --single --stop-after-setup, 5896e92): 부스터 선택 전 상태를 판마다 setup_state.json으로 저장. 4좌석 같은 교사 ships_menu1_all_tier cap60-p2 비교 4(133 · 134와 같은 교사), 시드 = 쿼텟 a · b · c · d · e 파일의 안 쓴 시드 4개씩 20개(맵 20개). 판정 없음(관찰). 정리 턴: 봇 턴에서 `tools/setup_report.py runs/lab-138-setup-placement-sim-20`(읽기 전용, 수 초)를 돌려 setup_report.md를 만들고 패턴을 본다 — ① 좌석별 내 시작 건물끼리 거리 분포(종족별 · 쿼텟별) ② 둘째 광산이 첫째 대비 새로 여는 행성 수(0–1이면 ‘겹침’) ③ 상대 건물까지 최단 거리 ④ 초반 건설 후보 5곳(QIC 없이 · 테라포밍 단계 · 상대 옆)의 단계 분포 ⑤ 두 광산 거리와 ②의 관계. 종족별 값은 좌석 수가 적어(쿼텟당 4판) 적기만 함. 한계: 1R 이후 결과 없음, 휴리스틱 지표(사거리는 현재 항해 단계 기준, 연방 분리 · 위성 수는 이번에 안 셈). 예상 ≈ 1–3시간(배치 결정 판당 8–9개, 결정당 열린 자리 전부 비교 — 실측 없음), 제한 8시간. 리플레이 게시 없음.

종료 코드 0

```
{"game": "runs/lab-138-setup-placement-sim-20/pair-002/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-003/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-004/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-007/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-006/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-005/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-009/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-011/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-008/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-010/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-012/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-014/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-013/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-015/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-016/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-018/game-0-A02", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-017/game-0-A03", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
{"game": "runs/lab-138-setup-placement-sim-20/pair-019/game-0-A01", "complete": true, "scores": {"0": 10, "1": 10, "2": 10, "3": 10}, "failure": null}
| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1 / 2 |
| BalTaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 4 / 3 |
| Bescods | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 8 / 0 |
| Darkanians | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1 / 0 |
| Firaks | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Geodens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 3 / 1 |
| Gleens | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 2 / 6 |
| HadschHallas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Itars | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1 / 3 |
| Ivits | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 2 / 2 |
| Lantids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 3 / 1 |
| Moweyds | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Nevlas | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 2 / 6 |
| SpaceGiants | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Taklons | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Terrans | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Tinkeroids | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 1 / 1 |
| Xenos | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| **전체 (좌석 평균)** | 0 | — | — | 0 | 0 | 0 / 0 | 0 / 0 | 28 / 25 |

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
   "A_decisions": 2,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 1,
   "A_unsearched_comparisons": 1,
   "B_decisions": 6,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 2,
   "B_unsearched_comparisons": 2
  },
  "BalTaks": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 4,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 4,
   "A_unsearched_comparisons": 4,
   "B_decisions": 4,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 3,
   "B_unsearched_comparisons": 3
  },
  "Bescods": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 8,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 8,
   "A_unsearched_comparisons": 10,
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
   "A_decisions": 3,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 1,
   "A_unsearched_comparisons": 5,
   "B_decisions": 1,
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
   "A_decisions": 4,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 0,
   "A_unsearched_comparisons": 0,
   "B_decisions": 4,
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
   "A_decisions": 6,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 3,
   "A_unsearched_comparisons": 209,
   "B_decisions": 2,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 1,
   "B_unsearched_comparisons": 67
  },
  "Gleens": {
   "pairs": 0,
   "mean_B_minus_A": null,
   "ci95": null,
   "error_games": 0,
   "timeout_games": 0,
   "A_decisions": 2,
   "A_fallback_timeouts": 0,
   "A_federation_limit_hits": 0,
   "A_unsearched_decisions": 2,
   "A_unsearched_comparisons": 22,
   "B_decisions": 6,
   "B_fallback_timeouts": 0,
   "B_federation_limit_hits": 0,
   "B_unsearched_decisions": 6,
   "B_unsearched_comparisons": 65
  },
  "HadschHallas": {
   "pairs": 0,
   
```

<sub>agentmaco · 커밋 6c69d96 · 2026-11-26T11:34:32+09:00 → 2026-11-26T12:00:10+09:00</sub>
