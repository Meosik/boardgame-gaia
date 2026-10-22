# review-code-d60b9b0 — 검수

코드 검수 b4eb8d9..d60b9b0: 5개 파일 (자동)

검수자 gpt-6-astra (원문 그대로)

결론: 지적 1건

- `gaia-rl/tools/teacher_patches.py:3740` — **연방·토큰 제안이 동점 우대에서 빠집니다.** `_plain_plan()`이 `family='root'`를 모두 일반 수로 분류하지만, `federation-*`(2856줄)와 `flip-*`(3104줄)도 이 family로 생성됩니다. 따라서 3759줄에서 제외되어, current-choice와 동점이어도 제안을 선택하지 않습니다.
  **확인 방법:** 동점 테스트에 `current-choice(first=3)`와 `federation-2(family='root', first=2)`만 넣으면 선택이 3에 남습니다. `flip-2`도 동일합니다. 기존 테스트는 연방 값을 낮게 두어 이 경로를 검증하지 못합니다.

<sub>agentmaco · 커밋 c4c38a7 · 2026-10-22T16:41:00+09:00 → 2026-10-22T16:42:01+09:00</sub>
