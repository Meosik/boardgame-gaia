# 048-guide-r1-charge3-lf-more-vm-lf-ts-reach — 완료

사용자 확인(2026-10-12 "진행해"): A = guide_r1_charge3_lf_more_vm_lf_ts(047 B), B = A + reach(셋업 결정은 서로 다른 자리·부스터를 최대 4개 비교·셋업만 50초, 상대 인접 자리는 차단 대신 먼저 비교, 확장 가치·부스터 5에 항해 다음 사거리 단계 반영, 연구는 한 트랙 집중 또는 항해 2 먼저 순서). 볼 판 자동 게시 첫 적용. 새 시드 6쌍, 3라운드에서 종료. 판정은 1–3라운드 충전량(1점 = 1.5충전).

A: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json`
B: `tools/teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-cap20.json`
시드 6개 × 좌석 교대 2판 (비교 기본값 2, 스펙 파일에 있으면 그 값), 3라운드에서 종료

**1–3라운드 충전량 (판정 기준)** — 1R 시작부터 4R 시작까지 얻은 충전, 1점 = 1.5충전

| 종족 | 쌍 | B−A 충전 | 95% 신뢰구간 | A 평균 | B 평균 |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | +17.7 | [-44.2, +79.5] | 165.2 | 182.9 |
| Taklons | 6 | -24.8 | [-52.3, +2.7] | 157.4 | 132.6 |
| Terrans | 6 | -38.4 | [-89.4, +12.6] | 179.5 | 141.1 |
| Xenos | 6 | +2.0 | [-57.0, +61.1] | 125.6 | 127.7 |
| **전체 (좌석 평균)** | 6 | -10.9 | [-57.0, +35.2] |  |  |

다시보기 게시 실패 (pair-005/game-1-A03)

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
| A | 872 | 12.28초 | 20.01초 | 20.27초 | 24.0초 |
| B | 847 | 16.05초 | 20.04초 | 22.84초 | 57.3초 |

참고: 오류·미탐색 수와 3라운드 종료 시점 VP 차이 (판정에 쓰지 않음)

| 종족 | 완료 쌍 | 평균 점수 차이 (B−A) | 95% 신뢰구간 | 오류 중단 판 | 타임아웃 중단 판 | 폴백 타임아웃 결정 A / B | 연방 후보 누락 A / B | 비교 미탐색 결정 A / B |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Geodens | 6 | +5.5 | [-5.9, +16.9] | 0 | 0 | 0 / 0 | 0 / 0 | 158 / 148 |
| Taklons | 6 | -3.2 | [-9.6, +3.3] | 0 | 0 | 0 / 0 | 0 / 0 | 153 / 145 |
| Terrans | 6 | -2.8 | [-12.5, +6.8] | 0 | 0 | 0 / 0 | 0 / 0 | 156 / 166 |
| Xenos | 6 | +1.7 | [-6.5, +9.8] | 0 | 0 | 0 / 0 | 0 / 0 | 178 / 192 |
| **전체 (좌석 평균)** | 6 | +0.3 | [-2.9, +3.5] | 0 | 0 | 0 / 0 | 0 / 0 | 645 / 651 |

<sub>agentmaco · 커밋 fe5d895 · 2026-10-12T12:13:39+09:00 → 2026-10-12T13:56:39+09:00</sub>
