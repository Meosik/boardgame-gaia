# Cycle 032 — distinct_search with guide openings kept, hard 20 s cap

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-distinct-openings-cap20.json` (cycle 030's `distinct_search` minus the
opening change: no duplicate first moves among the comparisons, late-gain moves compared first,
setup decisions rolled through the round-2 income, other candidates continued with the best plan;
the round-1 BGG opening follows the guide as before). Question: does keeping the guide openings do
better than 030 (user's view: the guide openings score more)?
The lab name says cap10, but by the user's instruction (2026-10-05) both arms ran at the hard 20 s cap.
12 fresh seeds from lab/seeds.txt (geo-quartet-280930 …), disjoint from cycles 030 and 031,
× 2 seat-swapped games, agentmaco (4 games at once, lowest CPU priority), commit d6f33cd.
Result: lab/results/032-distinct-openings-search4-cap10.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 12 | +17.9 | [+2.4, +33.4] | 82.2 | 100.2 |
| Taklons | 12 | +1.0 | [−10.7, +12.7] | 93.5 | 94.5 |
| Terrans | 12 | +9.5 | [−2.3, +21.3] | 95.0 | 104.5 |
| Xenos | 12 | +5.0 | [−10.0, +20.0] | 98.2 | 103.2 |
| **Seat mean** | 12 | **+8.4** | **[−0.9, +17.6]** | 92.2 | 100.6 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 2801 | 3.44 s | 1.32 s | 10.30 s | 22.3 s |
| B distinct_search, guide openings | 2961 | 4.84 s | 2.03 s | 14.61 s | 24.1 s |

No errors, timeouts or fallback decisions in either arm.

Not significant overall, but the largest gain of the three distinct_search runs (+8.4 VP at 1.41×
the mean time; 030 +2.5, 031 +4.1), with the interval just reaching below zero. Geodens alone is
significant (+17.9).

Xenos is no longer the exception: +5.0 here against −12.8 (030) and −5.4 (031), the two runs that
included the opening change. Xenos B again made fewer decisions (797 vs 944), so the fewer-decisions
pattern does not by itself cost points; the opening change is the more likely cause of the Xenos
drop. The three other factions are about the same in all three runs (pair mean of Geodens, Taklons,
Terrans: 030 +7.6, 031 +7.2 [+0.2, +14.2], 032 +9.5 [+0.3, +18.6], the last computed by hand from
`final_scores` with the same pair-level t interval). This is a comparison across different seeds,
so it points to, but does not prove, "the search change helps, the opening change hurts Xenos".

032's arm B was defined before any of these results, so +8.4 is a fair test, not a pick after the
fact; it simply lacks power at 12 pairs. A second run of the same A/B on fresh seeds would settle it.

Side finding: max decision 24.1 s in B (22.3 s in A), over the 20 s cap but well under hard's 60 s
server guard.
