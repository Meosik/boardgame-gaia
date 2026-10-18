# Cycle 076 — ships vs ships_income, repeat on fresh seeds, full game

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-income-cap20.json` — A plus `track_income = 'sweet'`,
the same code as 074 (`_track_income_excess` in `teacher_patches.py`): Economy and Science track income counted in the
value, Economy only up to the faction's guide level (default 2, Geodens 3, Terrans 4), Science only for factions whose
guide tracks include Science (Taklons among the four); above that a research step stays priced once, 16 charges.
Queued by the user (2026-10-18 13:45 "배포 다 하고 실험 다 시작하면 안되나" → every pending proposal queued; this was
E1). 074 gave charges −2.4 (flat; Geodens −33.8 in five of six pairs) and final VP +4.2 (Terrans +23.8, Taklons +14.8,
each five pairs positive), both at the edge of 6-pair noise, so under "what was picked after seeing the result is
re-measured on fresh seeds" the same A/B is run again. Question: do the Terrans/Taklons final-VP gain and the Geodens
charge loss reproduce, and what do 074+076 say as 12 pairs?
6 fresh seeds (geo-quartet-791138 … 799894) × 2 seat-swapped games, agentmaco, commit 17ce17f, all six rounds,
3 h 11 min wall time. Result: lab/results/076-ships-income-rep-full.md.

Adoption condition set before the run (lab note): on the 12 pooled pairs, charges not lower, final VP positive, no
Economy-3-or-more pile-up → propose ships_income for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 187.4 | 150.2 | **−37.2** | [−73.6, −0.7] |
| Taklons | 6 | 187.6 | 161.1 | **−26.5** | [−52.4, −0.5] |
| Terrans | 6 | 179.5 | 182.2 | +2.7 | [−65.6, +71.0] |
| Xenos | 6 | 135.5 | 167.8 | +32.3 | [−19.9, +84.5] |
| **All** | 6 | | | **−7.2** | [−39.1, +24.8] |

Flat-to-negative overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −16 | −56 | +9 | −48 | **−90** | −21 |
| Taklons | −55 | −33 | −53 | +5 | −6 | −17 |
| Terrans | +28 | −17 | +98 | −27 | **−95** | +29 |
| Xenos | +44 | −22 | +114 | +57 | +6 | −5 |
| Pair mean | +0.3 | −32.2 | +41.9 | −3.3 | −46.1 | −3.6 |

Two pair means positive (p000 barely, p002 carried by Terrans +98 and Xenos +114). **Geodens are negative in five
of six pairs again** (074: five of six), the CI now excludes zero; p004 is −90 (B 142 against A 232). **Taklons are
negative in five of six** (074: 3:2:1 with a 0), three pairs at −33 to −55. Terrans swing ±95 both ways (p002 B 306,
the highest seat charge of the run; p004 B 157 against A 252). Xenos positive in four pairs; p002 B 269 against A 155
is the posted replay (`pair-002/game-1-A12`, seat 2 — Xenos A).

**Final VP** (read with the charges; not the verdict measure): All **+9.1** [−3.5, +21.8], four pair means positive
(+20.0, −0.5, −8.0, +14.3, +6.3, +22.8). **Taklons +12.5** [−0.3, +25.3], five pairs positive (−1, +13, +31, +2, +8,
+22); **Terrans +10.2** [−7.2, +27.5], five pairs positive (+24, −2, +7, +27, −15, +20); **Xenos +15.7** [−10.9, +42.2],
five pairs positive (+27, +10, −32, +34, +19, +36); Geodens −1.8 [−28.5, +24.8], 3:3 (+30, −23, −38, −6, +13, +13).
Seat-average final VP A 83.6 → B 92.7. Charges and final VP again point opposite ways: Taklons charges −26.5, VP
+12.5; Geodens charges −37.2, VP −1.8 (flat).

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1729 | 12.15 s | 16.86 s | 20.46 s | 35.9 s |
| B ships_income | 1758 | 12.13 s | 16.57 s | 20.41 s | 38.3 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1379 vs 1418. Decisions per faction A / B: Geodens
327 / 362, Taklons 506 / 447, Terrans 431 / 456, Xenos 465 / 493.

**074 + 076 pooled, 12 independent pairs** (pair means from both cycle documents, t-interval with 11 degrees of
freedom):

| | Charges B−A | 95% CI | Pairs B > A | Final VP B−A | 95% CI | Pairs B > A |
|---|---:|---|---:|---:|---|---:|
| Geodens | **−35.5** | [−57.5, −13.5] | 2 / 12 | −5.6 | [−22.2, +11.0] | 6 / 12 |
| Taklons | −12.5 | [−32.0, +7.0] | 5 / 12 | **+13.7** | [+3.3, +24.1] | 10 / 12 |
| Terrans | +15.0 | [−22.7, +52.7] | 8 / 12 | **+17.0** | [+0.3, +33.7] | 10 / 12 |
| Xenos | +14.0 | [−17.8, +45.8] | 7 / 12 | +1.7 | [−17.3, +20.7] | 8 / 12 |
| **All** | **−4.8** | [−20.6, +11.1] | 4 / 12 | **+6.7** | [−2.3, +15.7] | 8 / 12 |

On 12 pairs the overall charge measure is flat (−4.8, the interval covers zero) but the Geodens charge loss is now
significant and the only per-faction charge result that is; the Taklons and Terrans final-VP gains are significant on
12 pairs (ten pairs each). Seat-average final VP over both runs: A 83.8 → B 90.5.

**Where the value change shows (counts from the run folder).**

Rounds 1–3 research (`research_counts.py --rounds 1-3 --seats`, six seats per arm), A → B:

| Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---|---|---|---|---|
| Geodens | 0 → 0 | 0 → 0 | **15 → 8** | 7 → 4 | **6 → 12** | 3 → 4 |
| Taklons | 3 → 2 | 1 → 0 | **11 → 2** | 9 → 2 | 3 → 6 | **4 → 15** |
| Terrans | 5 → 2 | 0 → 1 | **13 → 7** | 4 → 6 | **4 → 12** | 2 → 0 |
| Xenos | 8 → 4 | 10 → 16 | 1 → 1 | 0 → 1 | 7 → 4 | 0 → 0 |

The same shape as 074: AI steps go to Economy (Geodens, Terrans) and to Science (Taklons, whose guide track it is —
074 Science 4 → 10, here 4 → 15, per seat 1, 3, 4, 4, 1, 2 by the end of round 3). Xenos, who have no counted track,
are unchanged on Economy and move within noise. Economy level at the end of round 3 in B (no faction of the four
starts on Economy, so steps = level): Geodens 2, 2, 3, 2, 1, 2; Terrans 2, 1, 2, 3, 2, 2; Taklons 1 ×6 — five of six
Geodens and five of six Terrans reach Economy 2, **Economy 3 or more in 2 of 24 B seats** (A also has 2: Geodens 4,
Xenos 4). No 10-06 all-Economy pile-up, as in 074 (also 2 B seats). Whole game (`--rounds 1-6`): Geodens Economy
9 → 16 (cap 3 → most B seats 3 by the end), Terrans 11 → 22 (cap 4), Taklons Science 6 → 24, AI Geodens 20 → 17 ·
Taklons 19 → 16 · Terrans 19 → 17; Xenos Navigation 17 → 27.

Rounds 1–3 actions (`action_counts.py`, six seats per arm), A / B: Build Geodens **13 / 7**, Taklons 9 / 7, Terrans
7 / 8, Xenos 12 / 18; Upgrade Geodens 25 / 30, Taklons 30 / 27, Terrans 29 / 30, Xenos 24 / 28; GaiaFormation Geodens
**3 / 0**, Taklons 1 / 0, Terrans 2 / 2, Xenos 0 / 1; ResearchAdvance 19 / 18, 20 / 16, 16 / 14, 14 / 12.

Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`): first tile on the Economy track A 1/6 → B
**4/6** (074: 2/6 → 5/6); Science academy completed in round 1 A **1/6** (p004) → B **4/6** (p000, p002, p004, p005;
074 went 4/6 → 3/6, so the academy count is not what the value change moves — it is the search's own choice on the
seed). The B Geodens with the academy still lose charges (p000 −16, p004 −90; p002 +9, p005 −21).

End-of-game board (`game_profile.py`, mean per seat), A → B:

| Faction | final | turns | mines built | feds | research levels | gaia | ship actions | end: research VP | end: mission VP | pass VP | upgrade VP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | 70.3 → 68.5 | 35.5 → 33.2 | **5.3 → 2.8** | 0.8 → 0.8 | 13.8 → 12.7 | 1.2 → 0.3 | 5.3 → 2.7 | 19.3 → 18.0 | 27.5 → 25.3 | 3.2 → 1.7 | 4.0 → 6.3 |
| Taklons | 76.3 → **88.8** | 45.2 → 46.0 | 3.0 → 3.5 | 1.0 → 0.8 | 15.0 → **17.2** | 0.5 → 0.2 | 4.7 → 4.5 | 22.7 → **28.0** | 20.3 → **27.8** | 8.3 → 9.2 | 10.3 → 11.0 |
| Terrans | 86.7 → **96.8** | 44.0 → 43.8 | 4.5 → 3.3 | 1.0 → 1.0 | 16.2 → 15.7 | 1.0 → 0.7 | 8.2 → 6.7 | 26.0 → 25.3 | 25.0 → 25.2 | 8.0 → **14.2** | 5.7 → 10.2 |
| Xenos | 101.0 → 116.7 | 48.7 → 53.5 | 6.5 → 9.5 | 2.3 → 2.3 | 11.3 → 12.3 | 0.0 → 0.2 | 7.0 → 8.7 | 20.7 → 22.7 | 19.8 → 30.5 | 12.8 → 12.5 | 13.3 → 17.2 |

The B Geodens build half the mines (5.3 → 2.8 over the game, 13 → 7 in rounds 1–3), form no Gaia planets in rounds
1–3 (3 → 0), take fewer turns (35.5 → 33.2) and fewer ship actions, and end with lower research levels. The Economy
steps displace mines and terraforming — for Geodens that also removes the knowledge bonus for new planet types, which
the charge measure counts at once; the final VP is flat (−1.8) because the end-game points (research, mission) hold.
074 showed the same for Geodens in a weaker form (mines 4.7 → 4.5, federations 1.0 → 0.5, mission VP 26.2 → 19.5).
The B Taklons buy Science instead of AI: fewer QIC early (charges −26.5) but research levels 15.0 → 17.2 and research
end-VP +5.3, mission VP +7.5, final +12.5 — the charge-against-VP split of 075 (Taklons Navigation) and 074 (Terrans)
once more, now on Taklons with Science. The B Terrans gain through pass/booster VP (8.0 → 14.2) and upgrade VP
(5.7 → 10.2) with fewer mines (4.5 → 3.3); 074's Terrans gained through more mines (3.8 → 6.2), so the Terrans gain is
there both times but not through one mechanism. Xenos improve across the board here (+15.7) and fell in 074 (−12.3);
over 12 pairs they are flat (+1.7).

Reading. The question of the run is answered: the Geodens charge loss **reproduces** (five of six pairs both times,
12-pair CI [−57.5, −13.5]) and the Terrans/Taklons final-VP gain **reproduces** (ten of twelve pairs each, 12-pair CIs
exclude zero). The pre-set 12-pair condition reads: charges −4.8 [−20.6, +11.1] — not lower in the aggregate but
with one faction significantly lower; final VP +6.7 [−2.3, +15.7] — positive, eight of twelve pairs; no Economy
pile-up (2 of 24 B seats at 3+ both runs, Economy capped at the guide level as designed). On the verdict measure alone
(rounds 1–3 charges, the standing rule) ships_income is **not** a gain: flat overall, Geodens down. On the measures
the lab note asked to read together it meets the stated condition, so the base-stack proposal goes to the user with
the Geodens loss stated; the user decides. No code change, nothing to deploy; ships_income stays opt-in until then.
Note on the Geodens mechanism: the value counts Economy income but the mine the step displaces carried the Geodens
knowledge bonus and the planet for later federations — a scope question (does the Geodens Economy-3 count of B14-03
hold when the alternative is a new planet type?), to be read on a replay before any rule.

Candidate follow-ups (user decision pending, not queued; 077–082 are queued and run first, 077 started 19:31):
(a) **adopt ships_income into the base stack** as the 12-pair condition says (base = vm_lf_ts_ships_income; the live
teacher factory and 081/082 would then be re-pointed in a later step, both need the user); (b) before (a) or instead,
`explain_decision` on the B Geodens of pair-004/game-0-A01 (charges 142 against A 232) at their first rounds 1–3
Economy step, to see which mine/Gaia move the income value pushed out and by how much — one decision, no lab time;
(c) if (b) shows the Economy step beating a new-planet-type mine, a Geodens-only scope change (Economy income counted
only when no mine on a new planet type is available this round, order/scope only, no new number) measured as
ships_income vs ships_income_geo on 6 fresh pairs, full game, same measures. The bot's recommendation is (b) now,
then the user chooses between (a) as-is and (a) after (c).
