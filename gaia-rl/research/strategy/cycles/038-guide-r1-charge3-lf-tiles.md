# Cycle 038 — guide_r1_charge3_lf_tiles vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-tiles-cap20.json` — 037's B (`guide_r1_charge3_lf`) plus
`_guide['lf_tiles']` (standard tiles 6 and 12 get no fixed value and are left to the round-4 rollout,
tile 8 = 3 VP × (Gaia mines being formed + 1–2 to come), the frozen 0.5 VP × remaining rounds term
removed) and `_guide['charge_vp']` (the round-4 charge leaf keeps held VP at 1 VP = 1.5 charges, so
fleet entry VP is a cost and federations, artifacts and round scoring are gains).
Two changes against 037, not separated.
Question: do the tile values and counting VP in the charge leaf recover 037's loss?
User asked for 6 pairs and reporting by charges gained in rounds 1–3; no deploy condition was set.
6 fresh seeds (geo-quartet-443297 … 450885) × 2 seat-swapped games, agentmaco, commit 5ccb4f1.
Result: lab/results/038-guide-r1-charge3-lf-tiles.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | −40.7 | [−54.4, −26.9] | 91.7 | 51.0 |
| Taklons | 6 | −23.5 | [−46.4, −0.6] | 95.2 | 71.7 |
| Terrans | 6 | −12.0 | [−38.1, +14.1] | 102.5 | 90.5 |
| Xenos | 6 | +14.5 | [−17.6, +46.6] | 102.8 | 117.3 |
| **Seat mean** | 6 | **−15.4** | **[−23.7, −7.2]** | 98.0 | 82.6 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1345 | 4.35 s | 1.82 s | 14.11 s | 24.4 s |
| B charge3_lf_tiles | 1588 | 10.22 s | 9.99 s | 20.18 s | 28.4 s |

No errors, timeouts or fallback decisions in either arm.

B is significantly worse for the fifth guide package in a row (034 −10.0, 035 −16.6, 036 −21.8,
037 −19.3, 038 −15.4). Geodens B is the worst yet: 69, 48, 48, 21, 54, 66 (A 82–103). Taklons B
has 37 in one game and 64–91 otherwise. Terrans B has one 147 and is otherwise 70–86. Xenos is
positive (+14.5, not significant) but has stayed near zero or above in all five packages.

Research advances over the whole game (`research_counts.py`, rounds 1–6):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---:|---:|---:|---:|---:|---:|
| A | Geodens | 19 | 7 | 4 | 0 | 3 | 3 |
| B | Geodens | 2 | 5 | 21 | 4 | 7 | 1 |
| A | Taklons | 11 | 0 | 1 | 7 | 17 | 6 |
| B | Taklons | 16 | 12 | 21 | 5 | 5 | 1 |
| A | Terrans | 5 | 0 | 5 | 23 | 7 | 4 |
| B | Terrans | 12 | 2 | 18 | 10 | 8 | 4 |
| A | Xenos | 14 | 14 | 12 | 1 | 9 | 0 |
| B | Xenos | 6 | 22 | 11 | 0 | 7 | 0 |

Same pattern as 037, now on fresh seeds: Geodens B almost never terraforms (TF 2 vs 19) and puts its
research into AI (21 vs 4); Taklons and Terrans B also lean on AI (21 vs 1, 18 vs 5). Xenos, which
does not use the frozen four-faction values, shows no AI lean. The AI bias in the three guided
factions is the clearest repeatable difference and the likeliest cause of the Geodens collapse.

B makes more decisions (1588 vs 1345; Terrans 415 vs 295) at a median 10.0 s against the 20 s cap,
so round-4 rollouts are often cut short (unsearched decisions 1213 vs 1009).

Not measured here: charges gained in rounds 1–3 (`charge_rounds.py` is outside the Discord bot's
allowed tools) and fleet entries / ship actions per arm. The live hard teacher stays; no deploy proposal.
