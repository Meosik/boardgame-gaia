# Cycle 028 — 6 comparisons under the hard 20 s cap

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, 20 s cap).
B: `teacher-a-search6-h1-geodens-cap20.json` (6 comparisons, same 20 s cap).
12 fresh seeds from lab/seeds.txt (geo-quartet-177415 …) × 2 seat-swapped games, run by the lab on
agentmaco (4 games at once, lowest CPU priority beside the live server).
Result: lab/results/028-search6-cap20.md.

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 12 | −1.2 | [−13.3, +11.0] |
| Taklons | 12 | +3.7 | [−1.4, +8.7] |
| Terrans | 12 | +11.7 | [−0.3, +23.6] |
| Xenos | 12 | +2.7 | [−18.1, +23.5] |
| **Seat mean** | 12 | **+4.2** | **[−3.5, +11.9]** |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard (4 comparisons) | 2636 | 3.77 s | 1.34 s | 11.45 s | 23.9 s |
| B 6 comparisons | 2657 | 4.50 s | 1.78 s | 15.23 s | 34.4 s |

No errors, timeouts or fallback decisions in either arm.

The gain from 4 to 6 comparisons is not significant (+4.2, CI spans zero), against +13.1 to +21.1
for 2 to 4 (cycles 023, 025, 027). The search curve flattens past 4 comparisons at this cap. The
cost is +19% mean time and a 34.4 s maximum, which overruns the 20 s cap by 14 s (the cap is checked
only between comparisons; see cycle 027's side finding). Hard stays at 4 comparisons.
