# Cycle 053 — Taklons spaceship entry (vm_lf_ts_ships)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (the base stack, 052 B arm).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — A + `install_brainstone_ships`: the frozen
teacher's "no Brainstone Gaia commitment" rule blocked every Taklons spaceship entry (052: 0 entries in both arms); B
allows the entry while the Brainstone is in bowl I. Timing rule: while an opponent who has not passed still has a
building within 2 hexes (can still give charges), the entry is ranked just above passing; otherwise it keeps its own
score. Order only.
Question (user, 2026-10-13 "바꾸고 진행해야지"): does letting Taklons enter ships raise Taklons charges?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges, Taklons above all; the other three factions should
stay near 0; also look at the number of Taklons entries.
12 fresh seeds (geo-quartet-559074 … 586764) × 2 seat-swapped games, agentmaco, commit dafda20, stop_round 3.
Result: lab/results/053-vm-lf-ts-ships.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 12 | 150.0 | 149.1 | −0.9 | [−30.9, +29.1] |
| Taklons | 12 | 163.2 | 170.7 | +7.5 | [−13.9, +28.9] |
| Terrans | 12 | 164.4 | 165.1 | +0.7 | [−12.8, +14.1] |
| Xenos | 12 | 136.0 | 158.4 | +22.5 | [+1.5, +43.4] |
| **All** | 12 | | | **+7.4** | **[−3.5, +18.4]** |

Not significant overall, and not significant for Taklons, the only faction the patch changes. Per-pair B−A from the
seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 | p006 | p007 | p008 | p009 | p010 | p011 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | −13 | −51 | +51 | −4 | +51 | +62 | −90 | +43 | +13 | +2 | −42 | −34 |
| Taklons | +37 | −37 | −64 | +33 | +4 | +13 | +6 | +48 | +19 | −26 | +28 | +31 |
| Terrans | +15 | +26 | −7 | +3 | +15 | −47 | −3 | −17 | +30 | +6 | −16 | +4 |
| Xenos | +57 | +1 | −6 | +5 | 0 | +56 | −2 | +34 | +47 | +83 | +23 | −28 |
| Pair mean | +24.0 | −15.3 | −6.4 | +9.4 | +17.2 | +20.8 | −22.1 | +26.9 | +27.1 | +16.2 | −1.8 | −6.9 |

Seven pair means are positive, five negative. Taklons is positive in 9 of 12 pairs; the three negative pairs (−26, −37,
−64) are larger than most of the positive ones, so the mean is +7.5 with an interval of ±21. Geodens and Terrans are at
0 as expected for factions the patch does not touch.

Xenos is the one significant row (+22.5, lower bound +1.5), yet the patch contains no Xenos code. Eight pairs are
positive and four of those carry it (+47 to +83); the A arm has two very low Xenos seats (74 and 90). The change can
only reach Xenos indirectly (a Taklons that enters a ship takes a ship slot and passes at a different time), and one
borderline row out of four is also what chance gives. It is not read as an effect of the patch.

Does the entry happen? Checked in one game (`list_decisions.py`, pair-000/game-0-A02, Taklons on the B arm): round 2,
step 80 `ExploreSpaceship Rebellion` after a `PowerToQic`, VP 10 → 5, then pass at step 85; in round 3 the Rebellion
tech tile action (step 138). So the block is lifted and the entry comes late in the round as the timing rule intends.
The count over all 24 games was not taken — `action_counts.py` is outside the bot's allowed tools.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 12 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 0 | 0 | 30 | 9 | 8 | 6 | 53 |
| A | Taklons | 9 | 0 | 22 | 11 | 5 | 5 | 52 |
| A | Terrans | 11 | 1 | 22 | 3 | 8 | 5 | 50 |
| A | Xenos | 10 | 20 | 10 | 1 | 2 | 0 | 43 |
| B | Geodens | 3 | 2 | 24 | 10 | 9 | 6 | 54 |
| B | Taklons | 8 | 0 | 18 | 11 | 7 | 5 | 49 |
| B | Terrans | 12 | 2 | 23 | 5 | 8 | 5 | 55 |
| B | Xenos | 13 | 22 | 6 | 1 | 2 | 0 | 44 |

Research is nearly the same in both arms. Taklons takes AI a little less often (22 → 18); no track moves by more than
six advances for any faction.

VP held at round 4 (reference only, not used for the verdict): All +0.9 [−1.2, +3.1]; Taklons −5.5 [−9.2, −1.8],
Terrans +3.8, Xenos +3.8, Geodens +1.7. The Taklons figure is the entry cost (5 VP per ship); on the charge measure the
points are already counted at 1.5 and the Taklons total is still +7.5.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 1801 | 11.30 s | 15.79 s | 20.21 s | 24.2 s |
| B vm_lf_ts_ships | 1848 | 11.29 s | 15.81 s | 20.21 s | 24.0 s |

No errors, timeouts or fallback decisions (first league run of the new code). Unsearched decisions 1252 vs 1299.
Decision time is identical. Watch-replay publishing worked: pair-006/game-1-A13 seat 2 (Geodens on the B arm, 54
charges against 143).

No change to the live teacher. The patch removes a block that made a legal action impossible for Taklons and does no
measurable harm, but a Taklons gain is not shown: +7.5 at 12 pairs is inside the noise. Whether it joins the base stack
is the user's call; until then the base stack stays vm_lf_ts. The same block exists in the live hard teacher.
