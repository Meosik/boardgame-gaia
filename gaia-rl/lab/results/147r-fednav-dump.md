# 147r-fednav-dump — 완료

사용자 11-28 「돌려봐」(HANDOFF E388 (ㄴ), 이론 단계의 한 판 예외): 147-fednav-one-game과 같은 명령 · 같은 시드 e362-20388 Firaks · Itars · BalTaks · Xenos · 같은 공장 ..._formedmine_fednav cap60-p2 비교 4, --single 1판 6R. 달라진 것은 a4d737b(E389) 덤프뿐 — `No eligible continuation`이 나면 실패한 rollout 프레임(current · scores · remaining · goal · 좌석 · 후보별 blocked)을 게임 폴더 no-continuation-*.json.gz로 남기고 오류는 그대로(행동 불변). 판정 없음(진단). 볼 것(정리 턴): ① 재현 여부 — 147처럼 1R 26번째 결정(BalTaks)에서 멈추면 결정적 ② 덤프 파일 수와 내용: 단계(충전 응답 · 행동 단계 등), 후보 수(0인지), 후보별 blocked와 까닭 문자열(어느 필터인지), 막힌 좌석 · 목표 ③ 덤프가 없으면(오류인데 파일 0) 덤프 경로 버그 ④ 완주하면 147 볼 것(연방 수 · 시점 · fed_group2 활성)을 그대로 — 비결정 재생이라는 뜻. 건강: 종료 코드, 오류 · 타임아웃, 폴백, 최대 결정 시간(≈80초 이내). 예상 ≈10분(재현) – 2시간(완주), 제한 4시간.

종료 코드 0

```
{"game": "runs/lab-147r-fednav-dump/pair-000/game-0-A02", "complete": false, "scores": null, "failure": "error"}
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

<sub>agentmaco · 커밋 dce14f8 · 2026-11-28T21:51:38+09:00 → 2026-11-28T21:58:25+09:00</sub>
