# 095c-golden-compare-reach-memo — 완료

E60(2026-10-21, 사용자 "지금 시간 남는데 미리 작업해"; E58 (ㄴ) 사거리 메모): 엔진 후보 생성이 보드 전 헥스를 도는 사거리 검사(Build·GaiaFormation·부스터·Twilight·테라포밍 파워 액션)마다 BFS를 새로 돌리던 것을, 한 후보 생성 호출 안에서 (출발 헥스 집합, 사거리 상한)당 거리표 1개로 메모(ReachMemoScope). 후보 집합·순서 불변 조건 — 봇 venv에서 기록 판 20개 3022결정 골든(runs/golden-candidates, 이전 엔진 bfb65c38)과 바이트 비교 0 불일치, fork 4R 14.4ms → 3.1ms. 이 항목은 lab 엔진(자동 재빌드)으로 같은 비교를 한 번 더 한다. 결과 json의 identical이 true여야 하며, false면 engine_build_id와 mismatch 결정을 HANDOFF에 적고 엔진 커밋을 되돌린다(사용자).

종료 코드 0

```
ok lab-093-guide-vs-src-4r__pair-000__game-0-A02.jsonl.gz: 142 decisions
ok lab-093-guide-vs-src-4r__pair-001__game-0-A23.jsonl.gz: 151 decisions
ok lab-093-guide-vs-src-4r__pair-002__game-0-A03.jsonl.gz: 125 decisions
ok lab-093-guide-vs-src-4r__pair-003__game-0-A13.jsonl.gz: 148 decisions
ok lab-093-guide-vs-src-4r__pair-004__game-0-A01.jsonl.gz: 140 decisions
ok lab-093-guide-vs-src-4r__pair-005__game-0-A12.jsonl.gz: 115 decisions
ok lab-093-guide-vs-src-4r__pair-006__game-0-A02.jsonl.gz: 126 decisions
ok lab-093-guide-vs-src-4r__pair-007__game-0-A23.jsonl.gz: 175 decisions
ok lab-093-guide-vs-src-4r__pair-008__game-0-A03.jsonl.gz: 127 decisions
ok lab-093-guide-vs-src-4r__pair-009__game-0-A13.jsonl.gz: 139 decisions
ok lab-093-guide-vs-src-4r__pair-010__game-0-A01.jsonl.gz: 131 decisions
ok lab-093-guide-vs-src-4r__pair-011__game-0-A12.jsonl.gz: 133 decisions
ok lab-093-guide-vs-src-4r__pair-012__game-0-A02.jsonl.gz: 172 decisions
ok lab-093-guide-vs-src-4r__pair-013__game-0-A23.jsonl.gz: 184 decisions
ok lab-093-guide-vs-src-4r__pair-014__game-0-A03.jsonl.gz: 136 decisions
ok lab-093-guide-vs-src-4r__pair-015__game-0-A13.jsonl.gz: 154 decisions
ok lab-092-guide-vs-weak-4r__pair-000__game-0-A02.jsonl.gz: 159 decisions
ok lab-092-guide-vs-weak-4r__pair-006__game-0-A02.jsonl.gz: 141 decisions
ok lab-092-guide-vs-weak-4r__pair-012__game-0-A02.jsonl.gz: 153 decisions
ok lab-089-ships-vs-fed-full__pair-000__game-0-A02.jsonl.gz: 271 decisions
20 games, 3022 decisions, mismatched games 0, 3.4 s, engine bfb65c38cd3e4636f1e2c101b95b2cdf73acf1e8f9721ff57c799eea235d387a → 045232fa8b9dd27239c04612dcc43f3a9047228fce2769f709172be1a12283f4
```

지표

```json
{
 "golden_engine_build_id": "bfb65c38cd3e4636f1e2c101b95b2cdf73acf1e8f9721ff57c799eea235d387a",
 "engine_build_id": "045232fa8b9dd27239c04612dcc43f3a9047228fce2769f709172be1a12283f4",
 "games": {
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-000/game-0-A02": {
   "decisions": 142,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-001/game-0-A23": {
   "decisions": 151,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-002/game-0-A03": {
   "decisions": 125,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-003/game-0-A13": {
   "decisions": 148,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-004/game-0-A01": {
   "decisions": 140,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-005/game-0-A12": {
   "decisions": 115,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-006/game-0-A02": {
   "decisions": 126,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-007/game-0-A23": {
   "decisions": 175,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-008/game-0-A03": {
   "decisions": 127,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-009/game-0-A13": {
   "decisions": 139,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-010/game-0-A01": {
   "decisions": 131,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-011/game-0-A12": {
   "decisions": 133,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-012/game-0-A02": {
   "decisions": 172,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-013/game-0-A23": {
   "decisions": 184,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-014/game-0-A03": {
   "decisions": 136,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-093-guide-vs-src-4r/pair-015/game-0-A13": {
   "decisions": 154,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-092-guide-vs-weak-4r/pair-000/game-0-A02": {
   "decisions": 159,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-092-guide-vs-weak-4r/pair-006/game-0-A02": {
   "decisions": 141,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-092-guide-vs-weak-4r/pair-012/game-0-A02": {
   "decisions": 153,
   "mismatch": null
  },
  "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-089-ships-vs-fed-full/pair-000/game-0-A02": {
   "decisions": 271,
   
```

<sub>agentmaco · 커밋 ade4a6d · 2026-10-21T06:06:49+09:00 → 2026-10-21T06:06:54+09:00</sub>
