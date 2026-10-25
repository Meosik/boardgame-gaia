# Cycle 108b — ships_menu1 vs ships_menu1_all — 108 재실행(Lost Fleet 비용 수정 뒤), 1R 스모크

A = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-cap60-p2.json` (현재 스택 ships_menu1). B =
`tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-cap60-p2.json`: A + all 팩토리(E103 이후 통합 부품 전부).
108이 8/8판 `_mine_cost` RING.index 크래시로 끝나 14b4ad7 + ed5412b·9d8df5c(확장 룰북 p.7 단계값, 원시행성 3삽, 소행성 빈 포머면 0삽) 뒤 같은 설계로 재실행.
Queued 2026-10-25 by 사용자 "진행해"(E113 (ㄱ)).
Pre-registered verdict: **판정 없음(스모크)**. 통과 기준 ① 8/8판 오류·타임아웃 0 ② 실행 커밋이 d5ad0de 포함 ③ 최대 결정 ≈ 80초 이하.
볼 발동: 테란·제노스 1R 소행성 광산 A → B, 셋업 배치 비교(B compared에 bgg-opening 없음). 1R 충전은 참고만.
쿼텟 d(기오덴·모웨이드·타클론·팅커로이드)·e(스페이스자이언트·제노스·테란·다카니안), 4시드(quartet-d-113082·113944, quartet-e-106400·113676) × 좌석 교대 = 8판,
비교 4, cap60-p2, stop_round 1(2R 시작 종료), agentmaco, commit e25a649, 17:37 → 18:27(50분). Result: lab/results/108b-menu1-vs-all-de-1r-smoke.md.

**Health: 깨끗함 — 통과 기준 ①②③ 모두 통과.** 8/8판 완료, 오류 0, 타임아웃 0, 폴백 타임아웃 0/0, 연방 후보 누락 0/0.
커밋 e25a649 ⊇ d5ad0de(`git merge-base --is-ancestor` 통과). 결정 시간 A 254개 평균 17.8 · 중앙 17.8 · p90 39.7 · 최대 60.1초,
B 228개 22.1 · 22.2 · 45.3 · 60.1초(B가 평균 +4.3초). 비교 미탐색 결정 169 / 154.

## Charges in rounds 1–3 (the verdict)

1R만 돈 스모크라 표의 값은 **1R 충전**이고 판정이 아니다(쌍 2개, 판독선 25·드리프트 ±30 아래 = 읽을 수 없음).

| Faction | B parts | A | B | B−A | 95% CI | Pairs B > A | Per pair |
|---|---|---:|---:|---:|---|---:|---|
| Darkanians | all | 93.1 | 71.2 | −21.9 | [−213.2, +169.3] | — | 2쌍 |
| Geodens | all | 65.3 | 46.6 | −18.7 | [−231.2, +193.8] | — | 2쌍 |
| Moweyds | all | 49.9 | 52.7 | +2.8 | [−128.8, +134.3] | — | 2쌍 |
| SpaceGiants | all | 119.9 | 94.1 | −25.8 | [−158.9, +107.3] | — | 2쌍 |
| Taklons | all | 72.0 | 57.4 | −14.6 | [−225.8, +196.7] | — | 2쌍 |
| Terrans | all | 96.9 | 106.3 | +9.4 | [−477.9, +496.6] | — | 2쌍 |
| Tinkeroids | all | 63.9 | 70.4 | +6.5 | [−105.6, +118.7] | — | 2쌍 |
| Xenos | all | 91.0 | 105.4 | +14.4 | [−590.1, +618.9] | — | 2쌍 |
| **All (seat mean)** | | | | −6.0 | [−26.2, +14.1] | | 4쌍 |

Posted watch replay: `pair-003/game-1-A02` 좌석 3 — 제노스 B 130 vs A 68.
봇 추가 게시(10-25, 사용자 "리플레이 준비해", B팔 초점 종족당 1개, `ab_replays.py export` → `publish_replays.py` ~/gaia-media; 106 리플레이는 이때 삭제됨):
테란 `pair-003/game-0-A13` 좌석 2(step 54 = 프레임 55 `EclipseAsteroidMine`) · 제노스 `pair-002/game-0-A03` 1 · 다카니안 `pair-003/game-1-A02` 1 ·
스페이스자이언트 `pair-002/game-1-A12` 0 · 모웨이드 `pair-000/game-0-A02` 1 · 기오덴 `pair-001/game-0-A23` 0 · 타클론 `pair-000/game-1-A13` 2 · 팅커로이드 `pair-001/game-1-A01` 3.
2R 시작 VP(판정 아님): 전체 A 6.2 / B 5.8, 차 −0.4 [−5.6, +4.8].

전체 −6.0은 107(−6.1, 8쌍)과 같은 방향·크기지만 4쌍·1R이라 읽을 수 없음. 확장 종족 3개(다카니안·스페이스자이언트·기오덴 포함 −19~−26)가 음수인 것도 쌍 2개라 잡음 범위.

## Activation (round 1, A → B)

엔진 재생(`gaia_rl.Environment`로 결정 로그 재생, 고른 행동의 좌표 → 보드 행성 종류; 봇 한 줄 스크립트):
- **셋업 배치 비교**: A 26배치 중 14개가 비교됐고 14개 모두 compared에 `bgg-opening` 가족 있음 → B 26배치 중 **26개 비교, bgg-opening 0**. 기준대로 발동.
- **테란 1R 소행성 광산**: A `Build` 소행성 2 → B 0(대신 `EclipseAsteroid` 1 + 테라 `Build` 1 + 반란 무료 TS 1). 소행성 개척 총수 2 → 1.
- **제노스 1R 소행성 광산**: A 0 → B 0(양팔 모두 사막 위주; B는 Twilight 사거리·우주선 크레딧 행동을 씀).
- 참고: 스페이스자이언트 소행성 `Build` A 1 → B 2, 원시행성 시작 2 / 2(ed5412b의 원시행성 3삽 경로가 크래시 없이 지나감); 다카니안 소행성 시작 2 / 2.

## Reading (HANDOFF 1 order)

- 크래시 수정: 108의 `_mine_cost`·`_colony_cost` 확장 종족 경로가 양팔 8/8판에서 크래시 없이 지나감 — 14b4ad7·ed5412b·9d8df5c 확인(스모크 목적 달성).
- 1R 충전: ① 잡음 — 쌍 2개, 모든 종족 CI가 ±100 넘음. 전체 −6.0은 107(−6.1)과 같은 값이라 "all이 1R에 약간 손해" 가능성은 남지만 1R 창(⑤)이라 판단 안 함; 성능은 4R 1–3R 충전으로.
- 발동: 셋업 배치 비교는 설계대로(B는 bgg-opening 없이 배치만 비교). 테란 소행성 보류는 2 → 1로 줄었으나 B가 Eclipse 소행성 행동으로 1개 개척 — 보류 규칙이 Eclipse 경로에도 걸려야 하는지는 코드·리플레이 확인 전(미확인). 제노스는 양팔 0이라 이 시드들에선 발동 기회가 없었음.
- 시간: B 평균 +4.3초(+24%), 최대는 양팔 60.1초로 같음. 4R 본실험의 105식 예산 유효성(완료 비교/결정 차 < 2% 등)에서 B가 걸릴 수 있으니 그 집계가 판정 전 조건.
- 검수 절 없음(결과 페이지에 `## 검수` 없음).

코드·배포 변경 없음. lab 큐 비어 있음.

## Proposal (user decision, nothing queued)

- (ㄱ) menu1 vs all 4R A/B, 기본 쿼텟 새 시드, 판정 1–3R 충전 + 105식 예산 유효성(위반 시 판정 보류) — lab ≈ 8–9시간. 108 note의 사전 계획 그대로.
- (ㄴ) 같은 4R에 쿼텟 d·e를 포함할지 — 확장 종족은 PPO 일반화 시험 범위(2026-10-22 결정)라 기본은 제외, 포함하면 시간 +≈ 3시간.
- (ㄷ) 테란 B `EclipseAsteroid` 1R 개척 판 explain(봇 턴, lab 0) — 소행성 보류 규칙이 Eclipse 경로를 빠뜨렸는지.
Bot recommendation: (ㄱ) 기본 쿼텟만, (ㄷ)는 4R이 도는 동안 봇 턴으로.
