# Cycle 146 — prune 스펙 (140) vs prune + fed_plan — 연방 사전 계획 부품 한 판 관찰, 6R

A = 140의 실행(`…_ships_menu1_all_tier_prune` cap60-p2, 8f6fa17 실행본, fed_plan 없음; 맵·종족이 같은 비교 기준일 뿐 같은 실행의 팔이 아님).
B = `…_tier_prune_fedplan` cap60-p2 비교 4: 연방 사전 계획 부품 fed_plan(E371 — federation-plan-{mines,institute,station}(-upfirst)·ts3 목표 후보, `_plans` 기억, 예산 검사 E86)을 켠 팩토리. 4좌석 같은 교사(결과표의 A/B 표시는 좌석 이름일 뿐 같은 스펙).
큐: 사용자 11-27 「한번 해봐」(E372 (ㄱ), 이론 단계 보류의 한 판 예외).
사전 등록: **판정 없음(관찰)**, 1판이라 강도 판단 아님. 140 뒤 기본 prune 팩토리에 power_first도 더해져(teacher_patches.py:6330–6331) 140 대비 변화를 fed_plan만의 효과로 읽지 않음(토론 1/1).
e362-20388 Firaks(좌석 0) · Itars(1) · BalTaks(2) · Xenos(3), `teacher_ab run --single` 1판, 6R, agentmaco, 커밋 905b91a, 02:51 → 03:52(1시간 1분). Result: lab/results/146-fedplan-one-game.md.

**Health: 깨끗.** 완주 1/1, 종료 코드 0, 결정 291, 오류·타임아웃 판 0, 폴백 타임아웃 0, 연방 후보 누락 0; 결정 최대 60.7초 · 중앙 4.9초(140: 60.0 · 11.0). 미탐색 비교 결정 Firaks 53/73 · Itars 41/63 · BalTaks 55/78 · Xenos 62/77. (결정 로그 직접 집계.)

## Charges in rounds 1–3 (판정 아님 — 관찰 설계)

1–3R 충전은 **미확인**: `charge_rounds.py`가 작업 트리 엔진 빌드에서 재생하다 `candidate index 34 is out of bounds`로 멈춤 — 140과 같은 빌드 불일치(E367 (ㄱ) 엔진 재빌드 대기).

| 좌석 | 최종 VP 146 | 140 | 연방(FormFederation) 146 · 라운드 | 140 |
|---|---:|---:|---|---:|
| Firaks | 88 | 86 | 1 (R4) | 1 |
| Itars | 78 | 96 | 1 (R3) | 2 |
| BalTaks | **109** | 83 | 1 (R3) | 1 |
| Xenos | 89 | 110 | 3 (R3 · R5 · R6) | 3 |
| 합 | 364 | 375 | 6 | 7 |

1판 · 같은 코드 재실행 편차 미측정(E303 (ㄴ) 안 돌림) — VP 차이는 읽지 않음.

## Activation (결정 로그 `decisions.jsonl.gz`, python 한 줄 집계)

- **fed_plan 목표가 비교에 들어간 것: BalTaks만, 8결정 9번**(R2 5결정 · R3 3결정: federation-plan-mines 8 · federation-plan-up1 1). **이긴 횟수 0** — 매번 current-choice 또는 다른 root가 위(차 0.7 ~ 26.7, 가장 가까운 것 step 100 up1 272.2 대 root-10 277.9). 이기지 않았으니 `_plans`로 기억돼 실행된 계획도 없음.
- **메뉴에서 밀려난 것(menu_dropped): 66번** — Firaks 42(R2 12 · R3 30), BalTaks 24(R2 10 · R3 14). Firaks는 비교에 한 번도 못 들어감. 밀린 까닭(비교 4자리 경쟁인지 예산 검사 E86인지)은 로그 칸으로 구분 안 됨.
- **Itars · Xenos: fed_plan 목표 0**(menu_pool · menu · menu_dropped · compared 어디에도 없음). Xenos는 그래도 3연방(140과 같은 수).
- fed_plan 목표가 보인 라운드는 2–3R뿐(R2 9 · R3 15 결정); 4R 이후 0.
- 기존 three-federations-separate 목표는 그대로 비교에 나옴(Xenos 16 · BalTaks 6 · Firaks 5 · Itars 1).
- prune_blocked 합 5052 / 후보 10081(50%) — 140의 14.2%(2016/14166)와 크게 다름. 기록 방식·power_first 영향인지 미확인(사전 등록 밖, 읽지 않음).

## Reading (HANDOFF 1 order)

- 연방 수: ② **활성 부족이 먼저** — 부품은 넷 중 둘에게만 후보를 냈고, 비교에 든 BalTaks에서도 한 번도 안 이김, Firaks는 메뉴에서 전부 밀림. 그래서 연방 수 6(140: 7)은 fed_plan의 효과를 말하지 못함(부품이 고른 수 0). ① 1판이라 잡음도 큼, ④ power_first가 같이 바뀜.
- ③ 범위·구현: Itars · Xenos에서 목표가 하나도 안 생긴 까닭(예산 검사로 생성 단계에서 빠짐인지, 조건 미충족인지)은 로그에 없음 — 생성 단계 기록이 없으면 다음 실행도 같은 물음이 남음.
- ⑤ 측정 창: 계획이 2–3R에만 나옴. 사전 설계(E371)의 의도가 2–4R 연방 준비라면 창은 맞고, 4R 이후 0은 기존 연방이 이미 있거나 예산 미달일 공산(미확인).
- 건강·시간: 깨끗, 중앙 결정 시간 11.0 → 4.9초(1판, 원인 미분해).

코드·배포 변경 없음. lab 큐 비어 있음. 실험 보류(11-26) 유지.

## Proposal (user decision, nothing queued)

- (ㄱ) fed_plan 생성 단계 기록(봇 턴 + Sonnet 작은 수정): 결정마다 만든 계획 수 · 예산 검사로 걸러진 수와 까닭을 로그 한 칸에 → 같은 판 재실행 없이도 다음 판에서 「왜 Itars · Xenos 0」인지 바로 보임. 
- (ㄴ) 메뉴 밀림 원인 읽기(봇 턴, 코드 읽기만): Firaks 42번이 비교 4자리 경쟁인지 다른 필터인지.
- (ㄷ) 작업 트리 엔진 재빌드(사용자 명령, E367 (ㄱ)) → 140 · 146 1–3R 충전 재생.
- (ㄹ) 리플레이 게시(사용자 원하면).
Bot recommendation: (ㄴ) → (ㄱ) (봇 턴, 실험 아님). 새 판은 보류 해제 전 제안 안 함.
