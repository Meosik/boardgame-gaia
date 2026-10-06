# Cycle 037 — guide_r1_charge3_lf vs hard (20 s cap)

A: `teacher-a-search4-h1-geodens-cap20.json` (live hard: 4 comparisons, one-income rollouts, 20 s cap).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-cap20.json` — 036's B (`guide_r1_charge3`) plus the LF
value tables (`_guide['lf_tables']`): each entered ship takes its best net action once per round
(`SHIP_ACTION_NET`: Twilight 4, Rebellion 5.2, TF Mars 2.4, Eclipse 5.2 charges), a green federation
token is worth 3 charges, and pass-scoring advanced tiles are VP × (held + 1–2 to come) × remaining
passes without the 0.6 discount. The charge leaf still drops held VP (charge_vp came in 038).
Question: do the LF table values for ships, federations and advanced tiles recover 036's loss?
User asked for 6 pairs and reporting by charges gained in rounds 1–3; no deploy condition was set.
6 fresh seeds (geo-quartet-424171 … 442438) × 2 seat-swapped games, agentmaco, commit 4e2d255.
Result: lab/results/037-guide-r1-charge3-lf.md.

| Faction | Pairs | B−A VP | 95% CI | A mean | B mean |
|---|---:|---:|---|---:|---:|
| Geodens | 6 | −37.0 | [−71.2, −2.8] | 110.5 | 73.5 |
| Taklons | 6 | −31.7 | [−44.6, −18.8] | 98.3 | 66.7 |
| Terrans | 6 | −14.5 | [−42.5, +13.5] | 97.8 | 83.3 |
| Xenos | 6 | +5.8 | [−18.2, +29.8] | 108.3 | 114.2 |
| **Seat mean** | 6 | **−19.3** | **[−34.6, −4.1]** | 103.8 | 84.4 |

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1383 | 4.31 s | 1.58 s | 12.95 s | 21.9 s |
| B charge3_lf | 1549 | 10.74 s | 11.44 s | 20.19 s | 23.6 s |

No errors, timeouts or fallback decisions in either arm.

B is again significantly worse, about the same as 036 (−21.8 → −19.3): the LF table values did not
change the picture. Geodens B scores 86, 69, 90, 80, 47, 69 (A 84–143); Taklons B 61–82 in all six
games (A 80–118) and is now the clearest loss; Terrans B has one collapse (31) and is otherwise
close; Xenos stays flat for the fourth guide package (+5.9, −0.7, +1.2, +5.8).

Research advances over the whole game (`research_counts.py`, rounds 1–6):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---:|---:|---:|---:|---:|---:|
| A | Geodens | 18 | 10 | 4 | 1 | 12 | 3 |
| B | Geodens | 3 | 5 | 14 | 6 | 2 | 2 |
| A | Taklons | 14 | 0 | 7 | 0 | 24 | 4 |
| B | Taklons | 20 | 4 | 21 | 1 | 6 | 6 |
| A | Terrans | 13 | 0 | 5 | 20 | 5 | 1 |
| B | Terrans | 14 | 5 | 15 | 9 | 6 | 3 |
| A | Xenos | 13 | 17 | 10 | 0 | 14 | 0 |
| B | Xenos | 13 | 24 | 13 | 1 | 9 | 0 |

The Economy bias is gone in B (Taklons Eco 24 → 6), but B now leans on the AI track (Geodens 14
vs 4, Taklons 21 vs 7, Terrans 15 vs 5). Geodens B advances much less overall (32 vs 48) and
almost never terraforms (TF 3 vs 18) — for a faction whose engine is new planet types this is the
likeliest single cause of its collapse. Terrans B moves Gaia less (9 vs 20), as guide_r1 2 intends.

B makes more decisions (1549 vs 1383; Terrans 385 vs 290, Xenos 501 vs 434) and its median decision
takes 11.4 s against a 20 s cap, so round-4 rollouts are often cut short (unsearched decisions
1185 vs 1041).

Not measured here: charges gained in rounds 1–3 (`charge_rounds.py` is outside the Discord bot's
allowed tools) and fleet entries / ship actions per arm (the user asked to check whether B enters
fleets and then uses the ship actions). Not separated: guide_values vs the 035 parts vs charge3 vs
the LF tables. The live hard teacher stays; no deploy proposal.
