# Cycle 052 — live hard vs the current stack (vm_lf_ts)

A: `teacher-a-search4-h1-geodens-cap20.json` (the live hard teacher, geodens_guide).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (047 B arm, the base stack; no research focus).
Question (user, 2026-10-12 "진행 하고"): the deployment decision postponed since 046 — does the gain of 039 and 040
(lf_more vs hard, about +30 each) hold for the current stack?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; a significant positive result leads to a proposal
to replace the hard teacher (deployment itself only after the user confirms).
12 fresh seeds (geo-quartet-538735 … 557172) × 2 seat-swapped games, agentmaco, commit 35436f7, stop_round 3.
Result: lab/results/052-hard-vs-vm-lf-ts.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 12 | 73.9 | 195.0 | +121.1 | [+86.5, +155.6] |
| Taklons | 12 | 109.2 | 138.8 | +29.7 | [+10.8, +48.6] |
| Terrans | 12 | 118.9 | 147.8 | +29.0 | [+4.6, +53.4] |
| Xenos | 12 | 118.6 | 140.7 | +22.1 | [−7.9, +52.1] |
| **All** | 12 | | | **+50.5** | **[+35.1, +65.8]** |

Significant and positive: the condition set before the run is met. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 | p006 | p007 | p008 | p009 | p010 | p011 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | +155 | +95 | +115 | +93 | +183 | +84 | +220 | +93 | +14 | +97 | +149 | +156 |
| Taklons | +69 | +21 | +68 | +40 | +17 | −22 | +62 | +60 | +21 | −1 | +9 | +12 |
| Terrans | +58 | +18 | +4 | +51 | +53 | +27 | +11 | +105 | +24 | +20 | −56 | +33 |
| Xenos | +76 | +34 | −48 | −15 | +48 | +21 | −56 | +95 | +7 | −3 | +64 | +43 |
| Pair mean | +89.7 | +41.8 | +34.5 | +42.1 | +75.3 | +27.6 | +59.3 | +88.2 | +16.4 | +28.5 | +41.4 | +60.7 |

All 12 pair means are positive. Geodens is positive in 12 of 12 pairs, Terrans in 11, Taklons in 10, Xenos in 8.
Geodens carries most of the total: the live teacher's Geodens gains only 73.9 charges in three rounds (two seats at 25
and 32), while every B seat but one is above 158. Taklons and Terrans are significant on their own for the first time
with both at about +29. Xenos is positive but not significant, with swings of ±50–95 per pair.

Against 039 and 040 (lf_more vs hard, 6 pairs each): All +29.7 and +32.3 there, +50.5 here; Taklons +42.6 and +30.5,
now +29.7; Geodens +57.0 and +75.2, now +121.1; Terrans +18.0 and +21.8, now +29.0; Xenos +1.3 and +1.6, now +22.1.
The same shape on a third set of fresh seeds, and no faction lost what it had. The steps added since (value_max,
lf_frozen, ts_chain_direct, knowledge_spend, ship_setup) were each inside the noise at 6 pairs (043–047); this run does
not say which of them moved the total, only that the stack as a whole is ahead of hard by more than lf_more was.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 12 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 8 | 0 | 0 | 8 | 9 | 8 | 33 |
| A | Taklons | 1 | 0 | 1 | 2 | 28 | 8 | 40 |
| A | Terrans | 3 | 0 | 1 | 21 | 8 | 6 | 39 |
| A | Xenos | 1 | 22 | 2 | 1 | 19 | 0 | 45 |
| B | Geodens | 0 | 8 | 21 | 15 | 8 | 7 | 59 |
| B | Taklons | 12 | 0 | 7 | 19 | 3 | 4 | 45 |
| B | Terrans | 11 | 0 | 20 | 6 | 8 | 6 | 51 |
| B | Xenos | 9 | 29 | 2 | 2 | 2 | 0 | 44 |

The two teachers research differently. Hard puts Taklons into economy (28 of 40) and Terrans into Gaia (21 of 39); B
moves Taklons to Gaia and terraforming, Terrans to AI and terraforming, and drops economy for Taklons and Xenos
(28 → 3, 19 → 2). Geodens B researches far more (33 → 59) and takes AI 21 times against 0, with no terraforming at all
(8 → 0). An AI step pays a QIC at once (7 charges on this measure) and economy income is not counted per track in B's
values (guide_r1 part 4), so part of the charge gap comes from how the measure prices tracks, as noted in 049.

Limits of the result:

- The measure is the one B optimises (charge3 leaf value) and A does not, as in 039 and 040. B's settings were fixed
  before the run, so the test is fair on its own terms, but it shows B collects more of what the guide prices, not that
  it wins games.
- VP held at round 4 (reference only, not used for the verdict): −6.8 [−11.0, −2.7]; Terrans −14.4 [−21.1, −7.7],
  Geodens −8.0, Xenos −4.3, Taklons −0.6. B spends points in rounds 1–3 (fleet entry among others).
- Games stop at round 4 since 041, so nothing here covers rounds 4–6. The last full games of this family against hard
  were 039 and 040 (lf_more), where the final score was −15.0 and −20.2.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A hard | 1411 | 2.97 s | 0.79 s | 8.62 s | 25.1 s |
| B vm_lf_ts | 1744 | 11.34 s | 15.08 s | 20.20 s | 22.4 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1002 vs 1249. B makes 24% more decisions and is 3.8×
slower on average (median 19×); its maximum of 22.4 s is inside the live hard wait limit of 60 s. Watch-replay
publishing worked for the first time: pair-006/game-1-A13 seat 1 (Geodens on the A arm, 87 charges against 307).
The two extra replays the user asked for (B furthest ahead: pair-006/game-0-A02 Geodens; B furthest behind:
pair-010/game-0-A01 Terrans, 96 vs 152) were not published — `ab_replays.py export` is outside the bot's allowed tools.

No change to the live teacher in this cycle. The pre-set condition for proposing the hard teacher replacement is met on
the charge measure; the proposal and the open points (rounds 4–6 unseen, 3.8× decision time, the live worker has no
spec-based teacher selection yet) go to the user for a decision.
