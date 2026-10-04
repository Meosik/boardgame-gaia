# Cycle 029 — two-income horizon under the hard 20 s cap

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, rollouts to the next income, 20 s cap).
B: `teacher-a-search4-h2-geodens-cap20.json` (4 comparisons, rollouts through two incomes, same 20 s cap).
12 fresh seeds from lab/seeds.txt (geo-quartet-200102 …) × 2 seat-swapped games, run by the lab on
agentmaco (4 games at once, lowest CPU priority beside the live server), commit 9f32d80.
Result: lab/results/029-search4-h2-cap20.md.

| Faction | Pairs | B−A VP | 95% CI |
|---|---:|---:|---|
| Geodens | 12 | −2.4 | [−17.9, +13.1] |
| Taklons | 12 | +5.5 | [−3.0, +14.0] |
| Terrans | 12 | −7.1 | [−20.1, +6.0] |
| Xenos | 12 | +3.3 | [−18.4, +25.1] |
| **Seat mean** | 12 | **−0.2** | **[−7.2, +6.8]** |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard (one income) | 2716 | 3.79 s | 1.11 s | 11.93 s | 47.0 s |
| B two incomes | 2720 | 7.87 s | 5.78 s | 20.11 s | 48.0 s |

No errors, timeouts or fallback decisions in either arm.

Depth buys nothing here: −0.2 VP at 2.1× the mean time (median 5.2×). With the cap fixed at 20 s,
longer rollouts mean fewer finished comparisons per decision, so B spends its budget on depth and
loses breadth; the p90 sitting at the cap shows B is cap-bound. Together with cycle 028 (6
comparisons, +4.2, not significant), neither more breadth nor more depth past hard's setting pays
at this cap. Hard stays at 4 comparisons, one-income horizon.

This run used the original search (no `distinct_search`). Late-gain choices that the one-income
rollout misses (upgrades, cycle 030/031 notes) may need both fixes at once: a deeper horizon
cannot help if the comparison budget still goes to duplicate first moves. Not tested yet.

Side finding: the hard arm itself reached 47.0 s (cycle 028: 23.9 s), so the cap overrun is not
specific to normal; it stays under hard's 60 s server guard but confirms the cap is checked too
rarely.
