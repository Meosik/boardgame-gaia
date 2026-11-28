# Cycle 147r — 147 재실행(덤프) — `No eligible continuation` 원인 프레임 잡기, 6R 예정 1판

A = B = `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-menu1-all-tier-prune-fedplan-balance-formedmine-fednav-cap60-p2.json`
(147과 같은 공장 `..._formedmine_fednav`, 비교 4). 147과 달라진 것은 a4d737b(E389) 덤프뿐 — 오류 때 실패한 rollout 프레임을
`no-continuation-*.json.gz`로 남기고 오류는 그대로. 큐: 사용자 11-28 「돌려봐」(E388 (ㄴ)).
사전 등록: 판정 없음(진단). 볼 것 ① 재현 ② 덤프 수 · 내용(단계 · 후보 수 · 후보별 blocked 까닭 · 좌석 · 목표) ③ 오류인데 파일 0이면 덤프 경로 버그 ④ 완주하면 147 볼 것.
e362-20388 Firaks · Itars · BalTaks · Xenos, `--single` 1판, agentmaco, 커밋 dce14f8, 21:51:38 → 21:58:25(6분 47초).
결과: `lab/results/147r-fednav-dump.md`.

**건강: 실패(0/1판, 사전 등록한 재현 가지).** 종료 코드 0, 오류 판 1(`worker exited with code 1`), 타임아웃 · 폴백 타임아웃 0,
결정 26개(A 11 · B 15) 뒤 `step 26`에서 멈춤 — 147과 같은 자리(1R 26번째 결정, BalTaks의 비교 rollout,
`preparation.py:555`, `workers.log` traceback이 `parallel_search._compute` → `preparation.rollout`).

## 1–3라운드 충전 (판정)

해당 없음 — 1R에서 멈춤, 완료 쌍 0.

## 덤프 (볼 것 ①–③)

- ① **재현 — 결정적.** 147과 같은 결정 번호 · 같은 좌석 · 같은 오류.
- ③ **덤프는 남았으나 엉뚱한 폴더**: 게임 폴더 `runs/lab-147r-fednav-dump/pair-000/game-0-A02/`에는 0개,
  `baseline-teacher-20260917/runs/lab-147r-fednav-dump/pair-000/game-0-A02/no-continuation-989626-….json.gz` 1개(4.5 KB).
  까닭: `teacher_ab.Worker`가 상대 경로 `output`을 `GAIA_ROLLOUT_DUMP_DIR`로 넘기고, 워커는 교사 소스 폴더를 작업 폴더로 돎(추정 —
  파일 위치로만 확인) → 경로를 절대 경로로 넘기면 됨(작은 수정).
- ② **내용**(gzip json을 파이썬으로 읽음): rollout `step` 10, 행위자 = 차례 = 좌석 2 **BalTaks**(A 팔), 1R `ActionPhase`, 목표 `root-31`(`family root`, 남은 목표 같음).
  BalTaks 상태: 연구소 1 · 광산 1, 광석 4 · 돈 9 · 지식 0 · QIC 1 · 파워 2/4/0, 테라포밍 1 · 가이아 1.
  **후보 27개 — 0개가 아니라 전부 blocked:**
  - 19개 `conservation blocked: fixed opening takes priority` — 건설 3 · 우주선 탐사 3 · 파워 태우기 2 · 패스 3 · 부스터 테라포밍 건설 6 · 교역소 업그레이드 1
  - 8개 `conservation blocked: prune: pruning tables (E362)` — 광석→돈 1–4 · 광석→파워 1–4 · QIC→광석 1
  
  = 고정 오프닝 필터(`bgg_openings/fixed.py:261` `_restrict`)가 「오프닝 자금을 대는 수」만 남겼는데 그것이 자유 환전 8개뿐이고,
  E362 가지치기 표가 그 환전 8개를 모두 막음 → 선택 가능 후보 0.

## Reading (HANDOFF 1 순서)

- ① 잡음 아님(결정적 재현). ② 두 필터 모두 적힌 대로 발동. ③ 각 필터 단독 범위는 맞음 — 고정 오프닝은 「증명된 진척 · 자금 수만」,
  가지치기는 「자유 환전 막기」(E362 · 사용자 E368 「자원 바꾸기는 막혔을 때만」).
- ④ **원인 = 두 필터의 상호작용.** 고정 오프닝이 「막혔으니 환전으로 자금을 대라」고 고른 순간이 바로 E368의 「막혔을 때」인데,
  가지치기 표는 그 예외를 모름. 둘이 겹치면 전부 blocked → `select_goal`이 `None` → 오류. 147의 새 부품 다섯(fed_* · nav_good · good_by_cost)은 덤프에 나오지 않음.
  어느 필터가 먼저 도는지는 코드로 확인 안 함(결론은 순서와 무관: 남는 후보 0).
- 110–112 · 119의 같은 크래시가 같은 원인인지는 미확인(그때 덤프 없음).
- 코드 · 배포 변경 없음, lab 큐 비어 있음.

## Proposal (사용자 결정, 큐 안 넣음)

- (ㄱ) 가지치기 예외: 고정 오프닝이 자금 수로 남긴 환전(또는 환전 말고 남은 선택 가능 후보가 0일 때의 환전)은 E362 표가 막지 않음 —
  E368 「막혔을 때만 환전」과 같은 뜻. 교사 코드(봇 직접) + 이 덤프 상태로 단위 테스트(전부 blocked가 안 됨). 봇 턴.
- (ㄴ) 덤프 경로를 절대 경로로(`teacher_ab.Worker`, Sonnet 작은 수정 + 테스트).
- (ㄷ) (ㄱ)(ㄴ) 뒤 같은 시드 147 다시(≈1–2시간, 이론 단계의 한 판 예외 — 사용자 「돌려봐」 범위인지 사용자 확인).
Bot recommendation: (ㄱ)+(ㄴ) 한 턴에 → (ㄷ)는 사용자 답.
