# Cycle 077 — ships vs ships_fix_noacademy, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-fix-noacademy-cap20.json` — A plus the 073 bundle
**without academy_economy**: opening_budget with the first-step fix, budget_guard, opening_release and geodens_b14_tech
(first standard tile 10 or 4 on Economy, no Gaia advance before round 5). Order and scope only, no new number.
Queued by the user (2026-10-18 13:45 "배포 다 하고 실험 다 시작하면 안되나" → every pending proposal queued; this was
E2, the 073 follow-up (a)). Background: 071 and 073 showed the same academy_economy footprint (rounds 1–3 AI → Economy
for every academy faction, fewer end research levels) and 073 ended at final VP −9.5 with Geodens negative in all six
pairs; academy_economy is the only rule of the bundle that acts in rounds 2–3 for all four factions, so the rest is
measured without it. Question: do the budget, release and Geodens-first-tile rules alone keep charges and final VP from
falling?
6 fresh seeds (geo-quartet-802280 … 811267) × 2 seat-swapped games, agentmaco, commit 61d05fa, all six rounds,
3 h 08 min wall time. Result: lab/results/077-ships-fix-noacademy-full.md.

Adoption condition set before the run (lab note): charges positive and final VP not lower → propose ships_fix_noacademy
for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 189.9 | 158.5 | **−31.4** | [−71.2, +8.4] |
| Taklons | 6 | 170.8 | 194.4 | **+23.6** | [−15.3, +62.6] |
| Terrans | 6 | 154.4 | 144.5 | −9.9 | [−24.9, +5.1] |
| Xenos | 6 | 142.1 | 153.4 | +11.3 | [−27.7, +50.4] |
| **All** | 6 | | | **−1.6** | [−20.3, +17.1] |

Flat overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | **−86** | +11 | −39 | −14 | **−63** | +2 |
| Taklons | −9 | **+63** | +7 | +42 | −24 | **+62** |
| Terrans | −11 | +6 | −19 | −8 | +5 | −31 |
| Xenos | −22 | −43 | +37 | +48 | +41 | +8 |
| Pair mean | −31.8 | +9.0 | −3.6 | +17.1 | −10.3 | +10.1 |

Three pair means positive. **Geodens are negative in four of six pairs**, two of them large (p000 B 171 against A 256
— the posted replay, `pair-000/game-1-A13` seat 0; p004 B 155 against A 218). Taklons are positive in four pairs, three
of them by +42 to +63 (B 208, 197, 240 — the three highest Taklons seats of the run are all B). Terrans are negative in
four pairs, all within ±31. Xenos positive in four pairs, ±48 noise.

**Final VP** (read with the charges; not the verdict measure): All **−4.0** [−12.5, +4.6], two pair means positive
(−3.3, +4.5, +5.3, −5.0, −9.3, −16.0). **Geodens −11.5** [−31.0, +8.0], four pairs negative (−9, −34, −1, +5, +5,
−35; B 35 and 65 against A 70 and 99); Xenos −7.7 [−27.9, +12.6], four pairs negative (−2, +19, +9, −23, −29, −20);
Terrans −2.8 [−37.7, +32.0] (3:3, ±48); Taklons +6.2 [−24.3, +36.6], four pairs positive (+14, +17, −27, +26, −32,
+39). Seat-average final VP A 86.5 → B 82.5. The Geodens end result is lower again (073: −19.3, all six pairs; here
−11.5, four pairs) with academy_economy gone.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1788 | 11.98 s | 17.41 s | 20.29 s | 24.9 s |
| B ships_fix_noacademy | 1776 | 11.97 s | 17.29 s | 20.31 s | 24.9 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1409 vs 1377. Decisions per faction A / B: Geodens
409 / 376, Taklons 484 / 504, Terrans 422 / 409, Xenos 473 / 487.

**Where the rules fired (counts from the run folder).**

Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`), the rule geodens_b14_tech targets. B's first
standard tile is **tile 10 in five of six seats** (p000 takes tile 3 on Science); the tile is placed on Economy in three
of those (p001, p003, p005), with no advance in two (p002, p004). B completes the **Science academy in round 1 in all
six seats** (A: 2/6 — p000 and p005; three A seats stop at the lab with a Gaia placement, p004 builds a second trading
station instead). So the opening rules do what they were written to do, and the Geodens with the academy still lose
charges in four pairs: the round-1 academy is not the lever the charge measure rewards (064–068 said the same).

Rounds 1–3 research (`research_counts.py --rounds 1-3 --seats`, six seats per arm), A → B:

| Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---|---|---|---|---|
| Geodens | 0 → 0 | 0 → 1 | 12 → 16 | **10 → 0** | 7 → 6 | 5 → 5 |
| Taklons | 4 → 4 | 0 → 0 | 10 → 10 | 5 → 8 | 4 → 5 | 3 → 2 |
| Terrans | 4 → 4 | 0 → 1 | **15 → 10** | 3 → 3 | 3 → 6 | 5 → 6 |
| Xenos | **2 → 8** | 13 → 14 | 7 → 5 | 0 → 0 | 1 → 1 | 0 → 0 |

The academy_economy footprint of 071/073 (AI → Economy for every academy faction: 073 Geodens Economy 7 → 12, Taklons
2 → 9, Terrans 3 → 9, Xenos 0 → 5) is gone: Economy moves 7 → 6, 4 → 5, 3 → 6, 1 → 1. What remains is geodens_b14_tech's
Gaia block (Geodens Gaia **10 → 0** in rounds 1–3, 16 → 10 over the game; the steps go to AI 12 → 16) and a Xenos
Terraforming rise (2 → 8, 7 → 16 over the game) that no rule in the bundle names. Whole game (`--rounds 1-6`): Geodens
Navigation 10 → 5, Economy 15 → 17; Terrans AI 16 → 19, Economy 6 → 10; Taklons Economy 6 → 9; Xenos Navigation 21 → 25.

Rounds 1–3 actions (`action_counts.py`, six seats per arm), A / B:

| Faction | GaiaFormation | Build | Upgrade | Asteroid mine | Ship entries | ResearchAdvance |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 2 / 0 | **9 / 6** | **31 / 23** | 1 / 2 | 11 / 12 | 20 / 17 |
| Taklons | 1 / 0 | 9 / 11 | 31 / 31 | 1 / 2 | 9 / 10 | 15 / 19 |
| Terrans | **5 / 1** | 7 / 9 | 29 / 25 | 0 / 0 | 11 / 9 | 18 / 19 |
| Xenos | 0 / 0 | **20 / 12** | 25 / 33 | 1 / 3 | 16 / 16 | 14 / 14 |

The B Geodens build and upgrade less in rounds 1–3 (Build 9 → 6, Upgrade 31 → 23; 073 had 12 → 8 and 29 → 22 — the
same shape without academy_economy), the B Xenos trade mines for upgrades (20 → 12, 25 → 33), the B Terrans form fewer
Gaia planets (5 → 1).

End-of-game board (`game_profile.py`, mean per seat), A → B:

| Faction | final | turns | mines built | feds | research levels | gaia | ship actions | end: research VP | end: mission VP | pass VP | build VP | upgrade VP | fed VP | ship action VP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | 83.7 → **72.2** | 42.8 → 42.0 | 4.8 → 4.7 | 1.0 → 0.8 | 15.8 → **14.5** | 1.2 → 0.7 | 6.0 → 7.0 | 26.7 → **21.3** | 25.3 → 30.5 | 5.5 → 5.0 | 9.2 → 7.2 | 4.3 → 4.8 | 5.2 → 4.7 | **7.8 → 1.2** |
| Taklons | 74.5 → 80.7 | 45.8 → **50.8** | 4.0 → 4.7 | 1.3 → 1.0 | 14.2 → 15.2 | 1.0 → 0.2 | 5.8 → 6.2 | 22.0 → 24.0 | 23.8 → 23.2 | 7.8 → **16.8** | 3.7 → 2.7 | 7.5 → 7.7 | 10.0 → 6.8 | 4.5 → 3.3 |
| Terrans | 79.0 → 76.2 | 43.2 → 40.5 | 3.8 → 3.2 | 1.0 → 1.0 | 14.5 → 14.2 | 2.2 → 1.3 | 6.2 → 3.7 | 20.7 → 20.0 | 20.5 → 24.7 | 5.7 → 7.7 | 8.7 → 3.3 | 7.2 → 5.7 | 6.8 → 8.3 | 9.2 → 3.3 |
| Xenos | 108.7 → 101.0 | 48.0 → 51.0 | 6.8 → 6.3 | 2.5 → 2.2 | 10.7 → 12.8 | 0.0 → 0.0 | 6.3 → 7.2 | 20.0 → 25.3 | 29.8 → 24.8 | 16.2 → 13.7 | 7.2 → 8.3 | 15.8 → 8.2 | 19.8 → 16.2 | 7.3 → 10.2 |

The B Geodens end 11.5 VP lower with the same mines, turns and federations as A; the loss sits in research levels
(15.8 → 14.5, end research VP 26.7 → 21.3 — the Gaia block costs levels the track would have paid 4 VP each) and in
ship-action VP (7.8 → 1.2 with the same number of ship actions, so the B Geodens take ship actions that pay no VP).
Taklons gain through pass/booster VP (7.8 → 16.8) and five more turns (45.8 → 50.8) but lose federation VP
(10.0 → 6.8). Xenos lose upgrade VP (15.8 → 8.2) and federation VP for research levels (10.7 → 12.8).

Reading. The question of the run is answered **no**: without academy_economy the bundle is still flat on charges
(−1.6; 073 +0.9) and still lower on final VP (−4.0, seat average 86.5 → 82.5; 073 −9.5), and the Geodens are the
faction that loses on both (charges −31.4 in four pairs, final VP −11.5 in four pairs; 073 charges −6.1, VP −19.3 in
six pairs). academy_economy was therefore not the cause of the 073 VP drop, or not the only one. The 2–3R AI → Economy
footprint is gone as expected, and the Geodens opening works as designed (first tile 10 in 5/6, academy 6/6), yet the
Geodens end lower; the one Geodens-specific rule left is geodens_b14_tech's Gaia block (rounds 1–3 Gaia 10 → 0, end
research levels 15.8 → 14.5), and the three budget rules act on every faction (Taklons +23.6 charges in four pairs is
the one positive signal, three pairs by +42 to +63, not significant). The pre-set condition fails on both measures, so
ships_fix_noacademy is **not** proposed for the base stack; the base stays vm_lf_ts_ships, the bundle stays opt-in, no
code change, nothing to deploy. The ships_fix line has now been measured three ways (071 full bundle, 073 without
former_use, 077 without former_use and academy_economy) and never met the condition; 078 (label_value) and 079
(former_use alone) are queued and finish the line's single-rule reads.

Candidate follow-ups (user decision pending, not queued; 078–082 are queued and run first, 078 started 22:39):
(a) `explain_decision` on the B Geodens of pair-000/game-1-A13 (charges 171 against A 256, the posted replay) at
their first rounds 1–3 decision where A and B part — one decision, no lab time — to see whether the Gaia block or a
budget rule pushes out the better move; (b) **geodens_b14_tech alone vs ships** (6 fresh pairs, full game, same
measures), the 073 candidate (b): Geodens have lost final VP in both bundle runs that carried it, and it is the only
Geodens-specific rule left; if (a) shows the Gaia block, measure the rule with the Gaia block removed instead (first
tile 10/4 only); (c) the three budget rules alone vs ships, to read the Taklons +23.6 on its own — lower priority, as
the Taklons gain is within noise. The bot's recommendation is (a) now, then (b) after 079 has reported, and otherwise
closing the ships_fix line.
