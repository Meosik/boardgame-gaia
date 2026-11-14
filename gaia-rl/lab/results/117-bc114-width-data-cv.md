# 117-bc114-width-data-cv — 완료

사용자 2026-11-14 「진행해」(HANDOFF E151 (ㄴ), 토론 1/1·2/2 정정 반영, E152): 114 BC 표본(46판 13,841결정)에서 망 폭과 자료량이 한계인지 가르는 짝 비교. 대국 없음, 교사 판정 아님(인코딩 v4 설정 선택용). 고정 조건(116과 같음): 쿼텟 층화 5겹 판 단위 교차 검증, lr 0.001, 배치 256, 같은 torch 시드·배치 순서 시드, 검증 겹으로 epoch를 고르지 않음. 팔 7개(입력은 `expand+o` 53칸, o2 표시만 `expand+o2` 72칸): w64-all(폭 64·전부·9 epoch = 116 A팔) / w64-half(절반·9 epoch) / w64-half-steps(절반, 같은 겹 w64-all과 같은 갱신 횟수 9 × ceil(N전체/256)에서 epoch 중간 종료) / w256-all / w256-half / w256-half-steps / w256-all-o2. 절반 = 겹의 학습 판 중 쿼텟 안에서 manifest 순서로 하나 건너 하나(무작위 없음; 겹 0에서 19/35판·결정 54%). 버리는 상태 칸은 모든 팔에서 겹 전체 학습 집합 기준(같은 폭은 같은 초기값). 사전 등록 보고: 팔마다 판별 정확도·결정 가중·겹별 검증 손실·갱신 횟수·검증 9점 손실 곡선(겹 평균); 비교마다 판별 정확도 차이 평균·판 단위 t 구간·n/46·쿼텟별. 주 비교 4개와 읽기(구간 기준): ① 폭 w256-all − w64-all: 0 위면 v4 망 폭 256을 후보로, 0 포함이면 미확인(64 유지), 0 아래면 64 유지 — 9 epoch는 폭 64에서 정한 값이므로 폭 256 곡선의 최저점이 9번째가 아니면 같이 보고하되 판정은 9 epoch 값 ②③ 자료량 all − half-steps(같은 갱신 횟수; 폭 64, 폭 256 각각): 0 위면 이 설정에서 판 수가 한계 중 하나(추가 수집 근거), 0 포함이면 미확인 ④ o2 w256-all-o2 − w256-all: 0 위면 o2를 폭 256 조건의 v4 후보로 되돌림, 0 포함이면 116대로 미확인, 0 아래면 뺌. 곁 비교 2개(all − half, 같은 epoch·갱신 적음)는 참고만 — 자료량과 갱신 횟수가 섞임. 점검: w64-all 판별 정확도가 116 A팔 0.3466과 ±0.0005 안(아니면 재현성 문제로 따로 보고하고 다른 읽기 보류); half-steps 팔의 갱신 횟수가 같은 겹 all 팔과 다르면 스크립트가 assert로 끝남; o2.npz가 outcome.npz·추출 버전 2와 안 맞으면 오류로 끝남. 한계: torch 시드 1개, 비교 6개에 다중 비교 보정 없음(탐색), 절반 선택 1가지. lab venv에 torch가 없어 명령은 봇 작업 트리에서 작업 트리 venv로 돈다(shard·outcome.npz·o2.npz가 작업 트리 runs/에만 있음). 예상 ≈ 30–35분(봇 턴 스모크: 겹 0·1 epoch·7팔 43초, 갱신 횟수 42 = 42 일치).

종료 코드 0

```
loaded: games 46 | decisions 13841 | o columns 53 | o2 columns 72 | seconds 3
{"fold": 0, "val_games": 11, "val_decisions": 3242, "w64-all": {"loss": 2.234, "acc": 0.359, "steps": 378, "train_games": 35, "train_decisions": 10599}, "w64-half": {"loss": 2.291, "acc": 0.346, "steps": 207, "train_games": 19, "train_decisions": 5711}, "w64-half-steps": {"loss": 2.262, "acc": 0.357, "steps": 378, "train_games": 19, "train_decisions": 5711}, "w256-all": {"loss": 2.268, "acc": 0.381, "steps": 378, "train_games": 35, "train_decisions": 10599}, "w256-half": {"loss": 2.282, "acc": 0.348, "steps": 207, "train_games": 19, "train_decisions": 5711}, "w256-half-steps": {"loss": 2.534, "acc": 0.369, "steps": 378, "train_games": 19, "train_decisions": 5711}, "w256-all-o2": {"loss": 2.262, "acc": 0.383, "steps": 378, "train_games": 35, "train_decisions": 10599}, "seconds": 317}
{"fold": 1, "val_games": 11, "val_decisions": 3409, "w64-all": {"loss": 2.186, "acc": 0.351, "steps": 369, "train_games": 35, "train_decisions": 10432}, "w64-half": {"loss": 2.303, "acc": 0.333, "steps": 198, "train_games": 19, "train_decisions": 5544}, "w64-half-steps": {"loss": 2.376, "acc": 0.351, "steps": 369, "train_games": 19, "train_decisions": 5544}, "w256-all": {"loss": 2.191, "acc": 0.373, "steps": 369, "train_games": 35, "train_decisions": 10432}, "w256-half": {"loss": 2.225, "acc": 0.362, "steps": 198, "train_games": 19, "train_decisions": 5544}, "w256-half-steps": {"loss": 2.603, "acc": 0.363, "steps": 369, "train_games": 19, "train_decisions": 5544}, "w256-all-o2": {"loss": 2.186, "acc": 0.376, "steps": 369, "train_games": 35, "train_decisions": 10432}, "seconds": 635}
{"fold": 2, "val_games": 10, "val_decisions": 3137, "w64-all": {"loss": 2.207, "acc": 0.335, "steps": 378, "train_games": 36, "train_decisions": 10704}, "w64-half": {"loss": 2.309, "acc": 0.313, "steps": 198, "train_games": 19, "train_decisions": 5544}, "w64-half-steps": {"loss": 2.38, "acc": 0.322, "steps": 378, "train_games": 19, "train_decisions": 5544}, "w256-all": {"loss": 2.328, "acc": 0.336, "steps": 378, "train_games": 36, "train_decisions": 10704}, "w256-half": {"loss": 2.296, "acc": 0.328, "steps": 198, "train_games": 19, "train_decisions": 5544}, "w256-half-steps": {"loss": 2.726, "acc": 0.333, "steps": 378, "train_games": 19, "train_decisions": 5544}, "w256-all-o2": {"loss": 2.304, "acc": 0.338, "steps": 378, "train_games": 36, "train_decisions": 10704}, "seconds": 955}
{"fold": 3, "val_games": 8, "val_decisions": 2302, "w64-all": {"loss": 2.258, "acc": 0.331, "steps": 414, "train_games": 38, "train_decisions": 11539}, "w64-half": {"loss": 2.368, "acc": 0.301, "steps": 225, "train_games": 21, "train_decisions": 6379}, "w64-half-steps": {"loss": 2.406, "acc": 0.338, "steps": 414, "train_games": 21, "train_decisions": 6379}, "w256-all": {"loss": 2.35, "acc": 0.363, "steps": 414, "train_games": 38, "train_decisions": 11539}, "w256-half": {"loss": 2.334, "acc": 0.342, "steps": 225, "train_games": 21, "train_decisions": 6379}, "w256-half-steps": {"loss": 2.779, "acc": 0.338, "steps": 414, "train_games": 21, "train_decisions": 6379}, "w256-all-o2": {"loss": 2.366, "acc": 0.353, "steps": 414, "train_games": 38, "train_decisions": 11539}, "seconds": 1287}
{"fold": 4, "val_games": 6, "val_decisions": 1751, "w64-all": {"loss": 2.19, "acc": 0.357, "steps": 432, "train_games": 40, "train_decisions": 12090}, "w64-half": {"loss": 2.238, "acc": 0.33, "steps": 225, "train_games": 21, "train_decisions": 6379}, "w64-half-steps": {"loss": 2.323, "acc": 0.346, "steps": 432, "train_games": 21, "train_decisions": 6379}, "w256-all": {"loss": 2.238, "acc": 0.377, "steps": 432, "train_games": 40, "train_decisions": 12090}, "w256-half": {"loss": 2.264, "acc": 0.341, "steps": 225, "train_games": 21, "train_decisions": 6379}, "w256-half-steps": {"loss": 2.691, "acc": 0.348, "steps": 432, "train_games": 21, "train_decisions": 6379}, "w256-all-o2": {"loss": 2.205, "acc": 0.391, "steps": 432, "train_games": 40, "train_decisions": 12090}, "seconds": 1619}
per arm (n=46 games): per-game accuracy | decision-weighted | fold-mean validation loss at the 9 points (lowest point)
  w64-all          0.3462 | 0.3469 | 2.565 2.449 2.364 2.305 2.280 2.250 2.226 2.221 2.215 (9)
  w64-half         0.3252 | 0.3258 | 2.638 2.555 2.486 2.432 2.396 2.372 2.336 2.305 2.302 (9)
  w64-half-steps   0.3424 | 0.3430 | 2.564 2.447 2.374 2.330 2.297 2.289 2.304 2.311 2.349 (6)
  w256-all         0.3645 | 0.3651 | 2.405 2.290 2.228 2.203 2.188 2.194 2.194 2.224 2.275 (5)
  w256-half        0.3448 | 0.3451 | 2.501 2.394 2.327 2.286 2.283 2.264 2.262 2.284 2.280 (7)
  w256-half-steps  0.3509 | 0.3518 | 2.408 2.307 2.269 2.285 2.311 2.385 2.446 2.575 2.667 (3)
  w256-all-o2      0.3668 | 0.3672 | 2.407 2.290 2.226 2.204 2.192 2.192 2.198 2.224 2.265 (5)
w64-all per game 0.3462, expected 0.3466 (116 A arm): reproduced
width: 256 - 64, all games, 9 epochs: +0.0183 [+0.0100, +0.0265], games better 33, equal 1, worse 12 -> first arm better
  quartets: geo-quartet +0.036 2/2, quartet-a +0.015 6/10, quartet-b +0.020 7/9, quartet-c +0.006 4/9, quartet-d +0.016 6/8, quartet-e +0.033 8/8
data amount at the same step count, width 64: all - half: +0.0039 [-0.0024, +0.0101], games better 24, equal 3, worse 19 -> not confirmed (interval includes 0)
  quartets: geo-quartet -0.010 0/2, quartet-a +0.006 6/10, quartet-b +0.002 6/9, quartet-c +0.007 5/9, quartet-d +0.015 4/8, quartet-e -0.007 3/8
data amount at the same step count, width 256: all - half: +0.0136 [+0.0055, +0.0217], games better 31, equal 1, worse 14 -> first arm better
  quartets: geo-quartet -0.003 1/2, quartet-a +0.011 7/10, quartet-b +0.012 6/9, quartet-c +0.013 5/9, quartet-d +0.020 6/8, quartet-e +0.017 6/8
o2 at width 256: o2 - o: +0.0023 [-0.0030, +0.0077], games better 21, equal 6, worse 19 -> not confirmed (interval includes 0)
  quartets: geo-quartet +0.004 1/2, quartet-a +0.011 5/10, quartet-b +0.002 4/9, quartet-c -0.012 2/9, quartet-d +0.004 4/8, quartet-e +0.006 5/8
beside (same epochs, fewer steps), width 64: all - half: +0.0211 [+0.0141, +0.0280], games better 37, equal 1, worse 8 -> first arm better
  quartets: geo-quartet -0.014 0/2, quartet-a +0.028 10/10, quartet-b +0.029 7/9, quartet-c +0.016 6/9, quartet-d +0.026 8/8, quartet-e +0.014 6/8
beside (same epochs, fewer steps), width 256: all - half: +0.0197 [+0.0112, +0.0283], games better 34, equal 2, worse 10 -> first arm better
  quartets: geo-quartet +0.009 2/2, quartet-a +0.023 8/10, quartet-b +0.019 6/9, quartet-c +0.008 5/9, quartet-d +0.015 5/8, quartet-e +0.036 8/8
```

지표

```json
{
 "epochs": 9,
 "games": 46,
 "decisions": 13841,
 "arms": {
  "w64-all": {
   "input": "o",
   "width": 64,
   "games": "all",
   "stop": "epochs",
   "per_game": 0.3462,
   "decision_weighted": 0.3469,
   "fold_loss": "2.234 2.186 2.207 2.258 2.190",
   "fold_acc": "0.359 0.351 0.335 0.331 0.357",
   "fold_steps": "378 369 378 414 432",
   "fold_train_games": "35 35 36 38 40",
   "fold_train_decisions": "10599 10432 10704 11539 12090",
   "curve_loss_fold_mean": "2.565 2.449 2.364 2.305 2.280 2.250 2.226 2.221 2.215",
   "lowest_loss_point": 9
  },
  "w64-half": {
   "input": "o",
   "width": 64,
   "games": "half",
   "stop": "epochs",
   "per_game": 0.3252,
   "decision_weighted": 0.3258,
   "fold_loss": "2.291 2.303 2.309 2.368 2.238",
   "fold_acc": "0.346 0.333 0.313 0.301 0.330",
   "fold_steps": "207 198 198 225 225",
   "fold_train_games": "19 19 19 21 21",
   "fold_train_decisions": "5711 5544 5544 6379 6379",
   "curve_loss_fold_mean": "2.638 2.555 2.486 2.432 2.396 2.372 2.336 2.305 2.302",
   "lowest_loss_point": 9
  },
  "w64-half-steps": {
   "input": "o",
   "width": 64,
   "games": "half",
   "stop": "steps",
   "per_game": 0.3424,
   "decision_weighted": 0.343,
   "fold_loss": "2.262 2.376 2.380 2.406 2.323",
   "fold_acc": "0.357 0.351 0.322 0.338 0.346",
   "fold_steps": "378 369 378 414 432",
   "fold_train_games": "19 19 19 21 21",
   "fold_train_decisions": "5711 5544 5544 6379 6379",
   "curve_loss_fold_mean": "2.564 2.447 2.374 2.330 2.297 2.289 2.304 2.311 2.349",
   "lowest_loss_point": 6
  },
  "w256-all": {
   "input": "o",
   "width": 256,
   "games": "all",
   "stop": "epochs",
   "per_game": 0.3645,
   "decision_weighted": 0.3651,
   "fold_loss": "2.268 2.191 2.328 2.350 2.238",
   "fold_acc": "0.381 0.373 0.336 0.363 0.377",
   "fold_steps": "378 369 378 414 432",
   "fold_train_games": "35 35 36 38 40",
   "fold_train_decisions": "10599 10432 10704 11539 12090",
   "curve_loss_fold_mean": "2.405 2.290 2.228 2.203 2.188 2.194 2.194 2.224 2.275",
   "lowest_loss_point": 5
  },
  "w256-half": {
   "input": "o",
   "width": 256,
   "games": "half",
   "stop": "epochs",
   "per_game": 0.3448,
   "decision_weighted": 0.3451,
   "fold_loss": "2.282 2.225 2.296 2.334 2.264",
   "fold_acc": "0.348 0.362 0.328 0.342 0.341",
   "fold_steps": "207 198 198 225 225",
   "fold_train_games": "19 19 19 21 21",
   "fold_train_decisions": "5711 5544 5544 6379 6379",
   "curve_loss_fold_mean": "2.501 2.394 2.327 2.286 2.283 2.264 2.262 2.284 2.280",
   "lowest_loss_point": 7
  },
  "w256-half-steps": {
   "input": "o",
   "width": 256,
   "games": "half",
   "stop": "steps",
   "per_game": 0.3509,
   "decision_weighted": 0.3518,
   "fold_loss": "2.534 2.603 2.726 2.779 2.691",
   "fold_acc": "0.369 0.363 0.333 0.338 0.348",
   "fold_steps": "378 369 378 414 432",
   "fold_train_games": "19 19 19 21 21",
   "fold_train_decisions": "5711 5544 5544 6379 6379",
   "curve_loss_fold_mean": "2.408 2.307 2.269 2.285 2.311 2.385 2.446 2.57
```

<sub>agentmaco · 커밋 9f971cc · 2026-11-14T21:58:32+09:00 → 2026-11-14T22:25:34+09:00</sub>
