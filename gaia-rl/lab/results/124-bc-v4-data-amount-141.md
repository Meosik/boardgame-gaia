# 124-bc-v4-data-amount-141 — 완료

사용자 2026-11-13 「codex 이상 없으면 추천대로 진행해」 + 코덱스 이상 없음(E182 (ㄱ), 11-19): 123 큐 note가 정해 둔 다음 단계 — 114+119+123 141판(42,148결정, 셋 다 엔진 fc19671c4278에서 엄격 재생)을 인코딩 4로 쓰는 자료량 한 단계 더 + epoch 곡선 + 141판 전체 자료 체크포인트를 한 번에. 대국 없음, 교사 판정 아님. 스크립트 lab/scratch_v4_amount_141.py(8354afb, 큐 전에 커밋; 시작할 때 자기 파일에 미커밋 차이가 있거나 체크포인트 폴더가 이미 있으면 거부, 커밋 id를 지표 script_commit에 적음 — E162 규칙). 순서: ① bc_dataset.py export --encoding 4 --capacity 4096으로 123 manifest(runs/bc-123-fc19, 48판 14,050결정) → runs/bc-123-v4-shards-fc19-c4096(.partial에 쓰고 끝나면 이름 변경; 123에 후보 2,417개 결정 1건), 114·119 shard는 120·121a 것 그대로(shard 결정 수가 manifest와 다르면 assert 실패) ② 141판을 쿼텟 층화 5겹으로(쿼텟 안 k번째 판 → 겹 k mod 5, 114 → 119 → 123 순서라 114·119 판은 121a·122의 겹 그대로) ③ 겹마다 2팔 — tools/bc_train.py의 망·학습 스텝 그대로(폭 256, lr 0.001, 배치 256, torch 시드 0·배치 순서 시드 0, shard 순서대로), 검증 = 그 겹의 빼 둔 판: all(학습 판 전부 약 113판, 18 epoch, epoch마다 검증 손실·검증 결정별 적중) · twothirds-steps(쿼텟 안 학습 판 셋 중 둘 = 약 75판 — 셋째·여섯째… 판을 뺌, 무작위 추출 없음 — 같은 겹 all의 9 epoch 스텝 수에서 정지) ④ 같은 설정으로 141판 전부를 18 epoch 학습하며 epoch마다 체크포인트(runs/bc-141-v4-w256-fc19/epoch-01…18, bc_train과 같은 inference.pt + metadata.json; .partial에 쓰고 끝나면 이름 변경; 작업 트리, git 밖). 사전 등록 읽기 — 자료량(주 비교 1개): all의 epoch 9 − twothirds-steps(같은 스텝 수)의 판별 정확도 차, 검증 141판 짝, t 95% 구간, 좋음/같음/나쁨 판 수·겹별·쿼텟별·수집(114/119/123)별 보고. 0 위 → 약 113판에서도 판 수가 한계 중 하나(같은 방식 추가 수집이 여전히 지렛대 후보; 몇 판 더는 사용자 결정), 0 포함 → 약 75판을 넘어서는 이득 미확인 — 포화로 읽지 않고(구간이 0을 포함해도 큰 이득을 배제하지 못함, 121 토론 정정 그대로) 구간 상한을 보고만 함, 0 아래 → 보고하고 원인(부분집합·겹 흔들림)을 먼저 봄. 121a ①(약 74 대 37판 +2.32pt [+1.68, +2.96])과는 판 수 비가 달라(2배 대 1.5배) 크기를 직접 비교하지 않음. epoch(122와 같은 읽기): 체크포인트 epoch = 겹 평균 검증 손실이 최저인 epoch(bc_train 규칙); 최저가 18번째면 「아직 안 꺾임」 — 18 epoch 체크포인트, 더 긴 학습은 미측정으로 남김. epoch별 판별 정확도와 epoch 9 대비 짝 차이(141판)를 전부 보고; (i) 규칙 epoch − 9 (ii) 18 − 9: 0 위 → 9 epoch보다 긴 학습이 모방 정확도를 올림, 0 포함 → 미확인, 0 아래 → 해침. 정확도 최고 epoch ≠ 손실 최저 epoch면 둘의 짝 차이를 보고: 0 포함 → 손실 규칙 epoch 그대로, 0 위 → 후보 둘을 정리 턴에서 사용자에게(자동 규칙 없음; E171 (ㄱ)의 93판 epoch 선택도 답 대기 중). 보정 없음. 점검: all 팔 epoch별 스텝 수 = epoch당 스텝 × k(assert), twothirds-steps 스텝 수 = all의 9 epoch 스텝 수(assert), 검증 결정 전부 채점·두 팔 같은 결정(assert), 마지막 epoch 체크포인트를 다시 읽어 같은 손실·적중(assert), 학습 손실 유한(assert). all 팔의 epoch 1–9는 122와 같은 계산이 아님(학습 판이 다름) → 122 값과의 일치 점검 없음; 수집별 결정 가중 정확도(114·119·123 판)는 참고로 보고. 미리 적는 한계: 3분의 2 부분집합이 겹 사이에 겹침(구간에 부분집합 흔들림 없음), torch 시드 1개, 고른 epoch의 수치는 검증 판으로 고른 값이라 낙관적(참고), 겹 곡선은 약 113판·전체 학습은 141판(epoch당 스텝 약 25% 많음)이라 epoch 수로 옮기는 것, 전체 학습 모델은 자기 검증 없음, metadata 용량은 기본 2048(대국은 실행 용량 4096, db997d9), 폴백 행 12/42,148(검색 안 한 root 1위 표지)은 그대로 포함, 모방 정확도는 실력 아님(1–3R 충전은 BC vs 교사 A/B 몫). 알고 넣는 것: 이 뒤 env.rs 접미사 구현(E177·E181)으로 엔진 빌드 id가 바뀌면 이 체크포인트는 재빌드 뒤 다시 학습해야 함(120과 같은 재현 점검, ≈ 20분) — 자료량·epoch 측정값은 그대로 유효. 스모크(봇 턴, 123의 300결정·겹 0·2 epoch): epoch당 93스텝, twothirds-steps 93스텝·학습 51판(all 73판), 전체 232스텝·학습 손실 2.4000 → 2.1883, 다시 읽기 같음, 122초. 예상 ≈ 1.5시간(export ≈ 6분 + 겹당 ≈ 13분 × 5 + 전체 ≈ 10분; 스모크 ≈ 0.2초/스텝), 작업 트리 venv(lab venv에 torch 없음). 실행 중에는 작업 트리의 gaia_rl·엔진 소스를 고치지 않음(E169).

종료 코드 0

```
14050 samples in 8 shards -> gaia-rl/runs/bc-123-v4-shards-fc19-c4096.partial
exported gaia-rl/runs/bc-123-v4-shards-fc19-c4096 | seconds 382
loaded: games 141 {'geo-quartet': 6, 'quartet-a': 30, 'quartet-b': 28, 'quartet-c': 27, 'quartet-d': 26, 'quartet-e': 24} | decisions 42148 | script commit 8354afbb01cc | seconds 385
{"fold": 0, "val_games": 31, "val_decisions": 9231, "train_games": 110, "train_decisions": 32917, "steps_per_epoch": 138, "loss": [2.2628, 2.1751, 2.1304, 2.1577, 2.1629, 2.1034, 2.0945, 2.108, 2.1124, 2.1017, 2.108, 2.1499, 2.1377, 2.2036, 2.1839, 2.2195, 2.235, 2.1974], "accuracy": [0.3451, 0.3619, 0.3734, 0.3717, 0.3802, 0.3956, 0.3965, 0.4006, 0.398, 0.4021, 0.4003, 0.3954, 0.3993, 0.392, 0.3965, 0.3894, 0.4003, 0.3981], "twothirds-steps": {"train_games": 75, "train_decisions": 22464, "steps": 1242, "loss": [2.3187, 2.1927, 2.1862, 2.1159, 2.1365, 2.2011, 2.1673, 2.2194, 2.1387], "accuracy": [0.3209, 0.3512, 0.3653, 0.3796, 0.3861, 0.3621, 0.3709, 0.3493, 0.3844]}, "seconds": 1151}
{"fold": 1, "val_games": 29, "val_decisions": 8602, "train_games": 112, "train_decisions": 33546, "steps_per_epoch": 141, "loss": [2.237, 2.1518, 2.124, 2.1009, 2.097, 2.0917, 2.0878, 2.0676, 2.118, 2.1459, 2.1533, 2.1797, 2.1685, 2.1989, 2.2192, 2.171, 2.2167, 2.2475], "accuracy": [0.3443, 0.365, 0.3762, 0.3882, 0.3877, 0.4023, 0.4004, 0.4112, 0.4028, 0.3962, 0.3941, 0.3913, 0.4046, 0.4012, 0.3965, 0.4066, 0.3943, 0.4004], "twothirds-steps": {"train_games": 76, "train_decisions": 22782, "steps": 1269, "loss": [2.2436, 2.1877, 2.1375, 2.1474, 2.1017, 2.1143, 2.1664, 2.1774, 2.1753], "accuracy": [0.3372, 0.3567, 0.3664, 0.3681, 0.3799, 0.3855, 0.3654, 0.3777, 0.3862]}, "seconds": 1927}
{"fold": 2, "val_games": 28, "val_decisions": 8444, "train_games": 113, "train_decisions": 33704, "steps_per_epoch": 142, "loss": [2.247, 2.1603, 2.1062, 2.096, 2.1043, 2.0789, 2.0574, 2.0578, 2.073, 2.1374, 2.1233, 2.1197, 2.125, 2.1023, 2.1138, 2.1477, 2.1203, 2.1583], "accuracy": [0.3302, 0.3565, 0.3877, 0.3796, 0.3752, 0.3913, 0.3909, 0.4028, 0.3966, 0.3953, 0.3971, 0.4041, 0.3947, 0.401, 0.4043, 0.4012, 0.4018, 0.4027], "twothirds-steps": {"train_games": 77, "train_decisions": 23020, "steps": 1278, "loss": [2.3287, 2.1693, 2.1396, 2.1358, 2.0919, 2.0942, 2.1025, 2.1399, 2.1314], "accuracy": [0.3022, 0.3572, 0.3678, 0.3663, 0.3774, 0.3759, 0.3791, 0.3735, 0.376]}, "seconds": 2709}
{"fold": 3, "val_games": 27, "val_decisions": 7989, "train_games": 114, "train_decisions": 34159, "steps_per_epoch": 145, "loss": [2.2616, 2.1607, 2.1213, 2.1006, 2.0846, 2.0501, 2.0425, 2.0667, 2.0442, 2.0679, 2.1106, 2.1424, 2.139, 2.2612, 2.2171, 2.2025, 2.2698, 2.25], "accuracy": [0.3307, 0.3602, 0.3696, 0.3723, 0.3724, 0.3918, 0.3975, 0.3917, 0.4033, 0.4052, 0.3973, 0.3905, 0.3939, 0.3837, 0.3964, 0.393, 0.3942, 0.4027], "twothirds-steps": {"train_games": 78, "train_decisions": 23487, "steps": 1305, "loss": [2.232, 2.165, 2.138, 2.0972, 2.1098, 2.1278, 2.0874, 2.1196, 2.153], "accuracy": [0.3396, 0.3614, 0.3487, 0.3748, 0.3755, 0.395, 0.3888, 0.3838, 0.3689]}, "seconds": 3605}
{"fold": 4, "val_games": 26, "val_decisions": 7882, "train_games": 115, "train_decisions": 34266, "steps_per_epoch": 147, "loss": [2.2195, 2.14, 2.1195, 2.1664, 2.1366, 2.1825, 2.1609, 2.1369, 2.0951, 2.0932, 2.2457, 2.1681, 2.182, 2.1852, 2.1896, 2.1769, 2.1974, 2.2493], "accuracy": [0.3493, 0.367, 0.3799, 0.3631, 0.3769, 0.355, 0.3734, 0.3851, 0.4005, 0.4032, 0.3701, 0.3851, 0.3861, 0.3825, 0.3881, 0.396, 0.392, 0.388], "twothirds-steps": {"train_games": 79, "train_decisions": 23570, "steps": 1323, "loss": [2.2262, 2.1556, 2.1363, 2.0907, 2.1202, 2.1383, 2.1866, 2.2055, 2.175], "accuracy": [0.3448, 0.3599, 0.3658, 0.3871, 0.3844, 0.3838, 0.3731, 0.3664, 0.3627]}, "seconds": 4509}
amount {"comparison": "all at epoch 9 minus twothirds-steps at the same step count", "all": {"per_game": 0.4003, "decision_weighted": 0.4002, "train_games": [110, 112, 113, 114, 115], "fold_loss": [2.1124, 2.118, 2.073, 2.0442, 2.0951], "fold_accuracy": [0.398, 0.4028, 0.3966, 0.4033, 0.4005]}, "twothirds-steps": {"per_game": 0.3765, "decision_weighted": 0.3761, "train_games": [75, 76, 77, 78, 79], "fold_loss": [2.1387, 2.1753, 2.1314, 2.153, 2.175], "fold_accuracy": [0.3844, 0.3862, 0.376, 0.3689, 0.3627], "fold_loss_curve": [[2.3187, 2.1927, 2.1862, 2.1159, 2.1365, 2.2011, 2.1673, 2.2194, 2.1387], [2.2436, 2.1877, 2.1375, 2.1474, 2.1017, 2.1143, 2.1664, 2.1774, 2.1753], [2.3287, 2.1693, 2.1396, 2.1358, 2.0919, 2.0942, 2.1025, 2.1399, 2.1314], [2.232, 2.165, 2.138, 2.0972, 2.1098, 2.1278, 2.0874, 2.1196, 2.153], [2.2262, 2.1556, 2.1363, 2.0907, 2.1202, 2.1383, 2.1866, 2.2055, 2.175]]}, "difference": {"mean": 0.0238, "low": 0.0188, "high": 0.0289, "t": 9.38, "n": 141, "better": 110, "equal": 6, "worse": 25, "per_fold": [0.0141, 0.015, 0.0212, 0.0345, 0.0371], "per_quartet": {"geo-quartet": [0.0328, 6], "quartet-a": [0.0253, 30], "quartet-b": [0.0247, 28], "quartet-c": [0.0202, 27], "quartet-d": [0.0206, 26], "quartet-e": [0.0262, 24]}, "per_source": {"114": [0.0213, 46], "119": [0.0275, 47], "123": [0.0226, 48]}}}
epoch  1: loss 2.2456 (train 2.3830) | per-game accuracy 0.3396 | against epoch 9 -0.0607 [-0.0658, -0.0556] games 3/1/137
epoch  2: loss 2.1576 (train 2.1687) | per-game accuracy 0.3620 | against epoch 9 -0.0382 [-0.0428, -0.0337] games 11/2/128
epoch  3: loss 2.1203 (train 2.0752) | per-game accuracy 0.3770 | against epoch 9 -0.0233 [-0.0279, -0.0188] games 22/10/109
epoch  4: loss 2.1243 (train 2.0193) | per-game accuracy 0.3747 | against epoch 9 -0.0256 [-0.0303, -0.0209] games 22/7/112
epoch  5: loss 2.1171 (train 1.9732) | per-game accuracy 0.3781 | against epoch 9 -0.0222 [-0.0269, -0.0175] games 26/2/113
epoch  6: loss 2.1013 (train 1.9343) | per-game accuracy 0.3876 | against epoch 9 -0.0127 [-0.0176, -0.0078] games 44/11/86
epoch  7: loss 2.0886 (train 1.9006) | per-game accuracy 0.3918 | against epoch 9 -0.0085 [-0.0123, -0.0047] games 47/6/88
epoch  8: loss 2.0874 (train 1.8641) | per-game accuracy 0.3982 | against epoch 9 -0.0021 [-0.0060, +0.0018] games 65/7/69
epoch  9: loss 2.0885 (train 1.8287) | per-game accuracy 0.4003 | against epoch 9 +0.0000 [+0.0000, +0.0000] games 0/141/0
epoch 10: loss 2.1092 (train 1.8005) | per-game accuracy 0.4002 | against epoch 9 -0.0001 [-0.0033, +0.0031] games 67/12/62
epoch 11: loss 2.1482 (train 1.7800) | per-game accuracy 0.3922 | against epoch 9 -0.0081 [-0.0121, -0.0041] games 46/8/87
epoch 12: loss 2.1520 (train 1.7548) | per-game accuracy 0.3932 | against epoch 9 -0.0071 [-0.0111, -0.0031] games 50/10/81
epoch 13: loss 2.1504 (train 1.7230) | per-game accuracy 0.3960 | against epoch 9 -0.0043 [-0.0085, -0.0001] games 54/5/82
epoch 14: loss 2.1902 (train 1.7021) | per-game accuracy 0.3924 | against epoch 9 -0.0079 [-0.0122, -0.0036] games 50/5/86
epoch 15: loss 2.1847 (train 1.6822) | per-game accuracy 0.3968 | against epoch 9 -0.0035 [-0.0075, +0.0006] games 59/7/75
epoch 16: loss 2.1835 (train 1.6592) | per-game accuracy 0.3976 | against epoch 9 -0.0027 [-0.0070, +0.0016] games 62/5/74
epoch 17: loss 2.2079 (train 1.6395) | per-game accuracy 0.3969 | against epoch 9 -0.0034 [-0.0079, +0.0011] games 64/10/67
epoch 18: loss 2.2205 (train 1.6176) | per-game accuracy 0.3988 | against epoch 9 -0.0015 [-0.0059, +0.0028] games 64/9/68
selection {"rule": "the epoch with the lowest fold-mean validation loss", "checkpoint_epoch": 8, "lowest_loss_epoch": 8, "highest_accuracy_epoch": 9, "lowest_loss_epoch_per_fold": [7, 8, 7, 7, 10], "lowest_loss_is_the_last_epoch": false, "highest_accuracy_minus_lowest_loss": {"mean": 0.0021, "low": -0.0018, "high": 0.006, "t": 1.09, "n": 141, "better": 69, "equal": 7, "worse": 65, "per_fold": [-0.0018, -0.0071, -0.0055, 0.0115, 0.0156]}}
full {"directory": "gaia-rl/runs/bc-141-v4-w256-fc19", "epochs": 18, "games": 141, "decisions": 42148, "steps": 3078, "train_loss": [2.3453, 2.1322, 2.0372, 1.9803, 1.9402, 1.9164, 1.892, 1.8641, 1.8256, 1.7951, 1.7584, 1.7342, 1.7141, 1.6707, 1.6429, 1.6231, 1.5944, 1.5868], "capacity_in_metadata": 2048, "last_epoch_read_back_equal": true} | seconds 5178
checkpoints gaia-rl/runs/bc-141-v4-w256-fc19/epoch-01 ... epoch-18 | checkpoint epoch by the rule: 8 | seconds 5178
```

지표

```json
{
 "script": "gaia-rl/lab/scratch_v4_amount_141.py",
 "script_commit": "8354afbb01ccedab77c52fd4ad6884dbc5f528b1",
 "engine_build_id": "fc19671c4278246becaa0710511b6d1a37b4049d58290aa8450c1c9f2c9041db",
 "games": 141,
 "decisions": 42148,
 "games_per_quartet": {
  "geo-quartet": 6,
  "quartet-a": 30,
  "quartet-b": 28,
  "quartet-c": 27,
  "quartet-d": 26,
  "quartet-e": 24
 },
 "games_per_source": {
  "114": 46,
  "119": 47,
  "123": 48
 },
 "fold_val_games": [
  31,
  29,
  28,
  27,
  26
 ],
 "settings": {
  "width": 256,
  "epochs": 18,
  "reference_epoch": 9,
  "lr": 0.001,
  "batch": 256,
  "seed": 0,
  "export_capacity": 4096
 },
 "amount": {
  "comparison": "all at epoch 9 minus twothirds-steps at the same step count",
  "all": {
   "per_game": 0.4003,
   "decision_weighted": 0.4002,
   "train_games": [
    110,
    112,
    113,
    114,
    115
   ],
   "fold_loss": [
    2.1124,
    2.118,
    2.073,
    2.0442,
    2.0951
   ],
   "fold_accuracy": [
    0.398,
    0.4028,
    0.3966,
    0.4033,
    0.4005
   ]
  },
  "twothirds-steps": {
   "per_game": 0.3765,
   "decision_weighted": 0.3761,
   "train_games": [
    75,
    76,
    77,
    78,
    79
   ],
   "fold_loss": [
    2.1387,
    2.1753,
    2.1314,
    2.153,
    2.175
   ],
   "fold_accuracy": [
    0.3844,
    0.3862,
    0.376,
    0.3689,
    0.3627
   ],
   "fold_loss_curve": [
    [
     2.3187,
     2.1927,
     2.1862,
     2.1159,
     2.1365,
     2.2011,
     2.1673,
     2.2194,
     2.1387
    ],
    [
     2.2436,
     2.1877,
     2.1375,
     2.1474,
     2.1017,
     2.1143,
     2.1664,
     2.1774,
     2.1753
    ],
    [
     2.3287,
     2.1693,
     2.1396,
     2.1358,
     2.0919,
     2.0942,
     2.1025,
     2.1399,
     2.1314
    ],
    [
     2.232,
     2.165,
     2.138,
     2.0972,
     2.1098,
     2.1278,
     2.0874,
     2.1196,
     2.153
    ],
    [
     2.2262,
     2.1556,
     2.1363,
     2.0907,
     2.1202,
     2.1383,
     2.1866,
     2.2055,
     2.175
    ]
   ]
  },
  "difference": {
   "mean": 0.0238,
   "low": 0.0188,
   "high": 0.0289,
   "t": 9.38,
   "n": 141,
   "better": 110,
   "equal": 6,
   "worse": 25,
   "per_fold": [
    0.0141,
    0.015,
    0.0212,
    0.0345,
    0.0371
   ],
   "per_quartet": {
    "geo-quartet": [
     0.0328,
     6
    ],
    "quartet-a": [
     0.0253,
     30
    ],
    "quartet-b": [
     0.0247,
     28
    ],
    "quartet-c": [
     0.0202,
     27
    ],
    "quartet-d": [
     0.0206,
     26
    ],
    "quartet-e": [
     0.0262,
     24
    ]
   },
   "per_source": {
    "114": [
     0.0213,
     46
    ],
    "119": [
     0.0275,
     47
    ],
    "123": [
     0.0226,
     48
    ]
   }
  }
 },
 "epochs": [
  {
   "epoch": 1,
   "loss_fold_mean": 2.2456,
   "train_loss_fold_mean": 2.383,
   "fold_loss": [
    2.2628,
    2.237,
    2.247,
    2.2616,
    2.2195
   ],
   "fold_accuracy": [
    0.3451,
    0.3443,
    0.3302,
    0.3307,
    0.3493
   ],
   "per_game": 0.
```

<sub>agentmaco · 커밋 e1cc517 · 2026-11-19T06:59:21+09:00 → 2026-11-19T08:25:42+09:00</sub>
