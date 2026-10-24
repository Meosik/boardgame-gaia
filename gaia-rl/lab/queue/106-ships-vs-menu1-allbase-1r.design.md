# 106-ships-vs-menu1-allbase-1r — 설계 검수 (실험 보류)

검수자 gpt-6-astra (원문 그대로)

결론: 지적 1건

- **약속한 ‘1R 충전 중앙값 리플레이’ 선정 경로가 없습니다.** `gaia-rl/lab/queue/106-ships-vs-menu1-allbase-1r.json:3`은 이를 선정 기준으로 삼지만, `gaia-rl/tools/charge_rounds.py:26`은 측정 종료를 4R로 고정하고 `:128`에서 미도달 판을 제외합니다. `gaia-rl/tools/lab.py:505`도 이 도구를 그대로 호출하므로 이번 1R 기록은 전부 집계에서 빠집니다.
  **확인 방법:** 위 종료 조건과 `stop_round=1`을 대조하면 됩니다. 시작 전에 1R 측정 종료 시점과 집계 방법을 정해야 종족별 중앙값 판 14개를 약속대로 고를 수 있습니다.

<sub>agentmaco · 커밋 e96b1ef · 2026-10-24T21:37:58+09:00</sub>
