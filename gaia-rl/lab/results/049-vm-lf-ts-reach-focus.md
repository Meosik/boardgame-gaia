# 049-vm-lf-ts-reach-focus — 완료

사용자(2026-10-12 "부품 분리해서 원인 파악해"): 048 부품 분리 1/3. A = vm_lf_ts, B = A + 연구 집중(D)만, 항해 2 뒤에는 항해를 맨 뒤로 고친 버전(048은 항해만 계속 올림: 1–3R 타클론 Nav 18/25, 테란 13/23). 048과 같은 시드 6쌍(쌍별 비교용, 새 시드 확인 아님), 3라운드에서 종료. 판정은 1–3라운드 충전량(1점 = 1.5충전).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-focus-cap20.json`
시드 6개 × 좌석 교대 2판 (비교 기본값 2, 스펙 파일에 있으면 그 값), 3라운드에서 종료

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | -35.0 | [-80.0, +10.0] | 162.3 | 127.3 |
| Taklons | 6 | -19.3 | [-44.8, +6.2] | 155.9 | 136.6 |
| Terrans | 6 | -22.3 | [-32.8, -11.9] | 159.0 | 136.6 |
| Xenos | 6 | -6.8 | [-63.5, +49.9] | 158.8 | 152.0 |
| **전체 (좌석 평균)** | 6 | -20.9 | [-32.4, -9.3] |  |  |

다시보기 게시 실패 (pair-002/game-0-A03)

```
0, in replay_game
    replay = add_decision_log(replay)
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_log.py", line 10, in add_decision_log
    income_by_frame = recover_income(frames)
                      ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_income.py", line 25, in recover_income
    raise RuntimeError('Build income recovery first: cargo build -p gaia-engine --release --example replay_income')
RuntimeError: Build income recovery first: cargo build -p gaia-engine --release --example replay_income
```

결정 시간

| 팔 | 결정 수 | 평균 | 중앙값 | p90 | 최대 |
|---|---:|---:|---:|---:|---:|
| A | 849 | 12.14초 | 20.00초 | 20.23초 | 24.1초 |
| B | 846 | 11.65초 | 17.97초 | 20.20초 | 22.7초 |

참고: 오류·미탐색 수와 3라운드 종료 시점 VP 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Geodens | 6 | -6.0 | [-16.3, +4.3] | 0 | 0 | 0 / 0 | 0 / 0 | 138 / 132 |
| Taklons | 6 | +1.3 | [-5.2, +7.9] | 0 | 0 | 0 / 0 | 0 / 0 | 133 / 145 |
| Terrans | 6 | -0.7 | [-6.3, +5.0] | 0 | 0 | 0 / 0 | 0 / 0 | 145 / 125 |
| Xenos | 6 | -3.7 | [-8.4, +1.1] | 0 | 0 | 0 / 0 | 0 / 0 | 191 / 189 |
| **전체 (좌석 평균)** | 6 | -2.2 | [-6.0, +1.5] | 0 | 0 | 0 / 0 | 0 / 0 | 607 / 591 |

<sub>agentmaco · 커밋 4f8bf5c · 2026-10-12T14:11:45+09:00 → 2026-10-12T15:40:42+09:00</sub>
