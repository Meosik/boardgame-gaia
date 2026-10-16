# Cycle 066 — ships_label, reachable-only version, on the 064 seeds (vm_lf_ts_ships base)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-label-cap20.json` — A plus `opening_label`
(`teacher_patches.guide_label_forecast`), fixed after 065: the guide's round-1 opening label (e.g. Geodens 1AC+2M) is kept
as the remembered goal only while the compared plan's rollout shape can still grow into it (`planning.distance_to` ≠ None);
otherwise the catalog row matching the reached inventory is remembered, as the unmodified teacher does. In 065 the Xenos label
1RL+5M survived after its rollout had drifted to 1RL+1TS+3M, the opening mode never ended, and Xenos built half their mines
(−45 charges). Common to all 14 factions with a guide order; order and scope only, no new numbers.
Question (user, 2026-10-17 "진행해"): on the seeds where the unmodified stack stalls the Geodens academy at the research lab
(064: 5 of 6 games), does keeping a still-reachable label finish the academy and gain charges in rounds 1–3, without the Xenos
damage of 065? Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges, read the Geodens and Xenos rows first;
count Geodens round-1 academies (`upgrade_targets.py`; 064 B = 1/6), Xenos round 1–3 mines (`action_counts.py`; 065 19 → 9),
errors, unsearched. Adoption condition set in advance: more Geodens academies, Xenos mines recovered, no overall loss.
The 064 seeds reused (geo-quartet-699682 … 712850) × 2 seat-swapped games, agentmaco, commit c3482a3, stop_round 3 (ends at the
start of round 4). 1 h 31 min wall time. Result: lab/results/066-ships-label-reachable.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 172.7 | 157.5 | −15.1 | [−46.8, +16.5] |
| Taklons | 6 | 152.9 | 169.5 | +16.6 | [−15.8, +49.0] |
| Terrans | 6 | 176.9 | 162.7 | −14.2 | [−46.2, +17.8] |
| Xenos | 6 | 172.4 | 168.3 | −4.1 | [−51.8, +43.6] |
| **All** | 6 | | | **−4.2** | [−16.7, +8.3] |

Not significant for any row. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −60 | −33 | −4 | +28 | 0 | −22 |
| Taklons | +19 | +72 | −15 | −3 | 0 | +27 |
| Terrans | −44 | −61 | +16 | 0 | 0 | +3 |
| Xenos | +39 | −69 | +21 | −50 | 0 | +34 |
| Pair mean | −11.3 | −22.7 | +4.8 | −6.4 | 0.0 | +10.4 |

Two pairs positive, three negative, one exactly zero: in **pair-004 both games are identical to the second decimal in all four
seats**, so on that seed the label rule never changed a single decision. Terrans in pair-003 are also identical (158.1 both arms).
The other differences are seat-level swings of ±30–70 in both directions, the usual size for six pairs.

**Round-1 Geodens upgrade path** (`tools/upgrade_targets.py --rounds 1-1 --faction Geodens`), A / B per pair. The A arm is the
same stack and seeds as 064 B and reproduces its paths exactly (TS → RL in all six, a second RL in p001, academy in p003):

| Pair | A | B |
|---|---|---|
| p000 | TS → RL (Gaia, tile 5) | same |
| p001 | TS → RL (Gaia, tile 5) → **RL (AI, tile 10)** | TS → RL (Gaia, tile 5) → **AC Science (tile 2)** |
| p002 | TS → RL (tile 5) | same |
| p003 | TS → RL (Eco, tile 5) → AC Science (tile 2, AI) | same |
| p004 | TS → RL (Gaia, tile 5) | same |
| p005 | TS → RL (Eco, tile 5) | same |

Academies finished in round 1: **A 1 of 6 → B 2 of 6**. The fix fires visibly in one game (p001: the second research lab becomes
the academy), and that pair's Geodens row is −33 (the B Geodens game, 181, also had the A-arm Taklons collapse to 81 beside it;
the mirror game's A Geodens made 214). In the four games where the lab is reached and the ore runs out (p000, p002, p004, p005)
neither arm gets past the lab, label or not: keeping the 1AC+2M label does not by itself produce the six ore.

**Xenos**: Build in rounds 1–3 A 12 → B 11 (065: 19 → 9), Upgrade 30 → 30, Research 16 → 14, ExploreSpaceship 16 → 15. The
065 mine halving does not recur, so the reachable-only condition does what it was meant to do. Round-1 paths differ in two pairs
(p001 B adds a second TS, −69; p005 A takes AC Science, B a second RL with Terraforming tile 2, +34), identical in the other four.

Other counts, rounds 1–3 (`action_counts.py`, 6 games per arm, A / B): Geodens Build 11 / 7, Upgrade 22 / 23, Research 17 / 19,
FormFederation 3 / 2; Taklons Build 7 / 11, Upgrade 31 / 31; **Terrans Build 14 / 6**, Upgrade 27 / 27, FormFederation 3 / 1.
Terrans share the rule (their guide order is in the table) and lose in p000 (−44) and p001 (−61) while being identical in p003
and p004; whether the label steered Terrans away from mines in those two games has not been checked. Decisions 899 (A) vs
881 (B). Reference VP at the start of round 4 (not a verdict measure): +0.0 [−3.2, +3.3]; Geodens −3.7, Taklons +2.2,
Terrans −3.7, Xenos +5.3.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A | 899 | 11.66 s | 19.77 s | 20.25 s | 22.6 s |
| B | 881 | 11.78 s | 19.03 s | 20.23 s | 24.2 s |

No errors, timeouts or fallback decisions. Unsearched decisions 637 (A) vs 616 (B).

Reading: the fix removes the 065 failure mode (Xenos −45 → −4, mines 12 → 11) and nudges the Geodens academy count from 1 to
2 of 6, but there is no charge gain to show for it: overall −4.2 [−16.7, +8.3], Geodens −15.1 (065 −8.9; 12 pairs across both
runs about −12), Terrans −14.2. Of the pre-set adoption condition, "Xenos recovered" holds, "more academies" holds by one game,
"no overall loss" is not contradicted but the direction is negative in the two target rows. The rule changes few decisions
(one seed untouched, one Geodens path of six changed) and where it changes them it has not helped. ships_label is **not**
proposed as the base stack; the base stays vm_lf_ts_ships, the label factory/spec remain opt-in, no code change, nothing to
deploy. The underlying 064 finding stands: on these seeds the Geodens 1AC+2M opening is mostly a research-lab opening because
the ore for the academy is not there in round 1, and remembering the label does not change the ore.

Candidate follow-ups (user decision pending, not queued): (a) shelve ships_label and move on to the agreed agenda — former_use
A/B on the ships base (a `..._vm_lf_ts_ships_former` factory and spec are needed; the existing former spec is on the vm_lf_ts
base), then the "no federation" plan in the comparison set; (b) if the Terrans Build 14 → 6 is worth a look first, one
`explain_ab_decisions.py --arm B` run on pair-001/game-0-A23 (Terrans B 186.5 vs A 247.1 in the mirror) to see whether the
Terrans label is still alive when mines are skipped — user-side because of the bot turn limit; (c) 12 new seeds on the same A/B
to settle the Geodens row at 18 pairs (about ±30), low expected value given two runs in the same direction.
