# Cycle 049 — research focus alone, navigation fix (vm_lf_ts_reach_focus)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (047 B arm, same A as 048).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-focus-cap20.json` — A + part D of `install_reach` only:
research moves reordered (highest track at level 2+ first, otherwise navigation below 2 first), with the 048 bug fixed
(once navigation is 2 and no other track is at 2+, the other tracks come first and navigation last).
Question (user, 2026-10-12 "부품 분리해서 원인 파악해"): part split 1 of 3 — is the research reorder what cost Taklons and
Terrans in 048, and does the navigation fix bring them back to zero?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges.
Same 6 seeds as 048 (geo-quartet-534437 … 536873) × 2 seat-swapped games, agentmaco, commit 4f8bf5c, stop_round 3.
This is a cause-separation run on seeds already used, not a fresh-seed confirmation.
Result: lab/results/049-vm-lf-ts-reach-focus.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 162.3 | 127.3 | −35.0 | [−80.0, +10.0] |
| Taklons | 6 | 155.9 | 136.6 | −19.3 | [−44.8, +6.2] |
| Terrans | 6 | 159.0 | 136.6 | −22.3 | [−32.8, −11.9] |
| Xenos | 6 | 158.8 | 152.0 | −6.8 | [−63.5, +49.9] |
| **All** | 6 | | | **−20.9** | **[−32.4, −9.3]** |

Significantly negative. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | −24 | +24 | −103 | −56 | −39 | −13 |
| Taklons | −21 | −61 | −23 | +13 | −20 | −5 |
| Terrans | −24 | −37 | −12 | −10 | −26 | −26 |
| Xenos | −45 | −3 | +24 | −3 | +71 | −85 |
| Pair mean | −28.6 | −19.0 | −28.5 | −13.9 | −3.2 | −32.0 |

All six pair means are negative. Terrans is negative in 6 of 6 pairs (significant), Taklons and Geodens in 5 of 6. Xenos
swings ±70–85 per pair and is noise. p004 Geodens is low in both arms (A 72, B 34).

Compared with 048 on the same seeds: Taklons −24.8 → −19.3 and Terrans −38.4 → −22.3, so the fixed reorder alone still
carries most of their 048 loss. Geodens went from +17.7 (048, all four parts) to −35.0 (focus only). The A arm is the same
spec on the same seeds in both runs, yet its means moved (Xenos 125.6 → 158.8, Terrans 179.5 → 159.0) because the opposing
seats differ, so pair-by-pair comparison between the two runs is loose.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 6 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 0 | 1 | 13 | 6 | 4 | 2 | 26 |
| A | Taklons | 5 | 0 | 8 | 7 | 2 | 3 | 25 |
| A | Terrans | 4 | 1 | 15 | 1 | 4 | 4 | 29 |
| A | Xenos | 4 | 14 | 6 | 0 | 4 | 0 | 28 |
| B | Geodens | 0 | 7 | 5 | 3 | 5 | 1 | 21 |
| B | Taklons | 4 | 6 | 6 | 5 | 5 | 0 | 26 |
| B | Terrans | 7 | 8 | 4 | 1 | 4 | 3 | 27 |
| B | Xenos | 0 | 16 | 7 | 0 | 0 | 0 | 23 |

The navigation fix works as written: Taklons Nav 18 → 6 and Terrans 13 → 8 against 048 B, about one or two steps per seat
instead of every step. The loss stays anyway. What B gives up is AI (Geodens 13 → 5, Terrans 15 → 4) and Gaia, and Geodens
and Xenos research less in total (26 → 21, 28 → 23). An AI step pays a QIC at once, which the charge measure counts
(7 charges); a navigation step pays nothing at once and its range is only counted through reachable planets. Part of the
gap is therefore how the measure prices the tracks, not only weaker play — the run does not separate the two.
`academy_rounds.py` and `action_counts.py` were refused for the bot, so buildings and action counts were not checked.

VP held at round 4 (not used for the verdict): −2.2 [−6.0, +1.5].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 849 | 12.14 s | 20.00 s | 20.23 s | 24.1 s |
| B vm_lf_ts_reach_focus | 846 | 11.65 s | 17.97 s | 20.20 s | 22.7 s |

No errors, timeouts or fallback decisions. Unsearched decisions 607 vs 591. Watch-replay publishing picked
pair-002/game-0-A03 and failed again for the same reason as 048 (no `replay_income` example binary in the lab checkout).

No change to the live teacher. The research reorder (part D) lowers round 1–3 charges on its own, with or without the
navigation bug, so it stays out of the stack; the base stack remains vm_lf_ts. 050 (range +1) and 051 (setup parts) on the
same seeds will show whether the other parts are neutral.
