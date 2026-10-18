# Cycle 078 — ships vs ships_label_value, full game, fresh seeds

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-cap20.json` — the current base stack vm_lf_ts_ships.
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-ships-label-value-cap20.json` — A plus opening_label in its 066
form (the guide's round-1 label is kept only while the forecast's end-of-round-1 inventory can still grow into the target)
plus **label_value** (among the guide openings whose forecast completes, the comparison value picks the one to follow, the
guide order breaks ties, no plan outside the guide list is taken). Order and scope only, no new number. This is the 072
re-run: 072 was void because its factory set the flag without installing the hook; the factory was fixed and tested, and
the user queued the re-run on 2026-10-18 13:45 ("배포 다 하고 실험 다 시작하면 안되나", E3). Background: in 068 p001 the B
Geodens kept the 1AC+2M label (279.8) although the guide's own PI plan forecast 339.7, so the label cost 60 points of
comparison value. Questions: does letting the value choose inside the guide list raise rounds 1–3 charges and final VP,
and does the 065 Xenos mine loss (1RL+5M label kept while the rollout had left it) stay away?
6 fresh seeds (geo-quartet-815140 … 827152) × 2 seat-swapped games, agentmaco, commit cea4a48, all six rounds,
3 h 03 min wall time. Result: lab/results/078-ships-label-value-full.md.

Adoption condition set before the run (lab note): charges positive, no Xenos loss, final VP not lower → propose
ships_label_value for the base stack (user confirmation).

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 189.6 | 194.5 | +5.0 | [−28.3, +38.2] |
| Taklons | 6 | 171.7 | 171.0 | −0.6 | [−46.8, +45.6] |
| Terrans | 6 | 146.4 | 160.7 | +14.3 | [−12.1, +40.7] |
| Xenos | 6 | 162.6 | 174.8 | +12.2 | [−6.4, +30.8] |
| **All** | 6 | | | **+7.7** | [−17.6, +33.1] |

Per-pair B−A from the seat list (rounded):

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | **+55** | 0 | 0 | −43 | +17 | 0 |
| Taklons | **+78** | 0 | 0 | −32 | **−50** | 0 |
| Terrans | **+64** | 0 | 0 | +18 | +4 | 0 |
| Xenos | +30 | 0 | 0 | +39 | +4 | 0 |
| Pair mean | **+56.8** | 0.0 | 0.0 | −4.3 | −6.2 | 0.0 |

**Three of the six pairs are the same game through round 3 in all four seats** (p001, p002, p005: every seat's charges
equal to the decimal in both games), and the whole +7.7 is pair-000 (+56.8, all four B seats higher); p003 and p004 are
slightly negative. The "A Taklons 107" of the posted replay (`pair-000/game-1-A13` seat 3) is the A side of pair-000.

**Final VP** (read with the charges; not the verdict measure): All **+3.7** [−3.8, +11.1], pair means +4.5, +14.8, −4.0,
−3.8, +3.0, +7.5. Geodens +5.7 [−6.0, +17.3] (+4, +11, +16, −3, −11, +17), Taklons +6.7 [−11.1, +24.5] (+20, +14, −14,
−11, +28, +3), Terrans −1.3 [−13.8, +11.1] (−7, −17, +17, 0, −7, +6), Xenos +3.7 [−25.1, +32.5] (+1, **+51**, −35, −1,
+2, +4). Seat-average final VP A 87.3 → B 91.0. The three pairs that were identical through round 3 first part in
**round 4** (p001 step 170, p002 step 209, p005 step 166 — `list_decisions.py`), so their final-VP differences (+14.8,
−4.0, +7.5) are same-code drift of the kind 068 and 072 measured, not the rule.

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A ships | 1798 | 11.25 s | 13.77 s | 20.24 s | 23.4 s |
| B ships_label_value | 1742 | 11.23 s | 14.32 s | 20.27 s | 23.9 s |

No errors, timeouts or fallback decisions. Unsearched decisions 1383 vs 1316. Decisions per faction A / B: Geodens
401 / 405, Taklons 469 / 408, Terrans 411 / 393, Xenos 517 / 536.

**Where the rule fired** (first differing decision per pair from `decisions.jsonl.gz`, labels from the `selected` field,
values from `explain_ab_decisions.py`).

| Pair | First A≠B decision | Seat | Remembered label A → B | Round-1 move A → B | Taklons charges A → B |
|---|---|---|---|---|---:|
| p000 | step 46 (R1) | Taklons | 1RL+2M → 1AC+2M, then **switched to 1RL+1TS+1M** at step 47 | mine at −4,−2 → power→QIC, mine at −6,−2, second trading station at −9,1 | 107 → 185 |
| p003 | step 45 (R1) | Taklons | 1RL+2M → 1AC+2M | power→QIC (current-choice 283.9, a 1RL+1TS+1M shape, later the second TS) → power action 4 (only one comparison completed: 1AC+2M 281.9) | 227 → 195 |
| p004 | step 42 (R1) | Taklons | 1RL+2M → 1AC+2M | 2-ore power action from the plan Taklons-academy-Economy (236.0, not in B's comparison set) → power→QIC (current-choice 226.3 > 1AC+2M 223.8) | 201 → 151 |
| p001, p002, p005 | R4 | — | identical moves through round 3 | — | 0 |

So in every pair where the rule changed anything, the first changed decision is the **Taklons** seat in round 1, after the
research lab. Taklons are the one faction of the four whose guide list puts an academy opening first (1AC+2M, BGG 549
games, average 160) while the unpatched teacher remembers 1RL+2M; label_value keeps 1AC+2M because its forecast value is the
highest guide value at the start of the round. The 1AC+2M forecast never contains an academy (`r1_buildings` academy 0 in
every explain, `observed_completion` false; Taklons round-1 upgrades are TS and RL in all 12 seats, `upgrade_targets.py
--rounds 1-1`), so B holds an academy label over a lab-shaped plan — the 064–066 Geodens pattern on Taklons. The moves
themselves are then chosen by value_max over the completed comparisons, and the remembered label changes **which plans get
compared** inside the 20 s budget: in p004 A's set held the 236.0 academy-economy plan and B's did not; in p003 B completed
one comparison only. The one gain (p000 +78) came when B's 1AC+2M forecast turned into a 1RL+1TS+1M shape and the label
switched to it, which bought a second trading station the A side never built.

The other factions: the remembered label changed in Geodens p004 (1AC+1M → 1AC+2M), Terrans p004 and p005 (1RL+1M →
1AC+1M), Xenos p004 (1RL+4M → 1RL+5M), each **without any change of move**. Geodens round-1 upgrade paths are identical
A = B in all six pairs: academy in four (p001, p003, p004, p005 — both arms), lab stop in two where both arms' labels were
lab openings anyway (p000 1RL+1TS+2M, p002 1RL+3M). The 068 situation (an academy label kept while a PI plan forecasts
60 higher) did not arise on these seeds, so the question the run was built for was not exercised. Terrans round-1 paths
identical A = B (academy 1/6 both, p000).

Xenos (the 065 question): round-1 labels identical in five pairs, **1–3R Build 13 → 18** (065: 19 → 9), Upgrade 27 → 29,
no mine loss.

Rounds 1–3 research (`research_counts.py`), A → B: Geodens Gaia 8 → 12, AI 13 → 12; Taklons TF 4 → 3; Terrans AI 9 → 11,
TF 4 → 5; Xenos Nav 15 → 18, Eco 8 → 5, TF 1 → 3. Whole game: Taklons TF 7 → 14, Eco 12 → 5; Xenos TF 13 → 20, Eco 14 → 8;
Geodens TF 5 → 0. All within the three changed pairs plus round-4+ drift.

Rounds 1–3 actions (`action_counts.py`), A / B: Geodens Build 8 / 10, Upgrade 32 / 30; Taklons Build 13 / 10, Upgrade
26 / 25; Terrans Build 9 / 8; Xenos Build 13 / 18, Upgrade 27 / 29, asteroid 8 / 6; ship entries unchanged.

End-of-game board (`game_profile.py`, mean per seat), A → B: Geodens 71.0 → 76.7 (mines 3.2 → 4.0, mission VP 17.8 →
22.5, research VP 24.0 = 24.0); Taklons 74.8 → 81.5 (research-advance VP 1.7 → 5.8, artifacts 1.8 → 4.0, pass VP 7.3 →
4.3, levels 14.5 → 13.8); Terrans 76.5 → 75.2 (ship-action VP 6.8 → 1.8, upgrade VP 6.7 → 8.3); Xenos 126.8 → 130.5
(upgrade VP 22.3 → 15.3, federation VP 17.7 → 20.0, mission 28.7 → 31.7, feds 2.5 → 3.0).

Reading. The pre-set condition is met on the point estimates (charges +7.7, no Xenos loss, final VP +3.7), but the evidence
behind it is one pair: three pairs are the identical game through round 3, two are slightly negative, and all of the
+7.7 is pair-000, where a Taklons label switch bought a second trading station. The rule as written touches only the
Taklons round-1 play on these seeds (the guide-first academy opening whose forecast never reaches the academy), and there
its net is −0.6 with one +78 and two −32 / −50; what moved the result was not the label choice itself but the comparison
set that the remembered label pulls in under the time cap. The Geodens case it was built for (068 p001) did not occur in
six seeds, so the run neither confirms nor refutes that fix. Both CIs include zero. **Not proposed for the base stack on
this evidence**; the base stays vm_lf_ts_ships, ships_label_value stays opt-in, no code change, nothing to deploy. If the
user wants the pre-set condition honoured literally, the by-the-book next step is a fresh-seed re-check (6 pairs, full
game); the bot's reading is that a re-check would mostly re-measure drift and Taklons noise.

Candidate follow-ups (user decision pending, not queued; 079–082 are queued and run first, 079 started 01:42):
(a) close the label line — keep ships_label_value opt-in, no re-check; (b) by-the-book re-check with 6 fresh seeds,
full game, same measures (≈ 3 h 20 min), adopting only if charges stay positive on the 12-pair sum; (c) if the user wants
label_value to mean what it says, require the kept guide opening's forecast to **reach its target building** (academy
forecast must contain the academy) before its value may win — then Taklons 1AC+2M would not be kept on a lab rollout; this
is a scope change to the same rule, no new number, and would need its own A/B. The bot's recommendation is (a), and to
spend the next lab slot on the pending E9 (b) geodens_b14_tech alone or E7 (ships_land_safe) instead.
