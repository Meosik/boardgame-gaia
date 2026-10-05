# Cycle 033 — replication of cycle 032 on fresh seeds (hard, 20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-distinct-openings-cap20.json` (same B as cycle 032: `distinct_search`
without the opening change; the round-1 BGG opening follows the guide).
Question: does 032's +8.4 [−0.9, +17.6] hold on new seeds? Decided before the run: if significant,
propose switching the hard teacher to B.
24 fresh seeds from lab/seeds.txt (geo-quartet-306543 … 363554), disjoint from cycles 030–032,
× 2 seat-swapped games, agentmaco (4 games at once, lowest CPU priority), commit 819efe6.
Result: lab/results/033-distinct-openings-search4-cap20-rep.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 24 | +6.1 | [−6.3, +18.5] | 94.8 | 100.9 |
| Taklons | 24 | +11.8 | [+3.5, +20.2] | 93.2 | 105.0 |
| Terrans | 24 | −3.9 | [−14.6, +6.8] | 103.0 | 99.1 |
| Xenos | 24 | −11.8 | [−25.2, +1.5] | 102.8 | 90.9 |
| **Seat mean** | 24 | **+0.6** | **[−6.8, +7.9]** | 98.4 | 99.0 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 5401 | 3.64 s | 1.37 s | 10.75 s | 45.5 s |
| B distinct_search, guide openings | 5789 | 4.92 s | 2.24 s | 14.64 s | 41.6 s |

No errors, timeouts or fallback decisions in either arm.

032 does not replicate. With twice the pairs the overall effect is +0.6 VP, interval centred on
zero, at 1.35× the mean decision time. The pre-set condition for a deploy proposal is not met; the
hard teacher stays as it is.

Weighted by pairs, 032 + 033 (36 pairs) give about +3.2 VP overall; by faction about Geodens +10,
Taklons +8, Terrans +0.6, Xenos −6 (hand-computed from the summary means; no pooled interval).

The 032 reading "the Xenos drop comes from the opening change" does not hold: with the guide
openings kept, Xenos is −11.8 here (B again made fewer decisions, 1716 vs 1852). Across the four
distinct_search runs Xenos was −12.8, −5.4, +5.0, −11.8, so 032's +5.0 is the outlier. The
"three factions rise" pattern also weakens: Terrans is −3.9 here after +4.3, +9.7, +9.5. The
three-faction mean in 033 is +4.7 (mean of the three faction means). Only Taklons is significant
in this run, and Geodens, significant in 032, is not.

What remains consistent across 030–033: Geodens and Taklons are positive in every run, Xenos is
negative in three of four. Picking "Geodens and Taklons only" now would be a choice made after
seeing the results and would need its own fresh-seed run.

Side finding: max decision 45.5 s in A and 41.6 s in B, well over the 20 s cap (032: 22–24 s).
Still under hard's 60 s server guard, but this is the same overshoot as in HANDOFF item 2 and it
happens in the live hard arm too.
