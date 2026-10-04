# Cycle 027 — 4 comparisons under a 10 s cap

A: `teacher-a-search2-h1-geodens-cap5.json` (live normal: 2 comparisons, 5 s cap).
B: `teacher-a-search4-h1-geodens-cap10.json` (4 comparisons, 10 s cap).
12 fresh seeds from lab/seeds.txt (geo-quartet-168206 …) × 2 seat-swapped games, run by the lab on
agentmaco (Ryzen 7 6850H, 4 games at once, lowest CPU priority beside the live server).
Result: lab/results/027-search4-cap10.md.

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 12 | +25.2 | [+13.1, +37.4] |
| Taklons | 12 | +16.5 | [+3.6, +29.4] |
| Terrans | 12 | +14.9 | [+0.9, +28.9] |
| Xenos | 12 | +18.2 | [−3.1, +39.4] |
| **Seat mean** | 12 | **+18.7** | **[+10.8, +26.6]** |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A normal (cap 5) | 2568 | 1.43 s | 0.51 s | 4.88 s | 50.7 s |
| B 4 comparisons, cap 10 | 2630 | 2.91 s | 1.25 s | 10.01 s | 16.5 s |

Comparison with cycle 025 (hard, cap 20, laptop): +21.1 at 2.6× normal's mean time; here
+18.7 at 2.0×. Halving the cap keeps most of the strength. The mean, 2.9 s, is inside the agreed
normal target (2–3 s); the agreed 5 s cap is not. Whether normal moves to 4 comparisons with a
10 s cap is the user's call.

Side finding: the 5 s-capped arm had a 50.7 s decision (cycle 023 on the laptop: 65.5 s), above
the server's 30 s guard for normal, which then restarts the worker and plays a fallback move. The
cap is checked between comparisons, so something before or inside the first comparison can run
long. To investigate.
