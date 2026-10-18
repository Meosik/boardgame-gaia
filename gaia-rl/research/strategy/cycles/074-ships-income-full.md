# Cycle 074 — ships vs ships_income, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-income-cap20.json` — A plus `track_income = 'sweet'`
(`_track_income_excess` in `teacher_patches.py`): the Economy and Science track income goes back into the value, but
Economy only up to the level the faction's guide names (`ECONOMY_COUNTED`: default 2 from B18-03 / B17-03 / B15-03,
Geodens 3 from B14-03, Terrans 4 from PG18-T20, HadschHallas and Darkanians 4; every level when Economy is the faction's
first guide track — Nevlas, Firaks, Ivits, HadschHallas, Darkanians) and Science only for factions whose guide tracks
include Science (Taklons among the four). Above those levels a research step stays priced once, 16 charges, as in A.
Scope only, the levels are the sources'.
Queued by the user (2026-10-18 04:00 "예전 지시했어도 track_income 다시 해봐. 단 모든 종족이 다 경제 좋다고 올려버리면
안되고", 04:10 "진행해"). Background: guide_r1 rule 4 (2026-10-06 "다들 경제만 올린다") removed track income from the
value, so one Economy or Science step scored 0.00 and the AI step's QIC (4.67) was the largest one-off reward — the A-arm
Terrans of 071 went 19 AI steps in rounds 1–3 where the sources say Science and Navigation first (PG18-T05).
Question: does counting the income up to the guide level raise rounds 1–3 charges without the all-Economy shape of 10-06?
6 fresh seeds (geo-quartet-764225 … 773989) × 2 seat-swapped games, agentmaco, commit 5a441c9, all six rounds,
3 h 19 min wall time. Result: lab/results/074-ships-income-full.md.

Adoption condition set before the run: charges positive, no Economy-3-or-more pile-up, final VP not lower → propose
ships_income for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 205.4 | 171.5 | **−33.8** | [−73.5, +5.8] |
| Taklons | 6 | 142.8 | 144.0 | +1.2 | [−31.8, +34.2] |
| Terrans | 6 | 147.9 | 175.3 | +27.4 | [−31.8, +86.5] |
| Xenos | 6 | 154.4 | 150.2 | −4.2 | [−53.9, +45.5] |
| **All** | 6 | | | **−2.4** | [−24.1, +19.4] |

Flat overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −83 | −23 | −60 | +25 | −17 | −45 |
| Taklons | −25 | 0 | +55 | +10 | +4 | −35 |
| Terrans | +43 | −20 | +118 | +55 | −33 | +1 |
| Xenos | −2 | −4 | −71 | +43 | −43 | +51 |
| Pair mean | −16.8 | −12.0 | +10.6 | +33.2 | −22.1 | −7.2 |

Two pair means positive. Geodens are negative in five of six pairs, three of them by 45–83 (B 131 against A 214 in
p000). Terrans are positive in four pairs with one at +118 (p002, B 260 against A 142, the posted replay). Taklons and
Xenos are ±50 noise both ways.

**Final VP** (read with the charges; not the verdict measure): All **+4.2** [−13.4, +21.9], four pair means positive.
**Terrans +23.8** [−11.4, +59.1], five pairs positive (+57, +8, −35, +47, +41, +25; B 88–118 in five games against
A 52–99); **Taklons +14.8** [−7.2, +36.8], five pairs positive (−22, +36, +24, +11, +31, +9); Geodens −9.3
[−39.4, +20.7], 3:3 (−17, +20, −42, +6, −42, +19); Xenos −12.3 [−43.1, +18.4], 3:3 (+1, +12, −46, −12, −49, +20).
Seat-average final VP A 84.0 → B 88.2.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1854 | 12.41 s | 19.06 s | 20.60 s | 34.3 s |
| B ships_income | 1796 | 11.90 s | 16.96 s | 20.46 s | 34.5 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1446 vs 1378. Decisions per faction A / B: Geodens
462 / 372, Taklons 495 / 427, Terrans 403 / 508, Xenos 494 / 489.

**Where the value change shows (counts from the run folder).**

Rounds 1–3 research (`research_counts.py --rounds 1-3`, six seats per arm), A → B:

| Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---|---|---|---|---|
| Geodens | 0 → 0 | 1 → 0 | **15 → 11** | 5 → 3 | **5 → 12** | 3 → 1 |
| Taklons | 4 → 2 | 0 → 0 | **8 → 3** | 6 → 4 | **3 → 11** | **4 → 10** |
| Terrans | 3 → 3 | 1 → 0 | **11 → 7** | 1 → 5 | **6 → 10** | 3 → 3 |
| Xenos | 2 → 3 | 14 → 16 | 3 → 3 | 0 → 1 | 2 → 0 | 0 → 0 |

The value change does what it was built to do: AI steps move to Economy (and, for Taklons, Science) in rounds 1–3.
Seats reaching Economy 2 by the end of round 3 (`--seats`): Geodens 1/6 → 5/6, Taklons 0/6 → 4/6, Terrans 0/6 → 4/6,
Xenos 1/6 → 0/6 (the Xenos B seats never touch Economy — Navigation 16 and Terraforming instead). Seats at Economy 3
or more in rounds 1–3: A one (Geodens p001 at 3), B two (Geodens p005 at 4, Taklons p003 at 3). **No all-Economy
pile-up**: Economy stops at the counted level in rounds 1–3 for Taklons and Terrans, and Geodens sit at 2–3.

Whole game (`--rounds 1-6`), A → B: Economy Geodens 11 → 18 (three B seats end at 4, the cap being 3; A one seat at
4), Taklons 8 → 13 (two B seats at 3, cap 2; A one seat at 4), Terrans 16 → 14 (max 3, cap 4), Xenos 3 → 0. Science
Taklons 4 → 14 (per seat 4, 3, 3, 1, 2, 1 against 1, 1, 0, 1, 0, 1). AI Geodens 20 → 17, Terrans 18 → 14, Xenos 16 → 10;
Gaia Geodens 16 → 7. Total steps Geodens 54 → 51, Taklons 56 → 69, Terrans 62 → 59, Xenos 55 → 52.

Rounds 1–3 action counts (`action_counts.py`, six seats per arm), A / B:

| Faction | GaiaFormation | Build | Upgrade | Asteroid mine | Ship entries | ResearchAdvance |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 0 / 0 | 9 / 8 | 28 / 27 | 4 / 2 | 12 / 13 | 20 / 15 |
| Taklons | 0 / 0 | 10 / 7 | 29 / 29 | 4 / 0 | 6 / 5 | 14 / 19 |
| Terrans | 1 / 2 | **9 / 13** | **25 / 32** | 2 / 1 | 10 / 10 | 17 / 19 |
| Xenos | 0 / 0 | 13 / 13 | 26 / 26 | 4 / 3 | 16 / 15 | 13 / 13 |

Terrans build and upgrade more in rounds 1–3 under B (9 → 13 mines, 25 → 32 upgrades); Geodens research less
(20 → 15) without building more. Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`): the first
standard tile advances Economy in five of six B seats (tile 5 three times, tile 2, tile 3; A: two seats) and B's
round-1 academies are 3/6 against A's 4/6 (p001 A reaches the academy, B stops at the lab with tile 5 on Economy;
p000 and p002 stop at the lab in both arms — those two pairs are −83 and −60 on Geodens charges, so the academy count
does not explain the loss).

End-of-game board (`game_profile.py`, mean per seat), A → B:

| Faction | final | turns | mines built | feds | research levels | end: research VP | end: mission VP | build VP | upgrade VP | pass VP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | 71.7 → 62.3 | 39.3 → 38.7 | 4.7 → 4.5 | 1.0 → 0.5 | 14.8 → 14.3 | 22.7 → 20.7 | 26.2 → **19.5** | 3.8 → 7.5 | 7.5 → 9.7 | 4.7 → 2.2 |
| Taklons | 72.8 → **87.7** | 46.2 → 44.0 | 3.8 → 3.0 | 1.5 → 1.2 | 14.0 → 14.8 | 21.3 → 23.3 | 21.5 → 26.0 | 1.7 → 6.7 | 12.0 → 8.8 | 5.7 → 7.5 |
| Terrans | 72.5 → **96.3** | 42.8 → 48.5 | 3.8 → **6.2** | 1.0 → 1.0 | 16.5 → 16.2 | 25.3 → 26.7 | 20.3 → 26.8 | 4.8 → 8.7 | 11.8 → 10.2 | 4.2 → 8.0 |
| Xenos | 118.8 → 106.5 | 52.8 → 49.0 | 7.3 → 7.8 | 2.2 → 2.3 | 13.0 → 11.2 | 26.0 → 21.3 | 26.2 → 33.2 | 6.3 → 6.0 | 15.5 → 10.5 | 15.7 → 15.0 |

The B Terrans play 5.7 more turns, build 2.4 more mines, gain 6.0 VP from Gaia forming (A 0.0) and 1.5 artifacts
(A 0.0). The B Geodens lose 6.7 VP at the end-of-game mission scoring and half their federations (1.0 → 0.5), with the
same turn count. Xenos (whose code path is unchanged except Economy counted to 2, which they never take) are −12.3
VP with two seats at −46 and −49 — inside the 6-pair drift that 072 measured (one seat ±29 VP, a pair mean ±12).

Reading: the pre-set condition fails on the verdict measure — charges are flat (−2.4), and Geodens are down in five
pairs. The user's stated worry (10-06: every faction climbs Economy) did **not** recur: Economy stops at the guide
level in rounds 1–3 and Xenos never take it. Final VP goes the other way from the charges: seat average 84.0 → 88.2,
Terrans +23.8 and Taklons +14.8 with five pairs each, which is the first value change since 052 where two factions rise
on final VP together, and the Terrans AI line of 071 A (a value-table artifact) is gone (AI 11 → 7, Economy 6 → 10,
mines 9 → 13). The Geodens charge loss (−33.8) is larger than drift but its mechanism is not visible in the counts:
round-1 paths and academy counts are nearly the same in the two arms, so it sits in rounds 2–3 where B Geodens
research less (20 → 15) and build no more. ships_income is **not** proposed for the base stack on this run; the base
stays vm_lf_ts_ships, ships_income stays opt-in, no code change, nothing to deploy.

Candidate follow-ups (user decision pending, not queued): (a) **re-run ships vs ships_income on fresh seeds** (6 pairs,
full game, same measures) — the project rule is that anything chosen after seeing a result is checked on new seeds,
and this run has a two-faction VP gain against a one-faction charge loss, both at the edge of 6-pair noise; the 8 seeds
left after 075 cover it without a top-up; (b) before (a), `explain_decision` on the B Geodens of pair-000/game-1-A13
(charges 131 against A 214) at the first rounds 2–3 decision where Economy is chosen, to see which move the counted
income displaced; (c) if 075 (ships_land, running since 13:14) is positive, the combined check ships vs
ships_income+land that the 10-18 04:40 plan already foresees. The bot's recommendation is (b) now, then (a) after 075.
