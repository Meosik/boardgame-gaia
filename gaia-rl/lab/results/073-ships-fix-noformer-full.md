# 073-ships-fix-noformer-full — 완료

사용자(2026-10-18 04:10 "진행해"): A = 기준 ships, B = ships_fix_noformer = ships_fix에서 former_use·instant_forming만 뺀 묶음(opening_budget 첫 단계 수정 + budget_guard + opening_release + geodens_b14_tech + academy_economy). 071에서 ships_fix 전체는 충전 −2.8(평평)인데 테란만 −45.3(유의, 1–3R 광산 11 → 2). p003-g0 테란 결정 31 재현: 다섯 플래그를 끄면 연구소 타일 5(광석 수입) 22.1 > 타일 2 20.1(A와 같은 선택), 켜면 타일 5만 18.8로 내려감 → former_use가 테란의 차원 변형 광산 옵션을 지워 광석 값이 떨어진 것이 유력. 질문: former_use를 빼면 테란 손해가 사라지고 기오덴(+12.8)·제노스(+20.6) 이득은 남는가. 새 시드 6쌍, 6라운드 끝까지. 판정 1–3라운드 충전량(1점 = 1.5충전) + 최종 VP 병독. 함께 볼 것: 테란 1–3R Build·GaiaFormation 수(action_counts.py --types GaiaFormation Build Upgrade EclipseAsteroidMine ExploreSpaceship ResearchAdvance --rounds 1-3; 071 B 테란 Build 2), 연구 단수(research_counts.py --rounds 1-3; 071 B 테란 AI 4·경제 10), 기오덴 1R 타일·경로(upgrade_targets.py --rounds 1-1 --faction Geodens), 1R 광석 출처(ore_sources.py --rounds 1-1), 결정 시간(071 A 최대 51.1초), 오류·미탐색. 충전 양수이고 테란이 안 떨어지고 최종 VP가 안 떨어지면 기준 스택 편입 후보(사용자 확인).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-noformer-cap20.json`
시드 6개 × 좌석 교대 2판 (비교 기본값 2, 스펙 파일에 있으면 그 값)

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | -6.1 | [-37.5, +25.3] | 174.4 | 168.3 |
| Taklons | 6 | +4.7 | [-29.7, +39.1] | 164.1 | 168.8 |
| Terrans | 6 | -5.3 | [-57.9, +47.3] | 159.9 | 154.6 |
| Xenos | 6 | +10.3 | [-25.4, +46.0] | 141.5 | 151.8 |
| **전체 (좌석 평균)** | 6 | +0.9 | [-16.4, +18.3] |  |  |

다시보기 게시: pair-002/game-1-A12 좌석 2 — Terrans A팔 충전 154 (상대 팔 232)

결정 시간

| 팔 | 결정 수 | 평균 | 중앙값 | p90 | 최대 |
|---|---:|---:|---:|---:|---:|
| A | 1844 | 12.46초 | 19.59초 | 20.36초 | 25.7초 |
| B | 1766 | 12.62초 | 20.00초 | 20.39초 | 25.2초 |

참고: 오류·미탐색 수와 최종 점수 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Geodens | 6 | -19.3 | [-43.1, +4.4] | 0 | 0 | 0 / 0 | 0 / 0 | 340 / 273 |
| Taklons | 6 | -7.8 | [-34.3, +18.7] | 0 | 0 | 0 / 0 | 0 / 0 | 419 / 370 |
| Terrans | 6 | -18.3 | [-56.3, +19.6] | 0 | 0 | 0 / 0 | 0 / 0 | 347 / 381 |
| Xenos | 6 | +7.7 | [-9.3, +24.6] | 0 | 0 | 0 / 0 | 0 / 0 | 363 / 382 |
| **전체 (좌석 평균)** | 6 | -9.5 | [-26.4, +7.5] | 0 | 0 | 0 / 0 | 0 / 0 | 1469 / 1406 |

<sub>agentmaco · 커밋 5c05bd9 · 2026-10-18T06:38:20+09:00 → 2026-10-18T09:55:25+09:00</sub>
