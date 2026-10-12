# 050-vm-lf-ts-reach-plus — 완료

사용자(2026-10-12 "부품 분리해서 원인 파악해"): 048 부품 분리 2/3. A = vm_lf_ts, B = A + 사거리 +1(C)만(확장 가치·부스터 5에 항해 다음 사거리 단계 반영). 048과 같은 시드 6쌍(쌍별 비교용, 새 시드 확인 아님), 3라운드에서 종료. 판정은 1–3라운드 충전량(1점 = 1.5충전).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-plus-cap20.json`
시드 6개 × 좌석 교대 2판 (비교 기본값 2, 스펙 파일에 있으면 그 값), 3라운드에서 종료

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | -10.8 | [-45.4, +23.8] | 144.3 | 133.6 |
| Taklons | 6 | +10.9 | [-37.2, +59.1] | 150.5 | 161.4 |
| Terrans | 6 | -3.4 | [-36.1, +29.3] | 169.1 | 165.7 |
| Xenos | 6 | -12.0 | [-44.7, +20.6] | 159.5 | 147.4 |
| **전체 (좌석 평균)** | 6 | -3.8 | [-27.3, +19.7] |  |  |

다시보기 게시 실패 (pair-004/game-0-A01)

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
| A | 864 | 11.90초 | 18.42초 | 20.22초 | 27.6초 |
| B | 872 | 12.61초 | 20.02초 | 20.25초 | 22.5초 |

참고: 오류·미탐색 수와 3라운드 종료 시점 VP 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Geodens | 6 | -1.7 | [-9.3, +6.0] | 0 | 0 | 0 / 0 | 0 / 0 | 145 / 133 |
| Taklons | 6 | +1.3 | [-3.6, +6.2] | 0 | 0 | 0 / 0 | 0 / 0 | 138 / 145 |
| Terrans | 6 | -0.2 | [-10.8, +10.4] | 0 | 0 | 0 / 0 | 0 / 0 | 137 / 153 |
| Xenos | 6 | -3.2 | [-10.0, +3.7] | 0 | 0 | 0 / 0 | 0 / 0 | 191 / 194 |
| **전체 (좌석 평균)** | 6 | -0.9 | [-6.0, +4.1] | 0 | 0 | 0 / 0 | 0 / 0 | 611 / 625 |

<sub>agentmaco · 커밋 dd9dce5 · 2026-10-12T15:40:45+09:00 → 2026-10-12T17:15:54+09:00</sub>
