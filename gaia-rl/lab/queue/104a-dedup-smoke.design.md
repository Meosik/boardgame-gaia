# 104a-dedup-smoke — 설계 검수 (실험 보류)

검수자 gpt-6-astra (원문 그대로)

결론: 지적 1건

- `gaia-rl/lab/queue/104a-dedup-smoke.json:3` — 판정은 **같은 이름 중복 0**인데, 구현은 **Goal 전체가 같은 경우만 제거**합니다(`gaia-rl/baseline-teacher-20260917/four_factions/preparation.py:115`). 정상적으로 남긴 동명·다른 단계 계획도 중복으로 집계됩니다. 예외를 이름별로 보고하더라도, 현재 로그는 단계 정보를 버려 정상 잔존인지 제거 실패인지 구분할 수 없습니다(`gaia-rl/tools/teacher_ab.py:315`).
  
  확인 방법: `gaia-rl/tools/test_teacher_patches.py:1292`의 동명·다른 단계 사례와 로그 필드를 대조하십시오. 시작 전에 `goal_spec` 또는 전체 Goal 식별값을 기록하고, **동일 Goal 중복 0**을 통과 기준으로 정해야 합니다.

<sub>agentmaco · 커밋 87b53e3 · 2026-10-23T12:24:02+09:00</sub>
