# 122-bc-v4-epochs-93 — 완료

사용자 2026-11-13 「codex 이상 없으면 추천대로 진행해」 + 코덱스 이상 없음(E166 (ㄱ), 11-18): 121a의 all 팔이 9 epoch에서 검증 손실 최저(마지막 점)라 더 긴 학습이 미측정 → epoch 길이 측정 + 93판 전체 자료 체크포인트를 한 번에. 대국 없음, 교사 판정 아님. 스크립트 lab/scratch_v4_epochs.py(6c4ace7, 큐 전에 커밋; 시작할 때 자기 파일에 미커밋 차이가 있거나 체크포인트 폴더가 이미 있으면 거부, 커밋 id를 지표 script_commit에 적음 — E162 규칙). 자료: 121a와 같은 shard(runs/bc-114-v4-shards-fc19 + runs/bc-119-v4-shards-fc19-c4096, 93판 28,098결정, 엔진 fc19671c4278), export 없음. 순서: ① 121a와 같은 쿼텟 층화 5겹, 겹마다 all 팔(그 겹의 학습 판 전부 72–77판; tools/bc_train.py의 망·학습 스텝 그대로 — 폭 256, lr 0.001, 배치 256, torch 시드 0·배치 순서 시드 0, shard 순서대로)을 18 epoch까지, epoch마다 검증 손실과 검증 결정별 적중 기록 ② 같은 설정으로 93판 전부를 18 epoch 학습하며 epoch마다 체크포인트 저장(runs/bc-93-v4-w256-fc19/epoch-01…18, bc_train과 같은 inference.pt + metadata.json; .partial에 쓰고 끝나면 이름 변경; 작업 트리, git 밖). 점검(사전 등록): (가) epoch 1–9는 121a all 팔과 같은 계산 → epoch 9의 겹별 손실·정확도가 121a 값(손실 2.0816·2.0940·2.1144·2.1069·2.1488, 정확도 40.52·40.07·36.47·38.07·39.17%)과 넷째 자리까지 같아야 함(identical_to_121a); 다르면 결정성 깨짐으로 보고하고 121a와의 비교는 쓰지 않음(곡선 자체는 읽음) (나) 마지막 epoch 체크포인트를 다시 읽어 같은 손실·적중(assert) (다) 학습 손실 유한(assert). 사전 등록 읽기: 체크포인트 epoch = 겹 평균 검증 손실이 최저인 epoch(bc_train의 규칙, 117). 최저가 18번째(마지막)면 「아직 안 꺾임」 — 18 epoch 체크포인트를 쓰고 더 긴 학습은 미측정으로 남김(연장은 따로 결정). 정확도: epoch별 판별 정확도(검증 93판 평균)와 epoch 9 대비 짝 차이(93판, t 95% 구간, 좋음/같음/나쁨 판 수, 겹별)를 전부 보고; 주 비교 둘 — (i) 규칙으로 고른 epoch − epoch 9 (ii) epoch 18 − epoch 9: 0 위 → 9 epoch보다 긴 학습이 모방 정확도를 올림, 0 포함 → 미확인(9 epoch와 구별 안 됨), 0 아래 → 긴 학습이 해침. 정확도 최고 epoch가 손실 최저 epoch와 다르면 둘의 짝 차이를 보고: 0 포함 → 손실 규칙 epoch 그대로, 0 위 → 후보 둘(정책 교사는 argmax로 두므로 정확도, PPO 시작값은 분포라 손실)로 보고하고 선택은 정리 턴에서 사용자에게 — 자동 규칙 없음. 보정 없음. 미리 적는 한계: 18개 epoch 중 검증 판으로 고른 값이라 그 epoch의 수치는 낙관적(참고), 시드 1개, 겹 곡선은 72–77판·전체 학습은 93판(epoch당 스텝 약 25% 많음)이라 epoch 수로 옮기는 것이지 스텝 수가 아님, 전체 학습 모델은 자기 검증이 없음, metadata 용량은 기본 2048(E165 (가)(나)(다) 미결정 — 가중치는 용량과 무관), OfflinePolicy 로딩·대국은 정리 턴의 스모크 시드(E158·E164 시드)에서 확인하고 여기서는 안 함. 스모크(봇 턴, 겹 0과 전체 학습을 2 epoch): 겹 0 스텝 182·손실 2.3406 → 2.2228·정확도 31.05 → 34.48%, 전체 228스텝·학습 손실 2.4007 → 2.1873, 다시 읽기 같음, 83초. 예상 ≈ 40분(겹당 ≈ 5.5분 × 5 + 전체 ≈ 7분; 스모크 ≈ 0.2초/스텝), 작업 트리 venv(lab venv에 torch 없음).

종료 코드 0

```
loaded: games 93 {'geo-quartet': 4, 'quartet-a': 20, 'quartet-b': 18, 'quartet-c': 18, 'quartet-d': 17, 'quartet-e': 16} | decisions 28098 | script commit 6c4ace743876 | seconds 2
{"fold": 0, "val_games": 21, "val_decisions": 6252, "train_games": 72, "train_decisions": 21846, "steps": 1638, "loss": [2.3406, 2.2228, 2.1781, 2.1539, 2.1438, 2.1413, 2.1039, 2.1308, 2.0816, 2.1018, 2.1216, 2.1624, 2.1098, 2.1449, 2.1386, 2.1578, 2.2048, 2.2324], "accuracy": [0.3105, 0.3448, 0.3591, 0.3664, 0.3797, 0.3666, 0.3866, 0.3976, 0.4052, 0.3981, 0.3965, 0.3852, 0.4184, 0.3916, 0.4071, 0.4096, 0.4074, 0.3983], "seconds": 340}
{"fold": 1, "val_games": 20, "val_decisions": 5922, "train_games": 73, "train_decisions": 22176, "steps": 1674, "loss": [2.3065, 2.2166, 2.1508, 2.1255, 2.1308, 2.0931, 2.0801, 2.1002, 2.094, 2.1096, 2.1302, 2.1412, 2.1455, 2.1623, 2.2324, 2.1905, 2.186, 2.1676], "accuracy": [0.3322, 0.3386, 0.3627, 0.3823, 0.3833, 0.382, 0.3948, 0.3975, 0.4007, 0.3995, 0.4017, 0.3994, 0.4113, 0.3961, 0.3897, 0.3862, 0.3955, 0.3994], "seconds": 717}
{"fold": 2, "val_games": 19, "val_decisions": 5859, "train_games": 74, "train_decisions": 22239, "steps": 1692, "loss": [2.3318, 2.2222, 2.1782, 2.1484, 2.1617, 2.1284, 2.0847, 2.0925, 2.1144, 2.1273, 2.123, 2.119, 2.1086, 2.1695, 2.2088, 2.2271, 2.2257, 2.2119], "accuracy": [0.3033, 0.3267, 0.3446, 0.353, 0.3693, 0.3762, 0.3857, 0.3878, 0.3647, 0.3699, 0.3891, 0.3893, 0.3827, 0.3733, 0.3791, 0.3825, 0.3919, 0.392], "seconds": 1052}
{"fold": 3, "val_games": 17, "val_decisions": 5140, "train_games": 76, "train_decisions": 22958, "steps": 1782, "loss": [2.3094, 2.2397, 2.1955, 2.1501, 2.1396, 2.1316, 2.1293, 2.1218, 2.1069, 2.1306, 2.1423, 2.1564, 2.1846, 2.1959, 2.1583, 2.2091, 2.2491, 2.2088], "accuracy": [0.3078, 0.3263, 0.344, 0.3603, 0.3566, 0.3607, 0.3726, 0.3751, 0.3807, 0.379, 0.3726, 0.3646, 0.377, 0.3751, 0.3807, 0.387, 0.379, 0.3907], "seconds": 1457}
{"fold": 4, "val_games": 16, "val_decisions": 4925, "train_games": 77, "train_decisions": 23173, "steps": 1782, "loss": [2.2815, 2.1854, 2.156, 2.1603, 2.1282, 2.0945, 2.1611, 2.1649, 2.1488, 2.1014, 2.1083, 2.178, 2.199, 2.1302, 2.2513, 2.294, 2.2157, 2.3101], "accuracy": [0.3267, 0.3549, 0.3598, 0.319, 0.3699, 0.3852, 0.3781, 0.3797, 0.3917, 0.3876, 0.3933, 0.3819, 0.3882, 0.3972, 0.3805, 0.3769, 0.3957, 0.3771], "seconds": 1854}
epoch  1: loss 2.3140 (train 2.4384) | per-game accuracy 0.3153 | against epoch 9 -0.0737 [-0.0799, -0.0675] games 0/0/93
epoch  2: loss 2.2173 (train 2.2272) | per-game accuracy 0.3375 | against epoch 9 -0.0515 [-0.0583, -0.0448] games 7/1/85
epoch  3: loss 2.1717 (train 2.1279) | per-game accuracy 0.3540 | against epoch 9 -0.0350 [-0.0404, -0.0295] games 7/2/84
epoch  4: loss 2.1476 (train 2.0572) | per-game accuracy 0.3576 | against epoch 9 -0.0314 [-0.0381, -0.0248] games 14/3/76
epoch  5: loss 2.1408 (train 2.0027) | per-game accuracy 0.3718 | against epoch 9 -0.0172 [-0.0236, -0.0107] games 24/4/65
epoch  6: loss 2.1178 (train 1.9695) | per-game accuracy 0.3734 | against epoch 9 -0.0156 [-0.0222, -0.0090] games 21/2/70
epoch  7: loss 2.1118 (train 1.9211) | per-game accuracy 0.3840 | against epoch 9 -0.0050 [-0.0104, +0.0003] games 39/3/51
epoch  8: loss 2.1220 (train 1.8914) | per-game accuracy 0.3877 | against epoch 9 -0.0013 [-0.0066, +0.0039] games 44/4/45
epoch  9: loss 2.1091 (train 1.8487) | per-game accuracy 0.3890 | against epoch 9 +0.0000 [+0.0000, +0.0000] games 0/93/0
epoch 10: loss 2.1141 (train 1.8171) | per-game accuracy 0.3869 | against epoch 9 -0.0021 [-0.0069, +0.0026] games 38/6/49
epoch 11: loss 2.1251 (train 1.7894) | per-game accuracy 0.3905 | against epoch 9 +0.0015 [-0.0047, +0.0078] games 41/1/51
epoch 12: loss 2.1514 (train 1.7608) | per-game accuracy 0.3846 | against epoch 9 -0.0045 [-0.0106, +0.0017] games 41/1/51
epoch 13: loss 2.1495 (train 1.7396) | per-game accuracy 0.3959 | against epoch 9 +0.0069 [+0.0015, +0.0123] games 55/5/33
epoch 14: loss 2.1606 (train 1.7142) | per-game accuracy 0.3864 | against epoch 9 -0.0026 [-0.0085, +0.0032] games 39/4/50
epoch 15: loss 2.1979 (train 1.6898) | per-game accuracy 0.3876 | against epoch 9 -0.0014 [-0.0072, +0.0044] games 44/1/48
epoch 16: loss 2.2157 (train 1.6640) | per-game accuracy 0.3885 | against epoch 9 -0.0005 [-0.0063, +0.0054] games 43/5/45
epoch 17: loss 2.2162 (train 1.6433) | per-game accuracy 0.3939 | against epoch 9 +0.0049 [-0.0012, +0.0110] games 48/5/40
epoch 18: loss 2.2262 (train 1.6168) | per-game accuracy 0.3917 | against epoch 9 +0.0027 [-0.0031, +0.0085] games 44/2/47
selection {"rule": "the epoch with the lowest fold-mean validation loss", "checkpoint_epoch": 9, "lowest_loss_epoch": 9, "highest_accuracy_epoch": 13, "lowest_loss_epoch_per_fold": [9, 7, 7, 9, 6], "lowest_loss_is_the_last_epoch": false, "highest_accuracy_minus_lowest_loss": {"first": 13, "second": 9, "mean": 0.0069, "low": 0.0015, "high": 0.0123, "t": 2.55, "n": 93, "better": 55, "equal": 5, "worse": 33, "per_fold": [0.0129, 0.0096, 0.0168, -0.0054, -0.0029]}}
check against 121a {"epoch": 9, "fold_loss": [2.0816, 2.094, 2.1144, 2.1069, 2.1488], "fold_accuracy": [0.4052, 0.4007, 0.3647, 0.3807, 0.3917], "reference_121a": {"loss": [2.0816, 2.094, 2.1144, 2.1069, 2.1488], "accuracy": [0.4052, 0.4007, 0.3647, 0.3807, 0.3917]}, "max_abs_difference_from_121a": 0.0, "identical_to_121a": true}
full {"directory": "gaia-rl/runs/bc-93-v4-w256-fc19", "epochs": 18, "games": 93, "decisions": 28098, "steps": 2052, "train_loss": [2.4007, 2.1873, 2.0869, 2.0193, 1.9756, 1.9281, 1.888, 1.8601, 1.8211, 1.7984, 1.7531, 1.7278, 1.7219, 1.691, 1.6626, 1.6295, 1.6211, 1.6081], "capacity_in_metadata": 2048, "last_epoch_read_back_equal": true} | seconds 2304
checkpoints gaia-rl/runs/bc-93-v4-w256-fc19/epoch-01 ... epoch-18 | checkpoint epoch by the rule: 9 | seconds 2304
```

지표

```json
{
 "script": "gaia-rl/lab/scratch_v4_epochs.py",
 "script_commit": "6c4ace7438766bc2bbb4fe27bb50599651a8ca69",
 "engine_build_id": "fc19671c4278246becaa0710511b6d1a37b4049d58290aa8450c1c9f2c9041db",
 "games": 93,
 "decisions": 28098,
 "games_per_quartet": {
  "geo-quartet": 4,
  "quartet-a": 20,
  "quartet-b": 18,
  "quartet-c": 18,
  "quartet-d": 17,
  "quartet-e": 16
 },
 "fold_val_games": [
  21,
  20,
  19,
  17,
  16
 ],
 "settings": {
  "width": 256,
  "epochs": 18,
  "lr": 0.001,
  "batch": 256,
  "seed": 0
 },
 "epochs": [
  {
   "epoch": 1,
   "loss_fold_mean": 2.314,
   "train_loss_fold_mean": 2.4384,
   "fold_loss": [
    2.3406,
    2.3065,
    2.3318,
    2.3094,
    2.2815
   ],
   "fold_accuracy": [
    0.3105,
    0.3322,
    0.3033,
    0.3078,
    0.3267
   ],
   "per_game": 0.3153,
   "decision_weighted": 0.3159,
   "decision_weighted_114_games": 0.3114,
   "decision_weighted_119_games": 0.3203,
   "against_reference": {
    "first": 1,
    "second": 9,
    "mean": -0.0737,
    "low": -0.0799,
    "high": -0.0675,
    "t": -23.67,
    "n": 93,
    "better": 0,
    "equal": 0,
    "worse": 93,
    "per_fold": [
     -0.0962,
     -0.0691,
     -0.061,
     -0.0736,
     -0.0651
    ]
   }
  },
  {
   "epoch": 2,
   "loss_fold_mean": 2.2173,
   "train_loss_fold_mean": 2.2272,
   "fold_loss": [
    2.2228,
    2.2166,
    2.2222,
    2.2397,
    2.1854
   ],
   "fold_accuracy": [
    0.3448,
    0.3386,
    0.3267,
    0.3263,
    0.3549
   ],
   "per_game": 0.3375,
   "decision_weighted": 0.3381,
   "decision_weighted_114_games": 0.3351,
   "decision_weighted_119_games": 0.341,
   "against_reference": {
    "first": 2,
    "second": 9,
    "mean": -0.0515,
    "low": -0.0583,
    "high": -0.0448,
    "t": -15.13,
    "n": 93,
    "better": 7,
    "equal": 1,
    "worse": 85,
    "per_fold": [
     -0.0605,
     -0.0632,
     -0.0389,
     -0.0553,
     -0.0363
    ]
   }
  },
  {
   "epoch": 3,
   "loss_fold_mean": 2.1717,
   "train_loss_fold_mean": 2.1279,
   "fold_loss": [
    2.1781,
    2.1508,
    2.1782,
    2.1955,
    2.156
   ],
   "fold_accuracy": [
    0.3591,
    0.3627,
    0.3446,
    0.344,
    0.3598
   ],
   "per_game": 0.354,
   "decision_weighted": 0.3542,
   "decision_weighted_114_games": 0.349,
   "decision_weighted_119_games": 0.3592,
   "against_reference": {
    "first": 3,
    "second": 9,
    "mean": -0.035,
    "low": -0.0404,
    "high": -0.0295,
    "t": -12.78,
    "n": 93,
    "better": 7,
    "equal": 2,
    "worse": 84,
    "per_fold": [
     -0.0466,
     -0.0373,
     -0.0207,
     -0.0371,
     -0.0315
    ]
   }
  },
  {
   "epoch": 4,
   "loss_fold_mean": 2.1476,
   "train_loss_fold_mean": 2.0572,
   "fold_loss": [
    2.1539,
    2.1255,
    2.1484,
    2.1501,
    2.1603
   ],
   "fold_accuracy": [
    0.3664,
    0.3823,
    0.353,
    0.3603,
    0.319
   ],
   "per_game": 0.3576,
   "decision_weighted": 0.3575,
   "decision_weighted_114_games": 0.3568,
   "decision_weighted_119_games": 0
```

<sub>agentmaco · 커밋 99b8394 · 2026-11-18T14:49:41+09:00 → 2026-11-18T15:28:08+09:00</sub>
