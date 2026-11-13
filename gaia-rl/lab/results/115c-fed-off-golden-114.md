# 115c-fed-off-golden-114 — 완료

사용자 2026-11-13 「진행해」(HANDOFF E137, 토론 1/1 수용): 엔진 966e9ea의 "플래그 끔이면 후보 목록 불변"을 전체 목록으로 확인 — 수정 전 빌드 36d2e007b6f9(봇 작업 트리)로 뜬 골든(114 48판 14176결정의 후보 목록 전체 + 각 판 마지막 상태의 자유 행동 fork 뒤 목록 56개의 해시·개수, pair-012 크래시 상태 포함)과 lab 새 빌드의 목록을 바이트 단위로 비교(golden_candidates.py compare, 플래그 끔). 판정 없음, 대국 없음. 사전 등록 통과 기준: identical 참 = 불일치 판 0, 비교 결정 수 14176, final_free_checked 56, 엔진 빌드 id가 골든과 다름(새 빌드). 불일치가 하나라도 있으면 끔 후보 목록이 바뀐 것 → 엔진 수정을 고치거나 되돌림. 115b(선택된 행동만 대조)는 재생 호환성 확인이고 목록 불변의 근거는 이 실험. 예상 5분 이내.

종료 코드 0

```
ok lab-114-all-tier-selfplay-18f-full__pair-009__game-0-A02.jsonl.gz: 320 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-010__game-0-A01.jsonl.gz: 312 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-011__game-0-A03.jsonl.gz: 268 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-012__game-0-A02.jsonl.gz: 224 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-013__game-0-A01.jsonl.gz: 285 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-014__game-0-A03.jsonl.gz: 304 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-015__game-0-A02.jsonl.gz: 284 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-016__game-0-A01.jsonl.gz: 229 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-017__game-0-A03.jsonl.gz: 320 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-018__game-0-A02.jsonl.gz: 250 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-019__game-0-A01.jsonl.gz: 262 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-020__game-0-A03.jsonl.gz: 299 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-021__game-0-A02.jsonl.gz: 267 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-022__game-0-A01.jsonl.gz: 387 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-023__game-0-A03.jsonl.gz: 333 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-024__game-0-A02.jsonl.gz: 296 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-025__game-0-A01.jsonl.gz: 308 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-026__game-0-A03.jsonl.gz: 307 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-027__game-0-A02.jsonl.gz: 288 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-028__game-0-A01.jsonl.gz: 288 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-029__game-0-A03.jsonl.gz: 369 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-030__game-0-A02.jsonl.gz: 309 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-031__game-0-A01.jsonl.gz: 278 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-032__game-0-A03.jsonl.gz: 301 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-033__game-0-A02.jsonl.gz: 272 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-034__game-0-A01.jsonl.gz: 271 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-035__game-0-A03.jsonl.gz: 294 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-036__game-0-A02.jsonl.gz: 255 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-037__game-0-A01.jsonl.gz: 111 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-038__game-0-A03.jsonl.gz: 300 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-039__game-0-A02.jsonl.gz: 334 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-040__game-0-A01.jsonl.gz: 262 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-041__game-0-A03.jsonl.gz: 380 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-042__game-0-A02.jsonl.gz: 324 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-043__game-0-A01.jsonl.gz: 282 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-044__game-0-A03.jsonl.gz: 265 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-045__game-0-A02.jsonl.gz: 316 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-046__game-0-A01.jsonl.gz: 348 decisions
ok lab-114-all-tier-selfplay-18f-full__pair-047__game-0-A03.jsonl.gz: 335 decisions
48 games, 14176 decisions, final-free checked 56, mismatched games 0, 74.0 s, engine 36d2e007b6f95ebacfe9e7d3033e6ec1f6674e62b1516fc93765a2732f149a1f → fc19671c4278246becaa0710511b6d1a37b4049d58290aa8450c1c9f2c9041db
```

지표

```json
{
 "golden_engine_build_id": "36d2e007b6f95ebacfe9e7d3033e6ec1f6674e62b1516fc93765a2732f149a1f",
 "engine_build_id": "fc19671c4278246becaa0710511b6d1a37b4049d58290aa8450c1c9f2c9041db",
 "games": {
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-000/game-0-A02": {
   "decisions": 254,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-001/game-0-A01": {
   "decisions": 324,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-002/game-0-A03": {
   "decisions": 324,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-003/game-0-A02": {
   "decisions": 290,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-004/game-0-A01": {
   "decisions": 304,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-005/game-0-A03": {
   "decisions": 324,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-006/game-0-A02": {
   "decisions": 297,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-007/game-0-A01": {
   "decisions": 343,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-008/game-0-A03": {
   "decisions": 279,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-009/game-0-A02": {
   "decisions": 320,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-010/game-0-A01": {
   "decisions": 312,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-011/game-0-A03": {
   "decisions": 268,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-012/game-0-A02": {
   "decisions": 224,
   "final_free": 44,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-013/game-0-A01": {
   "decisions": 285,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-014/game-0-A03": {
   "decisions": 304,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-114-all-tier-selfplay-18f-full/pair-015/game-0-A02": {
   "decisions": 284,
   "final_free": 0,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab
```

<sub>agentmaco · 커밋 00dca67 · 2026-11-13T13:23:32+09:00 → 2026-11-13T13:24:47+09:00</sub>
