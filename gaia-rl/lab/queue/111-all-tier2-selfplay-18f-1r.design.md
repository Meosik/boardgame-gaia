# 111-all-tier2-selfplay-18f-1r — 설계 검수 (실험 보류)

검수자 gpt-6-astra (원문 그대로)

결론: 지적 1건

- `gaia-rl/lab/queue/111-all-tier2-selfplay-18f-1r.json:3` — **110과 티어 값만 달라지는 비교가 아닙니다.** 실제 110 실행 커밋은 `9fcb58f`입니다(`lab/results/110-all-tier-selfplay-18f-1r.md:95`). 이후 필수 부스터 우선순위가 추가되고(`tools/teacher_patches.py:5109`), 선택 방식도 롤아웃 1회에서 즉시 반환으로 바뀌었습니다(`:5269`). 따라서 선택 변화가 새 가치표 때문인지 우선순위·선택 방식 때문인지 구분할 수 없습니다.
  
  확인: `git diff 9fcb58f HEAD -- gaia-rl/tools/teacher_patches.py`
  
  옛 가치표에도 동일한 우선순위·선택 방식을 적용해 비교하거나, note를 **“여러 수정의 합산 변화 관찰”**로 고쳐야 합니다.

<sub>agentmaco · 커밋 a978192 · 2026-10-26T01:09:16+09:00</sub>
