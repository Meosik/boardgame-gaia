# Cycle 112a2 — all_tier vs all_tier (같은 교사) — 112 pair-005 크래시 회귀 확인, 1R

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-cap60-p2.json`
(ships_menu1_all_tier, 4좌석 같은 교사). 시험 대상은 교사 부품이 아니라 크래시 수정 d5946bd·61edf20
(`gaia_asteroid_hold`가 남는 후보를 0으로 만들면 막지 않음 — E120 원인: 고정 오프닝 제한 × 소행성 포머 보류 충돌).
Queued 2026-10-26 (E122 뒤, 토론 1/1 코덱스: "새 순서 재실행은 실패 경로를 피할 수 있어 크래시 수정 검증이 아님").
Pre-registered verdict: **판정 없음**. 통과 = 2/2판 완료 + `No eligible continuation`(preparation.py:555) 0건.
쿼텟 b(발타크·매드 안드로이드·글린·아이타), 시드 `quartet-b-67485@order=1,2,3,0`(112 실패 판 그대로) 1쌍 × 좌석 교대 2판,
비교 4, cap60-p2, 1R 종료, agentmaco, commit d615532(61edf20 포함 확인 `git merge-base --is-ancestor`),
06:15 → 06:51 (36분, 추정 15분). Result: lab/results/112a2-crash-regression-1r.md.

**Health: 깨끗함 — 통과.** 2/2판 완료, 오류·타임아웃·폴백 0. `No eligible continuation` 0건
(`grep -rc` 실행 폴더 전체: workers.log 2개·decisions 포함 모두 0). 결정 A 70·B 67, 평균 23.1 / 28.6초,
p90 56.7 / 60.0초, 최대 60.0 / 60.0초. 112에서는 같은 시드·순서 두 판이 step 1에서 멈췄다.

## Charges in rounds 1–3 (참고, 같은 교사 = 판 안 표류)

| Faction | B parts | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| 발타크 | 없음 | 64.6 | 68.6 | +4.0 | — | 1/1 | n=1 |
| 매드 안드로이드 | 없음 | 101.1 | 99.5 | −1.6 | — | 0/1 | n=1 |
| 글린 | 없음 | 83.3 | 89.9 | +6.7 | — | 1/1 | n=1 |
| 아이타 | 없음 | 54.9 | 80.7 | +25.8 | — | 1/1 | n=1 |
| **All (seat mean)** | | | | +8.7 | — | | 1 pair |

Posted watch replay: `pair-000/game-1-A13` 좌석 2 — 아이타 B 81 vs A 55 (lab 자동).
1R 종료 VP 4.8 → 3.2 (의미 없음). 같은 교사라 차이는 전부 표류(±30 안, 아이타 +25.8도 안쪽) — 판정 대상 아님.

## Activation

- 크래시 경로 통과: 112의 두 판은 step 1에서 멈췄고, 같은 시드·순서·교사·커밋(수정 포함)에서 두 판 모두 1R 끝까지 감.
- 한계: 탐색은 시간 상한이 있어 결정적이지 않다 — 이번 판에서 롤아웃이 그 충돌 상태(발타크 광석 0·돈 3·QIC 1·광산 1개 남음)에
  다시 들어가 수정 분기(막지 않음)가 실제로 탔는지는 로그에 표시가 없어 직접 확인 못 함. 단위 테스트(d5946bd)가 그 분기를 덮는다.

## Reading (HANDOFF 1 order)

- 크래시: ② 수정 커밋 포함 + 실패 판 그대로 재실행 2/2 완료 → **회귀 확인 통과**(분기 발동은 간접 증거).
- 충전 차이: ① 같은 교사 1쌍 = 표류, 읽지 않음.
- 시간: 결정 최대 60.0초, cap60 기대(≈ 80초) 안. 실행 36분은 추정 15분보다 김(1R 결정 137개 × 평균 ≈ 26초).

검수 절 없음(결과 페이지에 `## 검수` 없음). 코드·배포 변경 없음. lab 큐: 112b-strength-order-current-1r(현재 강도식 ca96b32, ≈ 2.5시간) 다음 실행.

## Proposal (user decision, nothing queued)

- (ㄱ) 크래시 건 종료로 기록(E120 (ㄱ)·E118 (ㄱ) 끝남) — 비용 없음.
- (ㄴ) 112b 그대로 진행(이미 큐) — 쿼텟 b 다른 시드에서 같은 크래시가 다시 나면 그때 재현 봇 턴.
- (ㄷ) 분기 발동을 직접 보고 싶으면 `gaia_asteroid_hold` 해제 시 결정 로그에 한 줄 표시(Sonnet, 봇 턴).
Bot recommendation: (ㄱ) + (ㄴ), (ㄷ)는 다시 크래시 나면.
