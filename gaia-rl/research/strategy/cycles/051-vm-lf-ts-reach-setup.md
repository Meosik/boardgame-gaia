# Cycle 051 — setup parts alone (vm_lf_ts_reach_setup)

A: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-cap20.json` (047 B arm, same A as 048–050).
B: `teacher-a-search4-h1-guide-r1-charge3-lf-more-vm-lf-ts-reach-setup-cap20.json` — A + parts A and B of `install_reach`
only: setup decisions compare up to four distinct sites or boosters with a 50 s budget for setup only, and sites next to
an opponent are ordered first instead of the other sites being blocked.
Question (user, 2026-10-12 "부품 분리해서 원인 파악해"): part split 3 of 3 — do the setup parts carry any of the 048 loss?
Set before the run: judge by round 1–3 charges at 1 VP = 1.5 charges.
Same 6 seeds as 048 (geo-quartet-534437 … 536873) × 2 seat-swapped games, agentmaco, commit 3e32615, stop_round 3.
This is a cause-separation run on seeds already used, not a fresh-seed confirmation.
Result: lab/results/051-vm-lf-ts-reach-setup.md.

**Verdict measure: charges gained in rounds 1–3** (`charge_rounds.py`, 1 VP = 1.5).

| Faction | Pairs | A charges | B charges | B−A | 95% CI |
|---|---:|---:|---:|---:|---|
| Geodens | 6 | 147.5 | 186.1 | +38.6 | [−51.5, +128.7] |
| Taklons | 6 | 162.3 | 170.4 | +8.0 | [−14.4, +30.5] |
| Terrans | 6 | 158.0 | 187.2 | +29.2 | [−53.4, +111.8] |
| Xenos | 6 | 149.9 | 140.3 | −9.6 | [−34.4, +15.2] |
| **All** | 6 | | | **+16.6** | **[−11.7, +44.8]** |

Not significant; the direction is positive. Per-pair B−A from the seat list:

| Faction | p000 | p001 | p002 | p003 | p004 | p005 |
|---|---:|---:|---:|---:|---:|---:|
| Geodens | +136 | +85 | −116 | +11 | +55 | +61 |
| Taklons | −10 | +31 | −15 | +22 | −8 | +29 |
| Terrans | +117 | −4 | +30 | +98 | +38 | −103 |
| Xenos | −30 | −34 | +16 | +18 | −26 | −2 |
| Pair mean | +53.3 | +19.3 | −21.2 | +37.1 | +14.5 | −3.7 |

Four pair means are positive, two negative. Geodens is positive in 5 of 6 pairs, Terrans in 4, Taklons in 3, Xenos in 2.
The Geodens and Terrans means rest on a few very large swings in both directions: Geodens p000 (A 79 vs B 215) and
p002 (A 241 vs B 125), Terrans p000 (A 131 vs B 248), p003 (A 152 vs B 250) and p005 (A 209 vs B 106). Their intervals
are ±83–90, so neither faction's gain is established. Taklons is small and tight; Xenos is slightly negative.

Compared with 048–050 on the same seeds:

| Run | B parts | All | Taklons | Terrans | Geodens | Xenos |
|---|---|---:|---:|---:|---:|---:|
| 048 | setup + range +1 + focus (nav bug) | −10.9 | −24.8 | −38.4 | +17.7 | +2.0 |
| 049 | focus only (fixed) | −20.9 | −19.3 | −22.3 | −35.0 | −6.8 |
| 050 | range +1 only | −3.8 | +10.9 | −3.4 | −10.8 | −12.0 |
| 051 | setup only | +16.6 | +8.0 | +29.2 | +38.6 | −9.6 |

The setup parts do not reproduce the 048 Taklons and Terrans loss; both are positive here. Of the 048 negative pairs
p001–p003, only p002 is negative (−21, all of it Geodens). The three parts add up to about −8 (−20.9 − 3.8 + 16.6),
close to the 048 total of −10.9, which fits the reading that the research reorder (part D) is the source of the 048 loss
and the setup parts pulled the other way. As in 049 and 050 the A arm means move between runs on the same seeds, so
this cross-run sum is loose.

Research advances in rounds 1–3 (`research_counts.py --rounds 1-3`, sum over 6 seats):

| Arm | Faction | TF | Nav | AI | Gaia | Eco | Sci | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | Geodens | 3 | 2 | 15 | 4 | 3 | 3 | 30 |
| A | Taklons | 4 | 1 | 12 | 5 | 3 | 5 | 30 |
| A | Terrans | 5 | 0 | 14 | 3 | 4 | 4 | 30 |
| A | Xenos | 1 | 16 | 5 | 0 | 2 | 1 | 25 |
| B | Geodens | 0 | 3 | 14 | 8 | 5 | 3 | 33 |
| B | Taklons | 5 | 0 | 11 | 4 | 5 | 5 | 30 |
| B | Terrans | 3 | 1 | 13 | 1 | 5 | 5 | 28 |
| B | Xenos | 3 | 14 | 3 | 0 | 6 | 0 | 26 |

Research is nearly unchanged, as expected for a change that acts only in setup: navigation and AI stay where they are
for Taklons and Terrans. Geodens B takes Gaia more often (4 → 8) and terraforming less (3 → 0), which may follow from
different starting sites. Which sites and boosters B actually chose differently was not checked; `academy_rounds.py`
and `action_counts.py` are outside the bot's allowed tools.

VP held at round 4 (not used for the verdict): −0.4 [−5.1, +4.2].

| Arm | n | mean | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| A vm_lf_ts | 886 | 11.67 s | 18.27 s | 20.21 s | 23.3 s |
| B vm_lf_ts_reach_setup | 915 | 13.98 s | 18.30 s | 20.58 s | 52.5 s |

No errors, timeouts or fallback decisions. Unsearched decisions 614 vs 680. B is 1.20× slower on average; the maximum of
52.5 s is the 50 s setup budget overrunning by 2.5 s, inside the live hard wait limit of 60 s (048 reached 57.3 s).
Watch-replay publishing picked pair-000/game-1-A13 and failed again for the same reason as 048–050 (no `replay_income`
example binary in the lab checkout).

No change to the live teacher. The setup parts are the only one of the three reach parts with a positive direction, but
+16.6 at 6 pairs on reused seeds is inside the noise and driven by a handful of large Geodens and Terrans swings. It is
a candidate for a fresh-seed confirmation, not a result. The base stack remains vm_lf_ts until that is run; 052 (hard vs
vm_lf_ts, 12 fresh pairs) follows.
