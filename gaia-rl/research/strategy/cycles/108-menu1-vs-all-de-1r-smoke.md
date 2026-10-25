# Cycle 108 — ships_menu1 vs ships_menu1_all — 확장 쿼텟 d·e 재스모크(크래시 수정 확인), 1R

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-cap60-p2.json` (menu1 메뉴 앞자리 1칸).
B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-cap60-p2.json`: A + 10-25 all 팩토리 전부
(d218d13 셋업 크래시 수정, 711f7bb, 508f0ec gaia_asteroid_hold, 5f9c7fe/f14ed94 dead_tile, e3672af rebellion_ts, a017db1 등).
Queued 2026-10-25 by 사용자 "d·e 재스모크 먼저"(HANDOFF E112 (ㄱ)).
Pre-registered verdict: **판정 없음(스모크)**. 통과 기준 ① 8/8판 오류·타임아웃 0 ② 실행 커밋이 5bc843a 포함 ③ 최대 결정 ≈ 80초 이하.
쿼텟 d·e(다카니안·기오덴·모웨이드·스페이스 자이언트·타클론·테란·팅커로이드·제노스), 107 pair-008–011과 같은 4시드, 좌석 교대 8판,
비교 4, 양팔 cap60-p2, 2R 시작 종료, agentmaco, commit 9020fa0, 14:23 → 14:36(13분). Result: lab/results/108-menu1-vs-all-de-1r-smoke.md.

**Health: 실패 — 8/8판 오류.** 완료 0판, 타임아웃 0, 폴백 0. 모든 판이 step ≈14(셋업 직후 1R 첫 수 부근)에서 워커 종료
`RuntimeError('worker exited with code 1')`. 8개 `workers.log` 모두 같은 traceback(`grep -c "x not in tuple"` 8/8):
`plan_menu_goals → plan_affordable(E86) → _plan_cost → _mine_cost → RING.index(_home_type(player))` → `ValueError: tuple.index(x): x not in tuple`.
결정 시간 A 51개 평균 19.7 · 중앙 20.0 · p90 42.6 · 최대 60.0초 / B 48개 32.2 · 30.7 · 51.5 · 60.0초.
기준 ② 통과(9020fa0은 5bc843a 뒤), ③ 통과(최대 60초), ① 실패.

## Charges in rounds 1–3 (the verdict)

완료 쌍 0 — 표 없음(판정 없음 설계이기도 함).

## Activation (rounds 1–3, A → B)

측정 불가(1R 첫 수 전에 종료). gaia_asteroid_hold·셋업 배치 비교 발동은 확인 못 함.

## Reading (HANDOFF 1 order)

- ③ 구현: 107의 d218d13은 `_colony_cost` 경로만 고쳤고, E86 지불 가능성 검사의 `_mine_cost`(teacher_patches.py:4222)는
  확장 4종족 고향(팅커로이드·다카니안 = Asteroid, 모웨이드·스페이스 자이언트 = ProtoPlanet)을 RING에서 찾다 터짐. 양팔 공통 경로(plan_menu)라 A도 같이 죽음.
  107 기록의 "다른 `RING.index(home)` 자리는 이미 막힘"은 틀렸음(이 자리 누락).
- **14b4ad7 수정·푸시**: `_terraform_steps(state, player, kind)` 추가 — 확장 룰북 p.7 대로 다카니안 1, 스페이스 자이언트 2,
  팅커로이드·모웨이드는 엔진 필드 `expensive_terraforming_planet_types`의 색 3·나머지 1(필드 없으면 다른 좌석 고향 색이 비쌈), 기본 종족은 고리 거리.
  `_mine_cost`가 이를 씀. 테스트 추가, test_teacher_patches 100개 통과(unittest). 다른 7자리(325·1253·1842·2295·3724·3931·4105)는 `home in RING` 검사 또는 None 반환으로
  막혀 있음(Sonnet 감사). 단 1253(d218d13)은 확장 종족에 일률 3단계 — 규칙상 1/2/3이 맞아 값이 부정확(크래시 아님, 후속 후보).
- 1R 첫 수를 못 넘겼으므로 다음 크래시 자리가 더 있는지는 재실행으로만 확인 가능.
- 검수 절 없음(결과 페이지에 `## 검수` 없음).

코드 변경 14b4ad7(teacher, all·menu1 양팔 공통). 배포 변경 없음. lab 큐 비어 있음.

## Proposal (user decision, nothing queued)

- (ㄱ) 같은 108 설계 재실행(같은 4시드 × 좌석 교대, 1R, ≈ 15분–1시간) — 14b4ad7 포함 확인이 통과 기준 ②.
- (ㄴ) 1253 `_colony_cost`의 확장 종족 3단계를 `_terraform_steps`로 바꿔 규칙값으로(Sonnet 봇 턴, (ㄱ) 전에 넣으면 한 번에 확인).
- (ㄷ) (ㄱ) 통과 뒤 menu1 vs all 4R, 기본 쿼텟 새 시드, 1–3R 충전 + 105식 예산 유효성(≈ 8–9시간).
Bot recommendation: (ㄴ) → (ㄱ) → (ㄷ).
