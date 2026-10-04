# Cycle 030 — distinct_search under the hard 20 s cap

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-distinct-cap20.json` (same budget plus `teacher_patches:distinct_search`:
no duplicate first moves among the comparisons, the round-1 BGG opening only when its forecast is
highest, late-gain moves (action boosters, action tiles, exploration, upgrades) compared first,
setup decisions rolled through the round-2 income, other candidates continued with the best plan).
The lab name says cap10, but by the user's instruction (2026-10-05) both arms ran at the hard 20 s cap.
12 fresh seeds from lab/seeds.txt (geo-quartet-225730 …) × 2 seat-swapped games, run by the lab on
agentmaco (4 games at once, lowest CPU priority), commit 07d2328.
Result: lab/results/030-distinct-search4-cap10.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 12 | +10.2 | [−8.4, +28.8] | 86.5 | 96.7 |
| Taklons | 12 | +8.3 | [−5.8, +22.4] | 94.0 | 102.3 |
| Terrans | 12 | +4.3 | [−6.8, +15.4] | 99.1 | 103.4 |
| Xenos | 12 | −12.8 | [−29.0, +3.5] | 106.8 | 94.0 |
| **Seat mean** | 12 | **+2.5** | **[−6.9, +11.9]** | 96.6 | 99.1 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 2749 | 3.75 s | 1.44 s | 11.00 s | 24.7 s |
| B distinct_search | 2733 | 5.11 s | 2.61 s | 15.20 s | 28.3 s |

No errors, timeouts or fallback decisions in either arm.

Not significant overall: +2.5 VP at 1.36× the mean time. The three factions the fix was built
from (Taklons, Terrans, Geodens in the cycle-027 worst game) all move up (+4 to +10), none
significantly; Xenos moves down by 12.8, close to significant. Xenos B made far fewer decisions
(800 vs 915 over 12 games), so distinct_search changes how Xenos plays a round, not just which
first move it compares. Xenos is the one faction whose booster ranking already used
`integrated/boosters.py`, so the "late-gain first" ordering may displace comparisons that the
Xenos ranking had right.

Picking "distinct_search except Xenos" from this table would be choosing after the result; it
needs fresh seeds before it counts (rule from cycle 021). Cycle 032 (same fix, guide openings kept)
is still running and tells whether the opening change or the search change drives the split.

Side finding: max decision 28.3 s in B, 24.7 s in A; both over the 20 s cap but under hard's 60 s
server guard (cycle 029 hard reached 47.0 s).
