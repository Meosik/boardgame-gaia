# Cycle 075 — ships vs ships_land, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-land-cap20.json` — A plus `research_when_land`
(`research_when_land_scores` in `teacher_patches.py`): in rounds 1–3, when two or more research advances are on
offer, the land at hand decides which track leads. Land is counted as `tools/contested_planets.py` does — empty
planets of the home type, the two ring types one step away, Gaia and Transdim, within range plus the QIC held
(reach), and those an opponent reaches the same way (contested). Reach 0: the Navigation advance leads (Terraforming
when no Navigation advance is offered). Reach > 0 and contested 0 and Economy below `ECONOMY_SWEET` (2): the Economy
advance leads. Contested land: untouched. Order only, among research moves; the one number is zero.
Queued by the user (2026-10-18 04:30 "항해술을 나중에 올려도 땅 뺏길 걱정이 없다 싶을 때 올리는 게 경제라 그런걸
나타내는게 있었으면", 04:40 "알아서 처리해"). Background: the 071/060 counts put rounds 2–3 reach at 0.3–8 planets a
seat (the starting QIC are spent) and lost planets at 0–0.7 a round, so "no land" was the common early constraint, not
competition; and with Economy and Science priced 0.00 the teacher spends those research moves on AI (071 A Terrans
19 AI steps). Question: does choosing Navigation/Economy from the land signal raise rounds 1–3 charges, and does the
Navigation pile-up of 054 (Geodens 0 → 15) stay away?
6 fresh seeds (geo-quartet-774059 … 786195) × 2 seat-swapped games, agentmaco, commit b4641fe, all six rounds,
3 h 01 min wall time. Result: lab/results/075-ships-land-full.md.

Adoption condition set before the run: charges positive, no Navigation pile-up, final VP not lower → propose
ships_land for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 160.1 | 171.1 | +11.0 | [−15.1, +37.0] |
| Taklons | 6 | 175.4 | 161.7 | **−13.7** | [−33.7, +6.3] |
| Terrans | 6 | 179.8 | 180.8 | +1.0 | [−22.4, +24.3] |
| Xenos | 6 | 141.1 | 144.5 | +3.5 | [−41.9, +48.8] |
| **All** | 6 | | | **+0.4** | [−12.6, +13.5] |

Flat overall. Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +5 | +2 | −14 | +16 | −1 | +58 |
| Taklons | −16 | −37 | +15 | −9 | −4 | −31 |
| Terrans | −16 | +9 | −22 | −10 | +5 | +40 |
| Xenos | −5 | +44 | +50 | −7 | −69 | +7 |
| Pair mean | −7.9 | +4.6 | +7.4 | −2.3 | −17.3 | +18.2 |

Three pair means positive. Taklons are negative in five of six pairs (−37 in p001: B 132 against A 169; −31 in
p005). Geodens are positive in four pairs but the mean is one pair (p005 +58, B 177 against A 119). Xenos swing
±50–70 both ways (p004 −69 is the posted replay, B 121 against A 190). Terrans are ±20 noise with one +40.

**Final VP** (read with the charges; not the verdict measure): All **−0.8** [−14.7, +13.2], three pair means
positive (+12.0, +10.3, −23.5, −8.0, −0.3, +5.0). **Terrans −13.8** [−38.3, +10.6], two pairs positive (+6, −7,
−58, −12, −16, +4; p002 B 69 against A 127); Taklons +6.7 [−10.3, +23.6], four pairs positive (−11, +20, +27, −12,
+13, +3); Xenos +9.0 [−16.7, +34.7], four pairs positive (+53, +15, −11, +6, +7, −16); Geodens −4.8 [−33.7, +24.1],
2:1:3 (0, +13, −52, −14, −5, +29). Seat-average final VP A 88.3 → B 87.6. Charges and final VP point opposite ways
for Taklons (charges −13.7, VP +6.7) and Terrans (charges +1.0, VP −13.8), as in 074.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1845 | 11.32 s | 14.36 s | 20.31 s | 28.4 s |
| B ships_land | 1865 | 11.19 s | 13.91 s | 20.31 s | 28.4 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1405 vs 1400. Decisions per faction A / B: Geodens
441 / 377, Taklons 499 / 516, Terrans 406 / 481, Xenos 499 / 491.

**Where the rule shows (counts from the run folder).**

Rounds 1–3 research (`research_counts.py --rounds 1-3`, six seats per arm), A → B:

| Faction | TF | Nav | AI | Gaia | Eco | Sci |
|---|---|---|---|---|---|---|
| Geodens | 1 → 0 | 0 → 2 | 10 → 14 | 6 → 6 | **5 → 1** | 3 → 2 |
| Taklons | 4 → 3 | **0 → 8** | **11 → 3** | 6 → 5 | 6 → 6 | 4 → 3 |
| Terrans | 5 → 4 | 3 → 0 | 13 → 16 | 2 → 2 | 3 → 3 | 3 → 5 |
| Xenos | 3 → 4 | 12 → 14 | 2 → 0 | 0 → 0 | 3 → 6 | 5 → 0 |

The rule's Economy branch almost never fires. Its condition is reach > 0 **and contested 0**, and at the start of
rounds 2–3 that state holds for 3–6 of 24 seats per round in either arm, about one in five of the seats that have
any reach (`contested_planets.py --rounds 2-3 --games`): whenever a seat has land in reach, an opponent usually
reaches part of it too, so the rule leaves the choice to the search. Economy steps in rounds 1–3 do not rise (Geodens even fall 5 → 1, Taklons 6 → 6, Terrans
3 → 3, Xenos 3 → 6). What fires is the **reach-0 branch**: Taklons, the faction most often at reach 0 (A round 2
start: 4 of 6 seats; round 3: 2 of 6), go from 0 to 8 Navigation steps in rounds 1–3 (per seat 3, 1, 2, 0, 2, 0),
taken out of AI (11 → 3). Geodens 0 → 2, Terrans 3 → 0 (their B games never offer the rule a reach-0 research
choice: B Terrans are at reach 0 in only 2 round starts against A's 4). No 054-style pile-up (Taklons 3 → 20 there);
Taklons 0 → 8 is the one visible shift.

Land at round start (`contested_planets.py --rounds 1-4`, mean reach / contested per seat), A → B:

| Faction | R2 | R3 | R4 |
|---|---|---|---|
| Geodens | 2.7 / 1.2 → 2.5 / 1.7 | 6.2 / 3.3 → 8.2 / 3.0 | 4.8 / 3.2 → 16.8 / 11.5 |
| Taklons | **0.3 / 0.2 → 2.7 / 1.7** | **1.2 / 0.3 → 3.5 / 2.5** | 9.0 / 4.8 → 9.2 / 6.2 |
| Terrans | 0.5 / 0.2 → 3.0 / 1.5 | 4.3 / 1.7 → 1.8 / 1.0 | 18.3 / 11.7 → 9.3 / 5.2 |
| Xenos | 7.7 / 2.2 → 7.8 / 2.2 | 6.0 / 4.2 → 3.0 / 1.2 | 7.2 / 6.7 → 8.8 / 4.0 |

Seats at reach 0 at the start of rounds 2 and 3 together: A 15 of 48, B 11 of 48 (Taklons A 6 → B 3). The Taklons
Navigation steps do what they are for: round-2 reach 0.3 → 2.7, round-3 1.2 → 3.5, and rounds 1–3 Build 8 → 13
(`action_counts.py`: Geodens 16 → 12, Terrans 13 → 9, Xenos 11 → 13; upgrades Taklons 32 → 29, Terrans 24 → 31).
But their rounds 1–3 charges fall (−13.7, five pairs): the Navigation step buys land and mines, the AI step it
replaces bought QIC that the charge measure counts at once, and the mines do not pay back inside three rounds.
Lost planets stay at 0–0.7 a round in both arms; the rule's reading of the early game (no land, not competition)
holds, but acting on it does not raise charges.

End-of-game board (`game_profile.py`, mean per seat), A → B:

| Faction | final | turns | mines built | feds | research levels | end: research VP | end: mission VP | build VP | pass VP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | 69.5 → 64.7 | 39.2 → 37.7 | 5.5 → 4.7 | 0.8 → 1.0 | 14.3 → 14.3 | 19.3 → 20.0 | 24.0 → 19.8 | 2.8 → 5.0 | 6.8 → 3.2 |
| Taklons | 84.0 → **90.7** | 48.7 → 50.0 | 3.2 → **4.5** | 0.8 → 1.0 | 16.2 → 16.2 | 26.0 → 24.7 | 18.3 → 27.2 | 1.8 → 7.8 | 16.8 → 15.3 |
| Terrans | 90.5 → **76.7** | 42.7 → 44.3 | 4.8 → 3.8 | 1.0 → 1.0 | 15.8 → 15.0 | 26.0 → 22.0 | 26.3 → 23.7 | 3.2 → 1.5 | 9.0 → 7.8 |
| Xenos | 109.3 → 118.3 | 49.5 → 50.3 | 5.2 → 7.2 | 1.8 → 2.5 | 13.7 → 12.0 | 28.0 → 23.3 | 22.0 → 27.3 | 6.8 → 6.8 | 16.7 → 17.2 |

The B Taklons end with 1.3 more mines built, +6.0 build VP and +8.9 mission VP — the Navigation land turns into
points by round 6, which the rounds 1–3 charge measure does not see. The B Terrans lose 13.8 VP with fewer mines
(4.8 → 3.8) and lower research VP, in games where the rule fired for them at most a few times (Navigation 3 → 0,
AI 13 → 16): this is p002 (−58) plus three pairs at −12 to −16, inside the 6-pair drift that 072 measured (one
seat ±29 VP) but all on one side. Whole game (`--rounds 1-6`): Taklons Terraforming 7 → 14, Navigation 6 → 10,
Gaia 19 → 13; Xenos Science 6 → 1, Gaia 1 → 0.

Geodens round 1 (`upgrade_targets.py --rounds 1-1 --faction Geodens`): identical first tiles in the two arms
(pairwise the same tile and track), academies A 2/6 = B 3/6 (p002 B reaches the Science academy where A stops at
the lab; p004 both reach it). The rule does not touch round 1 in a visible way.

Reading: the pre-set condition fails — charges are flat (+0.4) and final VP is flat (−0.8); no Navigation pile-up.
The rule as written is mostly a **"no land → Navigation" rule**, because its Economy branch needs *no* contested
planet at all, a state that is rare once any land is in reach; the user's stated idea (Economy when there is no
worry about losing land) would need the branch to read "some land only I reach" (safe ≥ 1) rather than "nothing
contested". On the one faction where the reach-0 branch fires often (Taklons) it trades rounds 1–3 charges (−13.7)
for land, mines and final VP (+6.7, four pairs) — the same charge-against-VP split that 074 showed for Terrans
with the income value. ships_land is **not** proposed for the base stack on this run; the base stays
vm_lf_ts_ships, ships_land stays opt-in, no code change, nothing to deploy.

Candidate follow-ups (user decision pending, not queued; 076–082 are already queued and run first): (a)
**ships vs ships_land_safe** — the same rule with the Economy branch on safe ≥ 1 (at least one reach planet no
opponent reaches) instead of contested 0, reach-0 branch unchanged; 6 fresh pairs, full game, same measures; this
is the version that actually exercises the user's Economy idea, and the round-start count tells in advance that it
would fire in about four of five reach > 0 seats instead of one in five; (b) before (a), `explain_decision` on the B Taklons of
pair-001/game-1-A01 (charges 132 against A 169) at the first rounds 1–3 Navigation choice, to see what the
Navigation step displaced and whether the AI step's QIC is what the charge measure is paying for; (c) nothing on
ships_land until the 076 re-run of ships_income is in, then decide whether the two charge-against-VP splits
(074 Terrans, 075 Taklons) say the rounds 1–3 charge measure is under-reading mine investment in full games.
The bot's recommendation is (b) now (one decision, no lab time), (a) after the queue.
