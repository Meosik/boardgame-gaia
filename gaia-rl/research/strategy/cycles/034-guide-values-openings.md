# Cycle 034 — guide values + faction round-1 openings vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-values-openings-cap20.json` — `guide_values` (LF01·LF02 charge prices,
1 VP = 1.5 charge in every round, research step 16 charge, fleet action 2 charge/round, 4-charge
tile 4 charge/round) + `uiqoo_openings` (B04 Terrans, B10 Taklons, B15 Xenos round-1 openings moved
to the front of the BGG proposals; order only). Geodens keep geodens_guide openings.
Question: first check of the uiqoo material applied so far (user asked for 12 pairs). No deploy
condition was set; this was a direction check before the remaining guide items.
12 fresh seeds (geo-quartet-367653 … 395288) × 2 seat-swapped games, agentmaco, commit ef73ad7.
Result: lab/results/034-guide-values-openings.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 12 | −19.3 | [−34.9, −3.7] | 91.2 | 71.8 |
| Taklons | 12 | −7.0 | [−16.5, +2.5] | 88.0 | 81.0 |
| Terrans | 12 | −19.5 | [−34.9, −4.1] | 103.3 | 83.8 |
| Xenos | 12 | +5.9 | [−14.3, +26.1] | 108.2 | 114.2 |
| **Seat mean** | 12 | **−10.0** | **[−20.6, +0.6]** | 97.7 | 87.7 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 2507 | 4.54 s | 1.82 s | 15.00 s | 29.1 s |
| B guide values + openings | 3052 | 5.68 s | 2.39 s | 20.01 s | 27.5 s |

No errors, timeouts or fallback decisions in either arm.

B is worse. The overall interval only just touches zero, and Geodens and Terrans are each
significantly negative by about 19 VP. Geodens did not get a new opening, so their loss comes from
`guide_values` alone; the value change, not the opening order, is the main suspect.

B makes 22% more decisions (3052 vs 2507; Taklons 765 vs 551, Terrans 709 vs 577). This matches the
smoke-test observation before the run: more fleet entries and small actions, fewer buildings
(Terrans passed after two actions in round 1). At the source prices a third mine and a trading-station
upgrade are a loss by themselves (consistent with B01·B02), and one-income rollouts do not see the
later return, so the teacher builds less. Unsearched decisions also rose (2402 vs 1936), so the
larger default-rank share now follows the new values directly.

Xenos is the only positive faction (+5.9, wide interval); Xenos `resource_value` also moved to LF
prices. Not significant; not a basis for a faction-specific choice.

Not separated yet: values vs openings for Taklons, Terrans and Xenos. A values-only arm (no
`uiqoo_openings`) or an openings-only arm would split them.

Decision times: B is 1.25× slower on average; both arms stayed under 30 s this time.
