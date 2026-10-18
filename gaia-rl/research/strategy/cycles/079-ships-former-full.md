# Cycle 079 — ships vs ships_former, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-former-cap20.json` — A plus **former_use** alone
(`install_former_use`, `teacher_patches.py`): a Transdim planet is a colony option in the value only once it is being
formed (the `reserved` ones; a free former with tokens no longer prices the planet in reach as next round's mine), each
Asteroid in reach is a colony option per idle former (range QIC only), and while a former is idle the best forming or
Asteroid mine ranks ahead of a Gaia track advance that outranks it. No instant_forming (it is gated on former_use and was
never measured on its own). Scope and order only, no new number. Queued by the user on 2026-10-18 13:45 ("배포 다 하고
실험 다 시작하면 안되나", E6) as the last single-rule measurement of the 071 bundle. Background: 071 (the whole bundle)
lost −45.3 charges on Terrans with rounds 1–3 mines 11 → 2; 073 (bundle without former_use and instant_forming) had the
Terrans back at −5.3 with mines 12 / 11, so one of the two was the cause. Questions: does former_use on its own turn the
Terrans round 1 (Terraforming research → academy → mine) into forming → pass, and do Taklons and Terrans form more in
rounds 1–3? 6 fresh seeds (geo-quartet-828439 … 841005) × 2 seat-swapped games, agentmaco, commit 4a70abc, all six
rounds, 3 h 31 min wall time. Result: lab/results/079-ships-former-full.md.

Decision set before the run (lab note): a reproduced Terrans loss confirms former_use as the 071 cause; a positive result
makes it a base-stack candidate (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 152.9 | 173.7 | +20.7 | [−17.2, +58.7] |
| Taklons | 6 | 158.9 | 151.8 | −7.1 | [−46.7, +32.5] |
| Terrans | 6 | 182.1 | 162.3 | **−19.7** | [−50.5, +11.0] |
| Xenos | 6 | 174.4 | 143.5 | −30.8 | [−95.8, +34.1] |
| **All** | 6 | | | **−9.2** | [−28.4, +10.0] |

Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −12 | **+80** | −17 | +22 | +42 | +9 |
| Taklons | +10 | −46 | +16 | +23 | −64 | +18 |
| Terrans | −25 | +17 | **−61** | +8 | −19 | **−39** |
| Xenos | +9 | +51 | −29 | **−134** | −43 | −39 |
| Pair mean | −4.5 | +25.5 | −22.9 | −20.0 | −20.9 | −12.7 |

Five pair means negative; the one positive pair (p001) is Geodens +80 and Xenos +51 against Taklons −46. Terrans are
negative in four pairs (p000, p002, p004, p005), Xenos in four (p003 −134 is the posted replay `pair-003/game-1-A02`
seat 3, Xenos B 79 against A 213), Geodens positive in four, Taklons 3:3.

**Final VP** (read with the charges; not the verdict measure): All **−1.1** [−17.2, +15.0], pair means −4.3, +5.8, +12.3,
**−30.3**, +2.0, +8.0. Geodens **+8.7** [−8.7, +26.0] (−15, +32, +13, +2, 0, +20), Taklons −3.0 [−25.4, +19.4] (+6, −27,
+32, −10, +2, −21), Terrans **−6.7** [−23.5, +10.2] (−2, +1, −11, **−36**, −3, +11), Xenos −3.3 [−42.5, +35.9] (−6, +17,
+15, **−77**, +9, +22). Seat-average final VP A 90.3 → B 89.2. The p003 pair carries both big losses: Xenos B 65 against A
142 (turns 32 vs 60, research levels 6 vs 14, end research VP 0 vs 28, mines built 4 vs 8) and Terrans B 101 against A 137.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1757 | 11.73 s | 14.23 s | 20.33 s | **111.9 s** |
| B ships_former | 1709 | 12.41 s | 14.37 s | 20.34 s | **113.9 s** |

No errors, timeouts or fallback decisions. Unsearched decisions 1376 vs 1304. Decisions per faction A / B: Geodens
374 / 426, Taklons 438 / 414, Terrans 458 / 414, Xenos 487 / 455. **Both arms have one decision above 100 s** (the hard
cap is 60 s; the previous A-arm maximum was 51.1 s in 071). It is in the unchanged A arm as well, so it is not the rule;
the 078 analysis (`explain_ab_decisions.py` runs on the same host between 02:00 and 03:30) overlapped this run and is the
likely cause, not verified (the per-decision timing is in `decisions.jsonl.gz`, not in the summary).

**Where the rule fired (counts from the run folder).**

Terrans, the question of the run. Round 1 only (`action_counts.py --rounds 1-1`, six seats per arm), A / B:

| Faction | GaiaFormation | Build | Upgrade | ResearchAdvance | Asteroid mine |
|---|---:|---:|---:|---:|---:|
| Geodens | 0 / 0 | 5 / 6 | 14 / 14 | 6 / 4 | 0 / 1 |
| Taklons | 0 / 1 | 6 / 5 | 12 / 14 | 6 / 6 | 0 / 0 |
| **Terrans** | **1 / 5** | **1 / 0** | 15 / 14 | 6 / 5 | 0 / 0 |
| Xenos | 0 / 0 | 9 / 7 | 14 / 15 | 6 / 6 | 1 / 0 |

Rounds 1–3 (`--rounds 1-3`), A / B:

| Faction | GaiaFormation | Build | Upgrade | ResearchAdvance | Asteroid mine | Ship entries |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | 0 / 0 | **12 / 17** | 24 / 24 | 19 / 19 | 1 / 1 | 11 / 11 |
| Taklons | 0 / 1 | 12 / 12 | 29 / 29 | 16 / 15 | 1 / 0 | 9 / 5 |
| Terrans | 4 / 5 | **10 / 6** | 30 / 26 | **22 / 17** | 1 / 1 | 10 / 10 |
| Xenos | 0 / 0 | 16 / 12 | 28 / 28 | 15 / 14 | 7 / 5 | 15 / 12 |

Whole game: Terrans GaiaFormation 9 / 9, Build 22 / 18, ResearchAdvance 50 / 44; Taklons GaiaFormation 3 / 5, Build 29 / 23;
Geodens Build 18 / 21; Xenos Asteroid 17 / 11, Build 26 / 24.

So the 071 Terrans failure mode **does reproduce, at about half the size**: the B Terrans form five times in round 1
(A once) and build no round-1 mine (A one), then form nothing in rounds 2–3 (A three) — former_use moves the Terrans'
forming from rounds 2–3 into round 1, at the cost of the round-1 mine and research (rounds 1–3 mines 10 → 6, research
22 → 17 of which AI 16 → 11, Science 6 → 4). Round-1 upgrade paths (`upgrade_targets.py --rounds 1-1 --faction Terrans`):
TS 6 / 6, RL 6 / 6, **academy A 3/6 → B 2/6** (A: p000, p002, p003; B: p000, p003 — p002's academy is lost). Round-1 lab
tiles are the same mix (tile 5 ore income five times in both arms, tile 2 three times in both), so the 073 reading that
former_use devalues the ore tile is not visible in tile choice here; round-1 ore 30 / 27 (power action 3: 6 / 4). End
board (`game_profile.py`): Terrans turns 45.3 → 40.7, tech tiles 6.8 → 6.0, research levels 16.7 → 16.0, end research VP
27.3 → 24.0, final 92.5 → 85.8. 071 (bundle) was charges −45.3, mines 11 → 2, final VP −14.0; 079 (former_use alone) is
−19.7, 10 → 6, −6.7; the remainder of 071 would be instant_forming (gated on former_use, so it cannot be measured alone)
and the interaction with opening_budget, neither measured.

Taklons, the faction the rule was written for (052: 19 Gaia advances, 2 formings). Rounds 1–3 forming 0 → 1, whole game
3 → 5, Gaia research 5 → 5 in rounds 1–3, Asteroid mine 1 → 0, ship entries 9 → 5; charges −7.1 (3:3), end turns
42.3 → 39.8, final 84.0 → 81.0. The rule does not get the Taklons to form in rounds 1–3 on these seeds.

Geodens, the one gain: rounds 1–3 Build 12 → 17, Gaia research 6 → 11, AI 14 → 11, no forming (0 / 0; whole game 2 / 1);
end mines 5.5 → 6.5, labs 0.5 → 0.2, PI 0.2 → 0.0, tech tiles 4.7 → 3.7, artifacts 0.8 → 1.7, ship-action VP 3.3 → 6.7,
mission VP 22.3 → 26.3, final 68.3 → 77.0. Round-1 upgrade paths are the same shape in both arms (TS, then RL with a Gaia or
Economy tile; academy A 1/6 → B 2/6). There is no direct path from the rule to this footprint in the counts — the B
Geodens form nothing and advance Gaia *more* — so it is either indirect (Terrans leaving planets and research steps on
the shared board) or noise (CI [−17.2, +58.7], p001 +80 and p004 +42 carry it).

Xenos have no former in rounds 1–3 (Gaia research 0 in both arms), so the rule adds no option for them and the −30.8 is
one seat (p003 −134, a round-1-onward collapse to 32 turns) plus the shared-board effect; without p003 Xenos are −10.2.

Rounds 1–3 research (`research_counts.py`), A → B: Geodens Gaia 6 → 11, AI 14 → 11; Taklons TF 4 → 2, Nav 2 → 0; Terrans
AI 16 → 11, Nav 0 → 2, Sci 6 → 4; Xenos Nav 14 → 9, Eco 1 → 3.

Reading. The question is answered: **former_use on its own reproduces the 071 Terrans loss** (charges −19.7, four pairs
negative; round-1 forming 1 → 5 with the round-1 mine and one academy gone; final VP −6.7), about half the 071 size, in the
same shape. The rule's own target — Taklons forming with an idle former — does not move (rounds 1–3 forming 0 → 1, Gaia
advances 5 → 5), and the Geodens gain has no path through the rule that the counts show. Overall charges −9.2 with five
pair means negative, final VP −1.1. **Not proposed for the base stack**; the base stays vm_lf_ts_ships, ships_former
stays opt-in, no code change, nothing to deploy. With 073 (−former), 077 (−former −academy), 078 (label_value) and 079
(former_use) the 071 bundle is now taken apart: the Terrans loss is former_use, the final-VP drop of 073/077 is not
academy_economy, label_value did nothing on six seeds, and no single part has met the adoption condition.

Candidate follow-ups (user decision pending, not queued; 080–082 are queued and run first):
(a) **close the former_use line** — keep ships_former and ships_fix opt-in, no re-check; the 071 bundle has no part left
worth a fresh-seed run on this evidence; (b) if the user still wants the 052 Taklons behaviour (idle former → form), a
Taklons-only scope of rule 3 alone (order: forming ahead of a Gaia advance while a former is idle, **without** the
colony-option change that costs the Terrans their round-1 mine) — new factory and spec, 6 pairs, full game, judged on
Taklons charges and forming counts; (c) a Terrans-excluded former_use (Terrans keep the frozen Transdim valuation, the
other three take the rule) — same cost, but the only positive signal it would chase is the Geodens +20.7 whose mechanism
is not visible. The bot's recommendation is (a), and to spend the next lab slot on the pending E9 (b) geodens_b14_tech
alone or E7 (ships_land_safe).
