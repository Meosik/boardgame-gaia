# 095a-src-cap60-opening-smoke — 완료

사용자(2026-10-21 "그렇게 해", HANDOFF E59 (ㄴ)): 092·093에서 opening_only 목록(하드쉬 할라 AC/RL+4~5M, 앰바스 RL+4~6M·AC+2M, 매드 안드로이드 RL+4~5M·2RL+1M, 네블라 PI+RL·PI+TS+2M, 란티다 PI+3~6M)의 예보가 20초 탐색에서 완성되지 않아 B팔이 current-choice/local-baseline으로 1R을 뒀다(네블라 BGG 선택 0회, 앰바스 3회). 상한 60초(+비교 병렬 2)면 완성되는지 보는 스모크: A = guide cap60-p2, B = src cap60-p2(같은 규칙, 상한만 60초), 쿼텟 a·b·c 1시드씩 3쌍, 2라운드 시작에서 종료(≈ 30–40분). 판정 없음(충전은 안 읽음). 볼 것: plan_labels --prefix BGG-R1- 로 B팔 앰바스·매드 안드로이드·네블라·란티다·글린의 1R BGG 선택 수(093 cap20: 3·16·0·14·60)와 decisions의 completed_comparisons, 결정 시간(셋업·1R 최대). 완성되면 opening_only 종족을 cap60 양팔로 재측정(092 하드쉬 할라 포함), 안 되면 fixed_academy식 코치 경로(엔지니어링, 사용자 결정).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-guide-cap60-p2.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-byfaction-guide-src-cap60-p2.json`
시드 3개 × 좌석 교대 2판 (비교 기본값 4, 스펙 파일에 있으면 그 값), 1라운드에서 종료

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

충전량 계산 실패

```
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/charge_rounds.py", line 131, in <module>
    main()
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/charge_rounds.py", line 123, in main
    mean, (low, high) = ci95(seat_means)
                        ^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/charge_rounds.py", line 63, in ci95
    mean = sum(values)/n
           ~~~~~~~~~~~^~
ZeroDivisionError: division by zero
```

다시보기: 고를 판 없음

결정 시간

| 팔 | 결정 수 | 평균 | 중앙값 | p90 | 최대 |
|---|---:|---:|---:|---:|---:|
| A | 184 | 19.83초 | 19.73초 | 43.43초 | 73.7초 |
| B | 186 | 19.04초 | 18.64초 | 43.93초 | 81.3초 |

참고: 오류·미탐색 수와 1라운드 종료 시점 VP 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Ambas | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 11 / 11 |
| BalTaks | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 7 / 7 |
| Bescods | 1 | +5.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 8 / 8 |
| Firaks | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 8 / 9 |
| Gleens | 1 | +9.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 15 / 14 |
| HadschHallas | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 10 / 10 |
| Itars | 1 | -1.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 12 / 12 |
| Ivits | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 7 / 8 |
| Lantids | 1 | -5.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 9 / 10 |
| Nevlas | 1 | +5.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 11 / 11 |
| Terrans | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 12 / 12 |
| Xenos | 1 | +0.0 | — | 0 | 0 | 0 / 0 | 0 / 0 | 13 / 13 |
| **전체 (좌석 평균)** | 3 | +1.1 | [-3.6, +5.7] | 0 | 0 | 0 / 0 | 0 / 0 | 123 / 125 |

참고: 1라운드 종료 시점 VP 평균 (판정에 쓰지 않음)

| 종족 | A 평균 총점 | B 평균 총점 | 최고 |
|---|---:|---:|---:|
| Ambas | 10.0 | 10.0 | 10 |
| BalTaks | 3.0 | 3.0 | 3 |
| Bescods | 4.0 | 9.0 | 9 |
| Firaks | 4.0 | 4.0 | 4 |
| Gleens | 7.0 | 16.0 | 16 |
| HadschHallas | 14.0 | 14.0 | 14 |
| Itars | 9.0 | 8.0 | 9 |
| Ivits | 3.0 | 3.0 | 3 |
| Lantids | 10.0 | 5.0 | 10 |
| Nevlas | 4.0 | 9.0 | 9 |
| Terrans | 4.0 | 4.0 | 4 |
| Xenos | 6.0 | 6.0 | 6 |
| **전체** | 6.5 | 7.6 | 16 |

<sub>agentmaco · 커밋 a498287 · 2026-10-21T02:58:46+09:00 → 2026-10-21T03:38:22+09:00</sub>
