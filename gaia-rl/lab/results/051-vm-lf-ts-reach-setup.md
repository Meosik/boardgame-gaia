# 051-vm-lf-ts-reach-setup — 완료

사용자(2026-10-12 "부품 분리해서 원인 파악해"): 048 부품 분리 3/3. A = vm_lf_ts, B = A + 셋업 부품(A·B)만(셋업 결정은 서로 다른 자리·부스터 최대 4개 비교·셋업만 50초, 상대 인접 자리는 차단 대신 먼저). 048과 같은 시드 6쌍(쌍별 비교용, 새 시드 확인 아님), 3라운드에서 종료. 판정은 1–3라운드 충전량(1점 = 1.5충전).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-setup-cap20.json`
시드 6개 × 좌석 교대 2판 (비교 기본값 2, 스펙 파일에 있으면 그 값), 3라운드에서 종료

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | +38.6 | [-51.5, +128.7] | 147.5 | 186.1 |
| Taklons | 6 | +8.0 | [-14.4, +30.5] | 162.3 | 170.4 |
| Terrans | 6 | +29.2 | [-53.4, +111.8] | 158.0 | 187.2 |
| Xenos | 6 | -9.6 | [-34.4, +15.2] | 149.9 | 140.3 |
| **전체 (좌석 평균)** | 6 | +16.6 | [-11.7, +44.8] |  |  |

다시보기 게시 실패 (pair-000/game-1-A13)

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
| A | 886 | 11.67초 | 18.27초 | 20.21초 | 23.3초 |
| B | 915 | 13.98초 | 18.30초 | 20.58초 | 52.5초 |

참고: 오류·미탐색 수와 3라운드 종료 시점 VP 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Geodens | 6 | +1.8 | [-5.3, +9.0] | 0 | 0 | 0 / 0 | 0 / 0 | 135 / 166 |
| Taklons | 6 | -3.8 | [-14.7, +7.1] | 0 | 0 | 0 / 0 | 0 / 0 | 144 / 159 |
| Terrans | 6 | +1.8 | [-4.6, +8.2] | 0 | 0 | 0 / 0 | 0 / 0 | 153 / 166 |
| Xenos | 6 | -1.5 | [-17.5, +14.5] | 0 | 0 | 0 / 0 | 0 / 0 | 182 / 189 |
| **전체 (좌석 평균)** | 6 | -0.4 | [-5.1, +4.2] | 0 | 0 | 0 / 0 | 0 / 0 | 614 / 680 |

<sub>agentmaco · 커밋 3e32615 · 2026-10-12T17:15:57+09:00 → 2026-10-12T18:59:33+09:00</sub>
