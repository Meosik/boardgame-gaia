# Cycle 073 — ships vs ships_fix_noformer, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-noformer-cap20.json` — A plus the ships_fix bundle of
071 **without former_use and instant_forming**: opening_budget with the first-step fix, budget_guard, opening_release,
geodens_b14_tech (first standard tile 10 or 4 on Economy, no Gaia advance before round 5) and academy_economy (a faction
holding an academy, BalTaks excepted, researches Economy to 2 in rounds 1–3 first). Order and scope only, no new number.
Queued by the user (2026-10-18 04:10 "진행해") after the 071 Terrans loss (−45.3 charges, mines 11 → 2) was traced by
`explain_decision` to decision 31 of p003-g0: with the five flags on, the Terrans lab tile 5 (ore income) scored 18.8
against tile 2 at 20.1; with the flags off, tile 5 scored 22.1 and was chosen, as in A. The reading was that
former_use removes the Transdim mine option from the Terrans value and so lowers the value of ore income.
Question: does dropping former_use remove the Terrans loss while keeping the Geodens (+12.8) and Xenos (+20.6) gains?
6 fresh seeds (geo-quartet-756862 … 763746) × 2 seat-swapped games, agentmaco, commit 5c05bd9, all six rounds,
3 h 17 min wall time. Result: lab/results/073-ships-fix-noformer-full.md.

Adoption condition set before the run: charges positive, Terrans not lower, final VP not lower → propose
ships_fix_noformer for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 174.4 | 168.3 | −6.1 | [−37.5, +25.3] |
| Taklons | 6 | 164.1 | 168.8 | +4.7 | [−29.7, +39.1] |
| Terrans | 6 | 159.9 | 154.6 | −5.3 | [−57.9, +47.3] |
| Xenos | 6 | 141.5 | 151.8 | +10.3 | [−25.4, +46.0] |
| **All** | 6 | | | **+0.9** | [−16.4, +18.3] |

Flat overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +43 | −26 | −34 | +14 | −7 | −28 |
| Taklons | +3 | +24 | 0 | 0 | −49 | +50 |
| Terrans | −14 | −78 | +78 | +4 | −5 | −17 |
| Xenos | +20 | −3 | +52 | +3 | +35 | −45 |
| Pair mean | +13.2 | −20.8 | +24.2 | +5.5 | −6.5 | −10.2 |

Three pair means positive. The Terrans loss of 071 (five pairs negative, four by 60–87) is gone: Terrans are −5.3 with
one pair at −78 and one at +78, the rest within ±17. Geodens are negative in four pairs, Xenos positive in four.

**Final VP** (read with the charges, per the user's request; not the verdict measure): All **−9.5** [−26.4, +7.5].
**Geodens −19.3** [−43.1, +4.4], **negative in all six pairs** (−29, −60, −5, −3, −18, −1; B 46–81 against A 51–116);
Terrans −18.3 [−56.3, +19.6] (p005 −75, p001 −39, p004 −25, p002 +26); Taklons −7.8 [−34.3, +18.7] (3:3);
Xenos +7.7 [−9.3, +24.6] (four pairs positive). Seat-average final VP A 89.8 → B 80.4. In 071 the same rules plus
former_use gave Geodens +8.7 VP and Terrans −14.0; here Geodens turn negative on VP while their charges stay near zero.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1844 | 12.46 s | 19.59 s | 20.36 s | 25.7 s |
| B ships_fix_noformer | 1766 | 12.62 s | 20.00 s | 20.39 s | 25.2 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1469 vs 1406. Posted replay: pair-002/game-1-A12 seat 2
(Terrans A 154 against B 232 in the mirror game).

**Where the rules fired (counts from the run folder).**

Terrans, the question of the run. Rounds 1–3 action counts (`action_counts.py`, six seats per arm), A / B:

| Faction | GaiaFormation | Build | Upgrade | Asteroid mine | Ship entries | ResearchAdvance |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 0 / 0 | 12 / 8 | 29 / 22 | 1 / 2 | 10 / 9 | 20 / 16 |
| Taklons | 0 / 0 | 8 / 9 | 28 / 32 | 3 / 2 | 12 / 8 | 16 / 19 |
| Terrans | 3 / 4 | **12 / 11** | 26 / 24 | 2 / 2 | 12 / 10 | 14 / 15 |
| Xenos | 0 / 0 | 15 / 13 | 31 / 31 | 2 / 4 | 18 / 14 | 15 / 15 |

Terrans mines in rounds 1–3 are 12 / 11 (071: 11 / 2), round-1 Terraforming research ore 4 / 4 (071: 6 / 2), round-1
lab tiles the same in both arms (tile 2 four times, tile 5 twice), round-1 academies 2/6 in both arms. The 071 Terrans
failure mode (forming and passing in round 1 instead of researching Terraforming for the academy) does not appear:
former_use / instant_forming was its cause, as the decision-31 replay suggested.

Rounds 1–3 research (`research_counts.py`, six seats per arm), A → B:

| Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---|---|---|---|---|
| Geodens | 0 → 0 | 1 → 0 | 10 → 10 | **8 → 0** | **7 → 12** | 4 → 1 |
| Taklons | 3 → 5 | 0 → 0 | **14 → 8** | 2 → 5 | **2 → 9** | 5 → 3 |
| Terrans | 5 → 4 | 1 → 0 | **9 → 4** | 1 → 3 | **3 → 9** | 2 → 2 |
| Xenos | 5 → 3 | 10 → 13 | **8 → 2** | 0 → 0 | **0 → 5** | 0 → 0 |

academy_economy fires for all four factions as in 071 (AI → Economy); geodens_b14_tech removes the early Gaia advance
(8 → 0). Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`): B's first standard tile is 10 or 4 on
Economy in five of six seats (A: one Economy placement, three Gaia placements); round-1 academies A 5/6, B 5/6 (B p004
stops at the lab, A p005 stops at the lab). Round-1 ore (`ore_sources.py --rounds 1-1`): Geodens 31 / 29, Taklons
23 / 30 (power action 3 0 → 4), Terrans 29 / 30, Xenos 34 / 38.

End-of-game board (`game_profile.py`, mean per seat), A → B:

| Faction | final | turns | mines built | feds | research levels | end: research VP | end: mission VP | upgrade VP | pass VP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | 81.0 → **61.7** | 42.3 → **34.8** | 4.7 → 3.5 | 1.2 → **0.3** | 15.0 → 13.8 | 23.3 → 19.3 | 25.5 → 23.3 | 9.7 → **2.7** | 7.0 → 3.7 |
| Taklons | 93.8 → 86.0 | 48.2 → 47.2 | 4.5 → 3.3 | 1.0 → 1.2 | 15.7 → 15.0 | 25.3 → 22.7 | 30.8 → 26.0 | 8.5 → 10.7 | 12.0 → 13.2 |
| Terrans | 94.5 → 76.2 | 46.3 → 43.0 | 5.2 → 4.5 | 1.3 → 1.0 | 15.2 → 13.7 | 23.3 → 18.0 | 30.5 → 24.2 | 16.7 → 10.0 | 7.3 → 8.5 |
| Xenos | 90.0 → 97.7 | 46.7 → 52.0 | 7.3 → 8.2 | 2.2 → 2.3 | 11.0 → 10.8 | 19.3 → 19.3 | 18.5 → 18.0 | 9.5 → 10.8 | 17.3 → 17.0 |

The B Geodens play 7.5 fewer turns over the game, build almost no federation (1.2 → 0.3) and score 7 VP less from
upgrades; their rounds 1–3 Build 12 → 8 and Upgrade 29 → 22 are already lower. Terrans and Taklons also end with fewer
research levels (the Economy advances replace AI advances but do not add levels) and lower end-research VP. Xenos, the one
faction that gains on both measures in 071 and 073, play more turns (46.7 → 52.0) and build more mines.

Reading: the Terrans question is answered — without former_use / instant_forming the Terrans round-1 shape and mine count
are back to A's (charges −5.3, noise), so former_use was the 071 Terrans cost. But the remaining bundle is flat on charges
(+0.9) and **lower on final VP (−9.5, seat average 89.8 → 80.4)**, with Geodens negative in all six pairs at the end. The
pre-set condition fails on final VP, so ships_fix_noformer is **not** proposed for the base stack; the base stays
vm_lf_ts_ships, the bundle stays opt-in, no code change, nothing to deploy. Two runs (071, 073) now show the same
academy_economy footprint — AI → Economy in rounds 1–3 for every academy faction, fewer end research levels and fewer
turns for Geodens and Terrans — against a Geodens VP that was +8.7 in 071 and −19.3 here, so the Geodens end result is not
yet separated from the 6-pair drift (072: a single seat ±29 VP, a pair mean ±12 charges). The 071 note that the A-arm
Terrans AI line is a value-table artifact (Economy and Science score 0.00) still stands; 074 (ships_income) measures that
value change on its own.

Candidate follow-ups (user decision pending, not queued): (a) ships vs ships_fix_noformer **without academy_economy**
(= opening_budget fix + budget_guard + opening_release + geodens_b14_tech), fresh seeds, 6 pairs, full game, judged by
charges and final VP, with `research_counts.py --rounds 1-3` and `game_profile.py` (turns, research levels) — this isolates
the one rule that acts in rounds 2–3 for all four factions and whose footprint matches the VP drop; (b) geodens_b14_tech
alone vs ships, to read the Geodens end result on its own; (c) wait for 074 (ships_income) first, since the AI-over-Economy
value artifact it targets is the same lever academy_economy pushes by order. The bot's recommendation is (a), after 074
and 075 have finished so the queue order stands; the remaining seeds after 075 (8) cover one 6-pair run without a top-up.
