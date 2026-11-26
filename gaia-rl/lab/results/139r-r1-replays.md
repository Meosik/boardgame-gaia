# 139r-r1-replays — 실패

사용자 2026-11-26 「(나) ㄱㄱ」: 139(같은 20개 맵, 1라운드까지) 리플레이 20개 전부 게시 — 표시 시트가 이 리플레이에서 AI 시작 광산과 1R 초반 땅을 미리 찍는다(시트 생성은 사용자가 mark_sheet.py --replays로). 판정 없음.

종료 코드 1

```
    (cmd_list if args.command == 'list' else cmd_export)(args)
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 126, in cmd_export
    replays = [(Path(g), replay_game(Path(g), args.focus))
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 117, in replay_game
    replay = add_decision_log(replay)
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_log.py", line 10, in add_decision_log
    income_by_frame = recover_income(frames)
                      ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_income.py", line 35, in recover_income
    raise ValueError(f'Income reconstruction rejected; original replay preserved: {result.stderr.strip()}')
ValueError: Income reconstruction rejected; original replay preserved: Error: "recorded transition differs from current rules; income was not reconstructed"
pair-015/game-0-A02: focus seat 0; all-games
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 165, in <module>
    main()
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 161, in main
    (cmd_list if args.command == 'list' else cmd_export)(args)
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 126, in cmd_export
    replays = [(Path(g), replay_game(Path(g), args.focus))
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/ab_replays.py", line 117, in replay_game
    replay = add_decision_log(replay)
             ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_log.py", line 10, in add_decision_log
    income_by_frame = recover_income(frames)
                      ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/replay_income.py", line 35, in recover_income
    raise ValueError(f'Income reconstruction rejected; original replay preserved: {result.stderr.strip()}')
ValueError: Income reconstruction rejected; original replay preserved: Error: "recorded transition differs from current rules; income was not reconstructed"
pair-016/game-0-A01: focus seat 0; all-games
ab-lab-139-r1-placement-sim-20-pair-016-game-0-a01-4b57d40b: Xenos seat 0, 14 VP, 58 decisions
pair-017/game-0-A03: focus seat 0; all-games
ab-lab-139-r1-placement-sim-20-pair-017-game-0-a03-77187e90: SpaceGiants seat 0, 12 VP, 70 decisions
pair-018/game-0-A02: focus seat 0; all-games
ab-lab-139-r1-placement-sim-20-pair-018-game-0-a02-5d4bfb0c: Xenos seat 0, 9 VP, 50 decisions
pair-019/game-0-A01: focus seat 0; all-games
ab-lab-139-r1-placement-sim-20-pair-019-game-0-a01-ea96689a: Darkanians seat 0, 4 VP, 71 decisions
export failed; nothing published
```

<sub>agentmaco · 커밋 5a56e70 · 2026-11-26T17:39:15+09:00 → 2026-11-26T17:39:21+09:00</sub>
