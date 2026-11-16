# 120-bc114-v4-rebuilt-engine — 완료

사용자 2026-11-17 「진행해」(HANDOFF E160: 작업 트리 엔진 재빌드 뒤 재색인·export·학습, E161): 재빌드된 작업 트리 엔진(fc19671c4278 = lab 엔진)에서 114 46판을 인코딩 4로 다시 export하고 옛 빌드(36d2e007) shard와 전 행 비교, 118의 5겹을 다시 학습. 대국 없음, 교사 판정 아님. 재색인은 봇 턴에서 끝남(runs/bc-114-fc19/manifest.jsonl: 46/46 엄격 재생·6R 46·결정 13,841, 판 순서가 옛 manifest와 같음). 순서: ① bc_dataset.py export --encoding 4 → runs/bc-114-v4-shards-fc19 ② 옛 shard(runs/bc-114-v4-shards)와 상태 벡터·후보 행·후보 수·고른 번호·판 번호 전부 같음(하나라도 다르면 assert로 실패 종료) ③ 118과 같은 겹·설정(폭 256, 9 epoch, lr 0.001, 배치 256, 시드 0, 검증 손실 최저 epoch 저장)으로 tools/bc_train.py → runs/bc-114-v4-w256-fc19/fold-0…4 (metadata에 model_build_id와 엔진 fc19671c4278 = lab에서 읽히는 체크포인트). 사전 등록 읽기: ②가 통과하고 ③의 겹별·epoch별 검증 손실·정확도·학습 손실이 118 metrics와 같으면(최대 차이 0; 봇 턴에서 옛 빌드의 겹 0 재학습은 마지막 자리까지 같았음) 엔진 재빌드가 인코딩 4 입력과 학습 결과를 바꾸지 않음 → 114 shard를 119와 합쳐 쓰고 겹 체크포인트를 스모크·A/B에 씀. ② 실패면 어느 배열이 다른지 보고 119와 합치기 전에 원인부터(엔진 966e9ea는 플래그 끔이면 후보 목록 불변 — 115c — 이라 같아야 함). ②는 통과하고 ③만 다르면 학습의 비결정성으로 읽고 차이 크기(max_abs_difference_from_118)와 5겹 결정 가중 정확도(118: 36.38%)를 보고. 판정 아님 — 재현 점검. 예상 ≈ 15–20분(118: 15분), lab이 119를 끝낸 뒤 실행. lab venv에 torch가 없어 작업 트리 venv로 돈다.

종료 코드 0

```
{"epoch": 3, "train": {"loss": 2.2536667760895805, "accuracy": 0.33368481595092025, "chance": 0.15036590616890333, "samples": 10432}, "validation": {"loss": 2.2691291144391457, "accuracy": 0.3338222352596069, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 4, "train": {"loss": 2.169139879612835, "accuracy": 0.3582246932515337, "chance": 0.1503659061689033, "samples": 10432}, "validation": {"loss": 2.2231780880530514, "accuracy": 0.3528894103842769, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 5, "train": {"loss": 2.103925565269096, "accuracy": 0.3754792944785276, "chance": 0.15036590616890333, "samples": 10432}, "validation": {"loss": 2.171699074084684, "accuracy": 0.3523027280727486, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 6, "train": {"loss": 2.02659542940877, "accuracy": 0.401840490797546, "chance": 0.15036590616890336, "samples": 10432}, "validation": {"loss": 2.15994495001312, "accuracy": 0.35523613963039014, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 7, "train": {"loss": 1.9969724328971348, "accuracy": 0.40605828220858897, "chance": 0.15036590616890336, "samples": 10432}, "validation": {"loss": 2.161326396356898, "accuracy": 0.36931651510706953, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 8, "train": {"loss": 1.9317533041070576, "accuracy": 0.4279141104294479, "chance": 0.15036590616890327, "samples": 10432}, "validation": {"loss": 2.160485112936345, "accuracy": 0.3613963039014374, "chance": 0.15402745989870356, "samples": 3409}}
{"epoch": 9, "train": {"loss": 1.8961870063301975, "accuracy": 0.4410467791411043, "chance": 0.15036590616890325, "samples": 10432}, "validation": {"loss": 2.1607149571189086, "accuracy": 0.3801701378703432, "chance": 0.15402745989870356, "samples": 3409}}
{"fold": 1, "epoch 9": [2.1607, 0.3802], "saved epoch": 6, "difference": 0.0, "seconds": 562}
{"epoch": 1, "train": {"loss": 2.520607068756058, "accuracy": 0.2586883408071749, "chance": 0.14985578849924175, "samples": 10704}, "validation": {"loss": 2.409667443423504, "accuracy": 0.27414727446605036, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 2, "train": {"loss": 2.347905911672276, "accuracy": 0.3028774289985052, "chance": 0.1498557884992417, "samples": 10704}, "validation": {"loss": 2.309524373184316, "accuracy": 0.31240038253108066, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 3, "train": {"loss": 2.2357365946064083, "accuracy": 0.3415545590433483, "chance": 0.14985578849924172, "samples": 10704}, "validation": {"loss": 2.2811168564859376, "accuracy": 0.3245138667516736, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 4, "train": {"loss": 2.1460377532092267, "accuracy": 0.3649103139013453, "chance": 0.14985578849924172, "samples": 10704}, "validation": {"loss": 2.300528293131718, "accuracy": 0.3235575390500478, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 5, "train": {"loss": 2.0805607212676773, "accuracy": 0.3873318385650224, "chance": 0.14985578849924175, "samples": 10704}, "validation": {"loss": 2.214079166469507, "accuracy": 0.34395919668473063, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 6, "train": {"loss": 2.0078528878934714, "accuracy": 0.4086322869955157, "chance": 0.14985578849924172, "samples": 10704}, "validation": {"loss": 2.1846953329099073, "accuracy": 0.34523430028689833, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 7, "train": {"loss": 1.9535494392406423, "accuracy": 0.4235799701046338, "chance": 0.14985578849924172, "samples": 10704}, "validation": {"loss": 2.180275688134906, "accuracy": 0.35416002550207204, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 8, "train": {"loss": 1.896304475530559, "accuracy": 0.4398355754857997, "chance": 0.14985578849924167, "samples": 10704}, "validation": {"loss": 2.1636396364911863, "accuracy": 0.3618106471150781, "chance": 0.15608555430436608, "samples": 3137}}
{"epoch": 9, "train": {"loss": 1.8510518679882557, "accuracy": 0.4517937219730942, "chance": 0.1498557884992417, "samples": 10704}, "validation": {"loss": 2.1873024553488043, "accuracy": 0.3519285941982786, "chance": 0.15608555430436608, "samples": 3137}}
{"fold": 2, "epoch 9": [2.1873, 0.3519], "saved epoch": 8, "difference": 0.0, "seconds": 676}
{"epoch": 1, "train": {"loss": 2.507896617727745, "accuracy": 0.2612878065690268, "chance": 0.15270325359325881, "samples": 11539}, "validation": {"loss": 2.471654944995711, "accuracy": 0.2741094700260643, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 2, "train": {"loss": 2.353645708523959, "accuracy": 0.29768610798162753, "chance": 0.1527032535932588, "samples": 11539}, "validation": {"loss": 2.380051819165824, "accuracy": 0.3045178105994787, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 3, "train": {"loss": 2.2394106463508265, "accuracy": 0.3468238148886385, "chance": 0.1527032535932588, "samples": 11539}, "validation": {"loss": 2.309249475248786, "accuracy": 0.3318853171155517, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 4, "train": {"loss": 2.156511420982117, "accuracy": 0.3659762544414594, "chance": 0.1527032535932588, "samples": 11539}, "validation": {"loss": 2.2870071189078325, "accuracy": 0.3314509122502172, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 5, "train": {"loss": 2.0936365108554456, "accuracy": 0.3840887425253488, "chance": 0.15270325359325884, "samples": 11539}, "validation": {"loss": 2.2356161404235997, "accuracy": 0.34535186794092093, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 6, "train": {"loss": 2.0355258399149463, "accuracy": 0.3955282086835948, "chance": 0.15270325359325881, "samples": 11539}, "validation": {"loss": 2.2343942996836246, "accuracy": 0.34535186794092093, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 7, "train": {"loss": 1.9880161306888848, "accuracy": 0.4099142040038132, "chance": 0.15270325359325881, "samples": 11539}, "validation": {"loss": 2.2245717566495973, "accuracy": 0.3509991311902693, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 8, "train": {"loss": 1.9454796483047874, "accuracy": 0.4219603085189358, "chance": 0.1527032535932588, "samples": 11539}, "validation": {"loss": 2.212610060810318, "accuracy": 0.35708079930495223, "chance": 0.14407206808690984, "samples": 2302}}
{"epoch": 9, "train": {"loss": 1.9185640255906302, "accuracy": 0.4338330877892365, "chance": 0.1527032535932588, "samples": 11539}, "validation": {"loss": 2.2120598619860425, "accuracy": 0.3622936576889661, "chance": 0.14407206808690984, "samples": 2302}}
{"fold": 3, "epoch 9": [2.2121, 0.3623], "saved epoch": 9, "difference": 0.0, "seconds": 793}
{"epoch": 1, "train": {"loss": 2.51183592273343, "accuracy": 0.25955334987593054, "chance": 0.15150715478499713, "samples": 12090}, "validation": {"loss": 2.3698993897451666, "accuracy": 0.27584237578526555, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 2, "train": {"loss": 2.3305410749563213, "accuracy": 0.3076923076923077, "chance": 0.15150715478499713, "samples": 12090}, "validation": {"loss": 2.267354396055386, "accuracy": 0.32724157624214734, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 3, "train": {"loss": 2.2068025495909382, "accuracy": 0.350206782464847, "chance": 0.15150715478499707, "samples": 12090}, "validation": {"loss": 2.267790927266067, "accuracy": 0.33066818960593947, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 4, "train": {"loss": 2.130775314722306, "accuracy": 0.3690653432588916, "chance": 0.1515071547849971, "samples": 12090}, "validation": {"loss": 2.1917094754056206, "accuracy": 0.35579668760708166, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 5, "train": {"loss": 2.0376695107585445, "accuracy": 0.39272125723738627, "chance": 0.15150715478499713, "samples": 12090}, "validation": {"loss": 2.208809949002356, "accuracy": 0.35750999428897773, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 6, "train": {"loss": 1.9738326767636687, "accuracy": 0.41373035566583954, "chance": 0.15150715478499707, "samples": 12090}, "validation": {"loss": 2.227025528760177, "accuracy": 0.3432324386065106, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 7, "train": {"loss": 1.9177140380253568, "accuracy": 0.4265508684863524, "chance": 0.15150715478499713, "samples": 12090}, "validation": {"loss": 2.19688320541164, "accuracy": 0.35636778983438033, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 8, "train": {"loss": 1.8844311962648301, "accuracy": 0.4347394540942928, "chance": 0.15150715478499713, "samples": 12090}, "validation": {"loss": 2.2478658816666006, "accuracy": 0.3420902341519132, "chance": 0.14961464454486856, "samples": 1751}}
{"epoch": 9, "train": {"loss": 1.8797337894108397, "accuracy": 0.43647642679900744, "chance": 0.1515071547849971, "samples": 12090}, "validation": {"loss": 2.192637347684868, "accuracy": 0.36893203883495146, "chance": 0.14961464454486856, "samples": 1751}}
{"fold": 4, "epoch 9": [2.1926, 0.3689], "saved epoch": 4, "difference": 0.0, "seconds": 911}
5 folds, decision-weighted epoch 9 accuracy 0.3638 (118: 0.3638), identical to 118: True, largest difference 0.0
changed since 118: ['engine_build_id', 'python_build_id'] | torch threads 8
```

지표

```json
{
 "engine_build_id": "fc19671c4278246becaa0710511b6d1a37b4049d58290aa8450c1c9f2c9041db",
 "equal": {
  "decisions": 13841,
  "candidate_rows": 536858,
  "arrays": [
   "observation",
   "cand",
   "counts",
   "chosen",
   "game"
  ]
 },
 "folds": [
  {
   "fold": 0,
   "val_games": [
    0,
    2,
    7,
    12,
    17,
    21,
    26,
    30,
    35,
    38,
    43
   ],
   "saved_epoch": 6,
   "saved_epoch_118": 6,
   "validation": [
    {
     "loss": 2.446071506208435,
     "accuracy": 0.2964219617520049,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.3545080805030745,
     "accuracy": 0.3229487970388649,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.2869253270351027,
     "accuracy": 0.3433066008636644,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.2736069686908476,
     "accuracy": 0.34855027760641577,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.2648155140626733,
     "accuracy": 0.3491671807526218,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.221427506241513,
     "accuracy": 0.37939543491671807,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.2362498207492347,
     "accuracy": 0.36150524367674275,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.294465009994083,
     "accuracy": 0.34947563232572487,
     "chance": 0.14970623256232932,
     "samples": 3242
    },
    {
     "loss": 2.2851301439745346,
     "accuracy": 0.3565700185070944,
     "chance": 0.14970623256232932,
     "samples": 3242
    }
   ],
   "train_loss": [
    2.519572193481549,
    2.3634935644102812,
    2.2481365130075655,
    2.1598982139290115,
    2.0855976143966632,
    2.035059649872998,
    1.9827130329655032,
    1.9379925713897685,
    1.8888503793658304
   ],
   "max_abs_difference_from_118": 0.0
  },
  {
   "fold": 1,
   "val_games": [
    1,
    3,
    8,
    13,
    18,
    22,
    27,
    31,
    36,
    39,
    44
   ],
   "saved_epoch": 6,
   "saved_epoch_118": 6,
   "validation": [
    {
     "loss": 2.399611406222786,
     "accuracy": 0.29099442651804047,
     "chance": 0.15402745989870356,
     "samples": 3409
    },
    {
     "loss": 2.328215165164821,
     "accuracy": 0.30184804928131415,
     "chance": 0.15402745989870356,
     "samples": 3409
    },
    {
     "loss": 2.2691291144391457,
     "accuracy": 0.3338222352596069,
     "chance": 0.15402745989870356,
     "samples": 3409
    },
    {
     "loss": 2.2231780880530514,
     "accuracy": 0.3528894103842769,
     "chance": 0.15402745989870356,
     "samples": 3409
    },
    {
     "loss": 2.171699074084684,
     "accuracy": 0.3523027280727486,
     "chance": 0.15402745989870356,
     "samples": 3409
    },
    {
     "loss": 2.15994495001312,
     "accuracy": 0.35523613963039014,
     "chance": 0.15402745989870356,
     "samp
```

<sub>agentmaco · 커밋 2e5b23b · 2026-11-17T08:22:08+09:00 → 2026-11-17T08:37:21+09:00</sub>
