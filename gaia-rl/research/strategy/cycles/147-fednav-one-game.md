# Cycle 147 — 한 판 관찰 `..._fedplan_balance_formedmine_fednav` (4좌석 같은 교사) — 1R 26번째 결정에서 크래시, 6R 계획

A = B = 공장 `guide_r1_charge3_lf_more_vm_lf_ts_ships_menu1_all_tier_prune_fedplan_balance_formedmine_fednav`
(fed_absorb · fed_prep · nav_good · good_by_cost · fed_group2, E383–E387), cap60-p2 비교 4. Queued 2026-11-28 사용자
「일단 다시 실험해봐」(E387 뒤, 이론 단계의 한 판 예외). Pre-registered verdict: **없음(관찰)**. 건강 기준: 종료 코드 0, 완주,
오류 · 타임아웃 0. 볼 것: 연방 수 · 시점, fed_group2 활성, 묶음 사례(146과 나란히).
e362-20388 Firaks · Itars · BalTaks · Xenos(146과 같은 맵), `teacher_ab run --single` 1판, 6R 예정, agentmaco,
commit 7e93256, 21:09:46 → 21:16:29(7분). Result: lab/results/147-fednav-one-game.md.

**Health: 실패 — 0/1판.** 1R 26번째 결정(좌석 2 BalTaks, A)에서 `ValueError: No eligible continuation; do not silently
pass`(`four_factions/preparation.py:555`) — 비교 rollout 안의 한 좌석에서 `select_goal`/`best_index`가 None, 즉 그 상태에 선택
가능한 후보가 남지 않음(전부 `blocked`인지 · 후보 0인지 · 어느 단계인지는 덤프 전 미확인 — 충전 응답 단계엔 패스가 없고
`gaia-engine/src/rules/ai.rs:188–197` 연방 한도 경로는 연방 후보를 뺀다, 토론 1/1 코덱스)(workers.log: `parallel_search._compute` → `teacher_patches.py:1597` → `:389` → `preparation.rollout`;
호출은 `teacher_patches.py:4887 → :1830` search). 기록된 25결정: 오류 전 타임아웃 · 폴백 0, 결정 최대 36.2초(결정 로그
`seconds`), 둔 수는 배치 · 부스터 · 충전 · 교역소/연구소 업그레이드뿐.

## Charges in rounds 1–3 (the verdict)

없음 — 판이 1R에서 멈춰 1–3R 충전 · 연방 · VP 모두 없음. 볼 것 ①–③ 전부 **읽을 수 없음**.

## Activation

측정 불가(1R 업그레이드 단계까지만; fed_plan · fed_group2는 2R부터 쓰이는 부품).

## Reading (HANDOFF 1 order)

- ③ 구현 — 같은 크래시가 110 · 111 · 112(쿼텟 b, `gaia_asteroid_hold` 원인, d5946bd · 61edf20 수정)와 119(1/48, 원인 미확인,
  123 사이클 문서)에 있었다. 수정 뒤에도 "어떤 필터가 rollout 좌석의 후보를 전부 막는" 경로가 남아 있다는 119의 가설이
  여기서 다시 맞는다. 146(같은 맵 · 같은 시드, 이전 공장)은 완주했으므로 그 뒤 들어간 부품(balance · formedmine · fed_absorb ·
  fed_prep · nav_good · good_by_cost · fed_group2) 가운데 하나가 그 상태를 만들었을 수 있으나 **미확인**: 새 부품 diff
  (0450ba3 · c2784de · a2c4508 · a22f82f)에는 점수를 `blocked`로 만드는 줄이 없다(grep) — 새 목표(예: nav_good `explore@ship`)가
  rollout 경로를 바꿔 기존 필터에 걸렸을 가능성.
- 재현 시도: `explain_decision.py --step 26`이 재생 중 `candidate index 34 is out of bounds`로 멈춤 — 작업 트리 엔진 빌드가 lab과
  달라 재생이 갈라지는 E367 · 140 · 146과 같은 문제. 그래서 막힌 상태와 막은 필터는 이 턴에 못 봤다.
- ①②④–⑦ 해당 없음(판이 없음).

코드 · 배포 변경 없음. 큐 비어 있음.

## Proposal (user decision, nothing queued)

- (ㄱ) 진단 수정(Sonnet 작은 수정, 봇 턴): 감싸개 입력 `snapshot`은 탐색 시작 상태일 뿐이라(토론 1/1 코덱스) 실패 상태는
  `preparation.rollout`의 지역 변수 `current` · `scores` · `remaining` · `goal`(`preparation.py:522, 549–555`)에서 가져온다.
  동결 기준 파일은 건드리지 않고, `teacher_patches.py` rollout 감싸개(:1597, 워커 프로세스 안)에서 이 ValueError를 잡아
  traceback 가장 안쪽 `rollout` 프레임의 그 지역 변수 · 막힌 좌석 · 후보별 `blocked` 점수를 게임 폴더에 덤프한 뒤 다시 던진다
  (행동은 그대로, 기록만).
- (ㄴ) 같은 시드 147 재실행(lab ≈10분 — 결정적이면 같은 26번째 결정에서 재현되어 덤프가 나온다; 비결정이면 완주까지 ≈1–2시간).
- (ㄷ) 원인을 본 뒤 수정(필터가 마지막 후보는 막지 않게 등, 119 · 147 공통) → 147 다시.
- (ㄹ) 작업 트리 엔진 재빌드(사용자 명령, E367) — 재생 도구가 다시 쓸 수 있게.
Bot recommendation: (ㄱ)→(ㄴ)→(ㄷ). (ㄹ)은 사용자 명령.
