# Cycle 054 — first bundle of timing rules (vm_lf_ts_when, rules 1–3)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (vm_lf_ts, the base stack when the run was queued).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-when-cap20.json` — A + `install_when` rules 1–3, order only:
1. research_when: in rounds 1–3 a research advance takes Navigation if range 2 newly reaches a home-type or Gaia
   planet; otherwise Gaia (level 0 with a reachable asteroid, or below level 2 with two reachable transdim planets);
   otherwise Economy up to level 2.
2. contested_first: a move an opponent can take away (power/QIC action, mine, shared ship action) goes before the best
   upgrade or research, only at the decision being played and only if the postponed move can still be paid.
3. ship_when: among entries Rebellion first in rounds 1–2, Eclipse last in round 1, TF Mars last from round 3; a
   round 1–2 entry counts as a "contested" move.
Question (user, 2026-10-14 "계속해. 테스트는 안돌리나?"): do the guides' "when to do what" rules raise early charges?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges; also look at research tracks, unsearched
decisions and replays. Known caveat: the measure prices an Economy step at break-even.
12 fresh seeds (geo-quartet-586891 … 607670) × 2 seat-swapped games, agentmaco, commit 7f9826f, stop_round 3.
Neither arm has brainstone_ships (the run started before it joined the base stack).
Result: lab/results/054-vm-lf-ts-when.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 12 | 159.3 | 135.4 | −23.9 | [−57.4, +9.6] |
| Taklons | 12 | 155.5 | 151.2 | −4.3 | [−21.9, +13.4] |
| Terrans | 12 | 170.9 | 126.3 | −44.7 | [−78.9, −10.4] |
| Xenos | 12 | 151.8 | 141.8 | −10.0 | [−39.5, +19.6] |
| **All** | 12 | | | **−20.7** | **[−33.2, −8.2]** |

Significantly negative overall. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 | p006 | p007 | p008 | p009 | p010 | p011 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Geodens | +29 | −93 | −96 | −60 | +69 | −30 | 0 | +41 | −12 | −75 | −40 | −21 |
| Taklons | −8 | −49 | −19 | +2 | +1 | +8 | +65 | −34 | −13 | −10 | −5 | +11 |
| Terrans | −50 | −34 | −78 | +50 | −10 | −29 | −55 | −124 | −39 | −145 | −39 | +16 |
| Xenos | +8 | +70 | −13 | −61 | −111 | −18 | −19 | −10 | +53 | −16 | +1 | −2 |
| Pair mean | −5.1 | −26.7 | −51.6 | −17.1 | −12.8 | −17.4 | −2.1 | −31.7 | −2.6 | −61.5 | −20.8 | +1.2 |

Eleven of twelve pair means are negative. Terrans is negative in 10 of 12 pairs and significant on its own; the two
worst (−124, −145) are B seats at 131 and 51 charges against 254 and 196. Geodens is negative in 8 pairs with three
B seats at 59–81. Taklons and Xenos are inside the noise, both slightly negative.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 12 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 1 | 0 | 21 | 15 | 10 | 3 | 50 |
| A | Taklons | 11 | 3 | 13 | 15 | 10 | 6 | 58 |
| A | Terrans | 6 | 1 | 25 | 4 | 11 | 5 | 52 |
| A | Xenos | 5 | 26 | 6 | 1 | 5 | 0 | 43 |
| B | Geodens | 0 | 15 | 13 | 9 | 5 | 0 | 42 |
| B | Taklons | 6 | 20 | 7 | 11 | 7 | 2 | 53 |
| B | Terrans | 4 | 19 | 6 | 2 | 9 | 3 | 43 |
| B | Xenos | 1 | 21 | 0 | 17 | 2 | 1 | 42 |

Rule 1 changes research a great deal. Navigation: Geodens 0 → 15, Taklons 3 → 20, Terrans 1 → 19. Xenos Gaia 1 → 17
(the asteroid branch). AI drops everywhere (Terrans 25 → 6, Geodens 21 → 13, Xenos 6 → 0). Economy does not rise in
any faction (it falls), so the "otherwise Economy to 2" branch almost never fires: one of the first two conditions is
nearly always true. B also researches less in total for Geodens (50 → 42) and Terrans (52 → 43).

Actions in rounds 1–3 (`action_counts.py`, sum over 12 seats): Build A/B Geodens 30/35, Taklons 23/32, Terrans 28/26,
Xenos 29/38; ExploreSpaceship 23/21, 0/0, 22/24, 35/30; GaiaFormation Geodens 3/1, Terrans 8/3; PowerAction 13/11,
46/48, 17/20, 26/25. Rule 2 shows as more mines for three factions. Ship entries are unchanged in number (rule 3 only
reorders them). Xenos has 17 Gaia advances and 0 Gaia formations in the B arm.

The three rules ran together, so the run cannot say which one costs the charges. The research shift is the largest
visible change and matches cycles 048 and 049, where sending Taklons and Terrans to Navigation also lost charges
(049: −20.9, Terrans −22.3 in all six pairs). The measure counts a research step at a flat 16 charges plus its
immediate reward: an AI step brings power tokens and charges now, a Navigation 2 step brings nothing until planets
are built on, and three rounds may not be enough to show that. The loss is therefore partly real (fewer research
steps, Xenos Gaia steps with no formation) and partly what the measure cannot see.

VP held at round 4 (reference only, not used for the verdict): All −0.5 [−2.2, +1.2]; Terrans −2.3, Taklons −0.8,
Geodens +0.6, Xenos +0.3.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 1816 | 11.99 s | 20.00 s | 20.32 s | 26.0 s |
| B vm_lf_ts_when | 1803 | 11.57 s | 17.08 s | 20.29 s | 30.6 s |

No errors, timeouts or fallback decisions (first league run of the `install_when` code). Unsearched decisions 1306 vs
1260: B does not finish fewer comparisons, so the worry noted while building rule 2 (one finished comparison instead
of two at 20 s) does not show in the totals. Watch replay published: pair-009/game-0-A13 seat 0 (Terrans on the B arm,
51 charges against 196).

Rejected in this form: rules 1–3 as a bundle do not join the base stack. The base stack stays vm_lf_ts_ships. No change
to the live teacher.
