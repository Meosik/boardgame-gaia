# Cycle 031 — distinct_search at the live normal level (2 comparisons, 5 s cap)

A: `teacher-a-search2-h1-geodens-cap5.json` (live normal: 2 comparisons, one-income rollouts, 5 s cap).
B: `teacher-a-search2-h1-distinct-cap5.json` (same budget plus `teacher_patches:distinct_search`,
the same fix as cycle 030). Question: does removing duplicate first moves matter more when there
are only 2 comparisons?
The queue file had been renamed `_031-…` (out of the lab queue, see cycle 030); the run was started
by the user. 12 fresh seeds from lab/seeds.txt (geo-quartet-243796 …), disjoint from cycle 030,
× 2 seat-swapped games, agentmaco (4 games at once, lowest CPU priority), commit 275fe80.
Result: lab/results/031-distinct-search2-cap5.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 12 | +3.4 | [−7.5, +14.3] | 70.6 | 74.0 |
| Taklons | 12 | +8.6 | [−4.0, +21.1] | 81.8 | 90.4 |
| Terrans | 12 | +9.7 | [−0.4, +19.8] | 82.3 | 92.0 |
| Xenos | 12 | −5.4 | [−19.6, +8.8] | 95.6 | 90.2 |
| **Seat mean** | 12 | **+4.1** | **[−4.0, +12.1]** | 82.6 | 86.6 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A normal | 2523 | 1.50 s | 0.56 s | 5.02 s | 11.7 s |
| B distinct_search | 2479 | 2.01 s | 1.11 s | 5.06 s | 28.3 s |

No errors, timeouts or fallback decisions in either arm.

Not significant overall (+4.1 VP at 1.34× the mean time), the same shape as cycle 030 on new
seeds: Geodens, Taklons and Terrans up, Xenos down (−5.4 here, −12.8 in 030). Xenos B again made
fewer decisions (843 vs 889).

The "Xenos is the exception" reading came from cycle 030, and these seeds were not used to form
it, so this is an out-of-sample check of the direction, at a different level. Mean of the three
non-Xenos factions per pair (same pair-level t interval as teacher_ab): **+7.2 [+0.2, +14.2]**,
just above zero. One run at the normal level, not the hard level the user fixed for experiments,
so it supports but does not settle "distinct_search except Xenos".

Side finding: B's max decision was 28.3 s against a 5 s cap, close to normal's 30 s server guard
(A max 11.7 s). distinct_search at the normal level would need the cap overrun fixed or a longer
guard before deployment.
