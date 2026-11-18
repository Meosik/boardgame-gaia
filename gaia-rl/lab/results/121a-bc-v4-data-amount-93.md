# 121a-bc-v4-data-amount-93 — 완료

121 재실행(121은 119 export에서 실패, 3분: 119 20번째 판 quartet-b-98306 5R 매드 안드로이드 결정 하나가 후보 2,257개 — 그중 연방 경로 2,208개 — 로 인코더 용량 2048 초과 = Candidate capacity exceeded; 93판 28,098결정 중 1건, 114 최대 1,461). 고침 0370eff: bc_dataset.py export --capacity(export 인코더 용량만 키움, gaia_rl 패키지 불변 = 체크포인트 그대로 읽힘; 행은 자기 후보 수로 잘리므로 다른 행 불변 — 119 첫 300결정·후보 14,020행이 용량 2048 export와 같음을 봇 턴에서 확인), 스크립트는 export를 .partial 폴더에 쓰고 끝나면 이름을 바꿈(실패한 export가 완성본처럼 남지 않게). 설계·사전 등록 읽기는 121 그대로(아래, 토론 1/1 정정 포함). 고른 수가 2048번째 뒤 후보가 아니어도 이 결정은 용량 2048 정책이 대국에서 평가할 수 없는 행임 — 학습·검증에 그대로 포함(1행). 사용자 2026-11-13 「codex 이상 없으면 추천대로 진행해」 + 코덱스 이상 없음(E162 (ㄱ) 11-17 08:29, E163 ⏩ 뒤 다시 이상 없음) · 사용자 2026-11-18 「진행해」: 114+119 93판(28,098결정, 둘 다 엔진 fc19671c4278에서 엄격 재생; 120이 재빌드 엔진의 114 export가 옛 빌드와 전 행 같음을 보임)을 인코딩 4로 쓰는 자료량 효과 재측정. 대국 없음, 교사 판정 아님. 스크립트 lab/scratch_v4_amount.py(큐 전에 커밋됨; 시작할 때 자기 파일에 미커밋 차이가 있으면 거부하고 커밋 id를 지표 script_commit에 적음 — E162 규칙). 순서: ① bc_dataset.py export --encoding 4로 119 manifest(runs/bc-119-fc19) → runs/bc-119-v4-shards-fc19-c4096, export 인코더 용량 --capacity 4096 (114 shard는 120의 runs/bc-114-v4-shards-fc19 그대로; shard 결정 수가 manifest와 다르면 assert 실패) ② 93판을 쿼텟 층화 5겹으로(쿼텟 안 k번째 판 → 겹 k mod 5, 114 판이 앞이라 114 판은 117·118·120의 겹 그대로) ③ 겹마다 5팔 — tools/bc_train.py의 망·학습 스텝 그대로(폭 256, lr 0.001, 배치 256, torch 시드 0·배치 순서 시드 0, shard 순서대로), 검증 = 그 겹의 빼 둔 판: all(학습 판 전부 약 74판, 9 epoch) · half-steps(쿼텟 안 하나 걸러 약 37판, 같은 겹 all의 스텝 수에서 정지) · quarter-steps(쿼텟 안 넷에 하나 약 19판, 같은 스텝 수) · half · quarter(같은 부분집합, 자기 9 epoch = 스텝 적음, 참고). quarter ⊂ half ⊂ all, 무작위 추출 없음. 사전 등록 보고: 팔별 판별 정확도 평균·결정 가중 정확도(전체, 114 판만, 119 판만)·겹별 손실과 정확도·스텝 수·학습 판 수·9점 검증 손실 곡선과 최저점; 비교별 판별 정확도 차(마지막 점, 검증 93판으로 짝) 평균·t 95% 구간·좋음/같음/나쁨 판 수·겹별·쿼텟별·114 판/119 판별. 주 비교 셋(같은 스텝 수, 구간으로 읽음): ① all − half-steps(약 74 vs 37판): 0 위 → 74판에서도 판 수가 한계 중 하나 = 같은 방식의 추가 수집 근거(몇 판 더는 사용자 결정), 0 포함 → 37판을 넘어서는 이득 미확인 ② half-steps − quarter-steps(약 37 vs 19판): 117 ③(35 vs 20판, 폭 256, +1.36pt [+0.55, +2.17])의 실제 도구 재현 — 0 위 → 재현, 0 포함 → 미재현 ③ all − quarter-steps(약 74 vs 19판): 전체 폭. 읽기 조합(토론 1/1 코덱스 지적으로 실행 전에 정정): ① 0 위 → 수집을 더 하는 쪽이 다음 지렛대 후보; ① 0 포함 + ② 0 위 → 19→37판 이득 확인, 37→74판 추가 이득 미확인 — 포화(평평해짐)로 읽지 않고 다른 지렛대로 넘어가는 근거로도 쓰지 않음(구간이 0을 포함해도 큰 이득을 배제하지 못함); 포화 판단은 ① 구간 상한이 실용적으로 의미 있는 이득 기준 아래일 때만인데 그 기준은 미리 정한 값이 없어(사용자 수치) 121은 ① 구간 상한을 보고만 함; 둘 다 0 포함 → 이 설정에서 자료량 효과 미확인. 보정 없음(주 비교 3개, t 값을 같이 적음). 참고만: all − half · all − quarter(같은 epoch, 스텝 적음), all 팔의 114 판 결정 가중 정확도 대 118의 36.38%(114만으로 학습, 같은 겹·같은 검증 판이나 스텝 수가 달라 참고), 곡선 최저점(검증 판으로 고른 값). 점검: -steps 팔 스텝 수가 all과 같음(assert), 9점(assert), 검증 결정 전부 채점(assert). 스모크(봇 턴, 119의 300결정·겹 0·1 epoch): 스텝 46·46·46·27·17, 학습 판 37·20·11, 32초. 예상 ≈ 60분(export ≈ 6분 + 겹당 ≈ 10분; 스모크 0.15–0.2초/스텝), 작업 트리 venv(lab venv에 torch 없음). 체크포인트는 안 씀(측정만) — 전체 자료 체크포인트는 이 결과로 epoch를 정한 뒤 따로.

종료 코드 0

```
14257 samples in 8 shards -> gaia-rl/runs/bc-119-v4-shards-fc19-c4096.partial
exported gaia-rl/runs/bc-119-v4-shards-fc19-c4096 | seconds 415
loaded: games 93 {'geo-quartet': 4, 'quartet-a': 20, 'quartet-b': 18, 'quartet-c': 18, 'quartet-d': 17, 'quartet-e': 16} | decisions 28098 | script commit 0370eff1dc30 | seconds 418
{"fold": 0, "val_games": 21, "val_decisions": 6252, "all": {"loss": 2.0816, "accuracy": 0.4052, "steps": 819, "train_games": 72, "train_decisions": 21846}, "half-steps": {"loss": 2.1484, "accuracy": 0.3893, "steps": 819, "train_games": 37, "train_decisions": 11062}, "quarter-steps": {"loss": 2.3346, "accuracy": 0.373, "steps": 819, "train_games": 20, "train_decisions": 5922}, "half": {"loss": 2.2667, "accuracy": 0.3469, "steps": 450, "train_games": 37, "train_decisions": 11062}, "quarter": {"loss": 2.3151, "accuracy": 0.3276, "steps": 279, "train_games": 20, "train_decisions": 5922}, "seconds": 1081}
{"fold": 1, "val_games": 20, "val_decisions": 5922, "all": {"loss": 2.094, "accuracy": 0.4007, "steps": 837, "train_games": 73, "train_decisions": 22176}, "half-steps": {"loss": 2.2045, "accuracy": 0.3791, "steps": 837, "train_games": 38, "train_decisions": 11392}, "quarter-steps": {"loss": 2.266, "accuracy": 0.3723, "steps": 837, "train_games": 21, "train_decisions": 6252}, "half": {"loss": 2.3031, "accuracy": 0.3512, "steps": 477, "train_games": 38, "train_decisions": 11392}, "quarter": {"loss": 2.2391, "accuracy": 0.3377, "steps": 315, "train_games": 21, "train_decisions": 6252}, "seconds": 1740}
{"fold": 2, "val_games": 19, "val_decisions": 5859, "all": {"loss": 2.1144, "accuracy": 0.3647, "steps": 846, "train_games": 74, "train_decisions": 22239}, "half-steps": {"loss": 2.2457, "accuracy": 0.3572, "steps": 846, "train_games": 38, "train_decisions": 11392}, "quarter-steps": {"loss": 2.424, "accuracy": 0.346, "steps": 846, "train_games": 21, "train_decisions": 6252}, "half": {"loss": 2.3145, "accuracy": 0.3362, "steps": 477, "train_games": 38, "train_decisions": 11392}, "quarter": {"loss": 2.2565, "accuracy": 0.321, "steps": 315, "train_games": 21, "train_decisions": 6252}, "seconds": 2442}
{"fold": 3, "val_games": 17, "val_decisions": 5140, "all": {"loss": 2.1069, "accuracy": 0.3807, "steps": 891, "train_games": 76, "train_decisions": 22958}, "half-steps": {"loss": 2.2559, "accuracy": 0.3387, "steps": 891, "train_games": 40, "train_decisions": 12111}, "quarter-steps": {"loss": 2.3326, "accuracy": 0.3597, "steps": 891, "train_games": 21, "train_decisions": 6252}, "half": {"loss": 2.2539, "accuracy": 0.3496, "steps": 495, "train_games": 40, "train_decisions": 12111}, "quarter": {"loss": 2.2534, "accuracy": 0.3268, "steps": 315, "train_games": 21, "train_decisions": 6252}, "seconds": 3162}
{"fold": 4, "val_games": 16, "val_decisions": 4925, "all": {"loss": 2.1488, "accuracy": 0.3917, "steps": 891, "train_games": 77, "train_decisions": 23173}, "half-steps": {"loss": 2.2322, "accuracy": 0.3622, "steps": 891, "train_games": 40, "train_decisions": 12111}, "quarter-steps": {"loss": 2.3118, "accuracy": 0.3602, "steps": 891, "train_games": 21, "train_decisions": 6252}, "half": {"loss": 2.2143, "accuracy": 0.3661, "steps": 495, "train_games": 40, "train_decisions": 12111}, "quarter": {"loss": 2.2369, "accuracy": 0.3316, "steps": 315, "train_games": 21, "train_decisions": 6252}, "seconds": 3915}
all {"per_game": 0.389, "decision_weighted": 0.389, "decision_weighted_114_games": 0.3878, "decision_weighted_119_games": 0.3901, "fold_loss": [2.0816, 2.094, 2.1144, 2.1069, 2.1488], "fold_accuracy": [0.4052, 0.4007, 0.3647, 0.3807, 0.3917], "steps": [819, 837, 846, 891, 891], "train_games": [72, 73, 74, 76, 77], "train_decisions": [21846, 22176, 22239, 22958, 23173], "loss_curve_fold_mean": [2.314, 2.2173, 2.1717, 2.1476, 2.1408, 2.1178, 2.1118, 2.122, 2.1091], "lowest_point": 9}
half-steps {"per_game": 0.3658, "decision_weighted": 0.3665, "decision_weighted_114_games": 0.3604, "decision_weighted_119_games": 0.3724, "fold_loss": [2.1484, 2.2045, 2.2457, 2.2559, 2.2322], "fold_accuracy": [0.3893, 0.3791, 0.3572, 0.3387, 0.3622], "steps": [819, 837, 846, 891, 891], "train_games": [37, 38, 38, 40, 40], "train_decisions": [11062, 11392, 11392, 12111, 12111], "loss_curve_fold_mean": [2.3307, 2.2439, 2.2156, 2.1677, 2.2032, 2.1776, 2.1828, 2.1722, 2.2173], "lowest_point": 4}
quarter-steps {"per_game": 0.3621, "decision_weighted": 0.3626, "decision_weighted_114_games": 0.361, "decision_weighted_119_games": 0.3641, "fold_loss": [2.3346, 2.266, 2.424, 2.3326, 2.3118], "fold_accuracy": [0.373, 0.3723, 0.346, 0.3597, 0.3602], "steps": [819, 837, 846, 891, 891], "train_games": [20, 21, 21, 21, 21], "train_decisions": [5922, 6252, 6252, 6252, 6252], "loss_curve_fold_mean": [2.3877, 2.2711, 2.2836, 2.275, 2.2361, 2.2785, 2.2747, 2.3344, 2.3338], "lowest_point": 5}
half {"per_game": 0.3477, "decision_weighted": 0.3495, "decision_weighted_114_games": 0.3472, "decision_weighted_119_games": 0.3516, "fold_loss": [2.2667, 2.3031, 2.3145, 2.2539, 2.2143], "fold_accuracy": [0.3469, 0.3512, 0.3362, 0.3496, 0.3661], "steps": [450, 477, 477, 495, 495], "train_games": [37, 38, 38, 40, 40], "train_decisions": [11062, 11392, 11392, 12111, 12111], "loss_curve_fold_mean": [2.4143, 2.3175, 2.2582, 2.2237, 2.2263, 2.1954, 2.1931, 2.2257, 2.2705], "lowest_point": 7}
quarter {"per_game": 0.3284, "decision_weighted": 0.3289, "decision_weighted_114_games": 0.3268, "decision_weighted_119_games": 0.331, "fold_loss": [2.3151, 2.2391, 2.2565, 2.2534, 2.2369], "fold_accuracy": [0.3276, 0.3377, 0.321, 0.3268, 0.3316], "steps": [279, 315, 315, 315, 315], "train_games": [20, 21, 21, 21, 21], "train_decisions": [5922, 6252, 6252, 6252, 6252], "loss_curve_fold_mean": [2.4791, 2.4035, 2.3566, 2.3683, 2.3455, 2.3875, 2.3671, 2.3162, 2.2602], "lowest_point": 9}
1 data amount at the same step count: all - half: +0.0232 [+0.0168, +0.0296] t 7.18, games 72/1/20 of 93 - first arm better
2 data amount at the same step count: half - quarter: +0.0037 [-0.0029, +0.0102] t 1.12, games 49/3/41 of 93 - not confirmed (interval includes 0)
3 data amount at the same step count: all - quarter: +0.0269 [+0.0209, +0.0330] t 8.83, games 82/1/10 of 93 - first arm better
beside (same epochs, fewer steps): all - half: +0.0413 [+0.0340, +0.0486] t 11.19, games 81/1/11 of 93 - first arm better
beside (same epochs, fewer steps): all - quarter: +0.0606 [+0.0538, +0.0674] t 17.64, games 90/0/3 of 93 - first arm better
all: decision-weighted 0.3890 on 93 games, 0.3878 on the 114 games (118, trained on 114 only: 0.3638) | seconds 3915
```

지표

```json
{
 "script": "gaia-rl/lab/scratch_v4_amount.py",
 "script_commit": "0370eff1dc3081caea2354e03b9a502e88d46793",
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
  "epochs": 9,
  "lr": 0.001,
  "batch": 256,
  "seed": 0
 },
 "reference_118": {
  "decision_weighted_114_games_trained_on_114_only": 0.3638
 },
 "arms": {
  "all": {
   "per_game": 0.389,
   "decision_weighted": 0.389,
   "decision_weighted_114_games": 0.3878,
   "decision_weighted_119_games": 0.3901,
   "fold_loss": [
    2.0816,
    2.094,
    2.1144,
    2.1069,
    2.1488
   ],
   "fold_accuracy": [
    0.4052,
    0.4007,
    0.3647,
    0.3807,
    0.3917
   ],
   "steps": [
    819,
    837,
    846,
    891,
    891
   ],
   "train_games": [
    72,
    73,
    74,
    76,
    77
   ],
   "train_decisions": [
    21846,
    22176,
    22239,
    22958,
    23173
   ],
   "loss_curve_fold_mean": [
    2.314,
    2.2173,
    2.1717,
    2.1476,
    2.1408,
    2.1178,
    2.1118,
    2.122,
    2.1091
   ],
   "lowest_point": 9
  },
  "half-steps": {
   "per_game": 0.3658,
   "decision_weighted": 0.3665,
   "decision_weighted_114_games": 0.3604,
   "decision_weighted_119_games": 0.3724,
   "fold_loss": [
    2.1484,
    2.2045,
    2.2457,
    2.2559,
    2.2322
   ],
   "fold_accuracy": [
    0.3893,
    0.3791,
    0.3572,
    0.3387,
    0.3622
   ],
   "steps": [
    819,
    837,
    846,
    891,
    891
   ],
   "train_games": [
    37,
    38,
    38,
    40,
    40
   ],
   "train_decisions": [
    11062,
    11392,
    11392,
    12111,
    12111
   ],
   "loss_curve_fold_mean": [
    2.3307,
    2.2439,
    2.2156,
    2.1677,
    2.2032,
    2.1776,
    2.1828,
    2.1722,
    2.2173
   ],
   "lowest_point": 4
  },
  "quarter-steps": {
   "per_game": 0.3621,
   "decision_weighted": 0.3626,
   "decision_weighted_114_games": 0.361,
   "decision_weighted_119_games": 0.3641,
   "fold_loss": [
    2.3346,
    2.266,
    2.424,
    2.3326,
    2.3118
   ],
   "fold_accuracy": [
    0.373,
    0.3723,
    0.346,
    0.3597,
    0.3602
   ],
   "steps": [
    819,
    837,
    846,
    891,
    891
   ],
   "train_games": [
    20,
    21,
    21,
    21,
    21
   ],
   "train_decisions": [
    5922,
    6252,
    6252,
    6252,
    6252
   ],
   "loss_curve_fold_mean": [
    2.3877,
    2.2711,
    2.2836,
    2.275,
    2.2361,
    2.2785,
    2.2747,
    2.3344,
    2.3338
   ],
   "lowest_point": 5
  },
  "half": {
   "per_game": 0.3477,
   "decision_weighted": 0.3495,
   "decision_weighted_114_games": 0.3472,
   "decision_weighted_119_games": 0.3516,
   "fold_loss": [
    2.2667,
    2.3031,
    2.3145,
    2.2539,
    2.2143
   ],
   "fold_accuracy": [
    0.3469,
    0.3512
```

<sub>agentmaco · 커밋 e7707bf · 2026-11-18T13:29:15+09:00 → 2026-11-18T14:34:33+09:00</sub>
