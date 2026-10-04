# 027-search4-cap10 — 실패

기본 레벨 결정용: 비교 4개를 10초 상한으로 (hard는 20초에 +21.1, 평균 4.9초/p90 17초). 강함 대부분이 남으면서 대기가 줄어드는지.

teacher_ab 종료 코드 1

```
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-000/game-1-A13", "complete": true, "scores": {"0": 88, "1": 72, "2": 95, "3": 98}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-001/game-1-A01", "complete": true, "scores": {"0": 115, "1": 46, "2": 101, "3": 111}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-001/game-0-A23", "complete": true, "scores": {"0": 112, "1": 88, "2": 87, "3": 98}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-002/game-1-A12", "complete": true, "scores": {"0": 78, "1": 82, "2": 97, "3": 80}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-002/game-0-A03", "complete": true, "scores": {"0": 71, "1": 94, "2": 120, "3": 50}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-003/game-0-A13", "complete": true, "scores": {"0": 98, "1": 120, "2": 108, "3": 89}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-003/game-1-A02", "complete": true, "scores": {"0": 46, "1": 166, "2": 81, "3": 107}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-004/game-0-A01", "complete": true, "scores": {"0": 82, "1": 41, "2": 142, "3": 81}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-004/game-1-A23", "complete": true, "scores": {"0": 98, "1": 96, "2": 108, "3": 82}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-005/game-1-A03", "complete": true, "scores": {"0": 83, "1": 79, "2": 82, "3": 94}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-005/game-0-A12", "complete": true, "scores": {"0": 104, "1": 106, "2": 89, "3": 127}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-006/game-0-A02", "complete": true, "scores": {"0": 80, "1": 99, "2": 105, "3": 82}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-007/game-0-A23", "complete": true, "scores": {"0": 102, "1": 128, "2": 68, "3": 94}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-006/game-1-A13", "complete": true, "scores": {"0": 60, "1": 67, "2": 141, "3": 74}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-007/game-1-A01", "complete": true, "scores": {"0": 88, "1": 69, "2": 77, "3": 105}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-008/game-0-A03", "complete": true, "scores": {"0": 64, "1": 121, "2": 70, "3": 58}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-009/game-0-A13", "complete": true, "scores": {"0": 105, "1": 85, "2": 136, "3": 69}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-008/game-1-A12", "complete": true, "scores": {"0": 101, "1": 87, "2": 67, "3": 100}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-009/game-1-A02", "complete": true, "scores": {"0": 63, "1": 102, "2": 124, "3": 68}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-010/game-0-A01", "complete": true, "scores": {"0": 106, "1": 82, "2": 79, "3": 104}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-010/game-1-A23", "complete": true, "scores": {"0": 151, "1": 86, "2": 87, "3": 109}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-011/game-0-A12", "complete": true, "scores": {"0": 78, "1": 91, "2": 54, "3": 130}, "failure": null}
{"game": "/home/sohegi/projects/gaia-lab/gaia-rl/runs/lab-027-search4-cap10/pair-011/game-1-A03", "complete": true, "scores": {"0": 90, "1": 111, "2": 101, "3": 68}, "failure": null}
Traceback (most recent call last):
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 509, in <module>
    main()
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 505, in main
    run(args)
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 466, in run
    summary = summarize(pairs_rows, games)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 202, in summarize
    table = {f: line([r['B_minus_A'] for r in by_faction.get(f, [])], per_faction.get(f, empty),
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 195, in line
    'ci95': confidence_interval(values), 'error_games': errors_, 'timeout_games': timeouts,
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/sohegi/projects/gaia-lab/gaia-rl/tools/teacher_ab.py", line 170, in confidence_interval
    from scipy.stats import t
ModuleNotFoundError: No module named 'scipy'
```

<sub>agentmaco · 커밋 f5807a5 · 2026-10-04T18:51:48+09:00 → 2026-10-04T19:44:08+09:00</sub>
